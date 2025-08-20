import random
import logging
from threading import Thread
from fastapi import Response, status
from sqlalchemy import and_
from pydantic import BaseModel

from app.models import fast_app, app, History
from app.repos import run_export, run_private_import
from app.utils import set_projectname, get_cached_folders, get_folders, get_query_status_history, make_connection
from app.utils import folder_content_can_be_processed, repo_content_fits, update_history
from app.repos import check_connection, get_repocontent
from app.globalvars import *

logger = logging.getLogger()

### defining the post request bodies using pydantic ###

class Data(BaseModel):
    cloud_username: str
    cloud_password: str


class folderData(Data):
    folder: str | None = None
    cached: bool | None = False


class statusData(Data):
    remote: str
    complete_folder_path: str
    

class exportData(Data):
    project_name: str | None = None
    complete_folder_path: str
    metadata: dict | None = None
    # metadata.title: str
    repo: str
    repo_user: str | None = None
    repo_api_key: str | None = None
    use_zip: bool | None = False
    generate_metadata: bool | None = False
    dataverse_alias: str | None = None


class importData(Data):
    project_name: str | None = None
    complete_folder_path: str
    metadata: dict | None = None
    url: str
    repo: str
    repo_user: str | None = None
    repo_api_key: str | None = None


class historyData(Data):
    id: int | None = None

### end of post bodies ###


@fast_app.get("/version", status_code=200)
def fast_app_version(response: Response):
    return {"version": "1"}


@fast_app.post("/folders", status_code=200)
def fast_app_folders(data: folderData, response: Response):
    r_status = "OK"
    try:
        if make_connection(username=data.cloud_username, password=data.cloud_password):
            folder = "/"
            if data.folder:
                folder = data.folder
            if data.cached:
                result = get_cached_folders(data.cloud_username, cloud_password, folder)
            else:
                result = get_folders(username=data.cloud_username, password=data.cloud_password, folder=folder)
        else:
            r_status = "UNAUTHORIZED"
            result = None
            response.status_code = status.HTTP_401_UNAUTHORIZED
    except Exception as e:
        logger.error(e)
        r_status = "BAD_REQUEST"
        result = None
        response.status_code = status.HTTP_400_BAD_REQUEST
    return {"status": r_status,
            "data": data,
            "result": result}


@fast_app.post("/export", status_code=200)
def fast_app_export(data: exportData, response: Response):
    logger.info("export called")
    r_status = "OK"
    try:
        if make_connection(username=data.cloud_username, password=data.cloud_password):
            username = data.cloud_username
            password = data.cloud_password
            complete_folder_path = data.complete_folder_path
            metadata = data.metadata

            repo = data.repo
            
            repo_user = data.repo_user
            api_key = data.repo_api_key


            if data.project_name == None or data.project_name == "":
                num = int(random.random() * 100)
                project_name = f"api_{username}_{complete_folder_path}_{repo}_{num}"
            else:
                project_name = data.project_name

            set_projectname(username=username,folder=complete_folder_path,url=repo,projectname=project_name)


            if repo == 'surfs3' and (repo_user == None or repo_user == "") and (api_key == None or api_key == ""):
                try:
                    repo_user = surfs3_client_id
                    api_key = surfs3_client_secret
                except:
                    msg = "Surfs3 client_id and secrets are not configured."
                    logger.error(msg)
                    update_history(username=username, folder=complete_folder_path, url=repo, status=msg)
                    repo_user = None
                    api_key = None
            

            if api_key and check_connection(repo=repo, api_key=api_key, user=repo_user):
                use_zip = False
                generate_metadata = False
                dataverse_alias = None

                # validate metadata based on the set repo
                
                # check if the SRDC pod has enough space to run the export
                content_can_be_processed = folder_content_can_be_processed(username, password, complete_folder_path)
                msg = f"Content can be processed: {content_can_be_processed}"
                # update_history(username=username, folder=complete_folder_path, url=repo, status=msg)
                logger.info(msg)

                if content_can_be_processed['can_be_processed']==True:
                    # async call run_export
                    t = Thread(target=run_export, args=(
                        username, password, complete_folder_path, repo, repo_user, api_key, metadata, use_zip, generate_metadata, dataverse_alias))
                    t.start()
                    result = "Export started"
                else:
                    r_status = "REQUEST_ENTITY_TOO_LARGE"
                    total_size = content_can_be_processed['total_size']
                    free_bytes = content_can_be_processed['free_bytes']
                    result = f"The dataset is too large to be processed. To be processed: {total_size} bytes. Available for processing: {free_bytes} bytes"
                    update_history(username=username, folder=complete_folder_path, url=repo, status=result)
                    response.status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            else:
                r_status = "UNAUTHORIZED"
                result = f"Cannot connect to {repo}"
                update_history(username=username, folder=complete_folder_path, url=repo, status=result)
                response.status_code = status.HTTP_401_UNAUTHORIZED
        else:
            r_status = "UNAUTHORIZED"
            result = None
            response.status_code = status.HTTP_401_UNAUTHORIZED
    except Exception as e:
        logger.error(e)
        r_status = "BAD_REQUEST"
        result = e
        update_history(username=username, folder=complete_folder_path, url=repo, status=result)
    return {"status": r_status,
            "data": data,
            "result": result}


@fast_app.post("/status", status_code=200)
def fast_app_status(data: statusData, response: Response):
    r_status = "OK"
    try:
        if make_connection(username=data.cloud_username, password=data.cloud_password):
            result = get_query_status_history(username=data.cloud_username, folder=data.complete_folder_path, url=data.remote)
        else:
            r_status = "UNAUTHORIZED"
            result = None
            response.status_code = status.HTTP_401_UNAUTHORIZED
    except Exception as e:
        message = f"An exception occured: {e}"
        logger.error(message)
        r_status = "BAD_REQUEST"
        result = None
        response.status_code = status.HTTP_400_BAD_REQUEST
    return {"status": r_status,
            "data": data,
            "result": result}


@fast_app.post("/import", status_code=200)
def fast_app_import(data: importData, response: Response):
    logger.info("import called")
    r_status = "OK"
    try:
        if make_connection(username=data.cloud_username, password=data.cloud_password):
            username = data.cloud_username
            password = data.cloud_password
            complete_folder_path = data.complete_folder_path
            url = data.url
            repo = data.repo

            if data.project_name == None or data.project_name == "":
                num = int(random.random() * 100)
                project_name = f"api_{username}_{complete_folder_path}_{repo}_{num}"
            else:
                project_name = data.project_name
            set_projectname(username=username,folder=complete_folder_path,url=url,projectname=project_name)

            try:
                metadata = data.metadata
            except:
                metadata = {}
            
            try:
                repo_user = data.repo_user
            except:
                repo_user = surfs3_client_id
            
            try:
                api_key = data.repo_api_key
            except:
                api_key = surfs3_client_secret

            if repo == 'surfs3' and (repo_user == None or repo_user == "") and (api_key == None or api_key == ""):
                try:
                    repo_user = surfs3_client_id
                    api_key = surfs3_client_secret
                except:
                    msg = "Surfs3 client_id and secrets are not configured."
                    logger.error(msg)
                    update_history(username=username, folder=complete_folder_path, url=url, status=msg)
                    repo_user = None
                    api_key = None
            
            if api_key and check_connection(repo=repo, api_key=api_key, user=repo_user):

                # validate metadata based on the set repo

                # async call run_import

                # check if the pod has enough resources to process the import
                # Get the Repo_content
                repo_content = get_repocontent(repo=repo,url=url,api_key=api_key,user=repo_user)
                # Repo content will fit?
                repo_content_will_fit = repo_content_fits(repo_content, username, password, complete_folder_path)
                msg = f"repo_content_will_fit: {repo_content_will_fit}"
                logger.info(msg)
                # update_history(username=username, folder=complete_folder_path, url=url, status=msg)
                if repo_content_will_fit:
                    t = Thread(target=run_private_import, args=(
                        username, password, complete_folder_path, url, repo, api_key, repo_user))
                    t.start()    
                    result = "Import started"
                else:
                    r_status = "REQUEST_ENTITY_TOO_LARGE"
                    result = f"The dataset is too large to be processed."
                    update_history(username=username, folder=complete_folder_path, url=url, status=result)
                    response.status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            else:
                r_status = "UNAUTHORIZED"
                result = None
                response.status_code = status.HTTP_401_UNAUTHORIZED
        else:
            r_status = "UNAUTHORIZED"
            result = None
            response.status_code = status.HTTP_401_UNAUTHORIZED
    except Exception as e:
        r_status = "BAD_REQUEST"
        result = None
        response.status_code = status.HTTP_400_BAD_REQUEST
        message = f"Import could not be started: {e}"
        update_history(username=username, folder=complete_folder_path, url=url, status=message)
        logger.error(message)
    return {"status": r_status,
            "data": data,
            "result": result}

@fast_app.post("/history", status_code=200)
def fast_app_history(data: historyData, response: Response):
    r_status = "OK"
    history = []
    id = data.id
    username = data.cloud_username
    password = data.cloud_password
    # check if we can make connection
    try:
        if make_connection(username=data.cloud_username, password=data.cloud_password):
            with app.app_context():
                if id:
                    hist_of_id = History.query.filter_by(id=id).one()
                    folder = hist_of_id.folder
                    url = hist_of_id.url
                    projectname = hist_of_id.projectname
                    result = History.query.filter(
                        and_(
                            History.username == username,
                            History.folder == folder,
                            History.url == url,
                            History.projectname == projectname
                            )
                        ).order_by(History.id.desc()).all()
                else:
                    history = History.query.filter_by(
                        username=username
                        ).order_by(History.id.desc())
                    tmp_hist = []
                    latest_folder_url = []
                    # only get latest status per retrieval
                    for item in history:
                        if [item.folder, item.url, item.projectname] != latest_folder_url:
                            tmp_hist.append(item)
                            latest_folder_url = [item.folder, item.url, item.projectname]
                    result = tmp_hist
        else:
            r_status = "UNAUTHORIZED"
            result = None
            response.status_code = status.HTTP_401_UNAUTHORIZED
    except Exception as e:
        message = f"An exception occurred while getting the history: {e}"
        logger.error(message)
        r_status = "BAD_REQUEST"
        result = None
        response.status_code = status.HTTP_400_BAD_REQUEST
    return {"status": r_status,
            "data": data,
            "result": result}