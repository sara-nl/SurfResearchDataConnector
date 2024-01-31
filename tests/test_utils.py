import logging
import os
import shutil
import unittest
from app.utils import make_connection
from app.globalvars import *

log = logging.getLogger()


class TestUtils(unittest.TestCase):

    def setUp(self):
        self.url = "https://figshare.com/articles/dataset/Bitcoin_Prices_and_Technical_Variables/7445855"
        self.folder = "figsharedata"
        self.username = user_name
        self.password = app_password

    def tearDown(self):
        if os.path.exists(self.folder):
            shutil.rmtree(self.folder)

    # def test_get_data(self):
    #     # only run this test locally to check logic as it will call the DB
    #     if embed_app_url == 'https://aperture.data.surfsara.nl/index.php/apps/external/2':
    #         # act
    #         raised = False
    #         try:
    #             get_data(self.url, self.folder)
    #         except:
    #             raised = True
    #         # assert
    #         self.assertFalse(raised, 'Exception raised')

    def test_make_connection_success(self):
        # act
        result = make_connection(
            username=self.username, password=self.password)

        # assert
        self.assertTrue(result)

    def test_make_connection_fail(self):
        # act
        result = make_connection(username=self.username, password="dsfafd")

        # assert
        self.assertFalse(result)
