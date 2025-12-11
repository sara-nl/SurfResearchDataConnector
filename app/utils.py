import configparser
import os
import shutil
from flask import session
import datahugger
import owncloud
import nextcloud_client
import requests
import pandas as pd
import hashlib
from lxml import html
import math
import json
import time
import glob
import datetime
import string
import re
from rocrate.rocrate import ROCrate
from rocrate.model.person import Person
from rocrate.model.dataset import Dataset
from functools import lru_cache
from functools import wraps
import xml.etree.ElementTree as ET
from authlib.integrations.requests_client import OAuth2Session
import pandas as pd

try:
    from app.models import app, db, History
    from app.globalvars import *
    from app.logs import *
except:
    # for testing this file locally
    try:
        from models import app, db, History
    except:
        pass
    from globalvars import *
    from logs import *
    cloud_service = 'nextcloud'
    drive_url = 'https://tst-miskatonic.data.surfsara.nl'
    print("testing")


from pprint import pprint

if cloud_service == "owncloud":
    cloud = owncloud.Client(drive_url)
elif cloud_service == "nextcloud":
    cloud = nextcloud_client.Client(drive_url)
else:
    # defaulting to the nextcloud lib in case cloud_service is not configured
    cloud = nextcloud.Client(drive_url)

global query_status
query_status = {}

global canceled
canceled = {}

global summary
summary = {}

global query_projectname
query_projectname = {}

global query_project_id
query_project_id = {}

global memo
memo = {}
def global_memoize(function):
    """memoization decorator that uses a globally available storage.
    So this should work between threads
    """   
    @wraps(function)
    def wrapper(*args):
        logger.error(args)
        # add the new key to dict if it doesn't exist already  
        if args not in memo:
            logger.error("caching")
            memo[args] = function(*args)
        return memo[args]
    return wrapper


def make_connection(username=None, password=None):
    """This function  will test if the username and password
    are correct

    Args:
        username (str): username of the cloud account
        password (str): password of the cloud account

    Returns:
        bool: returns True if connection is succesful, otherwise False
    """
    try:
        r = cloud.login(username, password)
        return True
    except Exception as e:
        if cloud_service.lower() == 'nextcloud':
            if 'password' in session and 'access_token' in session and 'cloud_token' in session:
                if session['password'] == None or session['password'] == "" or session['password'] == session['access_token']:
                    data = refresh_cloud_token(session['cloud_token'])
                    if data:
                        session['cloud_token'] = data
                        new_token = session['password'] = session['access_token'] = data['access_token']
                        session['refresh_token'] = data['refresh_token']
                        try:
                            r = cloud.login(username, new_token)
                            return True
                        except Exception as ee:
                            logger.error(ee, exc_info=True)
                            return False                        
        logger.error(e, exc_info=True)
        return False


def set_canceled(username, b):
    """set the username to True in the global canceled var (dict)
    Is useful for passing the canceled by user action to a thread
    that is processing in the background.

    Args:
        username (str): the username in the session
        b (bool): True is user has caneled the process, otherwise False
    """
    try:
        canceled[username] = b
    except Exception as e:
        logger.error(e, exc_info=True)


def get_canceled(username):
    """Get the canceled status for a user.

    Args:
        username (str): the username in the session

    Returns:
        bool: True is user has canceled the process
    """
    try:
        if username in canceled:
            return canceled[username]
        return False
    except Exception as e:
        logger.error(e, exc_info=True)


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
            message = "failed to retrieve data from url: {e}"
        update_history(username=username, folder=folder,
                       url=url, status=message)
    except Exception as e:
        logger.error(e, exc_info=True)
        message = "failed to retrieve data from url: {e}"
        update_history(username=username, folder=folder,
                       url=url, status=message)

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
        logger.error(str(e))
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
        make_connection(username, password)
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
    try:
        with app.app_context():
            hist = History.query.filter_by(username=username).filter_by(
                url=url).filter_by(status='ready').all()
            if len(hist) > 0:
                return True
            else:
                return False
    except Exception as e:
        logger.error(e, exc_info=True)


def get_query_status_history(username, folder, url):
    """will get the query statusses from the history table for the specified user, foleder and url combination

    Args:
        username (str): username of the OC account
        folder (str): the folder path of the retrieval
        url (str): the url of the retrieval

    Returns:
        dict: all query statusses
    """
    try:
        with app.app_context():
            return History.query.filter_by(username=username).filter_by(
                url=url).filter_by(folder=folder).order_by(History.id.desc()).all()
    except Exception as e:
        logger.error(e, exc_info=True)


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
    try:
        query_status[(username, folder, url)] = status
    except Exception as e:
        logger.error(e, exc_info=True)


def set_projectname(username, folder, url, projectname):
    """will set the projectname

    Args:
        username (str): username of the OC account
        folder (str): the folder path of the retrieval
        url (str): the url of the retrieval
        projectname (str): the new projectname
    """
    try:
        query_projectname[(username, folder, url)] = projectname
    except Exception as e:
        logger.error("failed to set the projectname")
        logger.error(e, exc_info=True)


def get_projectname(username, folder, url):
    """will get the current projectname

    Args:
        username (str): username of the OC account
        folder (str): the folder path of the retrieval
        url (str): the url of the retrieval

    Returns:
        str: the current projectname
    """
    try:
        return query_projectname[(username, folder, url)]
    except Exception as e:
        logger.error("failed to get the projectname")
        logger.error((username, folder, url))
        logger.error(query_projectname)
        logger.error(e, exc_info=True)
        return None


def set_project_id(username, folder, url, project_id):
    """will set the project_id

    Args:
        username (str): username of the OC account
        folder (str): the folder path of the retrieval
        url (str): the url of the retrieval
        project_id (str): the new project_id
    """
    try:
        query_project_id[(username, folder, url)] = project_id
    except Exception as e:
        logger.error("failed to set the project_id")
        logger.error(e, exc_info=True)


def get_project_id(username, folder, url):
    """will get the current project_id

    Args:
        username (str): username of the OC account
        folder (str): the folder path of the retrieval
        url (str): the url of the retrieval

    Returns:
        str: the current project_id
    """
    try:
        return query_project_id[(username, folder, url)]
    except:
        return None




def total_files_count(folder):
    """calculate the total files count for a folder

    Args:
        folder (str): path to the folder

    Returns:
        int: file count
    """
    try:
        totalfilescount = 0
        for root, dirs, files in os.walk(folder):
            for file in files:
                totalfilescount += 1
        return totalfilescount
    except Exception as e:
        logger.error(e, exc_info=True)


def push_data(username, password, folder, url, repo=None):
    """Will push data from a local folder to a folder on an owncloud instance.

    Args:
        username (str): username for logging on to the owncloud instance.
        password (str): application password for logging on to the owncloud instance.
        folder (str): folder path
    """
    logger.info("Start push data via webdav to RD")


    restorefolderpath = folder
    if repo == "surfs3":
        restorefolderpath = f"./RESTORE/{folder}/"

    message = None
    try:
        folder_exists = check_if_folder_exists(username, password, folder, url)
        if folder_exists:
            message = f"folder {folder} already exists."
            update_history(username, folder, url, message)
            logger.info(message)

        # first login
        try:
            make_connection(username, password)
        except Exception as e:
            logger.error(e, exc_info=True)
            message = f"failed to login to webdav: {e}"
            update_history(username, folder, url, message)

        # calculate the total files count
        totalfilescount = total_files_count(restorefolderpath)

        # upload file by file to OC
        n = 1

        ### Lets first create all the needed folders at RD ###
        walkfolder = folder
        if repo == "surfs3":
            walkfolder = f"./RESTORE/{folder}/"

        for folderpath, dirs, files in os.walk(walkfolder):
            # make sure we do not create or upload to the temp folders: RESTORE, ARCHIVE and the files folder created by S3
            if repo == "surfs3":
                folderpath = folderpath.split("./RESTORE/")[-1]
                folderpath = folderpath.split("/ARCHIVE/files")[-1]
                folderpath = folderpath.split("/ARCHIVE")[-1]
                folderpath = folderpath.replace("//", "/")
            #If user did not cancel the import process
            if not get_canceled(username):

                # create the folder path at RD if it does not exist
                if not check_if_folder_exists(username, password, folderpath, url):
                    logger.info(f"folder {folderpath} does not exits, lets create it.")
                    try:
                        createdfolder = cloud.mkdir(folderpath)
                        if createdfolder:
                            logger.info(f"Succesfully created folder: {folderpath}")
                        else:
                            logger.info(f"Could not create folder: {folderpath} : {createdfolder}")
                    except Exception as e:
                        if str(e) == "HTTP error: 405":
                            message = "Folder already exists"
                            logger.info(message)
                        else:
                            logger.info(f"Could not create folder: {folderpath} : {e}")
                            message = f"failed to create folder: {e}"
                        update_history(username, folder, url, message)
        ### end of generating all folders at RD ###

        ### now let's start uploading all the files to the created folderpaths at RD ###
        for folderpath, dirs, files in os.walk(walkfolder):
            if not get_canceled(username):
                for file in files:
                    filepath = os.path.join(folderpath, file)
                    logger.info(f"About to upload file {n} of {totalfilescount}: {filepath}")
                    try:
                        # make sure we do not create or upload to the temp folders: RESTORE, ARCHIVE and the files folder created by S3
                        if repo == "surfs3":
                            remotefilepath = filepath.split("./RESTORE/")[-1]
                            remotefilepath = remotefilepath.split("/ARCHIVE/files")[-1]
                            remotefilepath = remotefilepath.split("/ARCHIVE")[-1]
                            remotefilepath = remotefilepath.replace("//", "/")
                            cloud.put_file(remotefilepath, filepath)
                            message = f"uploaded file {n} of {totalfilescount}: {remotefilepath}"
                        else:
                            cloud.put_file(filepath, filepath)
                            message = f"uploaded file {n} of {totalfilescount}: {filepath}"
                    except Exception as e:
                        try:
                            message = f"Retrying to upload file {n} of {totalfilescount}: {filepath} after exception: {e}"
                            update_history(username, folder, url, message)
                            # let's try to create the folder again
                            if cloud.mkdir(folderpath):
                                cloud.put_file(filepath, filepath)
                                message = f"uploaded file {n} of {totalfilescount}: {filepath}"                             
                        except Exception as ee:
                            logger.error(ee)
                            message = f"failed to upload file {n} of {totalfilescount}: {filepath} - {ee}"
                    update_history(username, folder, url, message)
                    n += 1
        ### end of uploading files ###

        # remove the local folder with the data
        try:
            shutil.rmtree(walkfolder)
            update_history(username,folder, url, "removing temporary data")
        except Exception as e:
            logger.error(e, exc_info=True)
            update_history(username,folder, url, f"failed to remove temporary data: {e}")
    except Exception as eee:
        try:
            shutil.rmtree(walkfolder)
            update_history(username,folder, url, "removing temporary data")
        except Exception as ee:
            logger.error(ee, exc_info=True)
            update_history(username,folder, url, f"failed to remove temporary data: {ee}")
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
    try:
        folder_exists = check_if_folder_exists(username, password, folderpath)
        if not folder_exists:
            if make_connection(username, password):
                cloud.mkdir(folderpath)
                cloud.delete(folderpath)
                return True
            else:
                logger.error("failed to login to webdav")
                return False
        else:
            logger.info("folder exists")
            return True
    except Exception as e:
        logger.error(e, exc_info=True)


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
        if make_connection(username, password):
            result = cloud.list(folder, depth=100)
            paths = ["/"]
            for item in result:
                folder_path = item.get_path()
                if folder_path not in paths:
                    paths.append(folder_path)
            return paths
        else:
            message = "failed to login to webdav"
            logger.error(message)
    except Exception as e:
        message = "failed to list folders"
        logger.error(message)
        logger.error(e, exc_info=True)
        return message


@global_memoize
def get_cached_folders(username, password, folder):
    return get_folders(username, password, folder)


def get_folder_content(username, password, folder, files_only=False):
    """Will get a folder content on an owncloud instance.

    Args:
        username (str): username for logging on to the owncloud instance.
        password (str): application password for logging on to the owncloud instance.
        folder (str): folder path

    Returns:
        list: list of available files and folder paths in the specified folder
    """
    try:
        if make_connection(username, password):
            paths = []
            try:
                result = cloud.list(folder, depth=100)
            except:
                result = []
            if len(result) > 0:
                for item in result:
                    if files_only:
                        if item.file_type == 'file':
                            folder_path = item.path
                            if folder_path not in paths:
                                paths.append(folder_path)
                    else:
                        folder_path = item.path
                        if folder_path not in paths:
                            paths.append(folder_path)
            return paths
        else:
            logger.error("Failed to make connection.")
            return []
    except Exception as e:
        logger.error(e, exc_info=True)
        return []


def get_folder_content_props(username, password, folder, properties=None):
    """Will get a folder content props on an cloud instance.

    Args:
        username (str): username for logging on to the cloud instance.
        password (str): application password for logging on to the cloud instance.
        folder (str): folder path

    Returns:
        list: list of available files and folder paths in the specified folder with all props 
    """
    try:
        if make_connection(username, password):
            result = []
            FileInfoObject = cloud.list(folder, depth=100, properties=properties)
            for object in FileInfoObject:
                object_dict = {}
                object_dict['path'] = object.path
                object_dict['file_type'] = object.file_type
                object_dict['attributes'] = object.attributes
                result.append(object_dict)
            return result
        else:
            logger.error("Failed to make connection.")
            return []
    except Exception as e:
        logger.error(e, exc_info=True)
        return []


def refresh_cloud_token(data):
    """Will refresh the cloud token data.

    Args:
        data (dict): the cloud token data

    Returns:
        dict: refreshed cloud token data
    """
    try:
        new_token = old_token = data['access_token']
        refresh_url = f'{drive_url}/index.php/apps/oauth2/api/v1/token'
        refresh_token = data['refresh_token']
        extra = {
            'client_id': cloud_client_id,
            'client_secret': cloud_client_secret,
        }
        rdrive = OAuth2Session(cloud_client_id, token=refresh_token)
        data = rdrive.refresh_token(url=refresh_url, refresh_token=refresh_token, **extra)
        new_token = data['access_token']
        if new_token != old_token:
            return data
    except Exception as e:
        logger.error(f"Failed at refresh access token")
        logger.error(e, exc_info=True)


def get_status_from_history(username, folder, url):
    try:
        with app.app_context():
            return History.query.filter_by(username=username).filter_by(
                url=url).filter_by(folder=folder).order_by(History.id.desc()).all()[0].status
    except Exception as e:
        logger.error(e, exc_info=True)


def update_history(username, folder, url, status):
    """update the history table in the database
    and update the query status

    Args:
        username (str): username of the owncloud
        folder (str): folder path of the data
        url (str): url of the location of the data
        status (str): status of the data import
        projectname (str): name of the project
    """
    try:
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
        
        projectname = get_projectname(username, folder, url)

        with app.app_context():
            history = History(username=username,
                            folder=folder,
                            url=url,
                            status=status,
                            projectname=projectname)
            db.session.add(history)
            db.session.commit()
        
        if status == 'ready':
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
                                status=final_message,
                                projectname=projectname)
                db.session.add(history)
                db.session.commit() 

        set_query_status(username, folder, url, status)
    except Exception as e:
        logger.error(e, exc_info=True)

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
                folderstripped = folder.split("./RESTORE/")[-1].replace("//", "/")
                # remove trailing slash if any
                if folderstripped[-1] == "/":
                    folderstripped = folderstripped[:-1]
                update_history(username, folderstripped, url, status)
        try:
            timestamp = str(time.time()).split('.')[0]
        except:
            timestamp = ""
        generated_path = create_generated_folder(folder)
        with open(f"{generated_path}/checksums{timestamp}.json", "w") as f:
            json.dump(checksums, f)
    except Exception as e:
        logger.error(e, exc_info=True)


def run_import(username, password, folder, url):
    """Execute steps for importing and updates the history for every step.

    Args:
        username (str): username of the owncloud account
        password (str): password of the owncloud account
        folder (str): folder path of the data
        url (str): url of the location of the data
    """
    try:
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
    except Exception as e:
        update_history(username, folder, url, f"failed at import: {e}")
        logger.error(e, exc_info=True)


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

        if cloud_service == 'nextcloud' and available < 0:
            total = "unlimited"
            percent = 0
        else:
            total = used + available
            percent = round((used / total) * 100.0)

        result = f"You are using {convert_size(used)} of {convert_size(total)} ({percent}%). "
        
        have_permission = quota[2]
        if have_permission:
            result += "You have write permission to this folder."
        else:
            result += "You do not have write permission to this folder."
        
        return result
    except Exception as e:
        logger.error("Exception at get_quota_text")
        logger.error(e, exc_info=True)


def get_quota(username, password, folder=None):
    """Will get the used and available storage quota in bytes

    Args:
        username (str): username for logging on to the owncloud instance.
        password (str): application password for logging on to the owncloud instance.
        folder (str): the folder that the user will be using

    Returns:
        tuple: the used and available quota in bytes
    """
    try:
        root_folder = "/"
        used = 0
        available = 0
        ### determine the project folder if there is one
        folders = folder.split("/")
        project_folder = "/"
        # by default the project folder is the folder on top of root
        if len(folders) > 1:
            project_folder = "/{}/".format(folders[1])
        # Or it can have (Projectfolder) in it's name
        for item in folders:
            if item.find(" (Projectfolder)") != -1:
                project_folder = f"/{item}/"

        have_permission = False
        test_folder = f"{project_folder}/testingpermissions"
 
        if make_connection(username, password):
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

            if cloud_service == "nextcloud":
                result = cloud.list(root_folder, depth=1)
                for r in result:
                    try:
                        used += int(r.attributes['{DAV:}quota-used-bytes'])
                        available = int(r.attributes['{DAV:}quota-available-bytes'])
                    except:
                        pass

        return (used, available, have_permission)
    except Exception as e:
        logger.error(e, exc_info=True)

def convert_to_size(number, size_name):
    """convert a number size_name combination to bytes

    Args:
        number (float): the number part of the human readble file size
        size_name (float): the size name part of the human readable file size

    Returns:
        int: the size in bytes
    """
    try:
        size_names = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
        i = size_names.index(size_name)
        p = math.pow(1024, i)
        return int(number * p)
    except Exception as e:
        logger.error(e, exc_info=True)


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
    except Exception as e:
        logger.error(e, exc_info=True)
        return size_bytes


def repo_content_fits(repo_content, username, password, folder):
    """compares the total filesize from the repo_content to the free storage size at RD.

    Args:
        repo_content (list): the repo_content_data
        username (str): webdav username
        password (str): webdav password
        folder (str): path tof the folder to hold the repo content

    Returns:
        bool: True if the files in repo_content will fit into the free storage space.
    """
    try:
        quota = get_quota(username, password, folder)
        free_bytes = int(quota[1])
        if free_bytes < 0 and cloud_service == 'nextcloud':
            return True

        # calculate the total size in bytes that the files will take up
        total_file_size = 0
        for item in repo_content:
            total_file_size += int(item['size'])

        if free_bytes > total_file_size:
            return True

    except Exception as e:
        logger.error("Exception at repo_content_fits")
        logger.error(e)
        return None

    return False


def repo_content_can_be_processed(repo_content):
    """compares the total filesize from the repo_content to the free storage size at the pod.

    Args:
        repo_content (list): the repo_content_data

    Returns:
        bool: True if the files in repo_content will fit into the free storage space.
    """
    try:
        # calculate the total size in bytes that the files will take up
        total_file_size = 0
        for item in repo_content:
            total_file_size += int(item['size'])

        # get the free bytes on the pod disk
        free_bytes = shutil.disk_usage("/").free
        
        # compare: we need twice the repo_content size as diskspace as we also download the content as a zip
        if free_bytes > total_file_size * 2.0:
            return True
        else:
            return False

    except Exception as e:
        logger.error("Exception at repo_content_can_be_processed")
        logger.error(e)
        return False

    return False



def folder_content_can_be_processed(username, password, folder):
    """Will get a the folder content and see if it is not to large to be processed by the pod.

    Args:
        username (str): username for logging on to the owncloud instance.
        password (str): application password for logging on to the owncloud instance.
        folder (str): folder path

    Returns:
        bool: True is processing can be done
    """
    result = {'can_be_processed' : False, 'total_size': 0, 'free_bytes' : 0}
    try:
        # calculate the total size in bytes that the files will take up
        if make_connection(username, password):
            list_result = cloud.list(folder, depth=100)
            for item in list_result:
                try:
                    result['total_size'] += item.get_size()
                except:
                    pass
        
        # get the free bytes on the pod disk
        result['free_bytes'] = int(shutil.disk_usage("/").free)

        # compare: we need twice the folder_content size as diskspace as we also create the content as a zip
        if result['free_bytes'] > result['total_size'] * 2.0:
            result['can_be_processed'] = True
    except Exception as e:
        logger.error(e, exc_info=True)
    return result


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
    except Exception as e:
        logger.error(e, exc_info=True)
        return {}


def get_rocrate(folder, rocrate_filename='ro-crate-metadata.json'):
    """check if the folder contains a rocrate file and return the content

    Args:
        folder (str): folder path to look for rocrate file

    Returns:
        dict: the content of the file
    """
    try:
        for dirpath, subdirs, files in os.walk(folder):
            if rocrate_filename in files:
                ro_crate_filepath = f"{dirpath}/ro-crate-metadata.json"
                with open(ro_crate_filepath, 'r') as f:
                    result = json.loads(f.read())
                return result
    except Exception as e:
        logger.error(e, exc_info=True)


def create_generated_folder(folder):
    """will check if there is a 'generated' folder in the folder and create it if it is not there.

    Args:
        folder (str): the folder path where the generated folder needs to be created
    """
    try:
        generated_path = f"{folder}/generated"
        if not os.path.isdir(generated_path):
            os.mkdir(generated_path)
        return generated_path
    except Exception as e:
        logger.error(e, exc_info=True)


def create_rocrate(url, folder, metadata = None, repo_content=None):
    """will create a rocrate file in the folder based on the metadata
    that will be retrieved from the url.

    Args:
        url (str): the url where the data will be retrieved from
        folder (str): the folder where the data will be written to
    """
    try:
        # TODO: if metadata is not none then use that data to ccreate rocrate file. This is for upload
        crate = ROCrate()
        dataset = crate.add(Dataset(crate, dest_path="./"))

        # get metadata from doi url if available
        if url.find('http') != -1 and metadata == {} or metadata == None:
            metadata = get_doi_metadata(url)
            if metadata != {} and metadata != None:
                metadata = parse_doi_metadata(metadata)

        # if we have metadata use this
        if metadata != {} and metadata != None:
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

        # add the files (datahugger)
        try:
            if repo_content:
                dataset['files'] = repo_content
            else:
                dataset['files'] = get_files_info(url)
        except:
            dataset['files'] = ['not available']
        

        # timestamp the ro-crate file
        dataset["timestamp"] = str(datetime.datetime.now())

        generated_path = create_generated_folder(folder)
        crate.write(generated_path)
    except Exception as e:
        logger.error(e, exc_info=True)


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
    try:
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
                        base[0]['files'].append(remaining_path)
                elif len(remaining_path_list) > 1 and remaining_path != "":
                    subfolder = f"{folder_path}{remaining_path_list[0]}/"
                    sub = parse_folder_structure(list_of_paths, subfolder)[0]
                    if sub not in base[0]['subfolders']:
                        base[0]['subfolders'].append(sub)
        return base
    except Exception as e:
        logger.error(e, exc_info=True)


def get_raw_folders(username, password, folder):
    try:
        list_of_paths = get_folder_content(username, password, folder)
        return parse_folder_structure(list_of_paths, folder)
    except Exception as e:
        logger.error(e, exc_info=True)


def get_user_info(username, password):
    """Gets the RD userinfo

    Args:
        username (str): username for connecting to RD
        password (str): the app password (OC) or token (NC)

    Returns:
        dict: all available user information
    """
    cloud.login(username, password)
    return cloud.get_user(username)


def get_user_info_by_token(token):
    """Gets the RD userinfo by oauth access_token

    Args:
        token (str): the oauth2 access_token

    Returns:
        dict: user info sub and name
    """
    try:
        url = f"{drive_url}/index.php/apps/oauth2/api/v1/userinfo"
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.request("GET", url, headers=headers)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(e, exc_info=True)
 

def get_webdav_token(token, username):
    """Will get a webdav token for owncloud.

    Args:
        token (str): the auth token
        username (str): the sub from userinfo
    Returns:
        str: the webdav token that has been set as app password under the name RDC
    """
    try:
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
    except Exception as e:
        logger.error(e, exc_info=True)


def get_webdav_poll_info_nc(token):
    """Will get a webdav poll info for nextcloud.

    Args:
        token (str): the auth token
    Returns:
        dict: the webdav poll info that can be used to set app password
    """
    try:
        result = {}
        url = f"{drive_url}/index.php/login/v2"
        print("url", url)
        headers = {'Authorization': f'Bearer {token}', 'User-Agent': 'SRDC'}
        response = requests.request("POST", url, headers=headers)
        if response.status_code == 200:
            result['poll_login'] = response.json()['login']
            poll_token = response.json()['poll']['token']
            result['poll_endpoint'] = response.json()['poll']['endpoint'] + "?token=" + poll_token
        return result
    except Exception as e:
        logger.error(e, exc_info=True)


def get_webdav_token_nc(poll_endpoint):
    """Will get a webdav token for nextcloud.

    Args:
        poll_endpoint (str): the endpoint url for polling the webdav app password
    Returns:
        dict: the webdav loginName and appPassword that has been set as app password
    """
    try: 
        headers = {'User-Agent': 'SRDC'}
        poll_response = requests.request("POST", poll_endpoint, headers=headers)
        if poll_response.status_code == 200:
            return poll_response.json()
    except Exception as e:
        logger.error(e, exc_info=True)

@lru_cache(maxsize=None)
def get_dans_audiences():
    """will return the dans_audiences

    Returns:
        json: the response result of the dans_audiences endpoint
    """
    results = []
    for i in list(string.ascii_lowercase):
        url = f'https://demo.vocabs.datastations.nl/rest/v1/search?unique=true&maxhits=2000&vocab=NARCIS&parent=&lang=en&&query=*{i}*'
        response = requests.get(url)
        for item in response.json()['results']:
            if item not in results:
                results.append(item)
    return results

@lru_cache(maxsize=None)
def memoize(f):
    """memoization function to wrap api requests that take long time to return, but whos responses do not change often.

    Args:
        f (obj): funtion call

    Returns:
        obj: return value of the function call
    """
    return f


def create_monthly(sqlquery):
    """Will take a sqlalchemy query and wrangle it into a pandas dataframe.

    Returns:
        tuple: two dataframes. one with monthly and one with cummulative data 
    """
    try:
        data = [u.__dict__ for u in sqlquery.all()]
        df = pd.DataFrame(data)
        df['year'] = df["time_created"].dt.year
        df['month'] = df["time_created"].dt.month
        df['year-month'] = df['year'].astype(str) + "-" + df["month"].astype(str)
        df['year-month']=pd.to_datetime(df['year-month'])
        monthly = df[["year-month"]].groupby(df["year-month"]).count()
        cummulative = df[["year-month"]].groupby(df["year-month"]).count().cumsum()
    except Exception as e:
        logger.error(str(e))
        return None
    return monthly, cummulative

def metavox_get_team_folders(user,token):
    """Does a get call to the Metavox API endpoint: /groupfolders.
    Returns all the available metavox team folders

    Args:
        user (str): the username of the connected nextcloud instance
        token (str): the (app) password for the users account

    Returns:
        json: _description_
    """
    try:
        endpoint = "/groupfolders"
        ocs_api = "/ocs/v2.php/apps/metavox/api/v1"
        url = drive_url + ocs_api + endpoint
        headers = {
                "Authorization": "sanitized",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "OCS-APIRequest": "true"
                }
        response = requests.request("GET", url, auth=(user, token), headers=headers)
        return response.json()
    except Exception as e:
        logger.error(e)

def metavox_get_files(user,token, groupfolderId):
    try:
        endpoint = f"/groupfolders/{groupfolderId}/files"
        ocs_api = "/ocs/v2.php/apps/metavox/api/v1"
        url = drive_url + ocs_api + endpoint
        headers = {
                "Authorization": "sanitized",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "OCS-APIRequest": "true"
                }
        response = requests.request("GET", url, auth=(user, token), headers=headers)
        return response.json()
    except Exception as e:
        logger.error(e)

def metavox_get_folder_meatadata(user,token, groupfolderId):
    try:
        endpoint = f"/groupfolders/{groupfolderId}/metadata"
        ocs_api = "/ocs/v2.php/apps/metavox/api/v1"
        url = drive_url + ocs_api + endpoint
        headers = {
                "Authorization": "sanitized",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "OCS-APIRequest": "true"
                }
        response = requests.request("GET", url, auth=(user, token), headers=headers)
        return response.json()
    except Exception as e:
        logger.error(e)

def metavox_get_file_metadata(user,token, groupfolderId, fileId):
    try:
        endpoint = f"/groupfolders/{groupfolderId}/files/{fileId}/metadata"
        ocs_api = "/ocs/v2.php/apps/metavox/api/v1"
        url = drive_url + ocs_api + endpoint
        headers = {
                "Authorization": "sanitized",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "OCS-APIRequest": "true"
                }
        response = requests.request("GET", url, auth=(user, token), headers=headers)
        return response.json()
    except Exception as e:
        logger.error(e)

def metavox_get_file_id(user,token, folder):
    try:
        endpoint = f"/files/{user}{folder}"
        dav_api = "/remote.php/dav"
        url = drive_url + dav_api + endpoint
        headers = {}
        data = """
        <d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns" xmlns:nc="http://nextcloud.org/ns">
            <d:prop>
                    <oc:fileid />
            </d:prop>
        </d:propfind>
        """
        response = requests.request("PROPFIND", url, auth=(user, token), data=data, headers=headers)
        result = re.findall(r'<oc:fileid>(.*?)</oc:fileid>', response.text)[0]
        return result
    except Exception as e:
        logger.error(e)

if __name__ == "__main__":
    user = 'dashboardadmin1'
    # token = 'AbdZW-mdEfs-e3yLT-zZSsj-w3sw6'
    token = "Nr6NJ-qECkz-MacMY-8CATz-EWajb"
    # pprint(metavox_get_team_folders(user, token))
    # pprint(metavox_get_folder_meatadata(user, token, 1))
    folder = "/Demo metavox/MetaVox_Testing_Folder/Nieuw document.docx"
    result = metavox_get_file_id(user,token, folder)
    print(result)
    # print(dir(result))