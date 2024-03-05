from app.repos.osf import Osf
from app.repos.figshare import Figshare
from app.repos.zenodo import Zenodo
from app.repos.dataverse import Dataverse
from app.repos.irods_repo import Irods
from app.repos.sharekit import Sharekit
from app.utils import update_history, create_generated_folder, total_files_count, get_canceled
from app.utils import create_rocrate, check_checksums, push_data, get_query_status, get_status_from_history
import logging
import owncloud
import zipfile
import shutil
import os
from urllib.parse import urlparse
from urllib.parse import parse_qs

try:
    from app.globalvars import *
except:
    # for testing this file locally
    from globalvars import *
    print("testing")


logger = logging.getLogger()

oc = owncloud.Client(drive_url)

def get_repocontent(repo, url, api_key, user=None):
    repo_content = [{'message' : f'failed to get repo content from {repo}'}]
    if repo == 'figshare':
        figshare = Figshare(api_key=api_key, api_address=figshare_api_url)
        try:
            article_id = int(url.split('/')[-1])
        except:
            article_id = int(url.split('/')[-2])
        repo_content = figshare.get_repo_content(article_id=article_id)
    if repo == 'zenodo':
        zenodo = Zenodo(api_key=api_key, api_address=zenodo_api_url)
        try:
            deposition_id = int(url.split('/')[-1])
        except:
            deposition_id = int(url.split('/')[-2])
        repo_content = zenodo.get_repo_content(deposition_id=deposition_id)
    if repo == 'osf':
        # logger.error(url)
        osf = Osf(api_key=api_key, api_address=osf_api_url)
        split_url = url.split('/')
        # logger.error(split_url)
        if split_url[-1] != '':
            project_id = str(split_url[-1])
        else:
            project_id = str(split_url[-2])
        repo_content = osf.get_repo_content(project_id=project_id)
        # logger.error(repo_content)
    if repo == 'dataverse':
        try:
            dataverse = Dataverse(api_key=api_key, api_address=dataverse_api_url)
            if url.find('doi.org') == -1:
                persistent_id = url.split('?')[-1]
                persistent_id = persistent_id.split('&')[0]
                persistent_id = persistent_id.split('=')[-1]
            else:
                persistent_id = url.split('doi.org/')[-1]
                persistent_id = 'doi:' + persistent_id
            repo_content = dataverse.get_repo_content(persistent_id=persistent_id)
        except:
            repo_content = []
    if repo == 'irods':
        # irods = Irods(api_key=api_key, user=user, api_address=irods_api_url)
        irods = Irods(api_key=api_key, api_address=irods_api_url, user=user)
        parsed = urlparse(url)
        path = parse_qs(parsed.query)['dir'][0]
        logger.error(f"path: {path}")
        repo_content = irods.get_repo_content(path=path)
    if repo == 'sharekit':
        sharekit = Sharekit(api_key=api_key, api_address=sharekit_api_url)
        try:
            article_id = int(url.split('/')[-1])
        except:
            article_id = int(url.split('/')[-2])
        repo_content = sharekit.get_repo_content(article_id=article_id)
    return repo_content


def get_private_metadata(repo, url, api_key, user=None):
    private_metadata = {}
    if repo == 'figshare':
        figshare = Figshare(api_key=api_key, api_address=figshare_api_url)
        try:
            article_id = int(url.split('/')[-1])
        except:
            article_id = int(url.split('/')[-2])
        private_metadata = figshare.get_private_metadata(article_id=article_id)
    if repo == 'zenodo':
        zenodo = Zenodo(api_key=api_key, api_address=zenodo_api_url)
        try:
            deposition_id = int(url.split('/')[-1])
        except:
            deposition_id = int(url.split('/')[-2])
        private_metadata = zenodo.get_private_metadata(deposition_id=deposition_id)
    if repo == 'osf':
        osf = Osf(api_key=api_key, api_address=osf_api_url)
        split_url = url.split('/')
        if split_url[-1] != '':
            project_id = str(split_url[-1])
        else:
            project_id = str(split_url[-2])
        private_metadata = osf.get_private_metadata(project_id=project_id)
    if repo == 'dataverse':
        dataverse = Dataverse(api_key=api_key, api_address=dataverse_api_url)
        if url.find('doi.org') == -1:
            persistent_id = url.split('?')[-1]
            persistent_id = persistent_id.split('&')[0]
            persistent_id = persistent_id.split('=')[-1]
        else:
            persistent_id = url.split('doi.org/')[-1]
            persistent_id = 'doi:' + persistent_id
        private_metadata = dataverse.get_private_metadata(persistent_id=persistent_id)
    if repo == 'irods':
        irods = Irods(api_key=api_key, user=user, api_address=irods_api_url)
        parsed = urlparse(url)
        path = parse_qs(parsed.query)['dir'][0]
        repo_content = irods.get_repo_content(path=path)
        private_metadata = irods.get_private_metadata(path=path)
    if repo == 'sharekit':
        sharekit = Sharekit(api_key=api_key, api_address=sharekit_api_url)
        try:
            article_id = int(url.split('/')[-1])
        except:
            article_id = int(url.split('/')[-2])
        private_metadata = sharekit.get_private_metadata(article_id=article_id)
    return private_metadata


def get_private_files(repo, url, folder, api_key, user=None):
    private_files = False
    if repo == 'figshare':
        figshare = Figshare(api_key=api_key, api_address=figshare_api_url)
        try:
            article_id = int(url.split('/')[-1])
        except:
            article_id = int(url.split('/')[-2])
        private_files = figshare.download_files(article_id=article_id, dest_folder=folder)
    if repo == 'zenodo':
        zenodo = Zenodo(api_key=api_key, api_address=zenodo_api_url)
        try:
            deposition_id = int(url.split('/')[-1])
        except:
            deposition_id = int(url.split('/')[-2])
        private_files = zenodo.download_files(deposition_id=deposition_id, dest_folder=folder)
    if repo == 'osf':
        osf = Osf(api_key=api_key, api_address=osf_api_url)
        split_url = url.split('/')
        if split_url[-1] != '':
            project_id = str(split_url[-1])
        else:
            project_id = str(split_url[-2])
        private_files = osf.download_files(project_id=project_id, dest_folder=folder)
    if repo == 'dataverse':
        dataverse = Dataverse(api_key=api_key, api_address=dataverse_api_url)
        if url.find('doi.org') == -1:
            persistent_id = url.split('?')[-1]
            persistent_id = persistent_id.split('&')[0]
            persistent_id = persistent_id.split('=')[-1]
        else:
            persistent_id = url.split('doi.org/')[-1]
            persistent_id = 'doi:' + persistent_id
        private_files = dataverse.download_files(persistent_id=persistent_id, dest_folder=folder)
    if repo == 'irods':
        irods = Irods(api_key=api_key, user=user, api_address=irods_api_url)
        parsed = urlparse(url)
        path = parse_qs(parsed.query)['dir'][0]
        repo_content = irods.get_repo_content(path=path)
        private_files = irods.download_files(path=path, dest_folder=folder)
    if repo == 'sharekit':
        sharekit = Sharekit(api_key=api_key, api_address=sharekit_api_url)
        try:
            article_id = int(url.split('/')[-1])
        except:
            article_id = int(url.split('/')[-2])
        private_files = sharekit.download_files(article_id=article_id, dest_folder=folder)
    return private_files


def run_private_import(username, password, folder, url, repo, api_key, user=None):
    """Execute steps for private imports and updates the history for every step.

    Args:
        username (str): username of the owncloud account
        password (str): password of the owncloud account
        folder (str): folder path of the data
        url (str): url of the location of the data
    """
    update_history(username, folder, url, 'started')
    if not get_canceled(username):
        update_history(username, folder, url, 'getting file data')
        result = get_private_files(repo, url, folder, api_key=api_key, user=user)
        if result == True:
            update_history(username, folder, url, f'getting file data done {result}')
        else:
            update_history(username, folder, url, f'getting file data failed: {result}')

    if not get_canceled(username):
        update_history(username, folder, url, 'start checking checksums')
        files_info = get_repocontent(repo, url, api_key, user=None)
        check_checksums(username, url, folder, files_info=files_info)
        update_history(username, folder, url, 'created checksums')

    if not get_canceled(username):
        update_history(username, folder, url,
                    'creating ro-crate-metadata.json file ')
        try:
            create_rocrate(url, folder)
            update_history(username, folder, url,
                    'created ro-crate-metadata.json file')
        except:
            update_history(username, folder, url,
                    'failed to create ro-crate-metadata.json file')

    if not get_canceled(username):
        update_history(username, folder, url, 'start pushing dataset to storage')
        push_data(username, password, folder, url)
        
    update_history(username, folder, url, 'ready')



def check_connection(repo, api_key, user=None):
    # logger.error("check connection")
    connection_ok = False
    if repo == 'osf':
        osf = Osf(api_key=api_key, api_address=osf_api_url)
        connection_ok = osf.check_token()
    if repo == "figshare":
        figshare = Figshare(api_key=api_key, api_address=figshare_api_url)
        connection_ok = figshare.check_token(api_key=api_key)
    if repo == "zenodo":
        zenodo = Zenodo(api_key=api_key, api_address=zenodo_api_url)
        connection_ok = zenodo.check_token(api_key=api_key)
    if repo == "dataverse":
        dataverse = Dataverse(api_key=api_key, api_address=dataverse_api_url)
        connection_ok = dataverse.check_token(api_key=api_key)   
    if repo == "irods":
        irods = Irods(api_key=api_key, api_address=irods_api_url, user=user)
        connection_ok = irods.check_token(api_key=api_key, user=user)
    if repo == "sharekit":
        sharekit = Sharekit(api_key=api_key, api_address=sharekit_api_url)
        connection_ok = sharekit.check_token(api_key=api_key)
    return connection_ok


def run_export(username, password, complete_folder_path, repo, repo_user, api_key, metadata, use_zip=False):

    ### NOTE ###
    # let's first implement an on disk solution, as we have seen that the buffered solution is not working with ScieboRDS
    # This is probably gonna be slower, but less error prone.
    # Let's first build something that works reliably and only then optimize for speed and prettyness
    # This will also allow reuse of code written for the retrieval of repos

    update_history(username=username, folder=complete_folder_path,
                   url=repo, status='started')

    # connect to OC
    try:
        oc.login(username, password)
    except:
        message = "failed to connect to RD"
        logger.error(message)
        update_history(username=username,
                       folder=complete_folder_path, url=repo, status=message)
        return

    if not get_canceled(username):
        # Download the data from OC
        update_history(username=username, folder=complete_folder_path,
                    url=repo, status='start downloading project as zipfile')
        tmpzip = complete_folder_path.split("/")[-1] + ".zip"
        downloaded = oc.get_directory_as_zip(
            remote_path=complete_folder_path, local_file=tmpzip)
        update_history(username=username, folder=complete_folder_path,
                    url=repo, status='done downloading project as zipfile')

    if not get_canceled(username):
        # unzip the file to folder with name of last part of complete folder path.
        update_history(username=username, folder=complete_folder_path,
                    url=repo, status='unzipping the zipfile')
        unzipped_folder = "./" + complete_folder_path.split("/")[-1]
        with zipfile.ZipFile(tmpzip, 'r') as zip_ref:
            zip_ref.extractall('./')

    if not get_canceled(username):
        # remove the zip
        update_history(username=username, folder=complete_folder_path,
                    url=repo, status='removing the zipfile')
        os.remove(tmpzip)


    if not get_canceled(username):
        # write metadata in ro-crate file in 'generated' folder inside the unzipped folder
        update_history(username=username, folder=complete_folder_path,
                    url=repo, status="creating ro-crate file in 'generated' folder")
        try:
            create_rocrate(url=repo, folder=unzipped_folder, metadata=metadata)
            update_history(username=username, folder=complete_folder_path,
                    url=repo, status="created ro-crate file in 'generated' folder")
        except:
            update_history(username=username, folder=complete_folder_path,
                    url=repo, status="failed at creating ro-crate file in 'generated' folder")

    # if not get_canceled(username):
    #     # write the metadata in generated folder back to OC
    #     # upload the local generate folder into the coomplete folder path at OC
    #     # TODO : Fix this, nice to have
    #     update_history(username=username, folder=complete_folder_path,
    #                 url=repo, status="backing up ro-crate file to RD")
    #     try:
    #         oc.put_directory(target_path=complete_folder_path, local_directory=f'{unzipped_folder}/generated')
    #     except:
    #         update_history(username=username, folder=complete_folder_path,
    #                 url=repo, status="failed at backing up ro-crate file to RD")

    if not get_canceled(username):
        # if user selected upload as zip to perserve folder structure
        if use_zip:
            # zip the unzipped_folder to tmpzip
            update_history(username=username, folder=complete_folder_path,
                    url=repo, status=f"creating zipfile {tmpzip} for upload")
            shutil.make_archive(complete_folder_path.split("/")[-1], 'zip', unzipped_folder)

    ### NOTE: Alternative implementation ###
    # instead of downloading all files at once, we can get the filepaths at oc as a list
    # in upload we provide the list and will download and upload each file one by one.
    # When downloading we can download to disk or we could buffer the file
    ##################################

    #########################################################################

    if not get_canceled(username):
        ### instantiate repo ###
        if repo == 'osf':
            osf = osf = Osf(api_key=api_key, api_address=osf_api_url)
        if repo == 'figshare':
            figshare = Figshare(api_key=api_key, api_address=figshare_api_url)
        if repo == 'dataverse':
            dataverse = Dataverse(api_key=api_key, api_address=dataverse_api_url)
        if repo == 'zenodo':
            zenodo = Zenodo(api_key=api_key, api_address=zenodo_api_url)
        if repo == 'irods':
            irods = Irods(api_key=api_key, api_address=irods_api_url, user=repo_user)
        if repo == 'sharekit':
            sharekit = Sharekit(api_key=api_key, api_address=sharekit_api_url)

    if not get_canceled(username):
        ### create project ###
        if repo != 'sharekit':
            update_history(username=username, folder=complete_folder_path,
                    url=repo, status=f'creating a project at {repo}')
        if repo == 'osf':
            try:
                result = osf.create_project()
                if type(result) == dict:
                    err = result['error']
                    update_history(username=username, folder=complete_folder_path,
                        url=repo, status=f'failed to create a project at {repo}: {err}')
                    update_history(username=username, folder=complete_folder_path,
                        url=repo, status=f'ready')
                    return
                else:
                    project_id = result.id        
            except Exception as e:
                update_history(username=username, folder=complete_folder_path,
                    url=repo, status=f'failed to create a project at {repo}: {e}')
                update_history(username=username, folder=complete_folder_path,
                    url=repo, status=f'ready')
                return
        if repo == 'figshare':
            try:
                result = figshare.create_new_article_internal(return_response=True)
                project_id = None
                if result.status_code == 201:
                    if 'entity_id' in result.json():
                        project_id = result.json()['entity_id']
                if project_id == None:
                    rtext = result.text
                    update_history(username=username, folder=complete_folder_path,
                        url=repo, status=f'failed to create a project at {repo}: {rtext}')
                    update_history(username=username, folder=complete_folder_path,
                        url=repo, status=f'ready')
                    return
            except:
                update_history(username=username, folder=complete_folder_path,
                    url=repo, status=f'failed to create a project at {repo}')
                update_history(username=username, folder=complete_folder_path,
                    url=repo, status=f'ready')
                return
        if repo == 'dataverse':
            try:
                r = dataverse.create_new_dataset(return_response=True)
                project_id = None
                if r.status_code <= 300:
                    try:
                        project_id = r.json()['data']['persistentId']
                    except:
                        project_id = None
                if project_id == None:
                    rtext = r.text
                    update_history(username=username, folder=complete_folder_path,
                        url=repo, status=f'failed to create a project at {repo}: {rtext}')
                    update_history(username=username, folder=complete_folder_path,
                        url=repo, status=f'ready')
                    return                    
            except:
                update_history(username=username, folder=complete_folder_path,
                    url=repo, status=f'failed to create a project at {repo}')
                update_history(username=username, folder=complete_folder_path,
                    url=repo, status=f'ready')
                return
        if repo == 'zenodo':
            try:
                project_id = None
                r = zenodo.create_new_deposition_internal(metadata=None, return_response=True)
                if r.status_code == 201:
                    if 'id' in r.json():
                        project_id = r.json()['id']
                if project_id == None:
                    try:
                        rtext = r.json()['message']
                        if rtext.find('no Referer') != -1:
                            rtext = 'please reconnect'
                    except:
                        rtext = r.text
                    update_history(username=username, folder=complete_folder_path,
                        url=repo, status=f'failed to create a project at {repo}: {rtext}')
                    update_history(username=username, folder=complete_folder_path,
                        url=repo, status=f'ready')                    
                    return       
            except Exception as e:
                logger.error(f"Failed to create project for Zenodo: {e}")
                update_history(username=username, folder=complete_folder_path,
                    url=repo, status=f'failed to create a project at {repo}')
                update_history(username=username, folder=complete_folder_path,
                    url=repo, status=f'ready')
                return
        if repo == 'irods':
            try:
                project = irods.create_new_collection_internal(metadata=metadata)
                if type(project) == 'dict':
                    if  'message' in project:
                        message = project['message']
                        update_history(username=username, folder=complete_folder_path,
                            url=repo, status=f'failed to create a project at {repo}: {message}')
                        update_history(username=username, folder=complete_folder_path,
                            url=repo, status=f'ready')
                        return
                project_id = project['id']
                project_path = project['path']
            except Exception as e:
                update_history(username=username, folder=complete_folder_path,
                    url=repo, status=f'failed to create a project at {repo}: {e}')
                update_history(username=username, folder=complete_folder_path,
                    url=repo, status=f'ready')
                return

    if not get_canceled(username):
        ### upload files ###
        # if user selected upload as zip to perserve folder structure there will be a zipfile
        sharekit_files = []
        tmpzip = complete_folder_path.split("/")[-1] + ".zip"
        if os.path.isfile(tmpzip):
            update_history(username=username, folder=complete_folder_path, url=repo, status="uploading the zipfile")
            result = False
            if repo == 'sharekit':
                # upload zip to sharekit and store file id in sharekit_files
                try:
                    response = sharekit.upload_file(file_path=tmpzip)
                    if response.status_code < 300:
                        repoItemID = response.json()['data']['id']
                        sharekit_files.append(repoItemID)
                        result = True
                except Exception as e:
                    message = f"failed to upload file {filepath}: {e}"
                    logger.error(message)
                    update_history(username=username, folder=complete_folder_path, url=repo, status=message)
            if repo == 'osf':
                result = osf.upload_new_file_to_project(project_id=project_id, path_to_file=tmpzip)
            if repo == 'figshare':
                result = figshare.upload_new_file_to_article_internal(
                                article_id=project_id, path_to_file=tmpzip)
            if repo == 'dataverse':
                result = dataverse.upload_new_file_to_dataset(
                        persistent_id=project_id, path_to_file=tmpzip)
            if repo == 'zenodo':
                r = zenodo.upload_new_file_to_deposition_internal(
                    deposition_id=project_id, path_to_file=filepath, return_response=True)
                if r.status_code == 201:
                    result = True
                else:
                    result = r.text
            if repo == 'irods':
                result = irods.upload_new_file_to_collection_internal(path=project_path, path_to_file=tmpzip)
            if result == True:
                message = f"uploaded file: {tmpzip}"
                update_history(username=username, folder=complete_folder_path, url=repo, status=message)
            else:
                message = f"failed to upload file {filepath}: {result}"
                update_history(username=username, folder=complete_folder_path, url=repo, status=message)
        # the unzipped folder will be uploaded
        else:
            uploads = "./" + complete_folder_path.split("/")[-1]

            # upload the unzipped folder to the project
            s = ''
            if repo != 'sharekit':
                update_history(username=username, folder=complete_folder_path, url=repo,
                            status=f'uploading the data to {repo}.')

            # calculate the total files count 
            totalfilescount = total_files_count(uploads)
            
            # upload file by file to repo
            n = 1
            for root, dirs, files in os.walk(uploads):
                logger.error((root, dirs, files))
                for j in files:
                    if not get_canceled(username):
                        filepath = os.path.join(root, j)
                        # logger.error(filepath)
                        try:
                            result = False
                            if repo == 'sharekit':
                                # upload zip to sharekit and store file id in sharekit_files
                                try:
                                    response = sharekit.upload_file(file_path=filepath)
                                    if response.status_code < 300:
                                        repoItemID = response.json()['data']['id']
                                        sharekit_files.append(repoItemID)
                                        result = True
                                    else:
                                        statuscode = response.status_code
                                        logger.error(f"failed to upload file. got {statuscode}")
                                        try:
                                            logger.error(r.text)
                                        except:
                                            pass
                                except:
                                    logger.error("failed to upload file")
                            if repo == 'osf':
                                result = osf.upload_new_file_to_project(project_id=project_id, path_to_file=filepath)
                            if repo == 'figshare':
                                result = figshare.upload_new_file_to_article_internal(
                                    article_id=project_id, path_to_file=filepath)
                            if repo == 'dataverse':
                                result = dataverse.upload_new_file_to_dataset(
                                    persistent_id=project_id, path_to_file=filepath)
                            if repo == 'zenodo':
                                r = zenodo.upload_new_file_to_deposition_internal(
                                    deposition_id=project_id, path_to_file=filepath, return_response=True)
                                if r.status_code == 201:
                                    result = True
                                else:
                                    result = r.text
                            if repo == 'irods':
                                result = irods.upload_new_file_to_collection_internal(path=project_path, path_to_file=filepath)

                            if result == True:
                                message = f"uploaded file {n} of {totalfilescount}: {filepath}"
                                update_history(username=username, folder=complete_folder_path, url=repo, status=message)
                            else:
                                message = f"failed to upload file {filepath}: {result}"
                                update_history(username=username, folder=complete_folder_path, url=repo, status=message)
                        except Exception as e:
                            logger.error(f"failed to upload file {filepath} - {e}")
                            message = f"failed to upload file {filepath} - {e}"
                            update_history(username=username, folder=complete_folder_path, url=repo, status=message)
                        n += 1
        update_history(username=username, folder=complete_folder_path,
                    url=repo, status='upload finished')

    if not get_canceled(username):
        if repo == 'sharekit':
            update_history(username=username, folder=complete_folder_path,
                    url=repo, status=f'creating a project at {repo}')
            #  now create a sharekit project AKA repoitem and also add the files by id from sharekit_files list.
            # also add any metadata in the same call.
            r = sharekit.create_item(files=sharekit_files, metadata=metadata)
            if r is None:
                update_history(username=username, folder=complete_folder_path,
                    url=repo, status=f'failed to create a project at {repo}')
    
        ####################################################################
        
        ### change metadata ###
        else:
            update_history(username=username, folder=complete_folder_path,
                            url=repo, status='updating metadata')

        try:
            title = metadata['title']
        except:
            title = 'untitled'
        try:
            author = metadata['author']
        except:
            author = ''
        try:
            affiliation = metadata['affiliation']
        except:
            affiliation = ''
        try:
            publisher = metadata['publisher']
        except:
            publisher = ''
        try:
            license = metadata['license']
        except:
            license = 'cc-by-4.0'
        try:
            publication_date = metadata['publication_date']
        except:
            publication_date = ''
        try:
            description = metadata['description']
        except:
            description = ''
        try:
            tags = metadata['tags']
        except:
            tags = ''
        try:
            categories = metadata['categories']
        except:
            categories = ''
        try:
            contact_email = metadata['contact_email']
        except:
            contact_email = "not@set.com"
        try:
            contact_name = metadata['contact_name']
        except:
            contact_name = "not set"
        try:
            subject = metadata['subject']
        except:
            subject = "Other"

        if repo == 'osf':

            data =     {
                "category":"project",
                "description": description,
                # "dateModified":"2017-03-17T16:11:35.721000",
                "title": title,
                # "dateCreated": str(publication_date),
                # "publicAccess":true,
                "tags": tags.split(",")
            }
            r = osf.update_metadata(project_id, data)
            if not r:
                update_history(username=username, folder=complete_folder_path,
                                url=repo, status='failed to update metadata')                

        if repo == 'figshare':
            data = {
                            'title': title,
                            'description': description,
                            'creators': [{'name': author, 'affiliation': affiliation}]
                        }
            r = figshare.change_metadata_in_article_internal(
                    article_id=project_id, metadata=data, return_response=True)
            if r.status_code != 205:
                code = r.status_code
                text = r.text
                logger.error(f"Failed to update metadata: {code} - {text}")
                update_history(username=username, folder=complete_folder_path,
                                url=repo, status='failed to update metadata')

        if repo == 'dataverse':
            subject = "Other"
            data = {
                    "metadataBlocks": {
                        "citation": {
                            "fields": [
                                {
                                    "value": title,
                                    "typeClass": "primitive",
                                    "multiple": False,
                                    "typeName": "title"
                                },
                                {
                                    "value": [
                                        {
                                            "authorName": {
                                                "value": author,
                                                "typeClass": "primitive",
                                                "multiple": False,
                                                "typeName": "authorName"
                                            },
                                            "authorAffiliation": {
                                                "value": affiliation,
                                                "typeClass": "primitive",
                                                "multiple": False,
                                                "typeName": "authorAffiliation"
                                            }
                                        }
                                    ],
                                    "typeClass": "compound",
                                    "multiple": True,
                                    "typeName": "author"
                                },
                                {
                                    "value": [
                                        {
                                            "datasetContactEmail": {
                                                "typeClass": "primitive",
                                                "multiple": False,
                                                "typeName": "datasetContactEmail",
                                                "value": contact_email
                                            },
                                            "datasetContactName": {
                                                "typeClass": "primitive",
                                                "multiple": False,
                                                "typeName": "datasetContactName",
                                                "value": contact_name
                                            }
                                        }
                                    ],
                                    "typeClass": "compound",
                                    "multiple": True,
                                    "typeName": "datasetContact"
                                },
                                {
                                    "value": [
                                        {
                                            "dsDescriptionValue": {
                                                "value": description,
                                                "multiple": False,
                                                "typeClass": "primitive",
                                                "typeName": "dsDescriptionValue"
                                            }
                                        }
                                    ],
                                    "typeClass": "compound",
                                    "multiple": True,
                                    "typeName": "dsDescription"
                                },
                                {
                                    "value": [
                                        subject
                                    ],
                                    "typeClass": "controlledVocabulary",
                                    "multiple": True,
                                    "typeName": "subject"
                                }
                            ],
                            "displayName": "Citation Metadata"
                        }
                    }
                }

            r = dataverse.change_metadata_in_dataset_internal(
                persistent_id=project_id, metadata=data, return_response=True)
            if r.status_code > 204:
                code = r.status_code
                text = r.text
                logger.error(f"Failed to update metadata: {code} - {text}")
                update_history(username=username, folder=complete_folder_path,
                                url=repo, status='failed to update metadata')

        if repo == 'zenodo':
            data = {
                        "title": title,
                        "publication_date": str(publication_date),
                        "description": description,
                        "access_right": "open",
                        "creators": [
                            {
                                "name": author,
                                "affiliation": affiliation
                            }
                        ],
                        "license": license,
                        "imprint_publisher": publisher,
                    }

            r = zenodo.change_metadata_in_deposition_internal(deposition_id=project_id, metadata=data, return_response=True)
            if r.status_code != 200:
                code = r.status_code
                text = r.text
                logger.error(f"Failed to update metadata: {code} - {text}")
                update_history(username=username, folder=complete_folder_path,
                                url=repo, status='failed to update metadata')
        
        if repo == 'irods':
            Given_Name = author.split()[0]
            Family_Name = author.split(Given_Name)[1]
            data = {'Affiliation': affiliation,
                # 'Collected': 'o11',
                # 'Contributor': 'o8',
                # 'Covered_Period': 'o1',
                # 'Creator': 'o5',
                'Data_Access_Restriction': 'Restricted - available upon '
                'request',
                'Data_Classification': 'Basic',
                'Data_Package_Access': 'Open Access',
                'Data_Type': 'Dataset',
                'Description': description,
                'Family_Name': Family_Name,
                # 'Funding_Reference': 'o12',
                'Given_Name': Given_Name,
                # 'Language': 'en - English',
                # 'License': 'Custom',
                # 'Name': 'o6',
                # 'Persistent_Identifier': 'o4',
                # 'Person_Identifier': 'o7',
                # 'Related_Datapackage': 'o3',
                # 'Retention_Period': '10',
                'Title': title,
                'Href': 'https://yoda.uu.nl/schemas/default-2/metadata.json',
                # 'Links': 'o2',
                'Rel': 'describedby',
                'Version': '1'}
            r = irods.change_metadata_in_collection(project_path, data)
            if r == None:
                update_history(username=username, folder=complete_folder_path,
                                url=repo, status='failed to update metadata')                
        
        if repo == 'irods':
            update_history(username=username, folder=complete_folder_path,
                        url=repo, status='updating metadata for yoda')
            try:
                yodametadata = irods.create_yoda_metadata(path=project_path, metadata=metadata)
                # write this data to yoda-metadata.json file
                json_file_path = "./" + complete_folder_path.split("/")[-1] + "/yoda-metadata.json"
                with open(json_file_path, 'w') as ff:
                    ff.write(yodametadata)
                # upload the yoda-metadata.json file
                irods.upload_new_file_to_collection_internal(path=project_path, path_to_file=json_file_path)
            except:
                update_history(username=username, folder=complete_folder_path,
                        url=repo, status='failed to update metadata for yoda')

    ###############################################################

    ### delete temp files ###
    update_history(username=username, folder=complete_folder_path,
                    url=repo, status='removing temporary files')
    shutil.rmtree(unzipped_folder)
    # if user selected upload as zip to perserve folder structure
    if use_zip:
        os.remove(tmpzip)

    ### ready ###
    update_history(username=username,
                    folder=complete_folder_path, url=repo, status='ready')
