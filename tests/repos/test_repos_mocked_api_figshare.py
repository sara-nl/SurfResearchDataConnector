import configparser
import logging
import os
import sys
from time import sleep
import unittest
from pactman import Consumer, Provider

from app.repos.figshare import Figshare

log = logging.getLogger()


def create_app():
    from src import bootstrap
    # creates a test client
    app = bootstrap(use_default_error=True,
                    address="http://localhost:3000").app
    # propagate the exceptions to the test client
    app.config.update({"TESTING": True})

    return app


pact = Consumer('PortFigshare').has_pact_with(Provider('Figshare'), port=3000)


api_address = "http://localhost:3000"
api_key = "123"

class TestFigshareMethodsNew(unittest.TestCase):
    """Test for the methods implemented for figshare.
    
    Tests are written according to the Arrange - Act -Assert design pattern.
    
    The api calls and responses are mocked using pactman.

    Args:
        unittest (base): basic testcase from the unittest lib
    """

    def test_raw_issue_request(self):
        """testing the raw_issue_request method by checking if the response of the
        /account/articles/ endpoint can be called and returns proper response.
        """

        # arrange
        pact.given(
            'articles endpoint can be called'
        ).upon_receiving(
            'the corresponding response is a list'
        ).with_request(
            'GET', '/account/articles'
        ) .will_respond_with(200, body=[{'id': 123}])

        with pact:
        
            # act
            result = Figshare(api_key=api_key, api_address=api_address).raw_issue_request(
                                        method="GET",
                                        url=f"{api_address}/account/articles",
                                        data=None,
                                        binary=False)
        
        # assert
        self.assertTrue(type(result) is list)
        if len(result) > 0:
            self.assertTrue(type(result[0]['id']) is int)            
        
        
    def test_issue_request(self):
        """testing the issue_request method by checking if the response of the
        /account/articles/ endpoint can be called and returns proper response.
        """

        # arrange
        pact.given(
            'articles endpoint can be called'
        ).upon_receiving(
            'the corresponding response is a list'
        ).with_request(
            'GET', '/account/articles'
        ) .will_respond_with(200, body=[{'id': 123}])

        with pact:
        
            # act
            result = Figshare(api_key=api_key, api_address=api_address).issue_request(
                                        method="GET",
                                        endpoint="/account/articles")

        # assert
        self.assertTrue(type(result) is list)
        if len(result) > 0:
            self.assertTrue(type(result[0]['id']) is int)  


    def test_get_file_check_data(self):
        """testing the get_file_check_data method by checking if the input to the file_path
        returns correct output
        """
        # arrange
        figshare = Figshare(api_key=api_key, api_address=api_address)

        # act
        response = figshare.get_file_check_data('./app/static/img/figshare.png')

        # assert
        self.assertEqual(response, ('4114f0120c74bd83d89bb82ac365488a', 6819))


    def test_initiate_new_upload(self):
        """testing the initiate_new_upload method by checking if the response contains an upload_token.
        """

        # arrange
        figshare = Figshare(api_key=api_key, api_address=api_address)

        article_id = 27991847
        file_path = "./app/static/img/figshare.png"

        pact.given(
            'file upload can be done'
        ).upon_receiving(
            'the corresponding response has a location for the upload info'
        ).with_request(
            'POST', f'/account/articles/{article_id}/files'
        ) .will_respond_with(200, body={'location': f'{api_address}/account/articles/27991847/files/51057548'})

        pact.given(
            'we can get file upload info'
        ).upon_receiving(
            'the corresponding response has an uploadtoken'
        ).with_request(
            'GET', '/account/articles/27991847/files/51057548'
        ) .will_respond_with(200, body={'upload_token': 'bef47832-bd67-4f88-9490-7f4d45dba742',
                                        'upload_url': 'https://fup-eu-west-1.figshare.com/upload/bef47832-bd67-4f88-9490-7f4d45dba742',
                                        'status': 'created', 'preview_state': 'preview_not_available', 'viewer_type': '', 'is_attached_to_public_version': False,
                                        'id': 51057548, 'name': './app/static/img/figshare.png', 'size': 6819, 'is_link_only': False,
                                        'download_url': 'https://ndownloader.figshare.com/files/51057548', 'supplied_md5': '4114f0120c74bd83d89bb82ac365488a',
                                        'computed_md5': '', 'mimetype': 'undefined'})

        with pact:
        
            # act
            result = figshare.initiate_new_upload(article_id, file_path)

        # assert
        self.assertTrue("upload_token" in result.keys())

    def test_complete_upload(self):
        """testing the complete_upload method by checking if the response is successful.
        """
        # arrange
        figshare = Figshare(api_key=api_key, api_address=api_address)

        article_id = 27991847
        path_to_file = "./app/static/img/figshare.png"

        pact.given(
            'file upload can be done1'
        ).upon_receiving(
            'the corresponding response has a location for the upload info1'
        ).with_request(
            'POST', f'/account/articles/{article_id}/files'
        ) .will_respond_with(200, body={'location': f'{api_address}/account/articles/27991847/files/51057548'})

        pact.given(
            'we can get file upload info2'
        ).upon_receiving(
            'the corresponding response has an uploadtoken2'
        ).with_request(
            'GET', '/account/articles/27991847/files/51057548'
        ) .will_respond_with(200, body={'upload_token': 'bef47832-bd67-4f88-9490-7f4d45dba742',
                                        'upload_url': 'https://fup-eu-west-1.figshare.com/upload/bef47832-bd67-4f88-9490-7f4d45dba742',
                                        'status': 'created', 'preview_state': 'preview_not_available', 'viewer_type': '', 'is_attached_to_public_version': False,
                                        'id': 51057548, 'name': './app/static/img/figshare.png', 'size': 6819, 'is_link_only': False,
                                        'download_url': 'https://ndownloader.figshare.com/files/51057548', 'supplied_md5': '4114f0120c74bd83d89bb82ac365488a',
                                        'computed_md5': '', 'mimetype': 'undefined'})

        pact.given(
            'we can post file upload info5'
        ).upon_receiving(
            'the corresponding response5'
        ).with_request(
            'POST', '/account/articles/27991847/files/51057548'
        ) .will_respond_with(200, body=None)


        pact.given(
            'file upload can be initiated3'
        ).upon_receiving(
            'the corresponding response3'
        ).with_request(
            'POST', '/upload/bef47832-bd67-4f88-9490-7f4d45dba742'
        ) .will_respond_with(200, body={'token': '4c21b29b-3fdd-4252-870f-80c4b8fb8947', 'md5': '4114f0120c74bd83d89bb82ac365488a',
                                        'size': 6819, 'name': '51060059/.appstaticimgfigshare.png', 'status': 'PENDING',
                                        'parts': [{'partNo': 1, 'startOffset': 0, 'endOffset': 6818, 'status': 'PENDING', 'locked': False}]})

        pact.given(
            'file part upload can be done4'
        ).upon_receiving(
            'the corresponding response4'
        ).with_request(
            'PUT', f'{api_address}/upload/4c21b29b-3fdd-4252-870f-80c4b8fb8947/1'
        ) .will_respond_with(200, body=None)


        with pact:
            file_info = figshare.initiate_new_upload(article_id, path_to_file)

            figshare.upload_parts(file_info, path_to_file)

        # act
            response = figshare.complete_upload(article_id, file_info['id'])


        # assert
        self.assertEqual(response, None)

    def test_get_article(self):
        """testing the get_article method by checking if we get a 200 response.
        """
        # arrange
        figshare = Figshare(api_key=api_key, api_address=api_address)
        article_id = 21631871
        
        pact.given(
            'article can be retrieved'
        ).upon_receiving(
            'the corresponding response with the article info'
        ).with_request(
            'GET', f'/account/articles/{article_id}'
        ) .will_respond_with(200, body={
                "files": [],
                "resource_title": 'None',
                "resource_doi": None,
                "group_resource_id": None,
                "custom_fields": [],
                "account_id": 3414786,
                "authors": [
                    {
                    "id": 14126808,
                    "full_name": "Dave Tromp",
                    "is_active": True,
                    "url_name": "Dave_Tromp",
                    "orcid_id": ""
                    }
                ],
                "figshare_url": "https://figshare.com/articles/dataset/_/21631871",
                "description": "",
                "funding": None,
                "funding_list": [],
                "version": 0,
                "status": "draft",
                "size": 0,
                "created_date": "2022-11-28T14:23:37Z",
                "modified_date": "2022-11-28T14:23:37Z",
                "is_public": False,
                "is_confidential": False,
                "is_metadata_record": False,
                "confidential_reason": "",
                "metadata_reason": "",
                "license": {
                    "value": 1,
                    "name": "CC BY 4.0",
                    "url": "https://creativecommons.org/licenses/by/4.0/"
                },
                "tags": [],
                "categories": [],
                "references": [],
                "has_linked_file": False,
                "citation": "Tromp, Dave (2022): Untitled. figshare. Dataset. https://figshare.com/articles/dataset/_/21631871",
                "is_embargoed": False,
                "embargo_date": None,
                "embargo_type": None,
                "embargo_title": "",
                "embargo_reason": "",
                "embargo_options": [],
                "id": 21631871,
                "title": "Untitled",
                "doi": "",
                "handle": "",
                "url": "https://api.figshare.com/v2/account/articles/21631871",
                "published_date": None,
                "thumb": "",
                "defined_type": 3,
                "defined_type_name": "dataset",
                "group_id": None,
                "url_private_api": "https://api.figshare.com/v2/account/articles/21631871",
                "url_public_api": "https://api.figshare.com/v2/articles/21631871",
                "url_private_html": "https://figshare.com/account/articles/21631871",
                "url_public_html": "https://figshare.com/articles/dataset/_/21631871",
                "timeline": {}
                })

        # act
        with pact:
            response = figshare.get_article(article_id, return_response=True)

        
        # assert
        self.assertEqual(response.status_code, 200)

    def test_create_new_article(self):
        """testing the create_new_article method
        """
        # arrange
        figshare = Figshare(api_key=api_key, api_address=api_address)
        
        pact.given(
            'article can be created'
        ).upon_receiving(
            'the corresponding response with the article_id as the entity_id for the article that has been created'
        ).with_request(
            'POST', f'/account/articles'
        ) .will_respond_with(201, body={
                "entity_id": 21631871,
                "location": "https://api.figshare.com/v2/account/articles/21631871",
                "warnings": []
                })

        # act
        with pact:
            response = figshare.create_new_article(return_response=True)
        
        article_id = int(response.json()['entity_id'])


        # assert
        self.assertEqual(response.status_code, 201)
        self.assertTrue(type(article_id) is int)

    def test_remove_article(self):
        """testing the remove_article method
        """
        # arrange
        figshare = Figshare(api_key=api_key, api_address=api_address)

        article_id = 21631871

        pact.given(
            'article can be removed'
        ).upon_receiving(
            'the corresponding response status'
        ).with_request(
            'DELETE', f'/account/articles/{article_id}'
        ) .will_respond_with(204, body=None)        

        # act
        with pact:
            response = figshare.remove_article(article_id, return_response=True)

        # assert
        self.assertEqual(response.status_code, 204)

    def test_upload_parts(self):
        """testing the upload_parts method by checking if the response contains the token key.
        """
        # arrange
        figshare = Figshare(api_key=api_key, api_address=api_address)

        article_id = 27991847
        path_to_file = "./app/static/img/figshare.png"

        pact.given(
            'file upload can be done1'
        ).upon_receiving(
            'the corresponding response has a location for the upload info1'
        ).with_request(
            'POST', f'/account/articles/{article_id}/files'
        ) .will_respond_with(200, body={'location': f'{api_address}/account/articles/27991847/files/51057548'})

        pact.given(
            'we can get file upload info2'
        ).upon_receiving(
            'the corresponding response has an uploadtoken2'
        ).with_request(
            'GET', '/account/articles/27991847/files/51057548'
        ) .will_respond_with(200, body={'upload_token': 'bef47832-bd67-4f88-9490-7f4d45dba742',
                                        'upload_url': 'https://fup-eu-west-1.figshare.com/upload/bef47832-bd67-4f88-9490-7f4d45dba742',
                                        'status': 'created', 'preview_state': 'preview_not_available', 'viewer_type': '', 'is_attached_to_public_version': False,
                                        'id': 51057548, 'name': './app/static/img/figshare.png', 'size': 6819, 'is_link_only': False,
                                        'download_url': 'https://ndownloader.figshare.com/files/51057548', 'supplied_md5': '4114f0120c74bd83d89bb82ac365488a',
                                        'computed_md5': '', 'mimetype': 'undefined'})

        pact.given(
            'we can post file upload info5'
        ).upon_receiving(
            'the corresponding response5'
        ).with_request(
            'POST', '/account/articles/27991847/files/51057548'
        ) .will_respond_with(200, body=None)


        pact.given(
            'file upload can be initiated3'
        ).upon_receiving(
            'the corresponding response3'
        ).with_request(
            'POST', '/upload/bef47832-bd67-4f88-9490-7f4d45dba742'
        ) .will_respond_with(200, body={'token': '4c21b29b-3fdd-4252-870f-80c4b8fb8947', 'md5': '4114f0120c74bd83d89bb82ac365488a',
                                        'size': 6819, 'name': '51060059/.appstaticimgfigshare.png', 'status': 'PENDING',
                                        'parts': [{'partNo': 1, 'startOffset': 0, 'endOffset': 6818, 'status': 'PENDING', 'locked': False}]})

        pact.given(
            'file part upload can be done4'
        ).upon_receiving(
            'the corresponding response4'
        ).with_request(
            'PUT', f'{api_address}/upload/4c21b29b-3fdd-4252-870f-80c4b8fb8947/1'
        ) .will_respond_with(200, body=None)
        
        with pact:
            file_info = figshare.initiate_new_upload(article_id, path_to_file)

            # act
            response = figshare.upload_parts(
                file_info=file_info, file_path=path_to_file)

        # assert
        self.assertTrue("token" in response.keys())



    def test_upload_part(self):
        """testing the upload_part method by checking if the response is None.
        """
        # arrange
        figshare = Figshare(api_key=api_key, api_address=api_address)

        article_id = 27991847
        path_to_file = "./app/static/img/figshare.png"

        pact.given(
            'file upload can be done1'
        ).upon_receiving(
            'the corresponding response has a location for the upload info1'
        ).with_request(
            'POST', f'/account/articles/{article_id}/files'
        ) .will_respond_with(200, body={'location': f'{api_address}/account/articles/27991847/files/51057548'})

        pact.given(
            'we can get file upload info2'
        ).upon_receiving(
            'the corresponding response has an uploadtoken2'
        ).with_request(
            'GET', '/account/articles/27991847/files/51057548'
        ) .will_respond_with(200, body={'upload_token': 'bef47832-bd67-4f88-9490-7f4d45dba742',
                                        'upload_url': 'https://fup-eu-west-1.figshare.com/upload/bef47832-bd67-4f88-9490-7f4d45dba742',
                                        'status': 'created', 'preview_state': 'preview_not_available', 'viewer_type': '', 'is_attached_to_public_version': False,
                                        'id': 51057548, 'name': './app/static/img/figshare.png', 'size': 6819, 'is_link_only': False,
                                        'download_url': 'https://ndownloader.figshare.com/files/51057548', 'supplied_md5': '4114f0120c74bd83d89bb82ac365488a',
                                        'computed_md5': '', 'mimetype': 'undefined'})

        pact.given(
            'we can post file upload info5'
        ).upon_receiving(
            'the corresponding response5'
        ).with_request(
            'POST', '/account/articles/27991847/files/51057548'
        ) .will_respond_with(200, body=None)


        pact.given(
            'file upload can be initiated3'
        ).upon_receiving(
            'the corresponding response3'
        ).with_request(
            'POST', '/upload/bef47832-bd67-4f88-9490-7f4d45dba742'
        ) .will_respond_with(200, body={'token': '4c21b29b-3fdd-4252-870f-80c4b8fb8947', 'md5': '4114f0120c74bd83d89bb82ac365488a',
                                        'size': 6819, 'name': '51060059/.appstaticimgfigshare.png', 'status': 'PENDING',
                                        'parts': [{'partNo': 1, 'startOffset': 0, 'endOffset': 6818, 'status': 'PENDING', 'locked': False}]})

        pact.given(
            'file part upload can be done4'
        ).upon_receiving(
            'the corresponding response4'
        ).with_request(
            'PUT', f'{api_address}/upload/4c21b29b-3fdd-4252-870f-80c4b8fb8947/1'
        ) .will_respond_with(200, body=None)
        
        with pact:
            file_info = figshare.initiate_new_upload(article_id, path_to_file)

            url = '{upload_url}'.format(**file_info)
            result = figshare.raw_issue_request('GET', url)

            # act
            with open(path_to_file, 'rb') as fin:
                for part in result['parts']:
                    response = figshare.upload_part(file_info, fin, part)

        # assert
        self.assertEqual(response, None)

    def test_upload_new_file_to_article(self):
        """testing the upload_new_file_to_article method
        """
        # arrange
        figshare = Figshare(api_key=api_key, api_address=api_address)

        article_id = 27991847
        path_to_file = "./app/static/img/figshare.png"

        pact.given(
            'file upload can be done1'
        ).upon_receiving(
            'the corresponding response has a location for the upload info1'
        ).with_request(
            'POST', f'/account/articles/{article_id}/files'
        ) .will_respond_with(200, body={'location': f'{api_address}/account/articles/27991847/files/51057548'})

        pact.given(
            'we can get file upload info2'
        ).upon_receiving(
            'the corresponding response has an uploadtoken2'
        ).with_request(
            'GET', '/account/articles/27991847/files/51057548'
        ) .will_respond_with(200, body={'upload_token': 'bef47832-bd67-4f88-9490-7f4d45dba742',
                                        'upload_url': 'https://fup-eu-west-1.figshare.com/upload/bef47832-bd67-4f88-9490-7f4d45dba742',
                                        'status': 'created', 'preview_state': 'preview_not_available', 'viewer_type': '', 'is_attached_to_public_version': False,
                                        'id': 51057548, 'name': './app/static/img/figshare.png', 'size': 6819, 'is_link_only': False,
                                        'download_url': 'https://ndownloader.figshare.com/files/51057548', 'supplied_md5': '4114f0120c74bd83d89bb82ac365488a',
                                        'computed_md5': '', 'mimetype': 'undefined'})

        pact.given(
            'we can post file upload info5'
        ).upon_receiving(
            'the corresponding response5'
        ).with_request(
            'POST', '/account/articles/27991847/files/51057548'
        ) .will_respond_with(200, body=None)


        pact.given(
            'file upload can be initiated3'
        ).upon_receiving(
            'the corresponding response3'
        ).with_request(
            'POST', '/upload/bef47832-bd67-4f88-9490-7f4d45dba742'
        ) .will_respond_with(200, body={'token': '4c21b29b-3fdd-4252-870f-80c4b8fb8947', 'md5': '4114f0120c74bd83d89bb82ac365488a',
                                        'size': 6819, 'name': '51060059/.appstaticimgfigshare.png', 'status': 'PENDING',
                                        'parts': [{'partNo': 1, 'startOffset': 0, 'endOffset': 6818, 'status': 'PENDING', 'locked': False}]})

        pact.given(
            'file part upload can be done4'
        ).upon_receiving(
            'the corresponding response4'
        ).with_request(
            'PUT', f'{api_address}/upload/4c21b29b-3fdd-4252-870f-80c4b8fb8947/1'
        ) .will_respond_with(200, body=None)

        # act
        with pact:
            response = figshare.upload_new_file_to_article(
                article_id, path_to_file, return_response=False, test=True)

        # assert
        self.assertEqual(response, True)

    def test_change_metadata_in_article(self):
        """testing the change_metadata_in_article method.
        """
        # arrange
        figshare = Figshare(api_key=api_key, api_address=api_address)

        article_id = 27991847

        pact.given(
            'we can put metadata'
        ).upon_receiving(
            'the corresponding response of the metadata push'
        ).with_request(
            'PUT', f'/account/articles/{article_id}'
        ) .will_respond_with(205, body={})

        metadata = {"title": "test"}

        # act
        with pact:
            response = figshare.change_metadata_in_article(
                article_id, metadata, return_response=True)
            # article = figshare.get_article(id=article_id, return_response=True)

        # assert
        # self.assertEqual(article.json()['title'], "test")
        self.assertEqual(response.status_code, 205)

    def test_check_token(self):
        """testing check_token
        """
        # arrange
        figshare = Figshare(api_key=api_key, api_address=api_address)
        # article_id = 21631871
        
        pact.given(
            'article can be retrieved to check token'
        ).upon_receiving(
            'the corresponding response with the article info'
        ).with_request(
            'GET', f'/account/articles'
        ) .will_respond_with(200, body=[
                    {
                        "id": 21631871,
                        "title": "Untitled",
                        "doi": "",
                        "handle": "",
                        "url": "https://api.figshare.com/v2/account/articles/21631871",
                        "published_date": None,
                        "thumb": "",
                        "defined_type": 3,
                        "defined_type_name": "dataset",
                        "group_id": None,
                        "url_private_api": "https://api.figshare.com/v2/account/articles/21631871",
                        "url_public_api": "https://api.figshare.com/v2/articles/21631871",
                        "url_private_html": "https://figshare.com/account/articles/21631871",
                        "url_public_html": "https://figshare.com/articles/dataset/_/21631871",
                        "timeline": {},
                        "resource_title": None,
                        "resource_doi": None
                    },
                    {
                        "id": 21631862,
                        "title": "Untitled",
                        "doi": "",
                        "handle": "",
                        "url": "https://api.figshare.com/v2/account/articles/21631862",
                        "published_date": None,
                        "thumb": "",
                        "defined_type": 3,
                        "defined_type_name": "dataset",
                        "group_id": None,
                        "url_private_api": "https://api.figshare.com/v2/account/articles/21631862",
                        "url_public_api": "https://api.figshare.com/v2/articles/21631862",
                        "url_private_html": "https://figshare.com/account/articles/21631862",
                        "url_public_html": "https://figshare.com/articles/dataset/_/21631862",
                        "timeline": {},
                        "resource_title": None,
                        "resource_doi": None
                    }
                ])

        # act
        with pact:
            response = figshare.check_token()

        # assert
        self.assertTrue(response)

    def test_get_files_from_article(self):
        """testing get_files_from_article
        """
        
        # arrange
        figshare = Figshare(api_key=api_key, api_address=api_address)
        article_id = 21631871
        
        pact.given(
            'files from article can be retrieved'
        ).upon_receiving(
            'the corresponding response with the article files info'
        ).with_request(
            'GET', f'/account/articles/{article_id}/files'
        ) .will_respond_with(200, body=[
            {"upload_token": "25a99dd6-19af-44ce-b484-d77215a4eb3d",
            "upload_url": "", "status": "available", "preview_state": "preview_in_progress",
            "viewer_type": "", "is_attached_to_public_version": False, "id": 51099071,
            "name": "./app/static/img/figshare.png", "size": 6819, "is_link_only": False,
            "download_url": "https://ndownloader.figshare.com/files/51099071",
            "supplied_md5": "4114f0120c74bd83d89bb82ac365488a",
            "computed_md5": "4114f0120c74bd83d89bb82ac365488a", "mimetype": "undefined"}])


        # act
        with pact:
            response = figshare.get_files_from_article(article_id)

        # assert
        self.assertTrue('upload_token' in response[0].keys())


if __name__ == '__main__':
    unittest.main()
