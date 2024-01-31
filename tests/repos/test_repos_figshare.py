import configparser
import logging
import os
import sys
from time import sleep
import unittest

from app.repos.figshare import Figshare

log = logging.getLogger()

try:
    config = configparser.ConfigParser()
    config.read('env.ini')
except Exception as e:
    config = None
    log.error(str(e))


try:
    api_key = os.getenv(
        "FIGSHARE_API_KEY",
        config.get('TESTS', 'FIGSHARE_API_KEY')
    )
except Exception as e:
    log.error(f"Could not get an api_key for testing: {str(e)}")
    log.info("Halting tests")
    sys.exit()

api_address = os.getenv(
    "API_ADDRESS",
    "https://api.figshare.com/v2"
)

# adding some sleep time between tests as to not overwhelm the figshare api.
# Not sure if this is needed, but it won't hurt.
sleep_time = 1

class TestFigshareMethodsNew(unittest.TestCase):
    """Test for the methods implemented for figshare.
    
    Tests are written according to the Arrange - Act -Assert design pattern.
    
    Before asserting we will do any needed cleanup, because after a possible failed assert
    the test is exited and cleanup will not happen if we try it after the assert.

    Tests need the FIGSHARE_API_KEY to be available either as an ENV VAR or
    as a variable in the local-env.ini file.

    Args:
        unittest (base): basic testcase from the unittest lib
    """

    def test_raw_issue_request(self):
        """testing the raw_issue_request method by checking if the response of the
        /account/articles/ endpoint can be called and returns proper response.
        """
        # arrange
        sleep(sleep_time)
        figshare = Figshare(api_key=api_key, api_address=api_address)

        # act
        response = figshare.raw_issue_request(
            method="GET", url=f"{api_address}/account/articles", data=None, binary=False)

        # assert
        self.assertTrue(type(response) is list)
        if len(response) > 0:
            self.assertTrue(type(response[0]['id']) is int)

    def test_issue_request(self):
        """testing the issue_request method by checking if the response of the
        /account/articles/ endpoint can be called and returns proper response.
        """
        # arrange
        sleep(sleep_time)
        figshare = Figshare(api_key=api_key, api_address=api_address)

        # act
        response = figshare.issue_request(
            method="GET", endpoint="/account/articles")

        # assert
        self.assertTrue(type(response) is list)
        if len(response) > 0:
            self.assertTrue(type(response[0]['id']) is int)

    def test_get_file_check_data(self):
        """testing the get_file_check_data method by checking if the input to the file_path
        returns correct output
        """
        # arrange
        sleep(sleep_time)
        figshare = Figshare(api_key=api_key, api_address=api_address)

        # act
        response = figshare.get_file_check_data('./app/static/img/figshare.png')

        # assert
        self.assertEqual(response, ('4114f0120c74bd83d89bb82ac365488a', 6819))

    def test_initiate_new_upload(self):
        """testing the initiate_new_upload method by checking if the response contains an upload_token.
        """
        # arrange
        sleep(sleep_time)
        figshare = Figshare(api_key=api_key, api_address=api_address)
        article_id = int(figshare.create_new_article()['entity_id'])
        file_path = "./app/static/img/figshare.png"

        # act
        response = figshare.initiate_new_upload(article_id, file_path)

        # cleanup
        figshare.remove_article(article_id)

        # assert
        self.assertTrue("upload_token" in response.keys())

    def test_complete_upload(self):
        """testing the complete_upload method by checking if the response is successful.
        """
        # arrange
        sleep(sleep_time)
        figshare = Figshare(api_key=api_key, api_address=api_address)
        article_id = int(figshare.create_new_article()['entity_id'])
        path_to_file = "./app/static/img/figshare.png"
        file_info = figshare.initiate_new_upload(article_id, path_to_file)
        figshare.upload_parts(file_info, path_to_file)

        # act
        response = figshare.complete_upload(article_id, file_info['id'])

        # cleanup
        figshare.remove_article(article_id)

        # assert
        self.assertEqual(response, None)

    def test_get_article(self):
        """testing the get_article method by creating an article and then get it and
        checking if we get a 200 response.
        """
        # arrange
        sleep(sleep_time)
        figshare = Figshare(api_key=api_key, api_address=api_address)
        article_id = int(figshare.create_new_article()['entity_id'])

        # act
        response = figshare.get_article(article_id, return_response=True)

        # cleanup
        figshare.remove_article(article_id)

        # assert
        self.assertEqual(response.status_code, 200)

    def test_create_new_article(self):
        """testing the create_new_article method
        """
        # arrange
        sleep(sleep_time)
        figshare = Figshare(api_key=api_key, api_address=api_address)

        # act
        response = figshare.create_new_article(return_response=True)
        article_id = int(response.json()['entity_id'])

        # cleanup
        figshare.remove_article(article_id)

        # assert
        self.assertEqual(response.status_code, 201)
        self.assertTrue(type(article_id) is int)

    def test_remove_article(self):
        """testing the remove_article method
        """
        # arrange
        sleep(sleep_time)
        figshare = Figshare(api_key=api_key, api_address=api_address)
        article_id = int(figshare.create_new_article()['entity_id'])

        # act
        response = figshare.remove_article(article_id, return_response=True)

        # assert
        self.assertEqual(response.status_code, 204)

    def test_upload_parts(self):
        """testing the upload_parts method by checking if the response contains the token key.
        """
        # arrange
        sleep(sleep_time)
        figshare = Figshare(api_key=api_key, api_address=api_address)
        article_id = int(figshare.create_new_article()['entity_id'])
        path_to_file = "./app/static/img/figshare.png"
        file_info = figshare.initiate_new_upload(article_id, path_to_file)

        # act
        response = figshare.upload_parts(
            file_info=file_info, file_path=path_to_file)

        # cleanup
        figshare.remove_article(article_id)

        # assert
        self.assertTrue("token" in response.keys())

    def test_upload_part(self):
        """testing the upload_part method by checking if the response is None.
        """
        # arrange
        sleep(sleep_time)
        figshare = Figshare(api_key=api_key, api_address=api_address)
        article_id = int(figshare.create_new_article()['entity_id'])
        path_to_file = "./app/static/img/figshare.png"
        file_info = figshare.initiate_new_upload(article_id, path_to_file)

        url = '{upload_url}'.format(**file_info)
        result = figshare.raw_issue_request('GET', url)

        # act
        with open(path_to_file, 'rb') as fin:
            for part in result['parts']:
                response = figshare.upload_part(file_info, fin, part)

        # cleanup
        figshare.remove_article(article_id)

        # assert
        self.assertEqual(response, None)

    def test_upload_new_file_to_article(self):
        """testing the upload_new_file_to_article method
        """
        # arrange
        sleep(sleep_time)
        figshare = Figshare(api_key=api_key, api_address=api_address)
        article_id = int(figshare.create_new_article()['entity_id'])
        path_to_file = "./app/static/img/figshare.png"

        # act
        response = figshare.upload_new_file_to_article(
            article_id, path_to_file, return_response=False, test=True)

        # cleanup
        figshare.remove_article(article_id)

        # assert
        self.assertEqual(response, True)

    def test_change_metadata_in_article(self):
        """testing the change_metadata_in_article method.
        """
        # arrange
        sleep(sleep_time)
        figshare = Figshare(api_key=api_key, api_address=api_address)
        article_id = int(figshare.create_new_article()['entity_id'])
        metadata = {"title": "test"}

        # act
        response = figshare.change_metadata_in_article(
            article_id, metadata, return_response=True)
        article = figshare.get_article(id=article_id, return_response=True)

        # cleanup
        figshare.remove_article(article_id)

        # assert
        self.assertEqual(article.json()['title'], "test")
        self.assertEqual(response.status_code, 205)

    @unittest.skip
    def test_publish_article(self):
        """Will not test publish_article method as published articles cannot be removed.
        """
        log.info(
            "Will not test publish_article method as published articles cannot be removed.")
        pass
        # arrange
        # sleep(sleep_time)
        # figshare = Figshare(api_key=api_key, api_address=api_address)
        # article_id = int(figshare.create_new_article()['entity_id'])

        # # articles can only be published with set categories, keywords and description
        # metadata = {"title" : "test article",
        #             "description": "Test description of test article",
        #             "keywords": ["test1"],
        #             "categories_by_source_id": ["300204", "400207"]
        #             }
        # setmeta = figshare.change_metadata_in_article(article_id=article_id, metadata=metadata, return_response=True)
        # log.info(setmeta.status_code, setmeta.json())

        # # act
        # response = figshare.publish_article(article_id=article_id, return_response=True)

        # cleanup
        # figshare.remove_article(article_id)

        # assert
        # self.assertEqual(response.status_code, 201)

    def test_delete_all_files_from_article(self):
        """testing delete_all_files_article
        """
        # arrange
        sleep(sleep_time)
        figshare = Figshare(api_key=api_key, api_address=api_address)
        article_id = int(figshare.create_new_article()['entity_id'])
        path_to_file = "./app/static/img/figshare.png"
        figshare.upload_new_file_to_article(
            article_id, path_to_file, return_response=False, test=True)

        # act
        response = figshare.delete_all_files_from_article_internal(article_id)

        # cleanup
        figshare.remove_article(article_id)

        # assert
        self.assertTrue(response)

    def test_check_token(self):
        """testing check_token
        """
        # arrange
        sleep(sleep_time)
        figshare = Figshare(api_key=api_key, api_address=api_address)

        # act
        response = figshare.check_token(api_key)

        # assert
        self.assertTrue(response)

    def test_get_files_from_article(self):
        """testing get_files_from_article
        """
        # arrange
        sleep(sleep_time)
        figshare = Figshare(api_key=api_key, api_address=api_address)
        article_id = int(figshare.create_new_article()['entity_id'])
        path_to_file = "./app/static/img/figshare.png"
        figshare.upload_new_file_to_article(
            article_id, path_to_file, return_response=False, test=True)

        # act
        response = figshare.get_files_from_article(article_id)

        # cleanup
        figshare.remove_article(article_id)

        # assert
        self.assertTrue('upload_token' in response[0].keys())


if __name__ == '__main__':
    unittest.main()
