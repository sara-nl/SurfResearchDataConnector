import inspect
import requests
import json
import os
import logging
from flask import abort, request
import functools
import re
import time

try:
    from app.globalvars import *
except:
    # for testing this file locally
    import sys
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    print(SCRIPT_DIR)
    sys.path.append(os.path.dirname(SCRIPT_DIR))
    from globalvars import *
    print("testing")

log = logging.getLogger()

# logging.basicConfig(level=logging.DEBUG)

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


class Dataverse(object):

    def __init__(self, api_key, api_address=None, dataverse_alias=None, datastation=None, *args, **kwargs):
        self.dataverse_api_address = api_address
        if api_address is None and datastation is None:
            self.dataverse_api_address = os.getenv(
                "DATAVERSE_API_ADDRESS", "https://demo.dataverse.nl/api"
            )
        if api_address is None and datastation is not None:
            self.dataverse_api_address = os.getenv(
                "DATASTATION_API_ADDRESS", "https://demo.ssh.dataverse.nl/api"
            )
        if datastation is None:
            self.dataverse_parent_dataverse = dataverse_parent_dataverse
        else:
            self.dataverse_parent_dataverse = datastation_parent_dataverse
        
        self.api_key = api_key
        self.dataverse_alias = dataverse_alias
        self.datastation = datastation

        # monkeypatching all functions with internals
        self.get_dataset = self.get_dataset_internal
        self.create_new_dataset = self.create_new_dataset_internal
        self.remove_dataset = self.remove_dataset_internal
        self.upload_new_file_to_dataset = self.upload_new_file_to_dataset_internal
        self.change_metadata_in_dataset = self.change_metadata_in_dataset_internal
        self.publish_dataset = self.publish_dataset_internal
        self.delete_all_files_from_dataset = (
            self.delete_all_files_from_dataset_internal
        )

    def check_token(self):
        """Check the API-Token `api_key`.

        Returns `True` if the token is correct and usable, otherwise `False`."""
        log.debug("Check token: Starts")
        try:
            if dataverse_create_user_dataverse.lower() == "ok":
                user_dataverse = self.get_user_dataverse()
            response = self.create_new_dataset(return_response=True)
            log.error("check_token")
            log.error(response)
            persistent_id = response.json()['data']['persistentId']
            r = self.get_dataset(persistent_id=persistent_id, return_response=True)
            log.error(f"Check Token: Status Code: {r.status_code}")
            # cleanup
            self.remove_dataset(persistent_id)
            return r.status_code == 200
        except Exception as e:
            logger.error(e)
            return False

    def set_metadata(self, metadata=None):
        """Set the minimum required metadata if metadata is None

        Returns:
            dict: metadata for testing purposes
        """
        log.debug(f"set_metadata in: {metadata}")
        if metadata is None:
            title = "untitled"
            authorName = "not set"
            authorAffiliation = "not set"
            datasetContactEmail = "not@set.com"
            datasetContactName = "not set"
            dsDescriptionValue = "not set"
            subject = "Other"
            metadata = {
                    "metadataBlocks": {
                        "citation": {
                            "fields": [
                                {
                                    "value": title,
                                    "typeClass": "primitive",
                                    "multiple": False,
                                    "typeName": "title"
                                },
                                {
                                    "value": [
                                        {
                                            "authorName": {
                                                "value": authorName,
                                                "typeClass": "primitive",
                                                "multiple": False,
                                                "typeName": "authorName"
                                            },
                                            "authorAffiliation": {
                                                "value": authorAffiliation,
                                                "typeClass": "primitive",
                                                "multiple": False,
                                                "typeName": "authorAffiliation"
                                            }
                                        }
                                    ],
                                    "typeClass": "compound",
                                    "multiple": True,
                                    "typeName": "author"
                                },
                                {
                                    "value": [
                                        {
                                            "datasetContactEmail": {
                                                "typeClass": "primitive",
                                                "multiple": False,
                                                "typeName": "datasetContactEmail",
                                                "value": datasetContactEmail
                                            },
                                            "datasetContactName": {
                                                "typeClass": "primitive",
                                                "multiple": False,
                                                "typeName": "datasetContactName",
                                                "value": datasetContactName
                                            }
                                        }
                                    ],
                                    "typeClass": "compound",
                                    "multiple": True,
                                    "typeName": "datasetContact"
                                },
                                {
                                    "value": [
                                        {
                                            "dsDescriptionValue": {
                                                "value": dsDescriptionValue,
                                                "multiple": False,
                                                "typeClass": "primitive",
                                                "typeName": "dsDescriptionValue"
                                            }
                                        }
                                    ],
                                    "typeClass": "compound",
                                    "multiple": True,
                                    "typeName": "dsDescription"
                                },
                                {
                                    "value": [
                                        subject
                                    ],
                                    "typeClass": "controlledVocabulary",
                                    "multiple": True,
                                    "typeName": "subject"
                                }
                            ],
                            "displayName": "Citation Metadata"
                        }
                    }
                }
            if self.datastation:
                metadata['metadataBlocks']['dansRights'] = {
                        "displayName": "Rights Metadata",
                        "name": "dansRights",
                        "fields": [
                            {
                                "typeName": "dansRightsHolder",
                                "multiple": True,
                                "typeClass": "primitive",
                                "value": [
                                    "Not set"
                                ]
                            },
                            {
                                "typeName": "dansPersonalDataPresent",
                                "multiple": False,
                                "typeClass": "controlledVocabulary",
                                "value": "Unknown"
                            },
                            {
                                "typeName": "dansMetadataLanguage",
                                "multiple": True,
                                "typeClass": "controlledVocabulary",
                                "value": [
                                    "Not applicable"
                                ]
                            }
                        ]
                    }
                metadata['metadataBlocks']['dansRelationMetadata'] = {
                        "displayName": "Relation Metadata",
                        "name": "dansRelationMetadata",
                        "fields": [
                            {
                                "typeName": "dansAudience",
                                "multiple": True,
                                "typeClass": "primitive",
                                "value": ["https://www.narcis.nl/classification/E14000"]
                            }
                        ]
                    }
            log.debug(f"set_metadata out: {metadata}")
        return metadata


    def get_dataverse_info(self, dataverse):
        dataverse_info = {'type': 'dataverse'}
        url = f"{self.dataverse_api_address}/dataverses/{dataverse}"
        headers = {
            'X-Dataverse-key': self.api_key,
            'Content-Type': 'application/json'
        }

        if datastation_basicauth_token:
            headers['X-Authorization'] = datastation_basicauth_token


        req = requests.request("GET", url, headers=headers)
        if req.status_code == 200:
            if req.json()['status'] == 'OK':
                dataverse_info['id'] = req.json()['data']['id']
                dataverse_info['title'] = req.json()['data']['name']
                dataverse_info['alias'] = req.json()['data']['alias']
        return dataverse_info


    def get_sub_dataverses(self, root_dataverse=dataverse_parent_dataverse):
        subdataverses = []
        url = f"{self.dataverse_api_address}/dataverses/{root_dataverse}/contents"
        
        headers = {
            'X-Dataverse-key': self.api_key,
            'Content-Type': 'application/json'
        }

        if datastation_basicauth_token:
            headers['X-Authorization'] = datastation_basicauth_token

        rr = requests.request("GET", url, headers=headers)
        if rr.status_code == 200:
            if rr.json()['status'] == 'OK':
                if 'data' in rr.json():
                    for item in rr.json()['data']:
                        if item['type'] == 'dataverse':
                            ID = item['id']
                            url = f"{self.dataverse_api_address}/dataverses/{ID}"
                            headers = {
                                'X-Dataverse-key': self.api_key,
                                'Content-Type': 'application/json'
                            }

                            if datastation_basicauth_token:
                                headers['X-Authorization'] = datastation_basicauth_token

                            req = requests.request("GET", url, headers=headers)
                            item['alias'] = req.json()['data']['alias']
                            subdataverses.append(item)
        return subdataverses


    def get_user_dataverse(self):
        """This method will return a dataverse name based on the userId.
        Each time it is called it will try to create a dataverse with the name
        based on the userId. If it already exists, then it will not create a new
        dataverse, but return the existing dataverse name.

        If it is not possible to retreive a userId or create a new dataverse (for
        example in testing), then the parent dataverse name will be returned.

        Returns:
            _str: name of the dataverse
        """
        
        if dataverse_create_user_dataverse.lower() != "ok":
            return #self.dataverse_parent_dataverse

        # parent dataverse at demo.dataverse.nl is "surf"
        parent_dataverse = self.dataverse_parent_dataverse

        # get user and email
        url = f"{self.dataverse_api_address}/users/:me"

        headers = {
            'X-Dataverse-key': self.api_key,
            'Content-Type': 'application/json'
        }

        if datastation_basicauth_token:
            headers['X-Authorization'] = datastation_basicauth_token

        try:
            rr = requests.request("GET", url, headers=headers).json()['data']
            
            dataverse_user = rr['persistentUserId']
            dataverse_name = ((re.sub(r"[^a-zA-Z0-9]+", '', dataverse_user)))
            email = rr['email']
            
            # create a dataverse inside the parent dataverse of the installation
            # If it already exist it will not be created
            dataverse = {
                "name": dataverse_name,
                "alias": dataverse_name,
                "dataverseContacts": [
                    {
                    "contactEmail": email
                    }
                ],
                "affiliation": "Surf Research Drive",
                "description": "This dataverse has been created as part of the automated transfer of data from Surf Research Drive",
                "dataverseType": "UNCATEGORIZED"
                }

            headers = {
                'X-Dataverse-key': self.api_key,
                'Content-Type': 'application/json'
            }

            if datastation_basicauth_token:
                headers['X-Authorization'] = datastation_basicauth_token

            url = f"{self.dataverse_api_address}/dataverses/{parent_dataverse}"
            payload = json.dumps(dataverse)
            r = requests.request("POST", url, headers=headers, data=payload)
            return dataverse_name
        except Exception as e:
            log.error(e)
            raise Exception("Cannot retrieve user info")
            


    def get_persistent_id_with_id(self, id: int):
        """Will get the persistent_id of a dataset.

        Args:
            id (int): id of a dataset

        Returns:
            str: persistent_id of the dataset
        """
        headers = {
            'X-Dataverse-key': self.api_key,
            'Content-Type': 'application/json'
        }
        
        if datastation_basicauth_token:
            headers['X-Authorization'] = datastation_basicauth_token

        url = f"{self.dataverse_api_address}/datasets/{id}/"
        
        r = requests.request("GET", url, headers=headers)

        persistent_id = r.json()["data"]["latestVersion"]["datasetPersistentId"]
        
        return persistent_id


    def get_latest_persistent_id(self):
        """Gets the persistent_id of the latest dataset created

        Returns:
            str: persistent_id of the dataset
        """

        headers = {
            'X-Dataverse-key': self.api_key,
            'Content-Type': 'application/json'
        }
        
        if datastation_basicauth_token:
            headers['X-Authorization'] = datastation_basicauth_token

        if dataverse_create_user_dataverse.lower() == "ok":
            dataverse_alias = self.get_user_dataverse()
        elif self.dataverse_alias:
            dataverse_alias = self.dataverse_alias
        else:
            dataverse_alias = self.dataverse_parent_dataverse

        url = f"{self.dataverse_api_address}/dataverses/{dataverse_alias}/contents"
        r = requests.request("GET", url, headers=headers)
        
        last_dataset_id = r.json()["data"][-1]['id']

        return self.get_persistent_id_with_id(last_dataset_id)
    

    @_rate_limit(per_second=5)
    def get_dataset_internal(
        self, persistent_id: str = None, return_response: bool = False, metadataFilter: dict = None
    ):
        """
        Get dataset information of specified persistent_id.
        If no persistent_id is given then all available datasets will we returned

        Args:
            persistent_id (str, optional): The dataset id.
            return_response (bool, optional): Set to True will return the API response. Defaults to False.
            metadataFilter (dict, optional): filter for selecting what data needs to returned. Defaults to None.

        Returns:
            json: : API response if return_response is set to True
        """
        log.debug(
            f"Entering at repos/dataverse.py {inspect.getframeinfo(inspect.currentframe()).function}")

        try:
            headers = {
                'X-Dataverse-key': self.api_key,
                'Content-Type': 'application/json'
            }

            if datastation_basicauth_token:
                headers['X-Authorization'] = datastation_basicauth_token

            if persistent_id is not None:
                url = f"{self.dataverse_api_address}/datasets/:persistentId"
                params = {"persistentId" : persistent_id}
                r = requests.get(url, params=params, headers=headers)
            else:
                if dataverse_create_user_dataverse.lower() == "ok":
                    dataverse_alias = self.get_user_dataverse()
                elif self.dataverse_alias:
                    dataverse_alias = self.dataverse_alias
                else:
                    dataverse_alias = self.dataverse_parent_dataverse
                url = f"{self.dataverse_api_address}/dataverses/{dataverse_alias}/contents"
                r = requests.get(url, headers=headers)
            if return_response:
                return r
            if r.status_code >= 300:
                abort(r.status_code)
            result = r.json()

            return result
    
        except Exception as e:
            log.error(
                f"Exception at repos/dataverse.py {inspect.getframeinfo(inspect.currentframe()).function}")
            log.error(str(e))


    def create_new_dataset_internal(self, metadata=None, return_response=False):
        """Creates a new untitled dataset in the parent dataverse.
        If metadata is specified, it will changes metadata after creating.

        Args:
            metadata (_type_, optional): Metadata for the dataset. Defaults to None.
            return_response (bool, optional): Set to True will return the API response. Defaults to False.

        Returns:
            json: API response if return_response is set to True
        """
        log.debug(
            f"Entering at lib/upload_dataverse.py {inspect.getframeinfo(inspect.currentframe()).function}")
        log.debug("Create new dataset: Starts")
        log.debug(f"### metadata: {metadata}")

        headers = {
            'X-Dataverse-key': self.api_key,
            'Content-Type': 'application/json'
        }

        if datastation_basicauth_token:
            headers['X-Authorization'] = datastation_basicauth_token

        log.error(headers)

        # Create a dataset as part of the parent dataverse
        if dataverse_create_user_dataverse.lower() == "ok":
            dataverse_alias = self.get_user_dataverse()
        elif self.dataverse_alias:
            dataverse_alias = self.dataverse_alias
        else:
            dataverse_alias = self.dataverse_parent_dataverse

        url = f"{self.dataverse_api_address}/dataverses/{dataverse_alias}/datasets"
        
        log.error(url)

        # use metadata here to set values of below variables els:
        
        metadata = self.set_metadata(metadata)
        metadata = { 'datasetVersion': metadata }
        payload = json.dumps(metadata)

        log.error(payload)

        r = requests.request("POST", url, headers=headers, data=payload)

        log.error(
            f"Create new datasets: Status Code: {r.json()}")

        return r.json() if not return_response else r

    def remove_dataset_internal(self, persistent_id, return_response=False):
        """Will remove an dataset based on it's id.

        Args:
            persistent_id (_type_): the dataset id
            return_response (bool, optional): Set to True will return the API response. Defaults to False.

        Returns:
            json: API response if return_response is set to True
        """
        log.debug(
            f"Entering at repos/dataverse.py {inspect.getframeinfo(inspect.currentframe()).function}")
        
        headers = {
            'X-Dataverse-key': self.api_key,
            'Content-Type': 'application/json'
        }

        if datastation_basicauth_token:
            headers['X-Authorization'] = datastation_basicauth_token

        url = f"{self.dataverse_api_address}/datasets/:persistentId/?persistentId={persistent_id}"
        r = requests.request("DELETE", url, headers=headers)

        return r.status_code == 204 if not return_response else r

    def upload_new_file_to_dataset_internal(
        self, persistent_id: str, path_to_file: str, file=None, return_response=False, test=False
    ):
        """Uploads a file to a dataset on Dataverse.

        Args:
            persistent_id (str): id of the dataset to upload to
            path_to_file (str): path to the file to be uploaded. Example: ~/mydatapackage.csv
            file (bytes, optional): file as a bytes object. Defaults to None.
            return_response (bool, optional): Set to True will return the API response. Defaults to False.

        Returns:
            bool: Alternative: json if return_response=True
        """
        log.debug(
            f"Entering at repos/dataverse.py {inspect.getframeinfo(inspect.currentframe()).function}")
               
        try:
            file_content = open(path_to_file, 'rb')

            files = {'file': (path_to_file.split("/")[-1], file_content)}

            params = dict()
            
            params_as_json_string = json.dumps(params)

            payload = dict(jsonData=params_as_json_string)
            
            if persistent_id == "None" or persistent_id is None:
                persistent_id = self.get_latest_persistent_id()

            url_persistent_id = f"{self.dataverse_api_address}/datasets/:persistentId/add?persistentId={persistent_id}&key={self.api_key}"


            headers = {}
            if datastation_basicauth_token:
                headers['X-Authorization'] = datastation_basicauth_token

            response = requests.post(
                url_persistent_id, headers=headers, data=payload, files=files)
            if return_response:
                return response           

            # check response. if all ok then true else return string of the response for user to see what went wrong
            if response.status_code == 200:
                if 'status' in response.json():
                    if response.json()['status'] == 'OK':
                        return True
            return response.text
            
        except Exception as e:
            log.error(
                f"Exception at repos/dataverse.py {inspect.getframeinfo(inspect.currentframe()).function}")
            log.error(str(e))
            return str(e)

    def get_files_from_dataset(self, persistent_id):
        """will get all the files metadata from the dataset requested.

        Args:
            persistent_id (int): id of the dataset

        Returns:
            json: json containing all the files from the dataset
        
        Example return value:
        ```python
            [
                {'description': 'Blue skies!',
                'label': 'dataverse.png',
                'restricted': False,
                'version': 1,
                'datasetVersionId': 225669,
                'categories': ['Jack of Hearts', 'Lily', 'Rosemary'],
                'dataFile': {'id': 2023741,
                            'persistentId': '',
                            'pidURL': '',
                            'filename': 'dataverse.png',
                            'contentType': 'image/png',
                            'filesize': 22688,
                            'description': 'Blue skies!',
                            'storageIdentifier': 's3://demo-dataverse-org:1862b5280c4-053bbecef4d5',
                            'rootDataFileId': -1,
                            'md5': 'cf3b4d8ac22c5b98898f9a0fd74c0e1f',
                            'checksum': {'type': 'MD5',
                                        'value': 'cf3b4d8ac22c5b98898f9a0fd74c0e1f'},
                            'creationDate': '2023-02-07'}
                }
            ]
        ```
        """
        log.debug(
            f"Entering at repos/dataverse.py {inspect.getframeinfo(inspect.currentframe()).function}")

        response = self.get_dataset(
            persistent_id=persistent_id, return_response=True)

        if response.status_code < 300:
            return response.json()['data']['latestVersion']['files']

        return []

    def change_metadata_in_dataset_internal(
        self, persistent_id, metadata, return_response=False
    ):
        """Will update a dataset according to the provided metadata.

        Args:
            persistent_id (int): id of the dataset
            return_response (bool, optional): Set to True will return the API response. Defaults to False.
            metadata (dict): A data-dict json-like object

        Returns:
            object: response of the PUT request to the datasets endpoint
        """
        log.debug(
            f"### Entering at repos/dataverse.py {inspect.getframeinfo(inspect.currentframe()).function}")

        headers = {
            'X-Dataverse-key': self.api_key,
            'Content-Type': 'application/json'
        }

        if datastation_basicauth_token:
            headers['X-Authorization'] = datastation_basicauth_token

        url = f"{self.dataverse_api_address}/datasets/:persistentId/versions/:draft?persistentId={persistent_id}"

        log.debug(f"### metadata change_metadata_in_dataset_internal: {metadata}")

        
        metadata = self.set_metadata(metadata)
        payload = json.dumps(metadata)

        log.debug(f"### payload: {payload}")

        r = requests.request("PUT", url, headers=headers, data=payload)
        rtext = r.text
        log.debug(f"### r: {rtext}") 

        return r.status_code == 204 if not return_response else r 

    def publish_dataset_internal(self, persistent_id, return_response=False):
        """Will publish an dataset if it is not under embargo

        Args:
            persistent_id (_type_): id of the dataset
            return_response (bool, optional): Set to True will return the API response. Defaults to False.

        Returns:
            object: response of the POST request to the datasets publish endpoint
        """
        log.debug(
            f"Entering at repos/dataverse.py {inspect.getframeinfo(inspect.currentframe()).function}")
        
        headers = {
            'X-Dataverse-key': self.api_key,
            'Content-Type': 'application/json'
        }

        if datastation_basicauth_token:
            headers['X-Authorization'] = datastation_basicauth_token

        url = f"{self.dataverse_api_address}/datasets/:persistentId/actions/:publish?persistentId={persistent_id}&type=major"

        r = requests.request("POST", url, headers=headers)

        return r.status_code == 204 if not return_response else r

    def delete_all_files_from_dataset_internal(self, persistent_id):
        """Will delete all files from an dataset.

        Args:
            persistent_id (int): id of an dataset

        Returns:
            bool: True if successful, False if not
        """
        log.debug(
            f"Entering at repos/dataverse.py {inspect.getframeinfo(inspect.currentframe()).function}")
        for file in self.get_files_from_dataset(persistent_id):
            log.debug(f"found file: {file}")

            if not self.delete_file_from_dataset_internal(persistent_id, file["dataFile"]["id"]):
                return False

        return True

    def delete_file_from_dataset_internal(self, persistent_id, file_id):
        """Not supported
        Will delete a file from an dataset

        Args:
            persistent_id (int): id of the dataset
            file_id (int): id of file

        Returns:
            bool: True if successful, False if not
        """
        log.debug(
            f"Entering at repos/dataverse.py {inspect.getframeinfo(inspect.currentframe()).function}")
        log.debug("Deletion of dataset files is not supported by the Dataverse API")

        return False


    ############ For downloads ###################

    def get_repo_content(self, persistent_id):
        """Get private repo content AKa list of files to be downloaded from the repo
        # Only work with

        Args:
            persistent_id (int): the id of the article that contains the files

        Returns:
            list: list of all the files information: name, size, link, hash, and hash_type
        """
        file_content = []
        files = self.get_files_from_dataset(persistent_id=persistent_id)
        for file in files:
            try:
                tmp = {}
                tmp['name'] = file['dataFile']['filename']
                tmp['size'] = file['dataFile']['filesize']
                tmp['link'] = file['dataFile']['id']
                tmp['hash'] = file['dataFile']['checksum']['value']
                tmp['hash_type'] = str(file['dataFile']['checksum']['type']).lower().replace("-", "")
                file_content.append(tmp)
            except Exception as e:
                log.error(f"dataset: {e}")
        return file_content


    def get_private_metadata(self, persistent_id):
        """Will get private metadata for a particular article

        Args:
            persistent_id (int): the id of the article

        Returns:
            dict: flat key value store with keys being the metadata field names and the values the metadata field values.
        """
        dataset = self.get_dataset(persistent_id=persistent_id, return_response=True)
        exclude = ['files']
        result = {}
        if dataset.ok:
            values = dataset.json()['data']
            for key in values:
                if key == 'latestVersion':
                    for key2 in values[key]:
                        if key2 not in exclude:
                            if key2 == 'metadataBlocks':
                                for item in values[key][key2]['citation']['fields']:
                                    if item['typeName'] == 'author':
                                        n = 1
                                        for author in item['value']:
                                            name = author['authorName']['value']
                                            affiliation = author['authorAffiliation']['value']
                                            result['author_' + str(n)] = name + ", " + affiliation
                                            n += 1
                                    elif item['typeName'] == 'datasetContact':
                                        n = 1
                                        for contact in item['value']:
                                            result['contact_' + str(n)] = contact['datasetContactName']['value']
                                            n += 1
                                    elif item['typeName'] == 'dsDescription':
                                        result['description'] = ''
                                        for description in item['value']:
                                            result['description'] += item['value'][0]['dsDescriptionValue']['value'] + ' '
                                    elif item['typeName'] == 'subject':
                                        result['subject'] = " ".join(item['value'])
                                    else:
                                        result[item['typeName']] = item['value']
                            else:
                                result[key2] = values[key][key2]
                else:
                    result[key] = values[key]
        return result


    def download_files(self, persistent_id, dest_folder):
        """Will download all files for a specific persistent_id to a folder

        Args:
            persistent_id (int): the id of the article
            dest_folder (str): the folder path to download to

        Returns:
            bool: returns True if download was succesful
        """
        try:
            if not os.path.exists(dest_folder):
                os.makedirs(dest_folder)  # create folder if it does not exist
            file_content = self.get_repo_content(persistent_id)
            for item in file_content:
                filename = item['name']
                # filenames can contain a path as well
                # we need to create that part of the path as well
                # so check for '/' in the filename
                if filename.find("/") != -1:
                    additional_path = filename.split('/')
                    # log.error(additional_path)
                    # drop last one as that is the filename
                    filename = additional_path.pop()
                    additional_path = "/".join(additional_path)
                    total_path = f"{dest_folder}/{additional_path}"
                    if not os.path.exists(total_path):
                        os.makedirs(total_path)  # create folder if it does not exist
                    file_path = os.path.join(total_path, filename)
                else:
                    file_path = os.path.join(dest_folder, filename)
                file_id = item['link']
                url = f'{self.dataverse_api_address}/access/datafile/{file_id}?persistentId={persistent_id}'
                
                headers = {
                    'X-Dataverse-key': self.api_key,
                    'Content-Type': 'application/json'
                }

                if datastation_basicauth_token:
                    headers['X-Authorization'] = datastation_basicauth_token

                r = requests.get(url,
                                headers=headers,
                                stream=True)
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


class DansDatastation(Dataverse):
    pass


if __name__ == "__main__":
    """Below code will test the code that interfaces the uploads to dataverse
    """
    import sys
    import configparser
    from prettyprinter import pprint

    try:
        config = configparser.ConfigParser()
        config.read('../../env.ini')
    except Exception as e:
        config = None
        log.error(str(e))
    try:
        api_key = os.getenv(
            "DATAVERSE_API_KEY",
            config.get('TESTS', 'DATAVERSE_API_KEY')
        )
    except Exception as e:
        log.error(f"Could not get an api_key for testing: {str(e)}")
        log.info("Halting tests")
        sys.exit()

    api_address = os.getenv(
        "API_ADDRESS",
        "https://demo.dataverse.org/api"
    )
    api_key = 'abc'
    api_address = "https://demo.dataverse.nl/api"
    dataverse = Dataverse(api_key=api_key, api_address=api_address)

    # print("### check token ###")
    # print(api_address)
    check = dataverse.check_token()
    # print(check)
    if check:
        pprint(dataverse.get_dataverse_info("surf"))
    #     persistent_id = "doi:10.80227/test-BON2UZ"
    #     repo_content = dataverse.get_repo_content(persistent_id)
    #     # repo_content = dataverse.get_private_metadata(persistent_id)
    #     pprint(repo_content)
    #     result = dataverse.download_files(persistent_id=persistent_id, dest_folder='tmptest')
    #     print(result)
        # print("### Create dataset ###")
        # dataset = dataverse.create_new_dataset(return_response=True)
        # print(dataset.json())

        # print("### Get the persistent_id ###")
        # persistent_id = dataset.json()['data']['persistentId']
        # print(persistent_id)

        # print("### upload a file with None as persistent_id ###")
        # file_path = "../dataverse.png"
        # r = dataverse.upload_new_file_to_dataset(
        #     persistent_id="None", path_to_file=file_path, file=None, return_response=True, test=True)
        # print(r)
        # print(r.text)

        # print("### Get dataset info ###")
        # r = dataverse.get_dataset(persistent_id=persistent_id, return_response=True)
        # print(r)
        # print(r.text)
        # id = r.json()['data']['id']


        # print("### Get dataset files ###")
        # r = dataverse.get_files_from_dataset(persistent_id=persistent_id)
        # print(r)

        # print("### Update dataset metadata ###")
        # data = {
        #     "metadataBlocks": {
        #         "citation": {
        #             "fields": [
        #                 {
        #                     "value": "Test",
        #                     "typeClass": "primitive",
        #                     "multiple": False,
        #                     "typeName": "title"
        #                 }
        #             ],
        #             "displayName": "Citation Metadata"
        #         }
        #     }
        # }
        # r = dataverse.change_metadata_in_dataset_internal(
        #     persistent_id=persistent_id, metadata=data, return_response=True)
        # print(r)
        # print(r.text)

        # print("### Get latest persistent_id ###")
        # print(dataverse.get_latest_persistent_id())
        # print(f"Should be the same as: {persistent_id}")


        # print("### Get persistent_id with id ###")
        # print(dataverse.get_persistent_id_with_id(id))
        # print(f"Should be the same as: {persistent_id}")


        # print("### Publish dataset ###")
        # print("Not executed as normal users cannot remove published datasets")
        # r = dataverse.publish_dataset_internal(persistent_id, return_response=True)
        # print(r)
        # print(r.text)

        # print("### Delete all files from dataset ###")
        # r = dataverse.delete_all_files_from_dataset(persistent_id=persistent_id)
        # print(r)

        # print("### Remove dataset ###")
        # r = dataverse.remove_dataset(persistent_id=persistent_id, return_response=True)
        # print(r)
        # print(r.text)
