import configparser
import os
import shutil
from flask import session
import datahugger
import owncloud
import nextcloud_client
import logging
import requests
import pandas as pd
import hashlib
from lxml import html
import math
import json
import time
import glob
import datetime
from rocrate.rocrate import ROCrate
from rocrate.model.person import Person
from rocrate.model.dataset import Dataset
from functools import lru_cache
import xml.etree.ElementTree as ET


try:
    from app.models import app, db, History
    from app.globalvars import *
except:
    # for testing this file locally
    from models import app, db, History
    from globalvars import *
    print("testing")

from pprint import pprint

logger = logging.getLogger()

if cloud_service == "owncloud":
    cloud = owncloud.Client(drive_url)
elif cloud_service == "nextcloud":
    cloud = nextcloud_client.Client(drive_url)
else:
    # defaulting to the owncloud lib in case cloud_service is not configured
    cloud = owncloud.Client(drive_url)

global query_status
query_status = {}

global canceled
canceled = {}

global summary
summary = {}


def set_canceled(username, b):
    """set the username to True in the global canceled var (dict)
    Is useful for passing the canceled by user action to a thread
    that is processing in the background.

    Args:
        username (str): the username in the session
        b (bool): True is user has caneled the process, otherwise False
    """
    canceled[username] = b


def get_canceled(username):
    """Get the canceled status for a user.

    Args:
        username (str): the username in the session

    Returns:
        bool: True is user has canceled the process
    """
    if username in canceled:
        return canceled[username]
    return False


def get_data(url, folder, username=None,):
    """Will get data from a specified url supported by datahugger and store it locally in the specified folder.

    Args:
        url (str): the url to pull the data from
        folder (str): the folder where to store the data locally
    """
    try:
        if check_if_url_in_history(username, url):
            message = "url in history"
            update_history(username=username, folder=folder,
                           url=url, status=message)
        message = "start data retrieval"
        update_history(username=username, folder=folder,
                       url=url, status=message)
        try:
            datahugger.get(url, folder, unzip=False, progress=False)
            message = "data retrieved"
        except Exception as e:
            message = str(e)
        update_history(username=username, folder=folder,
                       url=url, status=message)
    except Exception as e:
        logger.error(e, exc_info=True)
        message = "Failed to retrieve data from url"
        update_history(username=username, folder=folder,
                       url=url, status=message)


# @lru_cache(maxsize=1)
def get_files_info(url):
    """Will get file info by datahugger

    Args:
        url (str): url of the dataset repo

    Returns:
        list: list of dicts with file information
    """
    try:
        result = datahugger.info(url)
        return result.files
    except ValueError as e:
        return [{'message': str(e)}]


def check_if_folder_exists(username, password, folder, url=None):
    """Will check if the folder already exists on the users account.

    Args:
        username (str): username of the OC account
        password (str): the password of the OC account
        folder (str): the folder path of the folder on the OC account
        url (str): the url of the retrieval used for updating the history correctly.

    Returns:
        bool: True if the folder exists
    """
    # first login
    try:
        cloud.login(username, password)
    except:
        message = "failed to login to webdav"
        if url != None:
            update_history(username, folder, url, message)
    # we can use cloud.list to list content of a folder. If we get an error, we know it does not exist.
    try:
        cloud.list(folder)
        return True
    except:
        return False


def check_if_url_in_history(username, url):
    """will check if the url is in the history table

    Args:
        username (str): username of the OC account
        url (str): the url of the retrieval

    Returns:
        bool: True if the url is in history
    """
    with app.app_context():
        hist = History.query.filter_by(username=username).filter_by(
            url=url).filter_by(status='ready').all()
        if len(hist) > 0:
            return True
        else:
            return False


def get_query_status_history(username, folder, url):
    """will get the query statusses from the history table for the specified user, foleder and url combination

    Args:
        username (str): username of the OC account
        folder (str): the folder path of the retrieval
        url (str): the url of the retrieval

    Returns:
        dict: all query statusses
    """
    with app.app_context():
        return History.query.filter_by(username=username).filter_by(
            url=url).filter_by(folder=folder).order_by(History.id.desc()).all()


def get_query_status(username, folder, url):
    """will get the current query status

    Args:
        username (str): username of the OC account
        folder (str): the folder path of the retrieval
        url (str): the url of the retrieval

    Returns:
        str: the current status
    """
    try:
        return query_status[(username, folder, url)]
    except:
        return None


def set_query_status(username, folder, url, status):
    """will set the query status

    Args:
        username (str): username of the OC account
        folder (str): the folder path of the retrieval
        url (str): the url of the retrieval
        status (str): the new status
    """
    query_status[(username, folder, url)] = status


def total_files_count(folder):
    """calculate the total files count for a folder

    Args:
        folder (str): path to the folder

    Returns:
        int: file count
    """
    totalfilescount = 0
    for root, dirs, files in os.walk(folder):
        for file in files:
            totalfilescount += 1
    return totalfilescount


def push_data(username, password, folder, url):
    """Will push data from a local folder to a folder on an owncloud instance.

    Args:
        username (str): username for logging on to the owncloud instance.
        password (str): application password for logging on to the owncloud instance.
        folder (str): folder path
    """
    message = None
    try:
        folder_exists = check_if_folder_exists(username, password, folder, url)
        if folder_exists:
            message = "folder already exists."
            update_history(username, folder, url, message)

        # This does not seem to work
        # cloud.put_directory("/", folder)
        # So let's upload file by file
        # And create sub directories as well

        # first login
        try:
            cloud.login(username, password)
        except:
            message = "failed to login to webdav"
            update_history(username, folder, url, message)

        # calculate the total files count
        totalfilescount = total_files_count(folder)

        # upload file by file to OC
        n = 1
        for root, dirs, files in os.walk(folder):
            if not get_canceled(username):
                if not folder_exists:
                    try:
                        cloud.mkdir(root)
                    except:
                        message = "failed to create folder"
                        update_history(username, folder, url, message)
                for j in files:
                    filepath = os.path.join(root, j)
                    try:
                        cloud.put_file(filepath, filepath)
                        message = f"uploaded file {n} of {totalfilescount}: {filepath}"
                    except:
                        message = f"failed to upload file {filepath}"
                    update_history(username, folder, url, message)
                    n += 1
        
        # remove the local folder with the data
        try:
            shutil.rmtree(folder)
            update_history(username,folder, url, "Removing temporary data")
        except Exception as e:
            logger.error(e, exc_info=True)
    except Exception as eee:
        try:
            shutil.rmtree(folder)
            update_history(username,folder, url, "Removing temporary data")
        except Exception as ee:
            logger.error(ee, exc_info=True)
        logger.error(eee, exc_info=True)
        return (False, message)
    return (True, message)


def check_permission(username, password, folderpath):
    """Check if we have permission to create the folder at folderpath

    Args:
        username (str): username of the OC account
        folder (str): the folder path of the retrieval
        folderpath (str): path of the folder to create

    Returns:
        _type_: _description_
    """
    folder_exists = check_if_folder_exists(username, password, folderpath)
    if not folder_exists:
        try:
            cloud.login(username, password)
        except:
            logger.error("failed to login to webdav")
        try:
            cloud.mkdir(folderpath)
            cloud.delete(folderpath)
            return True
        except:
            return False
    else:
        logger.info("folder exists")
        return True

# @lru_cache(maxsize=1)
def get_folders(username, password, folder):
    """Will get the folders on an owncloud instance.

    Args:
        username (str): username for logging on to the owncloud instance.
        password (str): application password for logging on to the owncloud instance.
        folder (str): folder path

    Returns:
        list: list of available folder paths
    """
    try:
        cloud.login(username, password)
    except:
        message = "failed to login to webdav"
        logger.error(message)
    try:
        result = cloud.list(folder, depth=100)
        paths = ["/"]
        for item in result:
            folder_path = item.get_path()
            if folder_path not in paths:
                paths.append(folder_path)
        return paths
    except Exception as e:
        message = "failed to list folders"
        logger.error(message)


# @lru_cache(maxsize=1)
def get_folder_content(username, password, folder):
    """Will get a folder content on an owncloud instance.

    Args:
        username (str): username for logging on to the owncloud instance.
        password (str): application password for logging on to the owncloud instance.
        folder (str): folder path

    Returns:
        list: list of available files and folder paths in the specified folder
    """
    try:
        cloud.login(username, password)
    except:
        message = "failed to login to webdav"
    try:
        result = cloud.list(folder, depth=100)
        paths = []
        for item in result:
            folder_path = item.path
            if folder_path not in paths:
                paths.append(folder_path)
        return paths
    except Exception as e:
        message = "Failed to list folders"
        return []


def make_connection(username=None, password=None, token=None):
    """This function  will test if the username and password
    are correct

    Args:
        username (str): username of the owncloud account
        password (str): password of the owncloud account

    Returns:
        bool: returns True if connection is succesful, otherwise False
    """
    try:
        if token == None:
            r = cloud.login(username, password)
            return True
        else:
            return True
    except:
        return False


def get_status_from_history(username, folder, url):
    with app.app_context():
        return History.query.filter_by(username=username).filter_by(
            url=url).filter_by(folder=folder).order_by(History.id.desc()).all()[0].status


def update_history(username, folder, url, status):
    """update the history table in the database
    and update the query status

    Args:
        username (str): username of the owncloud
        folder (str): folder path of the data
        url (str): url of the location of the data
        status (str): status of the data import
    """
    logger.info(f"update_history: {status}")
    if status == 'started':
        summary[username] = {}
    if 'failed' in status.lower():
        if 'failed' not in summary[username]:
            summary[username]['failed'] = 1
        else:
            summary[username]['failed'] += 1
    if 'uploaded' in status.lower():
        if 'processed' not in summary[username]:
            summary[username]['processed'] = 1
        else:
            summary[username]['processed'] += 1
    if 'created' in status.lower():
        if 'created' not in summary[username]:
            summary[username]['created'] = 1
        else:
            summary[username]['created'] += 1

    # status can be up to 128 chars long
    status = status[:128]
    
    with app.app_context():
        history = History(username=username,
                          folder=folder,
                          url=url,
                          status=status)
        db.session.add(history)
        db.session.commit()
    
    if status == 'ready':
        logger.error(summary)
        canc = get_canceled(username)
        if 'failed' not in summary[username] and not canc:
            final_message = "Success! "
        else:
            final_message = "Completed with issues. Check the history. "
            
        if 'failed' in summary[username]:
            final_message += "Failures: {}. ".format(summary[username]['failed'])
        if 'created' in summary[username]:
            final_message += "Files created: {}. ".format(summary[username]['created'])
        if 'processed' in summary[username]:
            final_message += "Files processed: {}. ".format(summary[username]['processed'])
        if canc:
            final_message += "Process was canceled by user."
        final_message = final_message[:128]
        with app.app_context():
            history = History(username=username,
                            folder=folder,
                            url=url,
                            status=final_message)
            db.session.add(history)
            db.session.commit() 

    set_query_status(username, folder, url, status)


def check_checksums(username, url, folder, files_info=None):
    """Will pull info on the data to be retrieved including the checksums
    Then is will check these checksums to the checksums of the downloaded files
    and will update the history with the results.

    Args:
        username (str): username of the current session
        url (str): url to retrieve the data from
        folder (str): folder to push the data to
    """
    try:
        checksums = {}

        # get info of the data
        if files_info == None:
            # get file info using datahugger
            files_info = get_files_info(url)
        
        df = pd.DataFrame(files_info)

        # loop through the downloaded files in the folder
        for subdir, dirs, files in os.walk(folder):
            for file in files:
                filepath = os.path.join(subdir, file)
                df2 = df[df['name'] == file].reset_index()
                try:
                    hash = df2['hash'][0]
                except:
                    hash = None
                try:
                    hash_type = str(df2['hash_type'][0]).lower().replace("-", "")
                except:
                    hash_type = None
                newhash = None
                with open(filepath, "rb") as f:
                    if hash_type == 'md5':
                        newhash = hashlib.md5(f.read()).hexdigest()
                    if hash_type == 'sha1':
                        newhash = hashlib.sha1(f.read()).hexdigest()
                    if hash_type == 'sha224':
                        newhash = hashlib.sha224(f.read()).hexdigest()
                    if hash_type == 'sha256':
                        newhash = hashlib.sha256(f.read()).hexdigest()
                    if hash_type == 'sha384':
                        newhash = hashlib.sha384(f.read()).hexdigest()
                    if hash_type == 'sha512':
                        newhash = hashlib.sha512(f.read()).hexdigest()
                hash_match = (hash == newhash)
                status = f"---> Checksum match: {hash_match} - {file}"
                checksums[file] = hash_match
                update_history(username, folder, url, status)
        try:
            timestamp = str(time.time()).split('.')[0]
        except:
            timestamp = ""
        generated_path = create_generated_folder(folder)
        with open(f"{generated_path}/checksums{timestamp}.json", "w") as f:
            json.dump(checksums, f)
    except Exception as e:
        print(e)
        logger.error(f"Failed at checksum: {e}")


def run_import(username, password, folder, url):
    """Execute steps for importing and updates the history for every step.

    Args:
        username (str): username of the owncloud account
        password (str): password of the owncloud account
        folder (str): folder path of the data
        url (str): url of the location of the data
    """
    update_history(username, folder, url, 'started')
    if not get_canceled(username):
        get_data(url=url, folder=folder, username=username)
    if not get_canceled(username):
        update_history(username, folder, url, 'start checking checksums')
        check_checksums(username, url, folder)
        update_history(username, folder, url, 'created checksums')

    if not get_canceled(username):
        # check if there is just one file and it is a zip, then:
        # unzip that file
        for subdir, dirs, files in os.walk(folder):
            if len(files) == 1 and files[0].endswith(".zip"):
                # there is one file and it is a zip file
                update_history(username, folder, url, 'unzipping the zip file')
                zipfilepath = os.path.join(subdir, files[0])
                import zipfile
                with zipfile.ZipFile(zipfilepath, 'r') as zip_ref:
                    zip_ref.extractall(folder)
                # remove the zipfile
                update_history(username, folder, url, 'removing the zip file')
                os.remove(zipfilepath)

    if not get_canceled(username):
        update_history(username, folder, url,
                    'creating ro-crate-metadata.json file ')
        create_rocrate(url, folder)
        update_history(username, folder, url,
                    'created ro-crate-metadata.json file ')
    if not get_canceled(username):
        update_history(username, folder, url, 'start pushing dataset to storage')
        push_data(username, password, folder, url)
    update_history(username, folder, url, 'ready')


def get_quota_text(username, password, folder=None):
    """Will generate quota text using the get_quota function or will get it from the settings page

    Args:
        username (str): username for logging on to the owncloud instance.
        password (str): application password for logging on to the owncloud instance.
        folder (str): the folder that the user will be using

    Returns:
        str: The quota text from the settings page
    """
    try:
        quota = get_quota(username, password, folder)
        used = int(quota[0])
        available = int(quota[1])
        have_permission = quota[2]
        total = used + available
        percent = round((used / total) * 100.0)
        result = f"You are using {convert_size(used)} of {convert_size(total)} ({percent}%). "
        if have_permission:
            result += "You have write permission to this folder."
        else:
            result += "You do not have write permission to this folder."
        return result
    except:
        return None


def get_quota(username, password, folder=None):
    """Will get the used and available storage quota in bytes

    Args:
        username (str): username for logging on to the owncloud instance.
        password (str): application password for logging on to the owncloud instance.
        folder (str): the folder that the user will be using

    Returns:
        tuple: the used and available quota in bytes
    """
    r = cloud.login(username, password)
    
    root_folder = "/"
    used = 0
    available = 0

    ### determine the project folder if there is one
    folders = folder.split("/")
    # by default the project folder is the folder on top of root
    project_folder = "/{}/".format(folders[1])   
    # Or it can have (Projectfolder) in it's name
    for item in folders:
        if item.find(" (Projectfolder)") != -1:
            project_folder = f"/{item}/"

    have_permission = False
    test_folder = f"{project_folder}/testingpermissions"
    try:
        try:
            # delete test folder if there is any
            cloud.delete(test_folder)
        except:
            # if there is no test folder the delete will throw an exception
            pass
        # Now make the test folder. Will return True is we have permission else False
        have_permission = cloud.mkdir(test_folder)
        cloud.delete(test_folder)
    except:
        # if the mkdir or delete returns exception then we do not have permission.
        pass


    result = cloud.list(root_folder, depth=1)
    
    # if project_folder != root_folder:
    if project_folder.find(" (Projectfolder)") != -1:
        for r in result:
            try:
                if r.path == project_folder:
                    used += int(r.attributes['{DAV:}quota-used-bytes'])
                    available += int(r.attributes['{DAV:}quota-available-bytes'])
            except:
                pass   
    else:
        for r in result:
            if r.path == project_folder:
                available = int(r.attributes['{DAV:}quota-available-bytes'])
            try:
                used += int(r.attributes['{DAV:}quota-used-bytes'])
            except:
                used += int(r.attributes['{DAV:}getcontentlength'])

    return (used, available, have_permission)


def convert_to_size(number, size_name):
    """convert a number size_name combination to bytes

    Args:
        number (float): the number part of the human readble file size
        size_name (float): the size name part of the human readable file size

    Returns:
        int: the size in bytes
    """
    size_names = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    i = size_names.index(size_name)
    p = math.pow(1024, i)
    return int(number * p)


def convert_size(size_bytes):
    """will convert size in bytes to human readable size

    Args:
        size_bytes (int): number of bytes

    Returns:
        str: human readable size
    """
    try:
        if size_bytes == 0:
            return "0B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return "%s %s" % (s, size_name[i])
    except:
        return size_bytes


def repo_content_fits(repo_content, quota_text):
    """compares the total filesize from the repo_content to the free storage size in the quota_text.

    Args:
        repo_content (list): the repo_content_data
        quota_text (str): the quoata text from the owncloud general settingspage

    Returns:
        bool: True if the files in repo_content will fit into the free storage space.
    """
    try:
        # calculate the total size in bytes that the files will take up
        total_file_size = 0
        for item in repo_content:
            total_file_size += int(item['size'])

        # figure out how many free bytes we have in OC storage
        parsed_quota_text = quota_text.split()
        number_one = float(parsed_quota_text[3])
        size_name_one = parsed_quota_text[4]
        number_two = float(parsed_quota_text[6])
        size_name_two = parsed_quota_text[7]
        one = convert_to_size(number_one, size_name_one)
        two = convert_to_size(number_two, size_name_two)
        free_bytes = two - one

        if free_bytes > total_file_size:
            return True
    except Exception as e:
        logger.error(e)
        return None
    return False


# @lru_cache(maxsize=1)
def get_doi_metadata(url):
    """will pull metadata from the passed in url.

    Args:
        url (url): doi url

    Returns:
        dict: available metadata or empty dict
    """
    try:
        service = datahugger.info(url)
        metadata = service.resource.metadata.cls()
        return metadata
    except:
        return {}


def get_rocrate(folder, rocrate_filename='ro-crate-metadata.json'):
    """check if the folder contains a rocrate file and return the content

    Args:
        folder (str): folder path to look for rocrate file

    Returns:
        dict: the content of the file
    """
    for dirpath, subdirs, files in os.walk(folder):
        if rocrate_filename in files:
            ro_crate_filepath = f"{dirpath}/ro-crate-metadata.json"
            with open(ro_crate_filepath, 'r') as f:
                result = json.loads(f.read())
            return result


def create_generated_folder(folder):
    """will check if there is a 'generated' folder in the folder and create it if it is not there.

    Args:
        folder (str): the folder path where the generated folder needs to be created
    """
    generated_path = f"{folder}/generated"
    if not os.path.isdir(generated_path):
        os.mkdir(generated_path)
    return generated_path


def create_rocrate(url, folder, metadata = None):
    """will create a rocrate file in the folder based on the metadata
    that will be retrieved from the url.

    Args:
        url (str): the url where the data will be retrieved from
        folder (str): the folder where the data will be written to
    """
    # TODO: if metadata is not none then use that data to ccreate rocrate file. This is for upload
    crate = ROCrate()
    dataset = crate.add(Dataset(crate, dest_path="./"))

    # get metadata from doi url if available
    if url.find('http') != -1:
        metadata = get_doi_metadata(url)
    
    # if we have mata data use this
    if metadata != {} and metadata != None:
        logger.error("we have metadata")
        metadata = parse_doi_metadata(metadata)
        if 'author' in metadata:
            authors = []
            if type(metadata['author']) == 'list':
                for author in metadata['author']:
                    auth = crate.add(Person(crate, properties=author))
                    authors.append(auth)
                dataset['author'] = authors
            else:
                dataset['author'] = metadata['author']
        for key, value in metadata.items():
            if key not in ['author']:
                dataset[key] = value
    # else check to see if we have a ro-crate file to use as metadata.
    else:
        # see if there is a rocrate file with metadata
        rocrate_metadata = get_rocrate(folder)
        if rocrate_metadata:
            try:
                crate.add_jsonld(rocrate_metadata)
            except:
                # TODO: check if this works for adding metadata
                logger.info("no valid rocrate data to add")

    # add the files
    files_info = get_files_info(url)
    dataset['files'] = files_info

    # timestamp the ro-crate file
    dataset["timestamp"] = str(datetime.datetime.now())

    generated_path = create_generated_folder(folder)
    crate.write(generated_path)


def parse_doi_metadata(metadata):
    """will parse the metadata to a datastructure that is more flat and
    easier to use in presentation.

    Args:
        metadata (dict): the metadata datastructure

    Returns:
        dict: the flattened datastructure of the metadata
    """
    try:
        new_metadata = {}
        for key, value in metadata.items():
            if key == 'categories':
                value = ', '.join(value)
            if key == 'issued':
                value = list(value['date-parts'])
                if len(value[0]) == 1:
                    year = value[0][0]
                    value = f"{year}"
                if len(value[0]) == 2:
                    year = value[0][0]
                    month = value[0][1]
                    value = f"{year}-{month}"
                if len(value[0]) == 3:
                    year = value[0][0]
                    month = value[0][1]
                    day = value[0][2]
                    value = f"{year}-{month}-{day}"
            if key == 'author':
                authors = []
                if type(value) == 'list':
                    for item in value:
                        if 'literal' in item.keys():
                            literal_name = item['literal']
                            authors.append(literal_name)
                        elif 'given' in item.keys() and 'family' in item.keys():
                            given_name = item['given']
                            family_name = item['family']
                            authors.append(f"{given_name} {family_name}")
                        else:
                            authors.append(str(item))
                    value = ", ".join(authors)
            new_metadata[key] = value
        return new_metadata
    except Exception as e:
        logger.error(e)
        return metadata


def parse_folder_structure(list_of_paths, folder_path):
    """Recursive function that will build a datastructure that represents
    a folder structure based on a list of paths that comes from
    the get_folder_content function.

    Args:
        list_of_paths (list): a list
        folder_path (_type_): _description_

    Returns:
        _type_: _description_
    """
    # if folder_path[-1] != "/":
    #     folder_path += "/"
    base = [
            {
                'folder': folder_path,
                'subfolders': [],
                'files': []
            }
    ]

    for item in list_of_paths:
        if folder_path in item:
            remaining_path = item.split(folder_path)[-1]
            remaining_path_list = remaining_path.split('/')
            # if the remaining path is is file
            if len(remaining_path_list) == 1 and remaining_path != "":
                if remaining_path not in base[0]['files']:
                    # logger.error(remaining_path)
                    base[0]['files'].append(remaining_path)
            elif len(remaining_path_list) > 1 and remaining_path != "":
                subfolder = f"{folder_path}{remaining_path_list[0]}/"
                sub = parse_folder_structure(list_of_paths, subfolder)[0]
                if sub not in base[0]['subfolders']:
                    # logger.error(sub)
                    base[0]['subfolders'].append(sub)
    return base


# @lru_cache(maxsize=1)
def get_raw_folders(username, password, folder):
    list_of_paths = get_folder_content(username, password, folder)
    # logger.error(list_of_paths)
    return parse_folder_structure(list_of_paths, folder)


def get_user_info(token):
    """Gets the OC userinfo

    Args:
        token (str): _description_

    Returns:
        _type_: _description_
    """
    url = f"{drive_url}/index.php/apps/oauth2/api/v1/userinfo"
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.request("GET", url, headers=headers)
    if response.status_code == 200:
        return response.json()
 

def get_webdav_token(token, username):
    """Will get a webdav token.

    Args:
        token (str): the auth token
        username (str): the sub from userinfo
    Returns:
        str: the webdav token that has been set as app password under the name RDC
    """
    url = f"{drive_url}/ocs/v1.php/RDC/token/{username}"
    logger.debug(url)
    headers = {'Authorization': f'Bearer {token}'}
    logger.debug(headers)
    response = requests.request("GET", url, headers=headers)
    logger.debug(response)
    if response.status_code == 200:
        logger.debug(response.text)
        tree = ET.fromstring(response.text)
        for webdavtoken in tree.iter('token'):
            return webdavtoken.text


if __name__ == "__main__":
    from prettyprinter import pprint
    username = ""
    password = ""
    folder = ""
    result = get_quota(username, password)
    print(result)
    # print(cloud.get_permissions())
