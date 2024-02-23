import inspect
from io import BytesIO, StringIO
import json
import os
import logging
import requests
from flask import abort
import functools
import time
from irods.session import iRODSSession
from irods.meta import iRODSMeta
from RDS import ROParser

try:
    from app.globalvars import irods_zone, irods_base_folder
except:
    # for testing this file locally
    import sys
    sys.path.append('../')
    from globalvars import irods_zone, irods_base_folder
    print("testing")

ssl_settings = {'client_server_negotiation': 'request_server_negotiation',
                'client_server_policy': 'CS_NEG_REQUIRE',
                'encryption_algorithm': 'AES-256-CBC',
                'encryption_key_size': 32,
                'encryption_num_hash_rounds': 16,
                'encryption_salt_size': 8,
                }

zone = os.getenv("ZONE", irods_zone)
folder = os.getenv("BASE_FOLDER", irods_base_folder)

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


class Irods(object):

    def __init__(self, api_key, user, api_address=None, *args, **kwargs):
        self.file_content = []
        self.irods_api_address = api_address
        if api_address is None:
            self.irods_api_address = os.getenv(
                "API_ADDRESS", "surf-yoda.irods.surfsara.nl"
            )

        self.api_key = api_key
        self.user = user

        # monkeypatching all functions with internals
        self.get_collection = self.get_collection_internal
        self.create_new_collection = self.create_new_collection_internal
        self.remove_collection = self.remove_collection_internal
        self.upload_new_file_to_collection = self.upload_new_file_to_collection_internal
        self.change_metadata_in_collection = self.change_metadata_in_collection_internal
        self.publish_collection = self.publish_collection_internal
        self.delete_all_files_from_collection = (
            self.delete_all_files_from_collection_internal
        )

    @classmethod
    def get_collection(cls, api_key, *args, **kwargs):
        return cls(api_key, *args, **kwargs).get_collection(*args, **kwargs)

    @classmethod
    def create_new_collection(cls, api_key, *args, **kwargs):
        return cls(api_key, *args, **kwargs).create_new_collection_internal(
            *args, **kwargs
        )

    @classmethod
    def remove_collection(cls, api_key, *args, **kwargs):
        return cls(api_key, *args, **kwargs).remove_collection(*args, **kwargs)

    @classmethod
    def upload_new_file_to_collection(cls, api_key, *args, **kwargs):
        return cls(api_key, *args, **kwargs).upload_new_file_to_collection(
            *args, **kwargs
        )

    @classmethod
    def change_metadata_in_collection(cls, api_key, *args, **kwargs):
        return cls(api_key, *args, **kwargs).change_metadata_in_collection_internal(
            *args, **kwargs
        )

    @classmethod
    def publish_collection(cls, api_key, *args, **kwargs):
        return cls(api_key).publish_collection(*args, **kwargs)

    @classmethod
    def delete_all_files_from_collection(cls, api_key, *args, **kwargs):
        return cls(api_key).delete_all_files_from_collection_internal(*args, **kwargs)

    @classmethod
    def check_token(cls, api_key, *args, **kwargs):
        """Check the API-Token `api_key`.

        Returns `True` if the token is correct and usable, otherwise `False`."""
        try:
            r = cls(api_key, *args, **kwargs).get_collection()
            return True
        except Exception as e:
            log.error(e)
            return False

    @_rate_limit(per_second=5)
    def get_collection_internal(
        self, path: str = None, metadataFilter: dict = None
    ):
        """Get all collections for the account, which owns the api-key.

        Args:
            path (str, optional): The collection path. Defaults to None.
            metadataFilter (dict, optional): filter for selecting what data needs to returned. Defaults to None.
                                                Currently not implemented.

        Returns:
            list: : List of paths of sub collections
        """
        log.debug(
            f"Entering at lib/upload_irods.py {inspect.getframeinfo(inspect.currentframe()).function}")
        log.debug(
            f"get collections from irods, path? {path}, metadata? {metadataFilter}"
        )
 
        try:
            if path is None:
                path = f"/{zone}/home"

            with iRODSSession(host=self.irods_api_address,
                            port=1247,
                            user=self.user,
                            password=self.api_key,
                            zone=zone,
                            authentication_scheme='pam',
                            **ssl_settings) as irods_session:

                coll = irods_session.collections.get(path)
                if len(coll.subcollections) > 0:
                    available_collections = []
                    for col in coll.subcollections:
                        available_collection = {'create_time': str(col.create_time),
                                                'data_objects': [data_object.id for data_object in col.data_objects],
                                                'id': col.id,
                                                'inheritance': str(col.inheritance),
                                                'manager': col.manager.get(col.path).id,
                                                'metadata': {key: col.metadata.get_all(key)[0].value for key in col.metadata.keys()},
                                                'modify_time': str(col.modify_time),
                                                'name': str(col.name),
                                                'owner_name': str(col.owner_name),
                                                'owner_zone': str(col.owner_zone),
                                                'path': str(col.path),
                                                'subcollections': [col.path for col in col.subcollections]
                                                }
                        available_collections.append(available_collection)
                    return available_collections
                else:
                    available_collection = {'create_time': str(coll.create_time),
                                            'data_objects': [data_object.id for data_object in coll.data_objects],
                                            'id': coll.id,
                                            'inheritance': str(coll.inheritance),
                                            'manager': coll.manager.get(coll.path).id,
                                            'metadata': {key: coll.metadata.get_all(key)[0].value for key in coll.metadata.keys()},
                                            'modify_time': str(coll.modify_time),
                                            'name': str(coll.name),
                                            'owner_name': str(coll.owner_name),
                                            'owner_zone': str(coll.owner_zone),
                                            'path': str(coll.path),
                                            'subcollections': []
                                            }
                    return available_collection
        except Exception as e:
            log.error(f'exception at irods get_collection_internal: {e}')


    def create_new_collection_internal(self, metadata: dict = None):
        """Creates a new untitled collection.
        If metadata is specified, it will changes metadata after creating.

        Args:
            metadata (dict, optional): Metadata for the collection. Defaults to None.

        Returns:
            json: API response
        """
        log.debug(
            f"Entering at lib/upload_irods.py {inspect.getframeinfo(inspect.currentframe()).function}")
        log.debug("Create new collection: Starts")

        try:
            if metadata is not None and 'title' in metadata:
                title = metadata['title']
                path = f"/{zone}/home/{folder}/{title}-{str(time.time()).replace('.','')}"
            else:
                path = f"/{zone}/home/{folder}/SurfRDC-Upload-{str(time.time()).replace('.','')}"

            with iRODSSession(host=self.irods_api_address,
                            port=1247,
                            user=self.user,
                            password=self.api_key,
                            zone=zone,
                            authentication_scheme='pam',
                            **ssl_settings) as irods_session:
                coll = irods_session.collections.create(path)

            available_collection = {'create_time': str(coll.create_time),
                                    'data_objects': [data_object.id for data_object in coll.data_objects],
                                    'id': coll.id,
                                    'inheritance': str(coll.inheritance),
                                    'manager': coll.manager.get(coll.path).id,
                                    'metadata': {key: coll.metadata.get_all(key)[0].value for key in coll.metadata.keys()},
                                    'modify_time': str(coll.modify_time),
                                    'name': str(coll.name),
                                    'owner_name': str(coll.owner_name),
                                    'owner_zone': str(coll.owner_zone),
                                    'path': str(coll.path),
                                    'subcollections': [coll.path for col in coll.subcollections]
                                    }

            log.debug(f"Metadata: {metadata}")
            if metadata is not None and isinstance(metadata, dict):
                log.debug(metadata)
                self.change_metadata_in_collection_internal(
                    coll.path, metadata
                )

            return available_collection
        except Exception as e:
            log.error(f'exception at irods create_new_collection_internal: {e}')


    def remove_collection_internal(self, path: str):
        """Will remove an collection based on it's path.

        Args:
            path (str): the collection path

        Returns:
            json: API response
        """
        log.debug(
            f"Entering at lib/upload_irods.py {inspect.getframeinfo(inspect.currentframe()).function}")
        try:
            with iRODSSession(host=self.irods_api_address,
                              port=1247,
                              user=self.user,
                              password=self.api_key,
                              zone=zone,
                              authentication_scheme='pam',
                              **ssl_settings) as irods_session:
                r = irods_session.collections.remove(path=path)
            if r is None:
                return True
        except:
            return False


    def create_yoda_metadata(self, path, metadata=None):
        """for Yoda: create yoda-metadata.json file and upload it

        Args:
            path (str): path of the irods collection
            metadata (dict, optional): The metadata from irods. Defaults to None.

        Returns:
            json: yoda metadata
        """
        try:
            yodametadata = {}

            yodametadata["links"] = [
                {
                    "rel": "describedby",
                    "href": "https://yoda.uu.nl/schemas/default-2/metadata.json"
                }
            ]

            url = yodametadata["links"][0]["href"]
            schema = requests.get(url).json()

            # set default language
            yodametadata["Language"] = "en - English"
            # overwrite default if correctly specified in metadata
            if "Language" in metadata:
                if metadata['Language'] in schema["definitions"]["optionsISO639-1"]["enum"]:
                    yodametadata["Language"] = metadata['Language']

            # setting some fixe parameters for now
            yodametadata["Collected"] = {}
            yodametadata["Covered_Period"] = {}
            yodametadata["Related_Datapackage"] = [
                {
                    "Persistent_Identifier": {}
                }
            ]
            yodametadata["Retention_Period"] = 10
            yodametadata["Data_Type"] = "Dataset"

            try:
                Funder_Name = " ".join(metadata["funder"])
                yodametadata["Funding_Reference"] = [{"Funder_Name": Funder_Name}]
            except:
                pass

            yodametadata["Data_Access_Restriction"] = "Closed"
            yodametadata["Data_Classification"] = "Basic"
            yodametadata["License"] = "Custom"

            # set discipline only of correctly specified
            if "Discipline" in metadata:
                if metadata['Discipline'] in schema["definitions"]["optionsDiscipline"]["enum"]:
                    yodametadata["Discipline"] = [
                        metadata['Discipline']
                    ]

            # set tag if specified in metadata
            if "keywords" in metadata:
                yodametadata["Tag"] = metadata["keywords"].split(", ")

            # set creator
            try:
                yodametadata["Creator"] = [
                    {"Person_Identifier": [{}]}
                ]
                try:
                    Creator_Name = metadata["author"]
                    Given_Name = Creator_Name.split()[0].strip()
                    Family_Name = Creator_Name.split(Given_Name)[1].strip()
                    yodametadata["Creator"][0]["Name"] = {
                            "Given_Name": Given_Name,
                            "Family_Name": Family_Name
                        }
                except Exception as e:
                    logger.error(e)
                try:
                    Creator_Affiliation = metadata["publisher"]
                    yodametadata["Creator"][0]["Affiliation"] = [
                        Creator_Affiliation
                    ]
                except:
                    pass
            except:
                pass


            # set contributor
            try:
                yodametadata["Contributor"] = [
                    {"Person_Identifier": [{}]}
                ]
                try:
                    Contributor_Name = metadata["contributor"][0]
                    Given_Name = Contributor_Name.split()[0].strip()
                    Family_Name = Contributor_Name.split(Given_Name)[1].strip()
                    yodametadata["Contributor"][0]["Name"] = {
                            "Given_Name": Given_Name,
                            "Family_Name": Family_Name
                        }
                except:
                    pass
                try:
                    Contributor_Affiliation = metadata["contributor"][1]
                    yodametadata["Contributor"][0]["Affiliation"] = [
                        Contributor_Affiliation
                    ]
                except:
                    pass
            except:
                pass

            # set title
            try:
                yodametadata["Title"] = metadata["title"]
            except:
                pass

            # set description
            try:
                yodametadata["Description"] = metadata["description"]
            except:
                pass

            yodametadata = json.dumps(yodametadata)

            return yodametadata
        except Exception as e:
            log.error(f'exception at irods create_yoda_metadata: {e}')


    def upload_new_file_to_collection_internal(
        self, path, path_to_file, file=None, test=False
    ):
        """Uploads a file to an collection on Irods.

        Args:
            path (str): path of the collection to upload to
            path_to_file (str): path to the file to be uploaded. Example: ~/mydatapackage.csv
            file (bytes, optional): file as a bytes object. Defaults to None.

        Returns:
            json: Response Data of irods API
        """
        log.debug(
            f"Entering at lib/upload_irods.py {inspect.getframeinfo(inspect.currentframe()).function}")
        try:

            with iRODSSession(host=self.irods_api_address,
                              port=1247,
                              user=self.user,
                              password=self.api_key,
                              zone=zone,
                              authentication_scheme='pam',
                              **ssl_settings) as irods_session:
                irods_session.connection_timeout = 300
                # create a relative path if the file is in a subfolder
                # basically ignore the first folder. Any subsequent folders need to be created under the path
                file_path = path_to_file.split("/")
                subfolders = file_path[2:-1]
                if len(subfolders) > 0:
                    # create subfolders
                    for folder in subfolders:
                        irods_session.collections.create(f"{path}/{folder}")
                    subfoldersstring = "/".join(subfolders)
                    path = f"{path}/{subfoldersstring}"
                irods_session.data_objects.put(path_to_file, path)
            return True
        except Exception as e:
            log.error(
                f"Exception at lib/upload_irods.py {inspect.getframeinfo(inspect.currentframe()).function}")
            log.error(str(e))
            return False


    def get_files_from_collection(self, path):
        """will get all the files from the collection requested.

        Args:
            path (str): path of the collection

        Returns:
            list: list containing all the file paths from the collection
        """
        log.debug(
            f"Entering at lib/upload_irods.py {inspect.getframeinfo(inspect.currentframe()).function}")
        try:
            with iRODSSession(host=self.irods_api_address,
                            port=1247,
                            user=self.user,
                            password=self.api_key,
                            zone=zone,
                            authentication_scheme='pam',
                            **ssl_settings) as irods_session:
                coll = irods_session.collections.get(path)
                result = []
                for obj in coll.data_objects:
                    result.append(obj.path)
            return result
        except Exception as e:
            log.error(f'exception at irods get_files_from_collection: {e}')


    def change_metadata_in_collection_internal(
        self, path, metadata
    ):
        """Will update an collection according to the provided metadata.

        Args:
            collection_id (int): id of the collection
            return_response (bool, optional): Set to True will return the API response. Defaults to False.
            metadata (dict): A data-dict json-like object
                ```python
                Example: data = {
                    'metadata': {
                        'title': 'My first upload',
                        'upload_type': 'poster',
                        'description': 'This is my first upload',
                        'creators': [{'name': 'Doe, John',
                                    'affiliation': 'Irods'}]
                    }
                }
                ```
        Returns:
            object: response of the PUT request to the collections endpoint
        """
        log.debug(
            f"Entering at lib/upload_irods.py {inspect.getframeinfo(inspect.currentframe()).function}")
        try:
            with iRODSSession(host=self.irods_api_address,
                            port=1247,
                            user=self.user,
                            password=self.api_key,
                            zone=zone,
                            authentication_scheme='pam',
                            **ssl_settings) as irods_session:
                irods_session.connection_timeout = 300

                obj = irods_session.collections.get(path)

                # loop through the metadata and add each item
                for key, value in metadata.items():
                    try:
                        obj.metadata.remove(key)
                    except:
                        pass
                    try:
                        obj.metadata.add(key, value)
                    except:
                        pass

            return self.get_collection_internal(path)
        except Exception as e:
            log.error(f'exception at irods change_metadata_in_collection_internal: {e}')


    def publish_collection_internal(self, collection_id, return_response=False):
        """Will publish an collection if it is not under embargo

        Args:
            collection_id (_type_): id of the collection
            return_response (bool, optional): Set to True will return the API response. Defaults to False.

        Returns:
            object: response of the POST request to the collections publish endpoint
        """
        log.debug(
            f"Entering at lib/upload_irods.py {inspect.getframeinfo(inspect.currentframe()).function}")

        raise NotImplementedError()

    def delete_all_files_from_collection_internal(self, path):
        """Will delete all files from an collection.

        Args:
            path (str): path of an collection

        Returns:
            bool: True if successful, False if not
        """
        log.debug(
            f"Entering at lib/upload_irods.py {inspect.getframeinfo(inspect.currentframe()).function}")
        try:
            with iRODSSession(host=self.irods_api_address,
                              port=1247,
                              user=self.user,
                              password=self.api_key,
                              zone=zone,
                              authentication_scheme='pam',
                              **ssl_settings) as irods_session:
                coll = irods_session.collections.get(path)
                for obj in coll.data_objects:
                    obj.unlink(force=True)
                return True
        except:
            return False

    def delete_file_from_collection_internal(self, path):
        """Will delete a file from an collection

        Args:
            path (str): path of the file

        Returns:
            bool: True if successful, False if not
        """
        log.debug(
            f"Entering at lib/upload_irods.py {inspect.getframeinfo(inspect.currentframe()).function}")
        try:
            with iRODSSession(host=self.irods_api_address,
                              port=1247,
                              user=self.user,
                              password=self.api_key,
                              zone=zone,
                              authentication_scheme='pam',
                              **ssl_settings) as irods_session:
                obj = irods_session.data_objects.get(path)
                r = obj.unlink(force=True)

            if r is None:
                return True
            return False
        except:
            return False

    ############ For downloads ###################

    def get_file_info(self, path):
        """Recursively get all file_info and append to file_content dict

        Args:
            path (str): path to start getting the file info
        """
        try:
            with iRODSSession(host=self.irods_api_address,
                            port=1247,
                            user=self.user,
                            password=self.api_key,
                            zone=zone,
                            authentication_scheme='pam',
                            **ssl_settings) as irods_session:
                coll = irods_session.collections.get(path)

                for obj in coll.data_objects:
                    tmp = {}
                    tmp['name'] = obj.name
                    tmp['size'] = obj.size
                    tmp['link'] = obj.path
                    tmp['hash'] = obj.chksum().split(':')[1]
                    tmp['hash_type'] = obj.chksum().split(':')[0]
                    self.file_content.append(tmp)
                    if len(coll.subcollections) > 0:
                        for col in coll.subcollections:
                            self.get_file_info(col.path)
        except Exception as e:
            log.error(f'exception at irods get_file_info: {e}')


    def get_repo_content(self, path):
        """Get private repo content AKa list of files to be downloaded from the repo

        Args:
            article_id (int): the id of the article that contains the files

        Returns:
            list: list of all the files information: name, size, link, hash, and hash_type
        """
        try:
            self.file_content = []
            path = f"/{irods_zone}/home{path}"
            self.get_file_info(path)
            return self.file_content
        except Exception as e:
            log.error(f'exception at irods get_repo_content: {e}')


    def get_private_metadata(self, path):
        """Will get private metadata for a particular article

        Args:
            path (str): the path of the collection

        Returns:
            dict: flat key value store with keys being the metadata field names and the values the metadata field values.
        """
        try:
            path = f"/{irods_zone}/home{path}"
            with iRODSSession(host=self.irods_api_address,
                            port=1247,
                            user=self.user,
                            password=self.api_key,
                            zone=zone,
                            authentication_scheme='pam',
                            **ssl_settings) as irods_session:
                irods_session.connection_timeout = 300
                coll = irods_session.collections.get(path)
            result = {}
            for key in coll.metadata.keys():
                if key[:4].lower() != 'org_':
                    value = ""
                    for item in coll.metadata.get_all(key):
                        value += str(item.value) + ", "
                    result[key]=coll.metadata.get_all(key)[0].value
            return result
        except Exception as e:
            log.error(f'exception at irods get_private_metadata: {e}')


    def download_file(self, path, link, filename, dest_folder):
        """will download a file from irods path to dest_folder.
        Will also generate subfolders in the dest_folder if there are any in irods.

        Args:
            path (str): the path of the collection
            link (str): location / irods path of the file
            filename (str): name of the file
            dest_folder (str): the folder path to download to
        """
        try:
            full_coll_path = f"/{irods_zone}/home{path}"
            full_folder_path = link.split(filename)[0]
            folder_path = full_folder_path.split('home')[1]
            #only create subfolder when folder_path is not equal / more then the full_coll_path
            subfolder = "/"
            if folder_path.strip("/").lower() != path.strip("/").lower():
                subfolder = folder_path.split(path)[1]
            to_create_path = f"{dest_folder}/{subfolder}/"
            if not os.path.exists(to_create_path):
                os.makedirs(to_create_path)  # create folder if it does not exist
            write_to_path = f"{dest_folder}/{subfolder}/{filename}"
            with iRODSSession(host=self.irods_api_address,
                            port=1247,
                            user=self.user,
                            password=self.api_key,
                            zone=zone,
                            authentication_scheme='pam',
                            **ssl_settings) as irods_session:
                irods_session.connection_timeout = 300
                irods_session.data_objects.get(link, write_to_path, )
        except Exception as e:
            log.error(f'exception at irods download_file: {e}')

    def download_files(self, path, dest_folder):
        """Will download all files for a specific collection to a folder

        Args:
            path (str): the path of the collection
            dest_folder (str): the folder path to download to

        Returns:
            bool: returns True if download was succesful
        """
        try:
            if not os.path.exists(dest_folder):
                os.makedirs(dest_folder)  # create folder if it does not exist
            file_content = self.get_repo_content(path)
            for item in file_content:
                filename = item['name']
                link = item['link']
                self.download_file(path=path, link=link, filename=filename, dest_folder=dest_folder)
            return True
        except Exception as e:
            log.error(f'exception at irods download_files: {e}')

if __name__ == "__main__":
    pass