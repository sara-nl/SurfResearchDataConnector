import requests
import json
import os
import logging
from flask import abort
import functools
import time

log = logging.getLogger()

timeout = 100

def _rate_limit(func=None, per_second=1):
    """Limit number of requests made per second.

    Will sleep for 1/``per_second`` seconds if the last request was
    made too recently.
    """

    if not func:
        return functools.partial(_rate_limit, per_second=per_second)

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if hasattr(self, "last_request") and self.last_request is not None:
            now = time.time()
            delta = now - self.last_request
            if delta < (1 / per_second):
                waittimer = (1 / per_second) - delta
                log.debug("rate limiter wait for {}ms", waittimer)
                time.sleep(waittimer)

        self.last_request = time.time()
        return func(self, *args, **kwargs)

    return wrapper


class Zenodo(object):

    def __init__(self, api_key, api_address=None, *args, **kwargs):
        if api_address is None:
            self.zenodo_address = os.getenv(
                "ZENODO_API_URL", "https://sandbox.zenodo.org"
            ).split("/api")[0]
        else:
            self.zenodo_address = api_address.split("/api")[0]
        self.api_key = api_key

        # monkeypatching all functions with internals
        self.get_deposition = self.get_deposition_internal
        self.create_new_deposition = self.create_new_deposition_internal
        self.remove_deposition = self.remove_deposition_internal
        self.upload_new_file_to_deposition = self.upload_new_file_to_deposition_internal
        self.change_metadata_in_deposition = self.change_metadata_in_deposition_internal
        self.publish_deposition = self.publish_deposition_internal
        self.delete_all_files_from_deposition = (
            self.delete_all_files_from_deposition_internal
        )

    def check_token(self):
        """Check the API-Token `api_key`.

        Returns `True` if the token is correct and usable, otherwise `False`."""
        log.debug("Check token: Starts")
        r = self.get_deposition_internal(return_response=True)
        log.debug("Check Token: Status Code: {}".format(r.status_code))

        return r.status_code == 200

    @_rate_limit(per_second=5)
    def get_deposition_internal(
        self, id: int = None, return_response: bool = False, metadataFilter: dict = None
    ):
        """ Require: None
                Optional return_response: For testing purposes, you can set this to True.

            Returns: json, Alternative: request if return_response=True

            Description: Get all depositions for the account, which owns the api-key."""

        log.debug(
            f"get depositions from zenodo, id? {id}, return response? {return_response}, metadata? {metadataFilter}"
        )
        headers = {"Authorization": f"Bearer {self.api_key}"}
        log.debug("set header, now requests")

        if id is not None:
            r = requests.get(
                f"{self.zenodo_address}/api/deposit/depositions/{id}",
                headers=headers,
                verify=(os.environ.get("VERIFY_SSL", "True") == "True"),
                timeout=timeout
            )
        else:
            r = requests.get(
                f"{self.zenodo_address}/api/deposit/depositions",
                headers=headers,
                verify=(os.environ.get("VERIFY_SSL", "True") == "True"),
                timeout=timeout
            )
            log.debug(
                "Get Depositions: Status Code: {}".format(r.status_code))

        if return_response:
            return r

        if r.status_code >= 300:
            abort(r.status_code)

        result = r.json()

        if id is not None:
            result = [result]
        log.debug(f"filter only metadata, {result}")

        metadataList = []
        for res in result:
            if (
                "submitted" in res
                and res["submitted"]
                or "submitted" in res["metadata"]
                and res["metadata"]["submitted"]
            ):
                continue

            metadataList.append(res["metadata"])

        result = metadataList

        log.debug("apply filter")
        if metadataFilter is not None:
            result = {
                key: res[key]
                for res in result
                for key in metadataFilter.keys()
                if key in res
            }

        log.debug("finished applying filter")

        log.debug("return results")

        if id is not None:
            return result[0]

        return result

    def create_new_deposition_internal(self, metadata=None, return_response=False):
        """
        Require: None
        Returns: Boolean, Alternative: json if return_response=True
        Description: Creates a new deposition. You can get the id with r.json()['id']
        If metadata is specified, it will changes metadata after creating.
        """
        log.debug("Create new deposition: Starts")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        r = requests.post(
            f"{self.zenodo_address}/api/deposit/depositions",
            json={},
            headers=headers,
            verify=(os.environ.get("VERIFY_SSL", "True") == "True"),
            timeout=timeout
        )

        log.debug(
            "Create new deposition: Status Code: {}".format(r.status_code))

        if r.status_code != 200:
            return {} if not return_response else r

        if metadata is not None and isinstance(metadata, dict):
            return self.change_metadata_in_deposition(
                r.json()["id"], metadata, return_response=return_response
            )

        return r.json() if not return_response else r

    def remove_deposition_internal(self, id, return_response=False):
        r = requests.delete(
            f"{self.zenodo_address}/api/deposit/depositions/{id}",
            headers={"Authorization": f"Bearer {self.api_key}"},
            verify=(os.environ.get("VERIFY_SSL", "True") == "True"),
            timeout=timeout
        )

        return r.status_code == 201 if not return_response else r

    def upload_new_file_to_deposition_internal(
        self, deposition_id, path_to_file, file=None, return_response=False
    ):
        """
        Require:
            A deposit id (from get_deposition or create_new_deposition; r.json()['id'])
            A path to a file
                Example: ~/mydatapackage.csv
        Returns: Boolean, Alternative: json if return_response=True
        Description: Upload one(!) file to the deposition_id. This is a restriction from zenodo.
        (More: https://developers.zenodo.org/#deposition-files)
        """

        from werkzeug.utils import secure_filename

        from io import IOBase

        filename = secure_filename(os.path.basename(path_to_file))
        data = {"name": filename}

        try:
            if file is None:
                raise Exception("File is none.")

            from io import BytesIO

            log.debug("Try read the file content.")
            files = {"file": (filename, BytesIO(file.read()))}
            log.debug("size: {}".format(len(file.read())))
        except Exception as e:
            log.error(e)
            log.debug("Cannot read the content. So maybe it is in cache?")
            # for temporary files
            files = {"file": (filename, open(
                os.path.expanduser(path_to_file), "rb"))}

        log.debug(
            "Submit the following informations to zenodo.\nData: {}, Files: {}".format(
                data, files
            )
        )

        r = requests.post(
            f"{self.zenodo_address}/api/deposit/depositions/{deposition_id}/files",
            headers={"Authorization": f"Bearer {self.api_key}"},
            data=data,
            files=files,
            verify=(os.environ.get("VERIFY_SSL", "True") == "True"),
            timeout=timeout
        )

        log.debug("Content: {}".format(r.content))

        return r.status_code == 201 if not return_response else r

    def get_files_from_deposition(self, deposition_id):
        req = requests.get(
            f"{self.zenodo_address}/api/deposit/depositions/{deposition_id}/files",
            headers={"Authorization": f"Bearer {self.api_key}"},
            verify=(os.environ.get("VERIFY_SSL", "True") == "True"),
            timeout=timeout
        )

        result = req.json()

        return result

    def change_metadata_in_deposition_internal(
        self, deposition_id, metadata, return_response=False
    ):
        """
        Require:
            A deposit id (from get_deposition or create_new_deposition; r.json()['id'])

            A data-dict json-like object
                ```python
                Example: data = {
                    'metadata': {
                        'title': 'My first upload',
                        'upload_type': 'poster',
                        'description': 'This is my first upload',
                        'creators': [{'name': 'Doe, John',
                                    'affiliation': 'Zenodo'}]
                    }
                }
                ```
            Returns:
            Description: Set the metadata to the given data or changes the values to the corresponding keys.
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        data = {}
        data["metadata"] = metadata

        r = requests.put(
            f"{self.zenodo_address}/api/deposit/depositions/{deposition_id}",
            data=json.dumps(data),
            headers=headers,
            verify=(os.environ.get("VERIFY_SSL", "True") == "True"),
            timeout=timeout
        )
        
        return r.status_code == 200 if not return_response else r

    def publish_deposition_internal(self, deposition_id, return_response=False):
        r = requests.post(
            f"{self.zenodo_address}/api/deposit/depositions/{deposition_id}/actions/publish",
            headers={"Authorization": f"Bearer {self.api_key}"},
            verify=(os.environ.get("VERIFY_SSL", "True") == "True"),
            timeout=timeout
        )

        return r.status_code == 202 if not return_response else r

    def delete_all_files_from_deposition_internal(self, deposition_id):
        for file in self.get_files_from_deposition(deposition_id):
            log.debug("found file: {}".format(file))

            if not self.delete_file_from_deposition_internal(deposition_id, file["id"]):
                return False

        return True

    def delete_file_from_deposition_internal(self, deposition_id, file_id):
        r = requests.delete(
            "{}/api/deposit/depositions/{}/files/{}".format(
                self.zenodo_address, deposition_id, file_id
            ),
            headers={"Authorization": f"Bearer {self.api_key}"},
            verify=(os.environ.get("VERIFY_SSL", "True") == "True"),
            timeout=timeout
        )

        if r.status_code < 300:
            return True

        return False

    ############ For downloads ###################

    def get_repo_content(self, deposition_id):
        """Get private repo content AKa list of files to be downloaded from the repo

        Args:
            deposition_id (int): the id of the article that contains the files

        Returns:
            list: list of all the files information: name, size, link, hash, and hash_type
        """
        files = self.get_files_from_deposition(deposition_id=deposition_id)

        # if files cannot be retrieved then try to get as public article
        # if 'message' in files and files['message'] == 'Insufficient permissions':
        #     files = self.get_files_from_article(article_id=article_id, public=True)
        
        file_content = []
        for file in files:
            tmp = {}
            tmp['name'] = file['filename']
            tmp['size'] = file['filesize']
            tmp['link'] = file['links']['download']
            tmp['hash'] = file['checksum']
            tmp['hash_type'] = 'md5'
            file_content.append(tmp)
        return file_content


    def get_private_metadata(self, deposition_id):
        """Will get private metadata for a particular article

        Args:
            article_id (int): the id of the article

        Returns:
            dict: flat key value store with keys being the metadata field names and the values the metadata field values.
        """
        result = self.get_deposition(return_response=True, id=deposition_id)
        result = result.json()
        return result        

    def download_files(self, deposition_id, dest_folder):
        """Will download all files for a specific article to a folder

        Args:
            deposition_id (int): the id of the article
            dest_folder (str): the folder path to download to

        Returns:
            bool: returns True if download was succesful
        """
        try:
            if not os.path.exists(dest_folder):
                os.makedirs(dest_folder)  # create folder if it does not exist
            file_content = self.get_repo_content(deposition_id)
            for item in file_content:
                filename = item['name']
                
                # filenames can contain a path as well
                # we need to create that part of the path as well
                # so check for '/' in the filename
                if filename.find("/") != -1:
                    additional_path = filename.split('/')
                    # drop last one as that is the filename
                    filename = additional_path.pop()
                    additional_path = "/".join(additional_path)
                    total_path = os.path.join(dest_folder, additional_path)
                    if not os.path.exists(total_path):
                        os.makedirs(total_path)  # create folder if it does not exist
                    file_path = os.path.join(total_path, filename)
                else:
                    file_path = os.path.join(dest_folder, filename)
                link = item['link']
                r = requests.get(link,
                                headers={'Authorization': f"Bearer {self.api_key}"},
                                stream=True)
                print(r)
                if r.ok:               
                    with open(file_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=1024 * 8):
                            if chunk:
                                f.write(chunk)
                                f.flush()
                                os.fsync(f.fileno())

                else:  # HTTP status code 4XX/5XX
                    return 'could not get link to file'
            return True
        except Exception as e:
            return str(e)


if __name__ == "__main__":
    pass
