import logging
import os
import sys
import unittest
from pactman import Consumer, Provider

from app.repos.dataverse import Dataverse


def create_app():
    from src import bootstrap

    # creates a test client
    app = bootstrap(use_default_error=True, address="http://localhost:3000").app
    # propagate the exceptions to the test client
    app.config.update({"TESTING": True})

    return app


pact = Consumer("PortDataverse").has_pact_with(Provider("Dataverse"), port=3000)

api_address = "http://localhost:3000"
api_key = "123"

log = logging.getLogger()


class TestDataverseMethodsNewMockedApi(unittest.TestCase):
    """Test for the methods implemented for dataverse.

    Tests are written according to the Arrange - Act -Assert design pattern.
    We will mock the api calls during the arrange step.

    Args:
        unittest (base): basic testcase from the unittest lib
    """

    def test_get_dataset(self):
        """testing the get_dataset method by creating an dataset and then get it and
        checking if we get a 200 response.
        """
        # arrange

        persistent_id = "doi:10.80227/PDVNL/OGXXEP"
        call_url = f"/datasets/:persistentId"
        query = {"persistentId": persistent_id}

        pact.given("dataset can be retrieved for OGXXEP").upon_receiving(
            "the corresponding response with the dataset info"
        ).with_request("GET", call_url, query=query).will_respond_with(
            200,
            body={
                "status": "OK",
                "data": {
                    "id": 2767,
                    "identifier": "PDVNL/OGXXEP",
                    "persistentUrl": "https://doi.org/10.80227/PDVNL/OGXXEP",
                    "protocol": "doi",
                    "authority": "10.80227",
                    "publisher": "DataverseNL (demo)",
                    "storageIdentifier": "file://10.80227/PDVNL/OGXXEP",
                    "latestVersion": {
                        "id": 1154,
                        "datasetId": 2767,
                        "datasetPersistentId": "doi:10.80227/PDVNL/OGXXEP",
                        "storageIdentifier": "file://10.80227/PDVNL/OGXXEP",
                        "versionState": "DRAFT",
                        "latestVersionPublishingState": "DRAFT",
                        "lastUpdateTime": "2024-12-12T14:04:50Z",
                        "createTime": "2024-12-12T14:04:50Z",
                        "fileAccessRequest": True,
                        "metadataBlocks": {
                            "citation": {
                                "displayName": "Citation Metadata",
                                "name": "citation",
                                "fields": [
                                    {
                                        "typeName": "title",
                                        "multiple": False,
                                        "typeClass": "primitive",
                                        "value": "untitled",
                                    },
                                    {
                                        "typeName": "author",
                                        "multiple": True,
                                        "typeClass": "compound",
                                        "value": [
                                            {
                                                "authorName": {
                                                    "typeName": "authorName",
                                                    "multiple": False,
                                                    "typeClass": "primitive",
                                                    "value": "not set",
                                                },
                                                "authorAffiliation": {
                                                    "typeName": "authorAffiliation",
                                                    "multiple": False,
                                                    "typeClass": "primitive",
                                                    "value": "not set",
                                                },
                                            }
                                        ],
                                    },
                                    {
                                        "typeName": "datasetContact",
                                        "multiple": True,
                                        "typeClass": "compound",
                                        "value": [
                                            {
                                                "datasetContactName": {
                                                    "typeName": "datasetContactName",
                                                    "multiple": False,
                                                    "typeClass": "primitive",
                                                    "value": "not set",
                                                }
                                            }
                                        ],
                                    },
                                    {
                                        "typeName": "dsDescription",
                                        "multiple": True,
                                        "typeClass": "compound",
                                        "value": [
                                            {
                                                "dsDescriptionValue": {
                                                    "typeName": "dsDescriptionValue",
                                                    "multiple": False,
                                                    "typeClass": "primitive",
                                                    "value": "not set",
                                                }
                                            }
                                        ],
                                    },
                                    {
                                        "typeName": "subject",
                                        "multiple": True,
                                        "typeClass": "controlledVocabulary",
                                        "value": ["Other"],
                                    },
                                ],
                            }
                        },
                        "files": [],
                    },
                },
            },
        )

        # act
        with pact:
            dataverse = Dataverse(api_key=api_key, api_address=api_address)
            response = dataverse.get_dataset(persistent_id, return_response=True)

        # assert
        self.assertEqual(response.status_code, 200)

    def test_create_new_dataset(self):
        """testing the create_new_dataset method"""
        # arrange
        pact.given("dataset can be created for OGXXEP").upon_receiving(
            "the corresponding response with the dataset creation info"
        ).with_request("POST", "/dataverses/surf/datasets").will_respond_with(
            201,
            body={
                "status": "OK",
                "data": {"id": 2767, "persistentId": "doi:10.80227/PDVNL/OGXXEP"},
            },
        )

        # act
        with pact:
            dataverse = Dataverse(api_key=api_key, api_address=api_address)
            response = dataverse.create_new_dataset(return_response=True)
            persistent_id = response.json()["data"]["persistentId"]

        # assert
        self.assertEqual(response.status_code, 201)
        self.assertTrue(type(persistent_id) is str)

    def test_remove_dataset(self):
        """testing the remove_dataset method"""
        # arrange
        persistent_id = "doi:10.80227/PDVNL/OGXXEP"
        url = f"/datasets/:persistentId/"
        query = {"persistentId": persistent_id}

        pact.given("dataset can be removed for OGXXEP").upon_receiving(
            "the corresponding response with the dataset removal info"
        ).with_request("DELETE", url, query=query).will_respond_with(
            200,
            body={"status": "OK", "data": {"message": "Dataset :persistentId deleted"}},
        )

        # act
        with pact:
            dataverse = Dataverse(api_key=api_key, api_address=api_address)
            response = dataverse.remove_dataset(persistent_id, return_response=True)

        # assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "OK")

    @unittest.skip
    def test_upload_new_file_to_dataset(self):
        """testing the upload_new_file_to_dataset method"""
        # arrange
        ## !! Pactman does not seem to be able to mock file uploads the way needed !!
        persistent_id = "doi:10.80227/PDVNL/OGXXEP"
        path_to_file = "./app/static/img/dataverse.png"
        url = "/datasets/:persistentId/add"
        query = {"persistentId": persistent_id, "key": api_key}

        file_content = open(path_to_file, "rb")
        files = {"file": path_to_file.split("/")[-1]}
        log.error(files)

        payload = {"jsonData": files}

        headers = {"Content-Type": "multipart/form-data"}

        pact.given("file can be uploaded to dataset OGXXEP").upon_receiving(
            "the corresponding response with the file upload info"
        ).with_request(
            "POST", url, query=query, headers=headers, body=payload, files=None
        ).will_respond_with(
            200,
            body={
                "status": "OK",
                "data": {
                    "files": [
                        {
                            "description": "",
                            "label": "dataverse.png",
                            "restricted": False,
                            "version": 1,
                            "datasetVersionId": 1320,
                            "dataFile": {
                                "id": 2952,
                                "persistentId": "",
                                "filename": "dataverse.png",
                                "contentType": "image/png",
                                "friendlyType": "PNG Image",
                                "filesize": 4249,
                                "description": "",
                                "storageIdentifier": "file://194458a039a-6fc0df37ec77",
                                "rootDataFileId": -1,
                                "checksum": {
                                    "type": "SHA-1",
                                    "value": "a4261f9a0c32363beda07524f934e9cf58eef85c",
                                },
                                "tabularData": False,
                                "creationDate": "2025-01-08",
                                "fileAccessRequest": False,
                            },
                        }
                    ]
                },
            },
        )

        # act
        with pact:
            dataverse = Dataverse(api_key=api_key, api_address=api_address)
            response = dataverse.upload_new_file_to_dataset(
                persistent_id, path_to_file, return_response=True, test=True
            )
            log.error(response)
        # assert
        self.assertEqual(response.json()["status"], "OK")
        self.assertEqual(len(response.json()["data"]["files"]), 1)
        self.assertEqual(response.status_code, 200)

    def test_change_metadata_in_dataset(self):
        """testing the change_metadata_in_dataset method."""
        # arrange
        dataverse = Dataverse(api_key=api_key, api_address=api_address)
        persistent_id = "doi:10.80227/PDVNL/OGXXEP"
        metadata = dataverse.set_metadata()
        url = "/datasets/:persistentId/versions/:draft"
        query = {"persistentId": persistent_id}

        ## adding custom title to the default metadata
        for item in metadata["metadataBlocks"]["citation"]["fields"]:
            if item["typeName"] == "title":
                item["value"] = "My first upload"

        body = {
            "status": "OK",
            "data": {
                "id": 1323,
                "datasetId": 2955,
                "datasetPersistentId": "doi:10.80227/PDVNL/OGXXEP",
                "storageIdentifier": "file://10.80227/PDVNL/OGXXEP",
                "versionState": "DRAFT",
                "latestVersionPublishingState": "DRAFT",
                "lastUpdateTime": "2025-01-08T14:48:09Z",
                "createTime": "2025-01-08T14:48:09Z",
                "fileAccessRequest": False,
                "metadataBlocks": {
                    "citation": {
                        "displayName": "Citation Metadata",
                        "name": "citation",
                        "fields": [
                            {
                                "typeName": "title",
                                "multiple": False,
                                "typeClass": "primitive",
                                "value": "My first upload",
                            },
                            {
                                "typeName": "author",
                                "multiple": True,
                                "typeClass": "compound",
                                "value": [
                                    {
                                        "authorName": {
                                            "typeName": "authorName",
                                            "multiple": False,
                                            "typeClass": "primitive",
                                            "value": "not set",
                                        },
                                        "authorAffiliation": {
                                            "typeName": "authorAffiliation",
                                            "multiple": False,
                                            "typeClass": "primitive",
                                            "value": "not set",
                                        },
                                    }
                                ],
                            },
                            {
                                "typeName": "datasetContact",
                                "multiple": True,
                                "typeClass": "compound",
                                "value": [
                                    {
                                        "datasetContactName": {
                                            "typeName": "datasetContactName",
                                            "multiple": False,
                                            "typeClass": "primitive",
                                            "value": "not set",
                                        }
                                    }
                                ],
                            },
                            {
                                "typeName": "dsDescription",
                                "multiple": True,
                                "typeClass": "compound",
                                "value": [
                                    {
                                        "dsDescriptionValue": {
                                            "typeName": "dsDescriptionValue",
                                            "multiple": False,
                                            "typeClass": "primitive",
                                            "value": "not set",
                                        }
                                    }
                                ],
                            },
                            {
                                "typeName": "subject",
                                "multiple": True,
                                "typeClass": "controlledVocabulary",
                                "value": ["Other"],
                            },
                        ],
                    }
                },
                "files": [],
            },
        }

        pact.given("metadata of can be changed for OGXXEP").upon_receiving(
            "the corresponding response after changing the metadata"
        ).with_request("PUT", url, query=query, body=metadata).will_respond_with(
            200,
            body=body,
        )

        # act
        with pact:
            response = dataverse.change_metadata_in_dataset(
                persistent_id=persistent_id, metadata=metadata, return_response=True
            )

        # assert
        title = ""
        fields = response.json()["data"]["metadataBlocks"]["citation"]["fields"]
        for field in fields:
            if field["typeName"] == "title":
                title = field["value"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(title, "My first upload")

    def test_check_token(self):
        """testing check_token"""
        # arrange

        dataverse = Dataverse(api_key=api_key, api_address=api_address)

        # create dataset
        pact.given("dataset can be created for OGXXEP").upon_receiving(
            "the corresponding response with the dataset creation info"
        ).with_request("POST", "/dataverses/surf/datasets").will_respond_with(
            201,
            body={
                "status": "OK",
                "data": {"id": 2767, "persistentId": "doi:10.80227/PDVNL/OGXXEP"},
            },
        )

        # get dataset
        persistent_id = "doi:10.80227/PDVNL/OGXXEP"
        call_url = f"/datasets/:persistentId"
        query = {"persistentId": persistent_id}

        pact.given("dataset can be retrieved for OGXXEP").upon_receiving(
            "the corresponding response with the dataset info"
        ).with_request("GET", call_url, query=query).will_respond_with(
            200,
            body={
                "status": "OK",
                "data": {
                    "id": 2767,
                    "identifier": "PDVNL/OGXXEP",
                    "persistentUrl": "https://doi.org/10.80227/PDVNL/OGXXEP",
                    "protocol": "doi",
                    "authority": "10.80227",
                    "publisher": "DataverseNL (demo)",
                    "storageIdentifier": "file://10.80227/PDVNL/OGXXEP",
                    "latestVersion": {
                        "id": 1154,
                        "datasetId": 2767,
                        "datasetPersistentId": "doi:10.80227/PDVNL/OGXXEP",
                        "storageIdentifier": "file://10.80227/PDVNL/OGXXEP",
                        "versionState": "DRAFT",
                        "latestVersionPublishingState": "DRAFT",
                        "lastUpdateTime": "2024-12-12T14:04:50Z",
                        "createTime": "2024-12-12T14:04:50Z",
                        "fileAccessRequest": True,
                        "metadataBlocks": {
                            "citation": {
                                "displayName": "Citation Metadata",
                                "name": "citation",
                                "fields": [
                                    {
                                        "typeName": "title",
                                        "multiple": False,
                                        "typeClass": "primitive",
                                        "value": "untitled",
                                    },
                                    {
                                        "typeName": "author",
                                        "multiple": True,
                                        "typeClass": "compound",
                                        "value": [
                                            {
                                                "authorName": {
                                                    "typeName": "authorName",
                                                    "multiple": False,
                                                    "typeClass": "primitive",
                                                    "value": "not set",
                                                },
                                                "authorAffiliation": {
                                                    "typeName": "authorAffiliation",
                                                    "multiple": False,
                                                    "typeClass": "primitive",
                                                    "value": "not set",
                                                },
                                            }
                                        ],
                                    },
                                    {
                                        "typeName": "datasetContact",
                                        "multiple": True,
                                        "typeClass": "compound",
                                        "value": [
                                            {
                                                "datasetContactName": {
                                                    "typeName": "datasetContactName",
                                                    "multiple": False,
                                                    "typeClass": "primitive",
                                                    "value": "not set",
                                                }
                                            }
                                        ],
                                    },
                                    {
                                        "typeName": "dsDescription",
                                        "multiple": True,
                                        "typeClass": "compound",
                                        "value": [
                                            {
                                                "dsDescriptionValue": {
                                                    "typeName": "dsDescriptionValue",
                                                    "multiple": False,
                                                    "typeClass": "primitive",
                                                    "value": "not set",
                                                }
                                            }
                                        ],
                                    },
                                    {
                                        "typeName": "subject",
                                        "multiple": True,
                                        "typeClass": "controlledVocabulary",
                                        "value": ["Other"],
                                    },
                                ],
                            }
                        },
                        "files": [],
                    },
                },
            },
        )

        # remove dataset
        persistent_id = "doi:10.80227/PDVNL/OGXXEP"
        url = f"/datasets/:persistentId/"
        query = {"persistentId": persistent_id}

        pact.given("dataset can be removed").upon_receiving(
            "the corresponding response with the dataset removal info"
        ).with_request("DELETE", url, query=query).will_respond_with(
            200,
            body={"status": "OK", "data": {"message": "Dataset :persistentId deleted"}},
        )

        # act
        with pact:
            response = dataverse.check_token()

        # assert
        self.assertTrue(response)

    def test_get_files_from_dataset(self):
        """testing get_files_from_dataset"""
        # arrange
        dataverse = Dataverse(api_key=api_key, api_address=api_address)

        persistent_id = "doi:10.80227/PDVNL/LKOHUC"
        call_url = f"/datasets/:persistentId"
        query = {"persistentId": persistent_id}

        pact.given("dataset can be retrieved for LKOHUC").upon_receiving(
            "the corresponding response with the dataset info"
        ).with_request("GET", call_url, query=query).will_respond_with(
            200,
            body={
                "status": "OK",
                "data": {
                    "id": 2967,
                    "identifier": "PDVNL/LKOHUC",
                    "persistentUrl": "https://doi.org/10.80227/PDVNL/LKOHUC",
                    "protocol": "doi",
                    "authority": "10.80227",
                    "publisher": "DataverseNL (demo)",
                    "storageIdentifier": "file://10.80227/PDVNL/LKOHUC",
                    "latestVersion": {
                        "id": 1154,
                        "datasetId": 2967,
                        "datasetPersistentId": "doi:10.80227/PDVNL/LKOHUC",
                        "storageIdentifier": "file://10.80227/PDVNL/LKOHUC",
                        "versionState": "DRAFT",
                        "latestVersionPublishingState": "DRAFT",
                        "lastUpdateTime": "2024-12-12T14:04:50Z",
                        "createTime": "2024-12-12T14:04:50Z",
                        "fileAccessRequest": True,
                        "metadataBlocks": {
                            "citation": {
                                "displayName": "Citation Metadata",
                                "name": "citation",
                                "fields": [
                                    {
                                        "typeName": "title",
                                        "multiple": False,
                                        "typeClass": "primitive",
                                        "value": "untitled",
                                    },
                                    {
                                        "typeName": "author",
                                        "multiple": True,
                                        "typeClass": "compound",
                                        "value": [
                                            {
                                                "authorName": {
                                                    "typeName": "authorName",
                                                    "multiple": False,
                                                    "typeClass": "primitive",
                                                    "value": "not set",
                                                },
                                                "authorAffiliation": {
                                                    "typeName": "authorAffiliation",
                                                    "multiple": False,
                                                    "typeClass": "primitive",
                                                    "value": "not set",
                                                },
                                            }
                                        ],
                                    },
                                    {
                                        "typeName": "datasetContact",
                                        "multiple": True,
                                        "typeClass": "compound",
                                        "value": [
                                            {
                                                "datasetContactName": {
                                                    "typeName": "datasetContactName",
                                                    "multiple": False,
                                                    "typeClass": "primitive",
                                                    "value": "not set",
                                                }
                                            }
                                        ],
                                    },
                                    {
                                        "typeName": "dsDescription",
                                        "multiple": True,
                                        "typeClass": "compound",
                                        "value": [
                                            {
                                                "dsDescriptionValue": {
                                                    "typeName": "dsDescriptionValue",
                                                    "multiple": False,
                                                    "typeClass": "primitive",
                                                    "value": "not set",
                                                }
                                            }
                                        ],
                                    },
                                    {
                                        "typeName": "subject",
                                        "multiple": True,
                                        "typeClass": "controlledVocabulary",
                                        "value": ["Other"],
                                    },
                                ],
                            }
                        },
                        "files": [
                            {
                                "description": "Blue skies!",
                                "label": "dataverse.png",
                                "restricted": False,
                                "version": 1,
                                "datasetVersionId": 225669,
                                "categories": ["Jack of Hearts", "Lily", "Rosemary"],
                                "dataFile": {
                                    "id": 2023741,
                                    "persistentId": "",
                                    "pidURL": "",
                                    "filename": "dataverse.png",
                                    "contentType": "image/png",
                                    "filesize": 22688,
                                    "description": "Blue skies!",
                                    "storageIdentifier": "s3://demo-dataverse-org:1862b5280c4-053bbecef4d5",
                                    "rootDataFileId": -1,
                                    "md5": "cf3b4d8ac22c5b98898f9a0fd74c0e1f",
                                    "checksum": {
                                        "type": "MD5",
                                        "value": "cf3b4d8ac22c5b98898f9a0fd74c0e1f",
                                    },
                                    "creationDate": "2023-02-07",
                                },
                            }
                        ],
                    },
                },
            },
        )

        # act
        with pact:
            response = dataverse.get_files_from_dataset(persistent_id)

        # assert
        self.assertEqual(response[0]["label"], "dataverse.png")

    def test_get_latest_persistent_id(self):
        """testing the get_latest_persistent_id method"""
        # arrange
        dataverse = Dataverse(api_key=api_key, api_address=api_address)
        persistent_id = "doi:10.80227/PDVNL/SR3ZVF"
        url = f"/dataverses/surf/contents"

        body = {
            "status": "OK",
            "data": [
                {
                    "type": "dataverse",
                    "id": 1099,
                    "title": "Dave Tromp Test Sub Dataverse",
                },
                {"type": "dataverse", "id": 1186, "title": "davetrompcom"},
                {
                    "id": 1045,
                    "identifier": "PDVNL/5UGA1W",
                    "persistentUrl": "https://doi.org/10.80227/PDVNL/5UGA1W",
                    "protocol": "doi",
                    "authority": "10.80227",
                    "publisher": "DataverseNL (demo)",
                    "storageIdentifier": "file://10.80227/PDVNL/5UGA1W",
                    "type": "dataset",
                },
                {
                    "id": 1130,
                    "identifier": "PDVNL/GLEOV2",
                    "persistentUrl": "https://doi.org/10.80227/PDVNL/GLEOV2",
                    "protocol": "doi",
                    "authority": "10.80227",
                    "publisher": "DataverseNL (demo)",
                    "storageIdentifier": "file://10.80227/PDVNL/GLEOV2",
                    "type": "dataset",
                },
                {
                    "id": 1182,
                    "identifier": "PDVNL/KSQSCD",
                    "persistentUrl": "https://doi.org/10.80227/PDVNL/KSQSCD",
                    "protocol": "doi",
                    "authority": "10.80227",
                    "publisher": "DataverseNL (demo)",
                    "storageIdentifier": "file://10.80227/PDVNL/KSQSCD",
                    "type": "dataset",
                },
                {
                    "id": 1524,
                    "identifier": "PDVNL/0MV0IG",
                    "persistentUrl": "https://doi.org/10.80227/PDVNL/0MV0IG",
                    "protocol": "doi",
                    "authority": "10.80227",
                    "publisher": "DataverseNL (demo)",
                    "storageIdentifier": "file://10.80227/PDVNL/0MV0IG",
                    "type": "dataset",
                },
                {
                    "id": 1531,
                    "identifier": "PDVNL/4GUZQA",
                    "persistentUrl": "https://doi.org/10.80227/PDVNL/4GUZQA",
                    "protocol": "doi",
                    "authority": "10.80227",
                    "publisher": "DataverseNL (demo)",
                    "storageIdentifier": "file://10.80227/PDVNL/4GUZQA",
                    "type": "dataset",
                },
                {
                    "id": 1555,
                    "identifier": "PDVNL/USOVNI",
                    "persistentUrl": "https://doi.org/10.80227/PDVNL/USOVNI",
                    "protocol": "doi",
                    "authority": "10.80227",
                    "publisher": "DataverseNL (demo)",
                    "storageIdentifier": "file://10.80227/PDVNL/USOVNI",
                    "type": "dataset",
                },
                {
                    "id": 1565,
                    "identifier": "PDVNL/2BLSLN",
                    "persistentUrl": "https://doi.org/10.80227/PDVNL/2BLSLN",
                    "protocol": "doi",
                    "authority": "10.80227",
                    "publisher": "DataverseNL (demo)",
                    "storageIdentifier": "file://10.80227/PDVNL/2BLSLN",
                    "type": "dataset",
                },
                {
                    "id": 1581,
                    "identifier": "PDVNL/JF7IPC",
                    "persistentUrl": "https://doi.org/10.80227/PDVNL/JF7IPC",
                    "protocol": "doi",
                    "authority": "10.80227",
                    "publisher": "DataverseNL (demo)",
                    "storageIdentifier": "file://10.80227/PDVNL/JF7IPC",
                    "type": "dataset",
                },
                {
                    "id": 1588,
                    "identifier": "PDVNL/DSHETT",
                    "persistentUrl": "https://doi.org/10.80227/PDVNL/DSHETT",
                    "protocol": "doi",
                    "authority": "10.80227",
                    "publisher": "DataverseNL (demo)",
                    "storageIdentifier": "file://10.80227/PDVNL/DSHETT",
                    "type": "dataset",
                },
                {
                    "id": 1599,
                    "identifier": "PDVNL/Y0LWFV",
                    "persistentUrl": "https://doi.org/10.80227/PDVNL/Y0LWFV",
                    "protocol": "doi",
                    "authority": "10.80227",
                    "publisher": "DataverseNL (demo)",
                    "storageIdentifier": "file://10.80227/PDVNL/Y0LWFV",
                    "type": "dataset",
                },
                {
                    "id": 1609,
                    "identifier": "PDVNL/5RQKAH",
                    "persistentUrl": "https://doi.org/10.80227/PDVNL/5RQKAH",
                    "protocol": "doi",
                    "authority": "10.80227",
                    "publisher": "DataverseNL (demo)",
                    "storageIdentifier": "file://10.80227/PDVNL/5RQKAH",
                    "type": "dataset",
                },
                {
                    "id": 1616,
                    "identifier": "PDVNL/8RBP1M",
                    "persistentUrl": "https://doi.org/10.80227/PDVNL/8RBP1M",
                    "protocol": "doi",
                    "authority": "10.80227",
                    "publisher": "DataverseNL (demo)",
                    "storageIdentifier": "file://10.80227/PDVNL/8RBP1M",
                    "type": "dataset",
                },
                {
                    "id": 1679,
                    "identifier": "PDVNL/RZYSVD",
                    "persistentUrl": "https://doi.org/10.80227/PDVNL/RZYSVD",
                    "protocol": "doi",
                    "authority": "10.80227",
                    "publisher": "DataverseNL (demo)",
                    "storageIdentifier": "file://10.80227/PDVNL/RZYSVD",
                    "type": "dataset",
                },
                {
                    "id": 1690,
                    "identifier": "PDVNL/3LOT4O",
                    "persistentUrl": "https://doi.org/10.80227/PDVNL/3LOT4O",
                    "protocol": "doi",
                    "authority": "10.80227",
                    "publisher": "DataverseNL (demo)",
                    "storageIdentifier": "file://10.80227/PDVNL/3LOT4O",
                    "type": "dataset",
                },
                {
                    "id": 2364,
                    "identifier": "PDVNL/FY2SAT",
                    "persistentUrl": "https://doi.org/10.80227/PDVNL/FY2SAT",
                    "protocol": "doi",
                    "authority": "10.80227",
                    "publisher": "DataverseNL (demo)",
                    "storageIdentifier": "file://10.80227/PDVNL/FY2SAT",
                    "type": "dataset",
                },
                {
                    "id": 2832,
                    "identifier": "PDVNL/W0EOO4",
                    "persistentUrl": "https://doi.org/10.80227/PDVNL/W0EOO4",
                    "protocol": "doi",
                    "authority": "10.80227",
                    "publisher": "DataverseNL (demo)",
                    "storageIdentifier": "file://10.80227/PDVNL/W0EOO4",
                    "type": "dataset",
                },
                {
                    "id": 2998,
                    "identifier": "PDVNL/SR3ZVF",
                    "persistentUrl": "https://doi.org/10.80227/PDVNL/SR3ZVF",
                    "protocol": "doi",
                    "authority": "10.80227",
                    "publisher": "DataverseNL (demo)",
                    "storageIdentifier": "file://10.80227/PDVNL/SR3ZVF",
                    "type": "dataset",
                },
            ],
        }

        pact.given("get latest id").upon_receiving(
            "the corresponding response with all datasets / contents"
        ).with_request("get", url).will_respond_with(
            200,
            body=body,
        )

        url = "/datasets/2998/"
        body = {
            "status": "OK",
            "data": {
                "id": 2998,
                "identifier": "PDVNL/SR3ZVF",
                "persistentUrl": "https://doi.org/10.80227/PDVNL/SR3ZVF",
                "protocol": "doi",
                "authority": "10.80227",
                "publisher": "DataverseNL (demo)",
                "storageIdentifier": "file://10.80227/PDVNL/SR3ZVF",
                "latestVersion": {
                    "id": 1365,
                    "datasetId": 2998,
                    "datasetPersistentId": "doi:10.80227/PDVNL/SR3ZVF",
                    "storageIdentifier": "file://10.80227/PDVNL/SR3ZVF",
                    "versionState": "DRAFT",
                    "latestVersionPublishingState": "DRAFT",
                    "lastUpdateTime": "2025-01-13T11:08:38Z",
                    "createTime": "2025-01-13T11:08:38Z",
                    "fileAccessRequest": True,
                    "metadataBlocks": {
                        "citation": {
                            "displayName": "Citation Metadata",
                            "name": "citation",
                            "fields": [
                                {
                                    "typeName": "title",
                                    "multiple": False,
                                    "typeClass": "primitive",
                                    "value": "untitled",
                                },
                                {
                                    "typeName": "author",
                                    "multiple": True,
                                    "typeClass": "compound",
                                    "value": [
                                        {
                                            "authorName": {
                                                "typeName": "authorName",
                                                "multiple": False,
                                                "typeClass": "primitive",
                                                "value": "not set",
                                            },
                                            "authorAffiliation": {
                                                "typeName": "authorAffiliation",
                                                "multiple": False,
                                                "typeClass": "primitive",
                                                "value": "not set",
                                            },
                                        }
                                    ],
                                },
                                {
                                    "typeName": "datasetContact",
                                    "multiple": True,
                                    "typeClass": "compound",
                                    "value": [
                                        {
                                            "datasetContactName": {
                                                "typeName": "datasetContactName",
                                                "multiple": False,
                                                "typeClass": "primitive",
                                                "value": "not set",
                                            }
                                        }
                                    ],
                                },
                                {
                                    "typeName": "dsDescription",
                                    "multiple": True,
                                    "typeClass": "compound",
                                    "value": [
                                        {
                                            "dsDescriptionValue": {
                                                "typeName": "dsDescriptionValue",
                                                "multiple": False,
                                                "typeClass": "primitive",
                                                "value": "not set",
                                            }
                                        }
                                    ],
                                },
                                {
                                    "typeName": "subject",
                                    "multiple": True,
                                    "typeClass": "controlledVocabulary",
                                    "value": ["Other"],
                                },
                            ],
                        }
                    },
                    "files": [],
                },
            },
        }

        pact.given("get persistent id").upon_receiving(
            "the corresponding response with persistend id info"
        ).with_request("get", url).will_respond_with(
            200,
            body=body,
        )

        # act
        with pact:
            latest_persistent_id = dataverse.get_latest_persistent_id()

        # assert
        self.assertEqual(latest_persistent_id, persistent_id)

    def test_get_persistent_id_with_id(self):
        """testing the get_persistent_id_with_id method
        """
        # arrange
        dataverse = Dataverse(api_key=api_key, api_address=api_address)
        
        id = 2998
        persistent_id = "doi:10.80227/PDVNL/SR3ZVF"
        url = "/datasets/2998/"
        body = {
            "status": "OK",
            "data": {
                "id": 2998,
                "identifier": "PDVNL/SR3ZVF",
                "persistentUrl": "https://doi.org/10.80227/PDVNL/SR3ZVF",
                "protocol": "doi",
                "authority": "10.80227",
                "publisher": "DataverseNL (demo)",
                "storageIdentifier": "file://10.80227/PDVNL/SR3ZVF",
                "latestVersion": {
                    "id": 1365,
                    "datasetId": 2998,
                    "datasetPersistentId": "doi:10.80227/PDVNL/SR3ZVF",
                    "storageIdentifier": "file://10.80227/PDVNL/SR3ZVF",
                    "versionState": "DRAFT",
                    "latestVersionPublishingState": "DRAFT",
                    "lastUpdateTime": "2025-01-13T11:08:38Z",
                    "createTime": "2025-01-13T11:08:38Z",
                    "fileAccessRequest": True,
                    "metadataBlocks": {
                        "citation": {
                            "displayName": "Citation Metadata",
                            "name": "citation",
                            "fields": [
                                {
                                    "typeName": "title",
                                    "multiple": False,
                                    "typeClass": "primitive",
                                    "value": "untitled",
                                },
                                {
                                    "typeName": "author",
                                    "multiple": True,
                                    "typeClass": "compound",
                                    "value": [
                                        {
                                            "authorName": {
                                                "typeName": "authorName",
                                                "multiple": False,
                                                "typeClass": "primitive",
                                                "value": "not set",
                                            },
                                            "authorAffiliation": {
                                                "typeName": "authorAffiliation",
                                                "multiple": False,
                                                "typeClass": "primitive",
                                                "value": "not set",
                                            },
                                        }
                                    ],
                                },
                                {
                                    "typeName": "datasetContact",
                                    "multiple": True,
                                    "typeClass": "compound",
                                    "value": [
                                        {
                                            "datasetContactName": {
                                                "typeName": "datasetContactName",
                                                "multiple": False,
                                                "typeClass": "primitive",
                                                "value": "not set",
                                            }
                                        }
                                    ],
                                },
                                {
                                    "typeName": "dsDescription",
                                    "multiple": True,
                                    "typeClass": "compound",
                                    "value": [
                                        {
                                            "dsDescriptionValue": {
                                                "typeName": "dsDescriptionValue",
                                                "multiple": False,
                                                "typeClass": "primitive",
                                                "value": "not set",
                                            }
                                        }
                                    ],
                                },
                                {
                                    "typeName": "subject",
                                    "multiple": True,
                                    "typeClass": "controlledVocabulary",
                                    "value": ["Other"],
                                },
                            ],
                        }
                    },
                    "files": [],
                },
            },
        }

        pact.given("get persistent id").upon_receiving(
            "the corresponding response with persistend id info"
        ).with_request("get", url).will_respond_with(
            200,
            body=body,
        )

        # act
        with pact:
            new_persistent_id = dataverse.get_persistent_id_with_id(id)

        # assert - needs to be done before we remove the created dataset
        self.assertEqual(new_persistent_id, persistent_id)


if __name__ == "__main__":
    unittest.main()
