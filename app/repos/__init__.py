from app.repos.osf import Osf
from app.repos.figshare import Figshare
from app.repos.zenodo import Zenodo
from app.repos.dataverse import Dataverse
from app.repos.irods import Irods
from app.repos.surfs3 import Surfs3
from app.repos.sharekit import Sharekit
from app.utils import update_history, create_generated_folder, total_files_count, get_canceled, cloud, make_connection, get_folder_content_props
from app.utils import create_rocrate, check_checksums, push_data, get_query_status, get_status_from_history, set_project_id
import logging
import owncloud
import nextcloud_client
import zipfile
import shutil
import os
import json
from urllib.parse import urlparse
from urllib.parse import parse_qs
import requests

try:
    from app.globalvars import *
except:
    # for testing this file locally
    from globalvars import *
    print("testing")


logger = logging.getLogger()


def get_sharekit_token():
    # will get temp token / api_key based on client id en secret
    url = f"{sharekit_api_url}/upload/v1/auth/token"
    payload = f'client_id={sharekit_client_id}&client_secret={sharekit_client_secret}&grant_type=client_credentials&institute={sharekit_institute}'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.status_code < 300:
        return response.json()['access_token']


def get_repocontent(repo, url, api_key, user=None):
    repo_content = [{'message' : f'failed to get repo content from {repo}'}]
    if repo == 'figshare':
        figshare = Figshare(api_key=api_key, api_address=figshare_api_url)
        try:
            article_id = int(url.split('/')[-1])
        except:
            article_id = int(url.split('/')[-2])
        repo_content = figshare.get_repo_content(article_id=article_id)
    if repo == 'data4tu':
        data4tu = Figshare(api_key=api_key, api_address=data4tu_api_url)
        try:
            article_id = url.split('/')[-1]
        except:
            article_id = url.split('/')[-2]
        repo_content = data4tu.get_repo_content(article_id=article_id)
    if repo == 'zenodo':
        zenodo = Zenodo(api_key=api_key, api_address=zenodo_api_url)
        try:
            deposition_id = int(url.split('/')[-1])
        except:
            deposition_id = int(url.split('/')[-2])
        repo_content = zenodo.get_repo_content(deposition_id=deposition_id)
    if repo == 'osf':
        osf = Osf(api_key=api_key, api_address=osf_api_url)
        split_url = url.split('/')
        if split_url[-1] != '':
            project_id = str(split_url[-1])
        else:
            project_id = str(split_url[-2])
        repo_content = osf.get_repo_content(project_id=project_id)
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
    if repo == 'datastation':
        try:
            datastation = Dataverse(api_key=api_key, api_address=datastation_api_url, datastation=True)
            if url.find('doi.org') == -1:
                persistent_id = url.split('?')[-1]
                persistent_id = persistent_id.split('&')[0]
                persistent_id = persistent_id.split('=')[-1]
            else:
                persistent_id = url.split('doi.org/')[-1]
                persistent_id = 'doi:' + persistent_id
            repo_content = datastation.get_repo_content(persistent_id=persistent_id)
        except:
            repo_content = []
    if repo == 'irods':
        # irods = Irods(api_key=api_key, user=user, api_address=irods_api_url)
        irods = Irods(api_key=api_key, api_address=irods_api_url, user=user)
        parsed = urlparse(url)
        path = parse_qs(parsed.query)['dir'][0]
        repo_content = irods.get_repo_content(path=path)
    if repo == 'sharekit':
        sharekit = Sharekit(api_key=api_key, api_address=sharekit_api_url)
        try:
            article_id = int(url.split('/')[-1])
        except:
            article_id = int(url.split('/')[-2])
        repo_content = sharekit.get_repo_content(article_id=article_id)
    if repo == 'surfs3':
        surfs3 = Surfs3(api_key=api_key, user=user, api_address=surfs3_api_url)
        repo_content = surfs3.get_bucket_content(bucket_name=url)
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
    if repo == 'data4tu':
        data4tu = Figshare(api_key=api_key, api_address=data4tu_api_url)
        try:
            article_id = url.split('/')[-1]
        except:
            article_id = url.split('/')[-2]
        private_metadata = data4tu.get_private_metadata(article_id=article_id)
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
    if repo == 'datastation':
        datastation = Dataverse(api_key=api_key, api_address=datastation_api_url, datastation=True)
        if url.find('doi.org') == -1:
            persistent_id = url.split('?')[-1]
            persistent_id = persistent_id.split('&')[0]
            persistent_id = persistent_id.split('=')[-1]
        else:
            persistent_id = url.split('doi.org/')[-1]
            persistent_id = 'doi:' + persistent_id
        private_metadata = datastation.get_private_metadata(persistent_id=persistent_id)
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
    if repo == 'data4tu':
        data4tu = Figshare(api_key=api_key, api_address=data4tu_api_url)
        try:
            article_id = url.split('/')[-1]
        except:
            article_id = url.split('/')[-2]
        private_files = data4tu.download_files(article_id=article_id, dest_folder=folder)
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
    if repo == 'datastation':
        datastation = Dataverse(api_key=api_key, api_address=datastation_api_url, datastation=True)
        if url.find('doi.org') == -1:
            persistent_id = url.split('?')[-1]
            persistent_id = persistent_id.split('&')[0]
            persistent_id = persistent_id.split('=')[-1]
        else:
            persistent_id = url.split('doi.org/')[-1]
            persistent_id = 'doi:' + persistent_id
        private_files = datastation.download_files(persistent_id=persistent_id, dest_folder=folder)
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
    if repo == 'surfs3':
        surfs3 = Surfs3(api_key=api_key, user=user, api_address=surfs3_api_url)
        private_files = surfs3.download_files(bucket_name=url, dest_folder=folder)
    return private_files


def run_private_import(username, password, folder, url, repo, api_key, user=None):
    """Execute steps for private imports and updates the history for every step.

    Args:
        username (str): username of the owncloud account
        password (str): password of the owncloud account
        folder (str): folder path of the data
        url (str): url of the location of the data
        repo (str): name of the repo
        api_key (str): access_token or api_key needed to connect to the repo
        user(str | optional): user naem for connectionto the repo
    """
    folderpath = folder
    if repo == "surfs3":
        folderpath = f"./RESTORE/{folder}/"

    update_history(username, folder, url, 'started')
    if not get_canceled(username):
        update_history(username, folder, url, 'getting file data')
        result = get_private_files(repo, url, folderpath, api_key=api_key, user=user)
        if result == True:
            update_history(username, folder, url, f'getting file data done {result}')
        else:
            update_history(username, folder, url, f'getting file data failed: {result}')

    if not get_canceled(username):
        update_history(username, folder, url, 'start checking checksums')
        files_info = get_repocontent(repo, url, api_key, user=user)
        check_checksums(username, url, folderpath, files_info=files_info)
        update_history(username, folder, url, 'created checksums')

    if not get_canceled(username) and repo != 'surfs3':
        update_history(username, folder, url,
                    'creating ro-crate-metadata.json file ')
        try:
            create_rocrate(url, folder)
            update_history(username, folder, url,
                    'created ro-crate-metadata.json file')
        except Exception as e:
            update_history(username, folder, url,
                    f'failed to create ro-crate-metadata.json file: {e}')

    if not get_canceled(username):
        update_history(username, folder, url, 'start pushing dataset to storage')
        push_data(username, password, folder, url, repo=repo)
        
    update_history(username, folder, url, 'ready')



def check_connection(repo, api_key=None, user=None):
    logger.error("check connection")
    connection_ok = False
    if repo == 'osf':
        osf = Osf(api_key=api_key, api_address=osf_api_url)
        connection_ok = osf.check_token()
    if repo == "figshare":
        figshare = Figshare(api_key=api_key, api_address=figshare_api_url)
        connection_ok = figshare.check_token()
    if repo == "data4tu":
        data4tu = Figshare(api_key=api_key, api_address=data4tu_api_url)
        connection_ok = data4tu.check_token()
    if repo == "zenodo":
        zenodo = Zenodo(api_key=api_key, api_address=zenodo_api_url)
        connection_ok = zenodo.check_token()
    if repo == "dataverse":
        dataverse = Dataverse(api_key=api_key, api_address=dataverse_api_url)
        connection_ok = dataverse.check_token()
    if repo == "datastation":
        datastation = Dataverse(api_key=api_key, api_address=datastation_api_url, datastation=True)
        connection_ok = datastation.check_token()   
    if repo == "irods":
        irods = Irods(api_key=api_key, api_address=irods_api_url, user=user)
        connection_ok = irods.check_token()
    if repo == "surfs3":
        surfs3 = Surfs3(api_key=api_key, api_address=surfs3_api_url, user=user)
        connection_ok = surfs3.check_token()
    if repo == "sharekit":
        sharekit = Sharekit(api_key=api_key, api_address=sharekit_api_url)
        connection_ok = sharekit.check_token()
    if repo == 'datahugger':
        connection_ok = True
    return connection_ok


def run_export(username, password, complete_folder_path, repo, repo_user, api_key, metadata, use_zip=False, generate_metadata=False, dataverse_alias=None, files_folders_selection=None):

    ### NOTE ###
    # let's first implement an on disk solution, as we have seen that the buffered solution is not working with ScieboRDS
    # This is probably gonna be slower, but less error prone.
    # Let's first build something that works reliably and only then optimize for speed and prettyness
    # This will also allow reuse of code written for the retrieval of repos

    # setting a tmp folder path name that does not interfere with other projects or the SRDC code itself.
    tmp_folder_path_name = complete_folder_path.split("/")[-1]
    
    if tmp_folder_path_name in ['', 'app', 'local', 'instance', 'migrations', 'surf-rdc-chart', 'tests', 'ansible', 'tempstorage']:
        try:
            if repo == "surfs3":
                tmp_folder_path_name = "ARCHIVE"
            elif tmp_folder_path_name == "" and 'title' in metadata:
                tmp_folder_path_name = metadata['title'].replace(" ", "_")
            elif 'title' in metadata:
                tmp_folder_path_name = tmp_folder_path_name + "_" + metadata['title'].replace(" ", "_")
            else:
                tmp_folder_path_name = f"SRDC_{tmp_folder_path_name}"
        except:
            tmp_folder_path_name = f"SRDC_{tmp_folder_path_name}"


    # set the base storage path. This path will also show up in the path of the files at most repos
    # so it is best to set it to root or to something descriptive like ./SRDC.
    base_storage = "./"
    if not os.path.exists(base_storage):
        os.mkdir(base_storage)

    # set the unzipped_folder to a specific base storage folder
    # also note that the tmp_folder_path_name moust be set to a name that does not conflict with names of folders that are part of the app
    unzipped_folder = base_storage + tmp_folder_path_name


    update_history(username=username, folder=complete_folder_path,
                   url=repo, status='started')

    # connect to OC
    try:
        make_connection(username, password)
    except Exception as e:
        message = f"failed to connect to RD: {e}"
        logger.error(message)
        update_history(username=username,
                       folder=complete_folder_path, url=repo, status=message)
        update_history(username=username, folder=complete_folder_path,
            url=repo, status=f'ready')
        return


    if not get_canceled(username):
        # Download the data from OC
        update_history(username=username, folder=complete_folder_path,
                    url=repo, status='start downloading project as zipfile')
        
        tmpzip = unzipped_folder + ".zip"
        try:
            if  cloud_service.lower() == 'nextcloud':
                cloud.get_directory_as_zip(user_name=username,
                    remote_path=complete_folder_path, local_file=tmpzip)
            else:
                cloud.get_directory_as_zip(
                    remote_path=complete_folder_path, local_file=tmpzip)

            update_history(username=username, folder=complete_folder_path,
                        url=repo, status='done downloading project as zipfile')
        except Exception as e:
            update_history(username=username, folder=complete_folder_path,
                        url=repo, status=f'failed downloading project as zipfile: {e}')
            update_history(username=username, folder=complete_folder_path,
                url=repo, status=f'ready')
            return
    if not get_canceled(username):
        # unzip the file to a temp folder and then move the content to a folder with name of last part of complete folder path.

        update_history(username=username, folder=complete_folder_path,
                    url=repo, status='unzipping the zipfile')
               
        tmp_loc = "./app/tempstorage"
        try:
            os.mkdir(tmp_loc)
        except Exception as e:
            mkdirmes = f"temporary storage location cannot be created or already exists: {e}"
            logger.info(mkdirmes)
            # update_history(username=username, folder=complete_folder_path,
            #             url=repo, status=mkdirmes)
        # we extract the zipfile to a temporary location
        # ./tempstorages/zipfilemainfolder
        try:
            with zipfile.ZipFile(tmpzip, 'r') as zip_ref:
                zip_ref.extractall(tmp_loc)
        except Exception as e:
            update_history(username=username, folder=complete_folder_path,
                        url=repo, status=f'failed extracting the zipfile: {e}')

        

        # now we set ./tempstorages/zipfilemainfolder as source for moving
        try:
            # if the complete_folder_path == "/" then the extrated file sturcture contains ./files/ ....
            if complete_folder_path == "/":
                src = tmp_loc + "/" + complete_folder_path.split("/")[-1] + "files"
            else:
                src = tmp_loc + "/" + complete_folder_path.split("/")[-1]
            # the destination will be the unzipped folder
            dest = unzipped_folder
            # let's move it
            logger.error(f"############### Moving from {src} to {dest}")
            shutil.move(src, dest)
        except Exception as e:
            update_history(username=username, folder=complete_folder_path,
                        url=repo, status=f'failed moving the zipfile content to process location: {e}')

    if files_folders_selection:
        for root, dirs, files in os.walk(unzipped_folder):
            for j in files:
                filepath = os.path.join(root, j)
                if complete_folder_path == "/":
                    filepath_for_comparison = (complete_folder_path + filepath.split(unzipped_folder)[-1].replace(unzipped_folder,"")).replace("//","/")
                else:
                    filepath_for_comparison = complete_folder_path + filepath.split(unzipped_folder)[-1]
                logger.error(f"filepath_for_comparison: {filepath_for_comparison}")
                if filepath_for_comparison not in files_folders_selection:
                    os.remove(filepath)
                    


    if not get_canceled(username):
        # remove the zip
        update_history(username=username, folder=complete_folder_path,
                    url=repo, status='removing the zipfile')
        os.remove(tmpzip)


    if not get_canceled(username) and repo == 'surfs3':
    #     # generate a filelisitng file with all props
        try:
            update_history(username=username, folder=complete_folder_path,
                            url=repo, status="creating filelisting file in 'generated' folder")
            result = get_folder_content_props(username=username, password=password, folder=complete_folder_path)
            create_generated_folder(unzipped_folder)
            with open(f'{unzipped_folder}/generated/filelisting.json', 'w') as filelisting:
                filelisting.write(json.dumps(result))
        except Exception as e:
            update_history(username=username, folder=complete_folder_path,
                            url=repo, status=f"failed at creating filelisting file in 'generated' folder: {e}")


    if not get_canceled(username) and generate_metadata:
        # write metadata in ro-crate file in 'generated' folder inside the unzipped folder
        update_history(username=username, folder=complete_folder_path,
                    url=repo, status="creating ro-crate file in 'generated' folder")
        try:
            create_rocrate(url=repo, folder=unzipped_folder, metadata=metadata)
            update_history(username=username, folder=complete_folder_path,
                    url=repo, status="created ro-crate file in 'generated' folder")
        except Exception as e:
            update_history(username=username, folder=complete_folder_path,
                    url=repo, status=f"failed at creating ro-crate file in 'generated' folder: {e}")

    # if not get_canceled(username):
    #     # write the metadata in generated folder back to OC
    #     # upload the local generate folder into the coomplete folder path at OC
    #     # TODO : Fix this, nice to have
    #     update_history(username=username, folder=complete_folder_path,
    #                 url=repo, status="backing up ro-crate file to RD")
    #     try:
    #         cloud.put_directory(target_path=complete_folder_path, local_directory=f'{unzipped_folder}/generated')
    #     except:
    #         update_history(username=username, folder=complete_folder_path,
    #                 url=repo, status="failed at backing up ro-crate file to RD")

    if not get_canceled(username):
        # if user selected upload as zip to perserve folder structure
        if use_zip:
            # zip the unzipped_folder to tmpzip
            update_history(username=username, folder=complete_folder_path,
                    url=repo, status=f"creating zipfile {tmpzip} for upload")
            shutil.make_archive(tmp_folder_path_name, 'zip', unzipped_folder)

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
        if repo == 'data4tu':
            data4tu = Figshare(api_key=api_key, api_address=data4tu_api_url)
        if repo == 'dataverse':
            dataverse = Dataverse(api_key=api_key, api_address=dataverse_api_url, dataverse_alias=dataverse_alias)
        if repo == 'datastation':
            datastation = Dataverse(api_key=api_key, api_address=datastation_api_url, dataverse_alias=dataverse_alias, datastation=True)
        if repo == 'zenodo':
            zenodo = Zenodo(api_key=api_key, api_address=zenodo_api_url)
        if repo == 'irods':
            irods = Irods(api_key=api_key, api_address=irods_api_url, user=repo_user)
        if repo == 'surfs3':
            surfs3 = Surfs3(api_key=api_key, api_address=surfs3_api_url, user=repo_user)
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
        if repo == 'figshare' or repo == 'data4tu':
            try:
                if repo == 'data4tu':
                    result = data4tu.create_new_article_internal(return_response=True)
                else:
                    result = figshare.create_new_article_internal(return_response=True)
                project_id = None
                if result.status_code == 201:
                    if 'entity_id' in result.json():
                        project_id = result.json()['entity_id']
                if result.status_code == 200:
                    if 'location' in result.json():
                        project_id = result.json()['location'].split("/")[-1]
                if project_id == None:
                    rtext = result.text
                    update_history(username=username, folder=complete_folder_path,
                        url=repo, status=f'failed to create a project at {repo}: {rtext}')
                    update_history(username=username, folder=complete_folder_path,
                        url=repo, status=f'ready')
                    return
            except Exception as e:
                update_history(username=username, folder=complete_folder_path,
                    url=repo, status=f'failed to create a project at {repo}: {e}')
                update_history(username=username, folder=complete_folder_path,
                    url=repo, status=f'ready')
                return
        if repo == 'dataverse' or repo == 'datastation':
            try:
                if repo == 'dataverse':
                    r = dataverse.create_new_dataset(return_response=True)
                else:
                    r = datastation.create_new_dataset(return_response=True)
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
            except Exception as e:
                update_history(username=username, folder=complete_folder_path,
                    url=repo, status=f'failed to create a project at {repo}: {e}')
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
                    except Exception as e:
                        rtext = r.text
                    update_history(username=username, folder=complete_folder_path,
                        url=repo, status=f'failed to create a project at {repo}: {rtext}')
                    update_history(username=username, folder=complete_folder_path,
                        url=repo, status=f'ready')                    
                    return       
            except Exception as e:
                logger.error(f"Failed to create project for Zenodo: {e}")
                update_history(username=username, folder=complete_folder_path,
                    url=repo, status=f'failed to create a project at {repo}: {e}')
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
        if repo == 'surfs3':
            try:
                project = surfs3.create_new_bucket(metadata=metadata)
                if type(project) == 'dict':
                    if  'message' in project:
                        message = project['message']
                        update_history(username=username, folder=complete_folder_path,
                            url=repo, status=f'failed to create a project at {repo}: {message}')
                        update_history(username=username, folder=complete_folder_path,
                            url=repo, status=f'ready')
                        return
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
        tmpzip = tmp_folder_path_name + ".zip"
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
                    message = f"failed to upload file 1 of 1: {tmpzip}: {e}"
                    logger.error(message)
                    update_history(username=username, folder=complete_folder_path, url=repo, status=message)
            if repo == 'osf':
                result = osf.upload_new_file_to_project(project_id=project_id, path_to_file=tmpzip)
            if repo == 'figshare':
                result = figshare.upload_new_file_to_article_internal(
                                article_id=project_id, path_to_file=tmpzip)
            if repo == 'data4tu':
                url = f'https://data.4tu.nl/v3/datasets/{project_id}/upload'
                headers = {'Authorization': f"token {data4tu.api_key}"}
                logger.error(headers)
                payload = {}
                file_name = tmpzip.split('/')[-1]
                files = [
                            ('file',(file_name, open(tmpzip,'rb')))
                        ]
                response = requests.request('POST', url, headers=headers, data=payload, files=files)
                if response.status_code == 200:
                    result = True
            if repo == 'dataverse':
                result = dataverse.upload_new_file_to_dataset(
                        persistent_id=project_id, path_to_file=tmpzip)
            if repo == 'datastation':
                result = datastation.upload_new_file_to_dataset(
                        persistent_id=project_id, path_to_file=tmpzip)
            if repo == 'zenodo':
                r = zenodo.upload_new_file_to_deposition_internal(
                    deposition_id=project_id, path_to_file=tmpzip, return_response=True)
                if r.status_code == 201:
                    result = True
                else:
                    result = r.text
            if repo == 'irods':
                result = irods.upload_new_file_to_collection_internal(path=project_path, path_to_file=tmpzip)
            if repo == 'surfs3':
                result = surfs3.upload_new_file_to_bucket(bucket_name=metadata['s3archivename'], path_to_file=tmpzip)
            if result == True:
                message = f"uploaded file: {tmpzip}"
                update_history(username=username, folder=complete_folder_path, url=repo, status=message)
            else:
                message = f"failed to upload file 1 of 1: {tmpzip}: {result}"
                update_history(username=username, folder=complete_folder_path, url=repo, status=message)
        # the unzipped folder will be uploaded
        else:
            # upload the unzipped folder to the project
            s = ''
            if repo != 'sharekit':
                update_history(username=username, folder=complete_folder_path, url=repo,
                            status=f'uploading the data to {repo}.')

            # calculate the total files count 
            totalfilescount = total_files_count(unzipped_folder)
            
            # upload file by file to repo
            n = 1
            for root, dirs, files in os.walk(unzipped_folder):
                for j in files:
                    if not get_canceled(username):
                        filepath = os.path.join(root, j)
                        try:
                            result = False
                            if repo == 'sharekit':
                                # upload zip to sharekit and store file id in sharekit_files
                                try:
                                    response = sharekit.upload_file(file_path=filepath)
                                    if response.status_code < 300:
                                        logger.error("##################")
                                        logger.error(response.json())
                                        fileId = response.json()['id']
                                        sharekit_files.append({'fileId' : fileId,  'fileName' : j})
                                        result = True
                                    else:
                                        statuscode = response.status_code
                                        logger.error(f"failed to upload file. got {statuscode}")
                                        logger.error(response.text)
                                        try:
                                            logger.error(response.text)
                                        except:
                                            pass
                                except Exception as e:
                                    logger.error(f"failed to upload file: {e}")
                            if repo == 'osf':
                                result = osf.upload_new_file_to_project(project_id=project_id, path_to_file=filepath)
                            if repo == 'figshare':
                                result = figshare.upload_new_file_to_article_internal(
                                    article_id=project_id, path_to_file=filepath)
                            if repo == 'data4tu':
                                url = f'https://data.4tu.nl/v3/datasets/{project_id}/upload'
                                headers = {'Authorization': f"token {data4tu.api_key}"}
                                logger.error(headers)
                                payload = {}
                                file_name = filepath.split('/')[-1]
                                files = [
                                            ('file',(file_name, open(filepath,'rb')))
                                        ]
                                response = requests.request('POST', url, headers=headers, data=payload, files=files)
                                if response.status_code == 200:
                                    result = True
                            if repo == 'dataverse':
                                result = dataverse.upload_new_file_to_dataset(
                                    persistent_id=project_id, path_to_file=filepath)
                            if repo == 'datastation':
                                result = datastation.upload_new_file_to_dataset(
                                    persistent_id=project_id, path_to_file=filepath)
                                logger.error(result)
                            if repo == 'zenodo':
                                r = zenodo.upload_new_file_to_deposition_internal(
                                    deposition_id=project_id, path_to_file=filepath, return_response=True)
                                if r.status_code == 201:
                                    result = True
                                else:
                                    result = r.text
                            if repo == 'irods':
                                result = irods.upload_new_file_to_collection_internal(path=project_path, path_to_file=filepath)
                            if repo == 'surfs3':
                                result = surfs3.upload_new_file_to_bucket(bucket_name=metadata['s3archivename'], path_to_file=filepath)
                                filepath = filepath.split("./ARCHIVE/files/")[-1]
                                filepath = filepath.split("./ARCHIVE/")[-1]
                            if result == True:
                                message = f"uploaded file {n} of {totalfilescount}: {filepath}"
                                update_history(username=username, folder=complete_folder_path, url=repo, status=message)
                            else:
                                message = f"failed to upload file {n} of {totalfilescount} - {filepath}: {result}"
                                update_history(username=username, folder=complete_folder_path, url=repo, status=message)
                        except Exception as e:
                            message = f"failed to upload file {n} of {totalfilescount} - {filepath} - {e}"
                            logger.error(message)
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
        try:
            dans_audience_uri = metadata['dans_audience_uri']
        except:
            dans_audience_uri = "https://www.narcis.nl/classification/E14000"
        try:
            dansRights_personal = metadata['dansRights_personal']
        except:
            dansRights_personal = "Unknown"
        try:
            dansRights_language = metadata['dansRights_language']
        except:
            dansRights_language = "Not applicable"
        try:
            dansRights_holder = metadata['dansRights_holder']
        except:
            dansRights_holder = "Not set"

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

        if repo == 'figshare' or repo == 'data4tu':
            data = {
                            'title': title,
                            'description': description,
                            'creators': [{'name': author, 'affiliation': affiliation}]
                        }
            if repo == 'data4tu':
                r = data4tu.change_metadata_in_article_internal(
                            article_id=project_id, metadata=data, return_response=True)
            else:
                r = figshare.change_metadata_in_article_internal(
                            article_id=project_id, metadata=data, return_response=True)

            if r.status_code != 205:
                code = r.status_code
                text = r.text
                message = f"Failed to update metadata: {code} - {text}"
                logger.error(message)
                update_history(username=username, folder=complete_folder_path,
                                url=repo, status=message)

        if repo == 'dataverse' or repo == 'datastation':
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
            if repo == 'datastation':
                data['metadataBlocks']['dansRights'] = {
                        "displayName": "Rights Metadata",
                        "name": "dansRights",
                        "fields": [
                            {
                                "typeName": "dansRightsHolder",
                                "multiple": True,
                                "typeClass": "primitive",
                                "value": [
                                    dansRights_holder
                                ]
                            },
                            {
                                "typeName": "dansPersonalDataPresent",
                                "multiple": False,
                                "typeClass": "controlledVocabulary",
                                "value": dansRights_personal
                            },
                            {
                                "typeName": "dansMetadataLanguage",
                                "multiple": True,
                                "typeClass": "controlledVocabulary",
                                "value": [
                                    dansRights_language
                                ]
                            }
                        ]
                    }
                data['metadataBlocks']['dansRelationMetadata'] = {
                        "displayName": "Relation Metadata",
                        "name": "dansRelationMetadata",
                        "fields": [
                            {
                                "typeName": "dansAudience",
                                "multiple": True,
                                "typeClass": "primitive",
                                "value": [dans_audience_uri]
                            }
                        ]
                    }

            if repo == 'dataverse':
                r = dataverse.change_metadata_in_dataset_internal(
                    persistent_id=project_id, metadata=data, return_response=True)
            else:
                r = datastation.change_metadata_in_dataset_internal(
                    persistent_id=project_id, metadata=data, return_response=True)
            if r.status_code > 204:
                code = r.status_code
                text = r.text
                message = f"Failed to update metadata: {code} - {text}"
                logger.error(message)
                update_history(username=username, folder=complete_folder_path,
                                url=repo, status=message)

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
                message = f"Failed to update metadata: {code} - {text}"
                logger.error(message)
                update_history(username=username, folder=complete_folder_path,
                                url=repo, status=message)
        
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
            if type(r) == 'str':
                update_history(username=username, folder=complete_folder_path,
                                url=repo, status=f'failed to update metadata: {r}')                
        
        if repo == 'irods':
            update_history(username=username, folder=complete_folder_path,
                        url=repo, status='updating metadata for yoda')
            try:
                yodametadata = irods.create_yoda_metadata(path=project_path, metadata=metadata)
                # write this data to yoda-metadata.json file
                json_file_path = unzipped_folder + "/yoda-metadata.json"
                with open(json_file_path, 'w') as ff:
                    ff.write(yodametadata)
                # upload the yoda-metadata.json file
                irods.upload_new_file_to_collection_internal(path=project_path, path_to_file=json_file_path)
            except Exception as e:
                update_history(username=username, folder=complete_folder_path,
                        url=repo, status=f'failed to update metadata for yoda: {e}')

    ###############################################################

    ### delete temp files ###
    update_history(username=username, folder=complete_folder_path,
                    url=repo, status='removing temporary files')
    
    if os.path.exists(unzipped_folder):
        shutil.rmtree(unzipped_folder)

    # if user selected upload as zip to perserve folder structure
    if use_zip:
        os.remove(tmpzip)

    ### ready ###
    update_history(username=username,
                    folder=complete_folder_path, url=repo, status='ready')
