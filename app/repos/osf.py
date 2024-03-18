import inspect
import requests
import json
import os
import logging
from flask import abort, request
import functools
import re
import time
from io import BufferedReader
from osfclient import OSF

log = logging.getLogger()

class Osf(object):

    def __init__(self, api_key, api_address=None, *args, **kwargs):
        self.file_content = []
        self.osf_api_address = api_address
        if api_address is None:
            self.osf_api_address = os.getenv(
                "OSF_API_URL", "https://api.test.osf.io/v2"
            )
        self.api_key = api_key

        self.osf = OSF(
                    token=self.api_key,
                )
        self.osf.session.base_url = self.osf_api_address

    def check_token(self):
        try:
            # if we can get projects we are logged in
            self.osf.projects()
            return True
        except:
            return False

    def create_project(self):
        try:
            return self.osf.create_project(title='Untitled')
        except Exception as e:
            return {'error': str(e)}

    def get_project(self, project_id):
        return self.osf.project(project_id=project_id)
    
    def upload_new_file_to_project(self, project_id, path_to_file):
        try:
            with open(path_to_file, mode="rb") as data:
                result = self.osf.project(project_id).storage().create_file(
                    path=path_to_file, fp=BufferedReader(data), force=True
                )
            return result
        except Exception as e:
            return str(e)

    def update_metadata(self, project_id, metadata):
        """_summary_

        Args:
            project_id (str): id of the project
            metadata (dict): metadata

        Returns:
            bool: True if update was succesful, else False
        """
        metadata = {'data': {'attributes': metadata}}
        r = self.osf.project(project_id).update(metadata)
        return r


    ############ For downloads ###################

    

    def get_file_info(self, url):
        """Recursively get all file_info and append to file_content dict

        Args:
            url (str): url to start getting the file info
        """
        req = requests.get(
            url,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        if req.status_code < 300:
            for file in req.json()['data']:
                try:
                    tmp = {}
                    tmp['name'] = file['attributes']['materialized_path']
                    tmp['size'] = file['attributes']['size']
                    tmp['link'] = file['links']['download']
                    tmp['hash'] = file['attributes']['extra']['hashes']['md5']
                    tmp['hash_type'] = 'md5'
                    self.file_content.append(tmp)
                except Exception as e:
                    link_to_new_path = file['relationships']['files']['links']['related']['href']
                    self.get_file_info(link_to_new_path)


    def get_repo_content(self, project_id):
        """Get private repo content AKa list of files to be downloaded from the repo
        # Only work with

        Args:
            project_id (int): the id of the article that contains the files

        Returns:
            list: list of all the files information: name, size, link, hash, and hash_type
        """
        self.file_content = []
        project = self.get_project(project_id=project_id)
        storages_url = project._storages_url
        self.get_file_info(storages_url)
        return self.file_content


    def get_private_metadata(self, project_id):
        """Will get private metadata for a particular article

        Args:
            project_id (int): the id of the article

        Returns:
            dict: flat key value store with keys being the metadata field names and the values the metadata field values.
        """
        result = self.get_project(project_id=project_id)
        result = result.metadata()
        return result


    def download_files(self, project_id, dest_folder):
        """Will download all files for a specific article to a folder

        Args:
            project_id (int): the id of the article
            dest_folder (str): the folder path to download to

        Returns:
            bool: returns True if download was succesful
        """
        try:
            if not os.path.exists(dest_folder):
                os.makedirs(dest_folder)  # create folder if it does not exist
            file_content = self.get_repo_content(project_id)
            for item in file_content:
                filename = item['name']
                # filenames can contain a path as well
                # we need to create that part of the path as well
                # so check for '/' in the filename
                if filename.find("/") != -1:
                    additional_path = filename.split('/')
                    log.error(additional_path)
                    # drop last one as that is the filename
                    filename = additional_path.pop()
                    additional_path = "/".join(additional_path)
                    total_path = f"{dest_folder}/{additional_path}"
                    if not os.path.exists(total_path):
                        os.makedirs(total_path)  # create folder if it does not exist
                    file_path = os.path.join(total_path, filename)
                else:
                    file_path = os.path.join(dest_folder, filename)
                link = item['link']
                r = requests.get(link,
                                headers={'Authorization': f"Bearer {self.api_key}"},
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



if __name__ == "__main__":
    api_key = ""
    osf = Osf(api_key)
    # print(dir(osf))
    # print(dir(osf.check_token()))
    print(osf.check_token())
    # project_id = '6rgub'
    # project_id = osf.create_project().id
    # print(project_id)
    # path_to_file = "/home/dave/Projects/surfresearchdataretriever/requirements.txt"
    # print(osf.upload_new_file_to_project(project_id, path_to_file))
    # response = osf.get_repo_content(project_id='rbafs')
    # print(dir(response))
    # print(response.metadata())
    response = osf.download_files(project_id='rbafs', dest_folder='test1234')
    import prettyprinter as pprint
    pprint.pprint(response)
