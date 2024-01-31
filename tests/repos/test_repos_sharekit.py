import configparser
import logging
import os
import sys
from time import sleep
import unittest
import pytest

from app.repos.sharekit import Sharekit

log = logging.getLogger()

try:
    config = configparser.ConfigParser()
    config.read('env.ini')
except Exception as e:
    config = None
    log.error(str(e))


try:
    api_key = os.getenv(
        "SHAREKIT_API_KEY",
        config.get('TESTS', 'SHAREKIT_API_KEY')
    )
except Exception as e:
    log.error(f"Could not get an api_key for testing: {str(e)}")
    log.info("Halting tests")
    sys.exit()

api_address = os.getenv(
    "SHAREKIT_API_ADDRESS",
    "https://api.acc.surfsharekit.nl/api"
)

# adding some sleep time between tests as to not overwhelm the sharekit api.
# Not sure if this is needed, but it won't hurt.
sleep_time = 1


class TestSharekitMethodsNew(unittest.TestCase):
    """Test for the methods implemented for sharekit.

    Tests are written according to the Arrange - Act -Assert design pattern.

    Before asserting we will do any needed cleanup, because after a possible failed assert
    the test is exited and cleanup will not happen if we try it after the assert.

    Tests need the SHAREKIT_API_KEY to be available either as an ENV VAR or
    as a variable in the local-env.ini file.

    Args:
        unittest (base): basic testcase from the unittest lib
    """

    def test_get_item(self):
        """testing the get_item method.
        """
        # arrange
        sleep(sleep_time)
        sharekit = Sharekit(api_key=api_key, api_address=api_address)

        # act and assert
        with pytest.raises(NotImplementedError):
            sharekit.get_item(id="not implemented", return_response=True)

    def test_create_new_item(self):
        """testing the create_new_item method
        """
        # arrange
        sleep(sleep_time)
        sharekit = Sharekit(api_key=api_key, api_address=api_address)

        # act
        response = sharekit.create_new_item(return_response=True)

        # assert
        self.assertEqual(response.status_code, 201)
        self.assertTrue(type(response.json()['id']) is str)

    def test_remove_item(self):
        """testing the remove_item method
        """
        # arrange
        sleep(sleep_time)
        sharekit = Sharekit(api_key=api_key, api_address=api_address)

        # act and assert
        with pytest.raises(NotImplementedError):
            sharekit.remove_item(id='not implemented', return_response=True)

    @unittest.skip
    def test_upload_new_file_to_item(self):
        """testing the upload_new_file_to_item method
        """
        # arrange
        sleep(sleep_time)
        sharekit = Sharekit(api_key=api_key, api_address=api_address)
        item_id = "not implemented yet"
        path_to_file = "./app/static/img/sharekit.png"

        # act
        response = sharekit.upload_new_file_to_item(
            item_id, path_to_file, file=None, test=True)

        # assert
        self.assertEqual(response, True)

    def test_change_metadata_in_item(self):
        """testing the change_metadata_in_item method.
        """
        # arrange
        sleep(sleep_time)
        sharekit = Sharekit(api_key=api_key, api_address=api_address)
        item_id = "not implemented yet"
        metadata = {"title": "test"}

        # act and assert
        with pytest.raises(NotImplementedError):
            sharekit.change_metadata_in_item(
                item_id, metadata, return_response=True)

    def test_publish_item(self):
        """Will not test publish_item method as published items cannot be removed.
        """
        # arrange
        sleep(sleep_time)
        sharekit = Sharekit(api_key=api_key, api_address=api_address)
        item_id = "not implemented yet"

        # act and assert
        with pytest.raises(NotImplementedError):
            sharekit.publish_item(item_id=item_id)

    def test_delete_all_files_from_item(self):
        """testing delete_all_files_item
        """
        # arrange
        sleep(sleep_time)
        sharekit = Sharekit(api_key=api_key, api_address=api_address)
        item_id = "not implemented yet"


        # act and assert
        with pytest.raises(NotImplementedError):
            sharekit.delete_all_files_from_item_internal(item_id)

    def test_check_token(self):
        """testing check_token
        """
        # arrange
        sleep(sleep_time)
        sharekit = Sharekit(api_key=api_key, api_address=api_address)

        # act
        response = sharekit.check_token(api_key)

        # assert
        self.assertTrue(response)

    def test_get_files_from_item(self):
        """testing get_files_from_item
        """
        # arrange
        sleep(sleep_time)
        sharekit = Sharekit(api_key=api_key, api_address=api_address)
        item_id = "not implemented yet"
        
        # act and assert
        with pytest.raises(NotImplementedError):
            sharekit.get_files_from_item(item_id)


if __name__ == '__main__':
    unittest.main()
