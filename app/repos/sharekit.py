import inspect
import requests
import json
import os
import logging
import functools
import time

log = logging.getLogger()


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


class Sharekit(object):

    def __init__(self, api_key, api_address=None, *args, **kwargs):
        self.sharekit_api_address = api_address
        if api_address is None:
            self.sharekit_api_address = os.getenv(
                "API_ADDRESS", "https://api.acc.surfsharekit.nl/api"
            )

        self.api_key = api_key

        # monkeypatching all functions with internals
        self.get_item = self.get_item_internal
        self.create_new_item = self.create_new_item_internal
        self.remove_item = self.remove_item_internal
        self.upload_new_file_to_item = self.upload_new_file_to_item_internal
        self.change_metadata_in_item = self.change_metadata_in_item_internal
        self.publish_item = self.publish_item_internal
        self.delete_all_files_from_item = (
            self.delete_all_files_from_item_internal
        )

    @classmethod
    def get_item(cls, api_key, *args, **kwargs):
        return cls(api_key, *args, **kwargs).get_item(*args, **kwargs)

    @classmethod
    def create_new_item(cls, api_key, *args, **kwargs):
        return cls(api_key, *args, **kwargs).create_new_item_internal(
            *args, **kwargs
        )

    @classmethod
    def remove_item(cls, api_key, *args, **kwargs):
        return cls(api_key, *args, **kwargs).remove_item(*args, **kwargs)

    @classmethod
    def upload_new_file_to_item(cls, api_key, *args, **kwargs):
        return cls(api_key, *args, **kwargs).upload_new_file_to_item(
            *args, **kwargs
        )

    @classmethod
    def change_metadata_in_item(cls, api_key, *args, **kwargs):
        return cls(api_key, *args, **kwargs).change_metadata_in_item_internal(
            *args, **kwargs
        )

    @classmethod
    def publish_item(cls, api_key, *args, **kwargs):
        return cls(api_key).publish_item(*args, **kwargs)

    @classmethod
    def delete_all_files_from_item(cls, api_key, *args, **kwargs):
        return cls(api_key).delete_all_files_from_item_internal(*args, **kwargs)

    @classmethod
    def check_token(cls, api_key, *args, **kwargs):
        """Check the API-Token `api_key`.

        Returns `True` if the token is correct and usable, otherwise `False`."""
        log.debug("Check token: Starts")
        r = cls(api_key, *args, **kwargs).get_format()
        log.debug(f"Check Token: Status Code: {r.status_code}")

        return r.status_code == 200

    @_rate_limit(per_second=5)
    def get_item_internal(
        self, id: int = None, return_response: bool = False, metadataFilter: dict = None
    ):
        """Get all items for the account, which owns the api-key.

        Args:
            id (int, optional): The item id. Defaults to None.
            return_response (bool, optional): Set to True will return the API response. Defaults to False.
            metadataFilter (dict, optional): filter for selecting what data needs to returned. Defaults to None.

        Returns:
            json: : API response if return_response is set to True

        Raises:
            NotImplementedError: This endpoint is not available in the sharekit API
        """
        log.debug(
            f"Entering at lib/upload_sharekit.py {inspect.getframeinfo(inspect.currentframe()).function}")
        raise NotImplementedError

    def create_new_item_internal(self, metadata=None, return_response=False):
        """Creates a new untitled item.

        Args:
            metadata (_type_, optional): Metadata for the item. Defaults to None.
            return_response (bool, optional): Set to True will return the API response. Defaults to False.

        Returns:
            json: API response if return_response is set to True
        """
        log.debug(
            f"Entering at lib/upload_sharekit.py {inspect.getframeinfo(inspect.currentframe()).function}")
        log.debug("### Create new item: Starts")

        r = self.create_item(metadata=metadata)

        log.debug(
            f"### Create new items: Status Code: {r.status_code}")

        if r.status_code != 201:
            return {} if not return_response else r

        return r.json() if not return_response else r

    def remove_item_internal(self, id, return_response=False):
        """Will remove an article based on it's id.

        Args:
            id (_type_): the item id
            return_response (bool, optional): Set to True will return the API response. Defaults to False.

        Raises:
            NotImplementedError: This endpoint is not available in the sharekit API
        """
        log.debug(
            f"Entering at lib/upload_sharekit.py {inspect.getframeinfo(inspect.currentframe()).function}")
        raise NotImplementedError

    def upload_new_file_to_item_internal(
        self, item_id, path_to_file, file=None, test=False
    ):
        """Uploads a file to an item on Sharekit.

        Args:
            item_id (int): id of the item to upload to (from get_item or create_new_item; r.json()['id'])
            path_to_file (str): path to the file to be uploaded. Example: ~/mydatapackage.csv
            file (bytes, optional): file as a bytes object. Defaults to None.

        Returns:
            bool: Alternative: json if return_response=True
        """
        log.debug(
            f"Entering at lib/upload_sharekit.py {inspect.getframeinfo(inspect.currentframe()).function}")
        try:
            upload_file_response = self.upload_file(
                file_path=path_to_file, file=file, item_id=item_id, test=test)
            # now create a repoItem with this file so user can see the file in Sharekit
            # the Sharekit API does not allow updating existing repoItems, so we need to create a new Item
            # for each file we upload
            # repo name will be filename
            if upload_file_response and upload_file_response.status_code < 300:
                fileId = upload_file_response.json()['data']['id']
                title = upload_file_response.json()['data']['attributes']['title']
                if title is None:
                    title = path_to_file
                files =  [
                            {
                                "fileId" : fileId,
                                "title" : title,
                                "access" : "restrictedaccess"
                            }
                        ]
                try:
                    self.create_item(files=files, metadata=None)
                except Exception as e:
                    log.error(
                            f"Exception calling create_item at lib/upload_sharekit.py in {inspect.getframeinfo(inspect.currentframe()).function}")
                    log.error(str(e)) 
                return True
        except Exception as e:
            log.error(
                f"Exception at lib/upload_sharekit.py {inspect.getframeinfo(inspect.currentframe()).function}")
            log.error(str(e))
            return False

    def get_files_from_item(self, item_id):
        """Not implemented

        Args:
            item_id (str): id of the item

        Raises:
            NotImplementedError: This endpoint is not available in the sharekit API
        """
        log.debug(
            f"Entering at lib/upload_sharekit.py {inspect.getframeinfo(inspect.currentframe()).function}")
        raise NotImplementedError

    def change_metadata_in_item_internal(
        self, item_id, metadata, return_response=False
    ):
        """Will update an item according to the provided metadata.

        Args:
            item_id (int): id of the item
            return_response (bool, optional): Set to True will return the API response. Defaults to False.
            metadata (dict): A data-dict json-like object
                ```python
                Example: data = {
                    'metadata': {
                        'title': 'My first upload',
                        'upload_type': 'poster',
                        'description': 'This is my first upload',
                        'creators': [{'name': 'Doe, John',
                                    'affiliation': 'Sharekit'}]
                    }
                }
                ```
        Raises:
            NotImplementedError: The update item endpoint is not available in the sharekit API
        """
        log.debug(
            f"Entering at lib/upload_sharekit.py {inspect.getframeinfo(inspect.currentframe()).function}")
        raise NotImplementedError

    def publish_item_internal(self, item_id, return_response=False):
        """Will publish an item if it is not under embargo

        Args:
            item_id (_type_): id of the item
            return_response (bool, optional): Set to True will return the API response. Defaults to False.

        Raises:
            NotImplementedError: This endpoint is not available in the sharekit API
        """
        log.debug(
            f"Entering at lib/upload_sharekit.py {inspect.getframeinfo(inspect.currentframe()).function}")
        raise NotImplementedError

    def delete_all_files_from_item_internal(self, item_id):
        """Will delete all files from an item.

        Args:
            item_id (int): id of an item

        Raises:
            NotImplementedError: This endpoint is not available in the sharekit API
        """
        log.debug(
            f"Entering at lib/upload_sharekit.py {inspect.getframeinfo(inspect.currentframe()).function}")
        raise NotImplementedError

    def delete_file_from_item_internal(self, item_id, file_id):
        """Will delete a file from an item

        Args:
            item_id (int): id of the item
            file_id (int): id of file

        Raises:
            NotImplementedError: This endpoint is not available in the sharekit API
        """
        log.debug(
            f"Entering at lib/upload_sharekit.py {inspect.getframeinfo(inspect.currentframe()).function}")
        raise NotImplementedError

    ### Start Implementation based on Surf Sharekit API ###

    def upload_file(self, file_path):
        """Uploads a file using the sharekit upload endpoint

        Args:
            file_path (str): the path of the file, usually also the file name
        Returns:
            response: the unaltered response of the upload endpoint
        """
        url = f"{self.sharekit_api_address}/repoitemupload/v1/upload"
        log.debug(f"### upload url: {url}")
       
        payload = {}
        log.debug(f"### payload: {payload}")

        files = [('file', open(file_path, 'rb'))]
        log.debug(f"### files: {files}")

        headers = {'Authorization': f'Bearer {self.api_key}'}
        log.debug(f"### headers: {headers}")

        response = requests.request(
            "POST", url, headers=headers, data=payload, files=files)
        
        log.debug(response.status_code)
        if response.status_code < 300:
            rjson = response.json()
            log.error(f"### response: {rjson}")
            
        return response

    def get_format(self):
        """Calls the format endpoint and returns information on the possible meta field for uploads

        Returns:
            json: data structure with info on possible meta fields for uploads
        """
        url = f"{self.sharekit_api_address}/repoitemupload/v1/format"
        payload = {}
        headers = {'Authorization': f'Bearer {self.api_key}'}
        response = requests.request("GET", url, headers=headers, data=payload)
        return response

    def get_institute_id(self):
        """Gets the institute id for the current user

        Returns:
            str: id of the institute
        """
        # This basically gets the first institute in a list of institutes that the api-key account has access to.
        # As the api-key is application specific and not user specific, many institutes can be returned
        # what we need is the institute id of that matches with the institute of the user.

        response = self.get_format()
        return response.json()['institute']['options'][0]['value']

    def create_item(self, files=[], metadata=None):
        """Creates a new sharekit item.

        Args:
            files (list, optional): The files it is the container of. Defaults to [].
            metadata (dict, optional): Metadata for the item. Defaults to None.

        Returns:
            response: the response of the API call at endpoint create
        """
        try:
            log.debug("create_item")
            log.debug(files)
            log.debug(metadata)
            if files is not None and isinstance(files, list) and len(files)==1:
                log.debug(f"files: {files}")
                try:
                    title = "File uploaded by SurfRDC: {}".format(files[0]['title'])
                except:
                    title = "File uploaded by SurfRDC"
            else:
                title = "Item created by SurfRDC"
            summary = "This item was automatically created by SurfRDC."
            if metadata is not None and isinstance(metadata, dict):
                log.debug(f"### Metadata in create item: {metadata}")
                try:
                    title = metadata["title"]
                except:
                    pass
                try:
                    summary = metadata["description"]
                except:
                    pass

            url = f"{self.sharekit_api_address}/repoitemupload/v1/create"
            payload = json.dumps({
                "type": "ResearchObject",
                "title": title,
                "summary": summary,
                "institute": f"{self.get_institute_id()}",
                "files": files
            })
            log.debug(f"### create_item payload:{payload}")
            headers = {'Authorization': f'Bearer {self.api_key}'}
            response = requests.request("POST", url, headers=headers, data=payload)
            rjson = response.json()
            log.debug(f"### create_item response:{rjson}")
            return response
        except Exception as e:
            log.error(f"Unhandled exception occured at create_item: {e}")
            
    ### End Implementation based on Surf Sharekit API ###

    ############ For downloads ###################

    def get_repo_content(self, article_id):
        return [{'message' : 'getting repo content not implemented'}]


    def get_private_metadata(self, article_id):
        return {'message' : 'getting private metadata not implemented'}


    def download_files(self, article_id, dest_folder):
        return 'downloading files not implemented'



if __name__ == "__main__":
    """Below code will test the code that interfaces the uploads to Sharekit
    """
    api_key = ""
    api_address = "https://api.acc.surfsharekit.nl/api"
    sharekit = Sharekit(api_key=api_key, api_address=api_address)
    print(sharekit.get_format().json())

    path_to_file = "./app/static/img/sharekit.png"
    path_to_file = "./app/repos/ro-crate-metadata.json"

    # act
    response = sharekit.upload_file(file_path=path_to_file)

    print(response)
    print(response.status_code)
    print(response.data)

    # first upload the file
    # file_path = "../sharekit.png"
    # file_path = "../../coverage.xml"
    # upload_file_response = sharekit.upload_file(file_path, test=True)
    # print(upload_file_response.text)

    # then create an item that will contain / reference the uploaded file(s)
    # fileId = upload_file_response.json()['data']['id']
    # files = [
    #     {
    #         "fileId": fileId,
    #         "title": file_path,
    #         "access": "closedAccess"
    #     }
    # ]
    # result = sharekit.create_item(files=files)
    # print(result.json())
    format = {'title': {'type': 'text', 'labelNL': 'Titel', 'labelEN': 'Title', 'isRequired': 1, 'regex': None, 'options': []},
                'type': {'type': 'string', 'labelNL': 'RepoType', 'labelEN': 'RepoType', 'isRequired': 1, 'regex': None, 'options': ['PublicationRecord', 'LearningObject', 'ResearchObject', 'Dataset', 'Project']},
                'institute': {'type': 'uuid', 'labelNL': 'InstituteID', 'labelEN': 'InstituteID', 'isRequired': 1, 'regex': None, 'options': [{'value': '1cb21e78-6d07-4d21-ba5d-f722dd2ba1bd', 'title': 'SURF edusources test'}]},
                'subtitle': {'type': 'text', 'labelNL': 'Ondertitel', 'labelEN': 'Subtitle', 'isRequired': 0, 'regex': None, 'options': []},
                'summary': {'type': 'textarea', 'labelNL': 'Samenvatting', 'labelEN': 'Summary', 'isRequired': 0, 'regex': None, 'options': []},
                'files': {'type': 'attachment', 'labelNL': 'Bestand', 'labelEN': 'File', 'isRequired': 1, 'regex': None, 'options': []}}


    data = {
            'data': {
                'attributes': {
                               'url': 'https://api.acc.surfsharekit.nl/api/v1/files/repoItemFiles/53674d05-71a8-4d6a-a45b-892b4106f6ba',
                               'title': None,
                               'permissions': {'canView': True}
                                },
                'type': 'repoItemFile',
                'id': '53674d05-71a8-4d6a-a45b-892b4106f6ba'
                }
            }
