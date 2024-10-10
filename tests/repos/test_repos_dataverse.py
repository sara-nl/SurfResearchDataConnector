import configparser
import logging
import os
import sys
from time import sleep
import unittest

from app.repos.dataverse import Dataverse

log = logging.getLogger()

try:
    config = configparser.ConfigParser()
    config.read('env.ini')
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
    "https://demo.dataverse.nl/api"
)

# adding some sleep time between tests as to not overwhelm the dataverse api.
# Not sure if this is needed, but it won't hurt.
sleep_time = 1

class TestDataverseMethodsNew(unittest.TestCase):
    """Test for the methods implemented for dataverse.
    
    Tests are written according to the Arrange - Act -Assert design pattern.
    
    Before asserting we will do any needed cleanup, because after a possible failed assert
    the test is exited and cleanup will not happen if we try it after the assert.

    Tests need the DATAVERSE_API_KEY to be available either as an ENV VAR or
    as a variable in the local-env.ini file.

    Args:
        unittest (base): basic testcase from the unittest lib
    """

    def test_get_dataset(self):
        """testing the get_dataset method by creating an dataset and then get it and
        checking if we get a 200 response.
        """
        # arrange
        sleep(sleep_time)
        dataverse = Dataverse(api_key=api_key, api_address=api_address)
        persistent_id = dataverse.create_new_dataset()['data']['persistentId']

        # act
        response = dataverse.get_dataset(persistent_id, return_response=True)

        # cleanup
        dataverse.remove_dataset(persistent_id)

        # assert
        self.assertEqual(response.status_code, 200)

    def test_create_new_dataset(self):
        """testing the create_new_dataset method
        """
        # arrange
        sleep(sleep_time)
        dataverse = Dataverse(api_key=api_key, api_address=api_address)

        # act
        response = dataverse.create_new_dataset(return_response=True)
        persistent_id = response.json()['data']['persistentId']

        # cleanup
        dataverse.remove_dataset(persistent_id)

        # assert
        self.assertEqual(response.status_code, 201)
        self.assertTrue(type(persistent_id) is str)

    def test_remove_dataset(self):
        """testing the remove_dataset method
        """
        # arrange
        sleep(sleep_time)
        dataverse = Dataverse(api_key=api_key, api_address=api_address)
        persistent_id = dataverse.create_new_dataset()['data']['persistentId']

        # act
        response = dataverse.remove_dataset(persistent_id, return_response=True)

        # assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], "OK")

    def test_upload_new_file_to_dataset(self):
        """testing the upload_new_file_to_dataset method
        """
        # arrange
        sleep(sleep_time)
        dataverse = Dataverse(api_key=api_key, api_address=api_address)
        persistent_id = dataverse.create_new_dataset()['data']['persistentId']
        path_to_file = "./app/static/img/dataverse.png"

        # act
        response = dataverse.upload_new_file_to_dataset(
            persistent_id, path_to_file, return_response=True, test=True)

        files = dataverse.get_files_from_dataset(persistent_id=persistent_id)

        # cleanup
        dataverse.remove_dataset(persistent_id)

        # assert
        self.assertEqual(response.json()['status'], 'OK')
        self.assertEqual(len(response.json()['data']['files']), 1)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(files[0]["label"], "dataverse.png")

    def test_change_metadata_in_dataset(self):
        """testing the change_metadata_in_dataset method.
        """
        # arrange
        sleep(sleep_time)
        dataverse = Dataverse(api_key=api_key, api_address=api_address)
        persistent_id = dataverse.create_new_dataset()['data']['persistentId']
        metadata = dataverse.set_metadata()
        log.debug(f"############### meta: {metadata}")
        for item in metadata['metadataBlocks']['citation']['fields']:
            if item['typeName'] == 'title':
                item['value'] = 'My first upload'
        # act
        response = dataverse.change_metadata_in_dataset(
            persistent_id=persistent_id, metadata=metadata, return_response=True).json()
        log.debug(f"###  response: {response}")
        
        dataset = dataverse.get_dataset(persistent_id=persistent_id, return_response=True)
        log.debug(dataset.json())

        # # cleanup
        dataverse.remove_dataset(persistent_id)

        # assert
        title = ""
        fields = dataset.json()['data']['latestVersion']['metadataBlocks']['citation']['fields']
        log.debug(fields)
        for field in fields:
            if field['typeName'] == "title":
                title = field['value']
        self.assertEqual(title, "My first upload")


    @unittest.skip
    def test_publish_dataset(self):
        """Will not test publish_dataset method as published articles cannot be removed.
        """
        log.info(
            "Will not test publish_dataset method as published articles cannot be removed.")
        pass
        # arrange
        # sleep(sleep_time)
        # dataverse = Dataverse(api_key=api_key, api_address=api_address)
        # persistent_id = dataverse.create_new_dataset()['data']['persistentId']

        # # articles can only be published with set categories, keywords and description
        # metadata = {"title" : "test dataset",
        #             "description": "Test description of test dataset",
        #             "keywords": ["test1"],
        #             "categories_by_source_id": ["300204", "400207"]
        #             }
        # setmeta = dataverse.change_metadata_in_dataset(persistent_id=persistent_id, metadata=metadata, return_response=True)
        # log.info(setmeta.status_code, setmeta.json())

        # # act
        # response = dataverse.publish_dataset(persistent_id=persistent_id, return_response=True)

        # cleanup
        # dataverse.remove_dataset(persistent_id)

        # assert
        # self.assertEqual(response.status_code, 201)

    @unittest.skip
    def test_delete_all_files_from_dataset(self):
        """testing delete_all_files_dataset
        """
        # arrange
        sleep(sleep_time)
        dataverse = Dataverse(api_key=api_key, api_address=api_address)
        persistent_id = dataverse.create_new_dataset()['data']['persistentId']
        path_to_file = "./app/static/img/dataverse.png"
        dataverse.upload_new_file_to_dataset(
            persistent_id, path_to_file, return_response=False, test=True)

        # act
        response = dataverse.delete_all_files_from_dataset_internal(persistent_id)

        # cleanup
        dataverse.remove_dataset(persistent_id)

        # assert
        self.assertTrue(response)

    def test_check_token(self):
        """testing check_token
        """
        # arrange
        sleep(sleep_time)
        dataverse = Dataverse(api_key=api_key, api_address=api_address)

        # act
        response = dataverse.check_token()

        # assert
        self.assertTrue(response)

    def test_get_files_from_dataset(self):
        """testing get_files_from_dataset
        """
        # arrange
        sleep(sleep_time)
        dataverse = Dataverse(api_key=api_key, api_address=api_address)
        persistent_id = dataverse.create_new_dataset()['data']['persistentId']
        path_to_file = "./app/static/img/dataverse.png"
        dataverse.upload_new_file_to_dataset(
            persistent_id, path_to_file, return_response=False, test=True)

        # act
        response = dataverse.get_files_from_dataset(persistent_id)
        log.debug(response)

        # cleanup
        dataverse.remove_dataset(persistent_id)

        # assert
        self.assertEqual(response[0]['label'], 'dataverse.png')


    def test_get_latest_persistent_id(self):
        """testing the get_latest_persistent_id method
        """
        # arrange
        sleep(sleep_time)
        dataverse = Dataverse(api_key=api_key, api_address=api_address)
        persistent_id = dataverse.create_new_dataset()['data']['persistentId']

        # act
        latest_persistent_id = dataverse.get_latest_persistent_id()

        # cleanup
        response = dataverse.remove_dataset(persistent_id, return_response=True)

        # assert
        self.assertEqual(latest_persistent_id, persistent_id)
        

    def test_get_persistent_id_with_id(self):
        """testing the get_persistent_id_with_id method
        """
        # arrange
        sleep(sleep_time)
        dataverse = Dataverse(api_key=api_key, api_address=api_address)
        dataset = dataverse.create_new_dataset()
        id = dataset['data']['id']
        persistent_id = dataset['data']['persistentId']

        # act
        new_persistent_id = dataverse.get_persistent_id_with_id(id)

        # assert - needs to be done before we remove the created dataset
        self.assertEqual(new_persistent_id, persistent_id)

        # cleanup
        dataverse.remove_dataset(persistent_id, return_response=True)


if __name__ == '__main__':
    unittest.main()
