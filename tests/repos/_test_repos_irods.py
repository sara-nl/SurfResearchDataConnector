import configparser
import logging
import os
import sys
from time import sleep
import unittest

from app.repos.irods import Irods, zone, folder

log = logging.getLogger()

try:
    config = configparser.ConfigParser()
    config.read('env.ini')
except Exception as e:
    config = None
    log.error(str(e))


try:
    api_key = os.getenv(
        "IRODS_API_KEY",
        config.get('TESTS', 'IRODS_API_KEY')
    )
except Exception as e:
    log.error(f"Could not get an api_key for testing: {str(e)}")
    log.info("Halting tests")
    sys.exit()

api_address = os.getenv(
    "API_ADDRESS",
    "scuba-yoda.irods.surfsara.nl"
)

user = os.getenv(
    "IRODS_USER",
    config.get('TESTS', 'IRODS_USER')
)

# adding some sleep time between tests as to not overwhelm the irods api.
# Not sure if this is needed, but it won't hurt.
sleep_time = 1

class TestIrodsMethodsNew(unittest.TestCase):
    """Test for the methods implemented for irods.
    
    Tests are written according to the Arrange - Act -Assert design pattern.
    
    Before asserting we will do any needed cleanup, because after a possible failed assert
    the test is exited and cleanup will not happen if we try it after the assert.

    Tests need the IRODS_API_KEY and IRODS_USER to be available either as an ENV VAR or
    as a variable in the local-env.ini file. The IRODS_API_KEY is only valid for 72 hrs.

    Args:
        unittest (base): basic testcase from the unittest lib
    """

    def test_get_collection(self):
        """testing the get_collection method by creating an collection and then get it and
        checking if we get a response where path in the reponse is same as the one created
        while arranging the test.
        """
        # arrange
        sleep(sleep_time)
        irods = Irods(api_key=api_key, api_address=api_address, user=user)
        collection_path = irods.create_new_collection()['path']

        # act
        response = irods.get_collection(path=f"/{zone}/home/{folder}/")
        get_collection_paths = []
        for item in response:
            get_collection_paths.append(item['path'])

        # cleanup
        irods.remove_collection(collection_path)

        # assert
        self.assertIn(collection_path, get_collection_paths)

    def test_create_new_collection(self):
        """testing the create_new_collection method
        """
        # arrange
        sleep(sleep_time)
        irods = Irods(api_key=api_key, api_address=api_address, user=user)

        # act
        response = irods.create_new_collection()
        collection_path = response['path']

        # cleanup
        irods.remove_collection(collection_path)

        # assert
        self.assertTrue(type(collection_path) is str)
        self.assertTrue(type(response) is dict)

    def test_remove_collection(self):
        """testing the remove_collection method
        """
        # arrange
        sleep(sleep_time)
        irods = Irods(api_key=api_key, api_address=api_address, user=user)
        collection_path = irods.create_new_collection()['path']

        # act
        response = irods.remove_collection(collection_path)

        # assert
        self.assertTrue(response)

    def test_upload_new_file_to_collection(self):
        """testing the upload_new_file_to_collection method
        """
        # arrange
        sleep(sleep_time)
        irods = Irods(api_key=api_key, api_address=api_address, user=user)
        collection_path = irods.create_new_collection()['path']
        path_to_file = "./app/static/img/irods.png"

        # act
        response = irods.upload_new_file_to_collection(
            collection_path, path_to_file, test=True)

        # cleanup
        irods.remove_collection(collection_path)

        # assert
        self.assertEqual(response, True)

    @unittest.skip
    def test_change_metadata_in_collection(self):
        """testing the change_metadata_in_collection method.
        """
        # arrange
        sleep(sleep_time)
        irods = Irods(api_key=api_key, api_address=api_address, user=user)
        collection_path = irods.create_new_collection()['path']
        metadata = {"title": "test"}

        # act
        response = irods.change_metadata_in_collection(collection_path, metadata)
        
        collection = irods.get_collection(collection_path)

        # cleanup
        irods.remove_collection(collection_path)

        # assert
        self.assertEqual(collection['metadata']['title'], "test")

    @unittest.skip
    def test_publish_collection(self):
        """Will not test publish_collection method as published collections cannot be removed.
        """
        log.info(
            "Will not test publish_collection method as published collections cannot be removed.")
        pass
        # arrange
        # sleep(sleep_time)
        # irods = Irods(api_key=api_key, api_address=api_address, user=user)
        # collection_path = int(irods.create_new_collection()['entity_id'])

        # # collections can only be published with set categories, keywords and description
        # metadata = {"title" : "test collection",
        #             "description": "Test description of test collection",
        #             "keywords": ["test1"],
        #             "categories_by_source_id": ["300204", "400207"]
        #             }
        # setmeta = irods.change_metadata_in_collection(collection_path=collection_path, metadata=metadata)
        # log.info(setmeta.status_code, setmeta.json())

        # # act
        # response = irods.publish_collection(collection_path=collection_path)

        # cleanup
        # irods.remove_collection(collection_path)

        # assert
        # self.assertEqual(response.status_code, 201)

    def test_delete_all_files_from_collection(self):
        """testing delete_all_files_collection
        """
        # arrange
        sleep(sleep_time)
        irods = Irods(api_key=api_key, api_address=api_address, user=user)
        collection_path = irods.create_new_collection()['path']
        path_to_file = "./app/static/img/irods.png"
        irods.upload_new_file_to_collection(
            collection_path, path_to_file, test=True)

        # act
        response = irods.delete_all_files_from_collection_internal(collection_path)

        # cleanup
        irods.remove_collection(collection_path)

        # assert
        self.assertTrue(response)

    def test_check_token(self):
        """testing check_token
        """
        # arrange
        sleep(sleep_time)
        irods = Irods(api_key=api_key, api_address=api_address, user=user)

        # act
        response = irods.check_token(api_key=api_key, user=user)

        # assert
        self.assertTrue(response)

    def test_get_files_from_collection(self):
        """testing get_files_from_collection
        """
        # arrange
        sleep(sleep_time)
        irods = Irods(api_key=api_key, api_address=api_address, user=user)
        collection_path = irods.create_new_collection()['path']
        path_to_file = "./app/static/img/irods.png"
        irods.upload_new_file_to_collection(
            collection_path, path_to_file, test=True)

        # act
        response = irods.get_files_from_collection(collection_path)

        # cleanup
        irods.remove_collection(collection_path)

        # assert
        self.assertEqual(response[0], f"{collection_path}/irods.png")


if __name__ == '__main__':
    unittest.main()
