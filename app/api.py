import random
from threading import Thread
from fastapi import Response, status
from sqlalchemy import and_
from pydantic import BaseModel
import pandas as pd
import matplotlib.pyplot as plt
import json

from app.models import fast_app, app, History
from app.repos import run_export, run_private_import
from app.utils import set_projectname, get_cached_folders, get_folders, get_query_status_history, make_connection
from app.utils import folder_content_can_be_processed, repo_content_fits, update_history, create_monthly
from app.repos import check_connection, get_repocontent
from app.globalvars import *
from app.logs import *

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
    return {"version": f"{code_version}"}


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


@fast_app.get("/stats", status_code=200)
def fast_app_stats(response: Response):
    r_status = "OK"
    result = {"images" : {}}
    try:
        with app.app_context():
            ###############################

            # BEGIN FILES PROCESSED STATS
            
            try:
                processed = History.query.filter(History.status.like("%Files processed:%"))
                processed = [u.__dict__ for u in processed.all()]
                df = pd.DataFrame(processed)
                df["files_processed"]=df["status"].apply(lambda x: int(x.split("Files processed:")[-1].split(".")[0].strip()))
                result["files_processed"] = df["files_processed"].sum()
            except:
                result["files_processed"] = 0

            try:
                failures = History.query.filter(History.status.like("%Failures:%"))
                failures = [u.__dict__ for u in failures.all()]
                df = pd.DataFrame(failures)
                df["failures"]=df["status"].apply(lambda x: int(x.split("Failures:")[-1].split(".")[0].strip()))
                result["failures"] = df["failures"].sum()
            except:
                result["failures"] = 0
            
            # END FILES PROCESSED STATS

            ###########################

            started = History.query.filter_by(
                            status="started"
                            )
            
            ##########################

            # BEGIN USERS STATS

            users_action = {
                "combined" : 0,
                "import" : 0,
                "export" : 0
            }

            try:
                exports = History.query.filter(History.status.like("%creating a project at%"))
                exports = [u.__dict__ for u in exports.all()]
                df = pd.DataFrame(exports)
                df = df.groupby(df["username"]).count()
                users_action["export"] = len(df)
            except:
                users_action["export"] = 0

            try:
                imports = History.query.filter(History.status.like("%start pushing dataset to storage%"))
                imports = [u.__dict__ for u in imports.all()]
                df = pd.DataFrame(imports)
                df = df.groupby(df["username"]).count()
                users_action["import"] = len(df)
            except:
                users_action["import"] = 0

            try:
                impex = [u.__dict__ for u in started.all()]
                df = pd.DataFrame(impex)
                df = df.groupby(df["username"]).count()
                users_action["combined"] = len(df)
            except:
                users_action["combined"] = 0

            result["users_action"] = users_action

            # END USERS STATS

            ###########################

            # BEGIN PROCESSING IMPORTS PER REPO

            imports_repo = {
                "datahugger" : 0,
                "figshare" : 0,
                "zenodo" : 0,
                "osf" : 0,
                "dataverse": 0,
                "datastation" : 0,
                "data4tu" : 0,
                "sharekit" : 0,
                "irods" : 0,
                "surfs3" : 0
            }
            
            exports_repo = {
                "figshare" : 0,
                "zenodo" : 0,
                "osf" : 0,
                "dataverse": 0,
                "datastation" : 0,
                "data4tu" : 0,
                "sharekit" : 0,
                "irods" : 0,
                "surfs3" : 0
            }

            plt.close()

            importrepokeys = []

            try:
                xdata = create_monthly(started.filter(History.url.like("%doi.org%")))
                if xdata:
                    plt.plot(xdata[1])
                    importrepokeys.append('datahugger')
                    imports_repo["datahugger"] = xdata[1]["year-month"][-1]
            except:
                imports_repo["datahugger"] = 0

            try:
                xdata = create_monthly(started.filter(History.url.like("%figshare.com%")))
                if xdata:
                    plt.plot(xdata[1])
                    importrepokeys.append('figshare')
                    imports_repo["figshare"] = xdata[1]["year-month"][-1]
            except:
                imports_repo["figshare"] = 0

            try:
                xdata = create_monthly(started.filter(History.url.like("%zenodo.org%")))
                if xdata:
                    plt.plot(xdata[1])
                    importrepokeys.append('zenodo')
                    imports_repo["zenodo"] = xdata[1]["year-month"][-1]
            except:
                imports_repo["zenodo"] = 0

            try:
                xdata = create_monthly(started.filter(History.url.like("%osf.io%")))
                if xdata:
                    plt.plot(xdata[1])
                    importrepokeys.append('osf')
                    imports_repo["osf"] = xdata[1]["year-month"][-1]
            except:
                imports_repo["osf"] = 0

            try:
                xdata = create_monthly(started.filter(History.url.like("%dataverse.nl%")))
                if xdata:
                    plt.plot(xdata[1])
                    importrepokeys.append('dataverse')
                    imports_repo["dataverse"] = xdata[1]["year-month"][-1]
            except:
                imports_repo["dataverse"] = 0

            try:
                xdata = create_monthly(started.filter(History.url.like("%datastations.nl%")))
                if xdata:
                    plt.plot(xdata[1])
                    importrepokeys.append('datastation')
                    imports_repo["datastation"] = xdata[1]["year-month"][-1]
            except:
                imports_repo["datastation"] = 0

            try:
                xdata = create_monthly(started.filter(History.url.like("%4tu.nl%")))
                if xdata:
                    plt.plot(xdata[1])
                    importrepokeys.append('data4tu')
                    imports_repo["data4tu"] = xdata[1]["year-month"][-1]
            except:
                imports_repo["data4tu"] = 0

            try:
                xdata = create_monthly(started.filter(History.url.like("%surfsharekit.nl%")))
                if xdata:
                    plt.plot(xdata[1])
                    importrepokeys.append('sharekit')
                    imports_repo["sharekit"] = xdata[1]["year-month"][-1]
            except:
                imports_repo["sharekit"] = 0

            try:
                xdata = create_monthly(started.filter(History.url.like("%.irods.%")))
                if xdata:
                    plt.plot(xdata[1])
                    importrepokeys.append('irods')
                    imports_repo["irods"] = xdata[1]["year-month"][-1]
            except:
                imports_repo["irods"] = 0

            try:
                xdata = create_monthly(started.filter(History.url.like("%Restoring_project%")))
                if xdata:
                    plt.plot(xdata[1])
                    importrepokeys.append('surfs3')
                    imports_repo["surfs3"] = xdata[1]["year-month"][-1]
            except:
                imports_repo["surfs3"] = 0

            plt.legend(importrepokeys, loc="upper left", title="Repo import usage by the SRDC")
            plt.xticks(rotation=35)
            plt.savefig("app/static/img/importstats.png")
            plt.close()
            
            result["images"]["importstats"] = "/static/img/importstats.png"

            # END PROCESSING IMPORTS PER REPO

            # BEGIN PROCESSING EXPORTS PER REPO
            plt.close()

            exportrepokeys = []

            try:
                xdata = create_monthly(started.filter_by(url="figshare"))
                if xdata:
                    plt.plot(xdata[1])
                    exportrepokeys.append('figshare')
                    exports_repo["figshare"] = xdata[1]["year-month"][-1]
            except:
                exports_repo["figshare"] = 0

            try:
                xdata = create_monthly(started.filter_by(url="zenodo"))
                if xdata:
                    plt.plot(xdata[1])
                    exportrepokeys.append('zenodo')
                    exports_repo["zenodo"] = xdata[1]["year-month"][-1]
            except:
                exports_repo["zenodo"] = 0

            try:
                xdata = create_monthly(started.filter_by(url="osf"))
                if xdata:
                    plt.plot(xdata[1])
                    exportrepokeys.append('osf')
                    exports_repo["osf"] = xdata[1]["year-month"][-1]
            except:
                exports_repo["osf"] = 0

            try:
                xdata = create_monthly(started.filter_by(url="dataverse"))
                if xdata:
                    plt.plot(xdata[1])
                    exportrepokeys.append('dataverse')
                    exports_repo["dataverse"] = xdata[1]["year-month"][-1]
            except:
                exports_repo["dataverse"] = 0

            try:
                xdata = create_monthly(started.filter_by(url="datastation"))
                if xdata:
                    plt.plot(xdata[1])
                    exportrepokeys.append('datastation')
                    exports_repo["datastation"] = xdata[1]["year-month"][-1]
            except:
                exports_repo["datastation"] = 0

            try:
                xdata = create_monthly(started.filter_by(url="data4tu"))
                if xdata:
                    plt.plot(xdata[1])
                    exportrepokeys.append('data4tu')
                    exports_repo["data4tu"] = xdata[1]["year-month"][-1]
            except:
                exports_repo["data4tu"] = 0

            try:
                xdata = create_monthly(started.filter_by(url="sharekit"))
                if xdata:
                    plt.plot(xdata[1])
                    exportrepokeys.append('sharekit')
                    exports_repo["sharekit"] = xdata[1]["year-month"][-1]
            except:
                exports_repo["sharekit"] = 0

            try:
                xdata = create_monthly(started.filter_by(url="irods"))
                if xdata:
                    plt.plot(xdata[1])
                    exportrepokeys.append('irods')
                    exports_repo["irods"] = xdata[1]["year-month"][-1]
            except:
                exports_repo["irods"] = 0

            try:
                xdata = create_monthly(started.filter(History.projectname.like("%Archiving_project%")))
                if xdata:
                    plt.plot(xdata[1])
                    exportrepokeys.append('surfs3')
                    exports_repo["surfs3"] = xdata[1]["year-month"][-1]
            except:
                exports_repo["surfs3"] = 0

            plt.legend(exportrepokeys, loc="upper left", title="Repo export usage by the SRDC")
            plt.xticks(rotation=35)
            plt.savefig("app/static/img/exportstats.png")
            plt.close()
            
            result["images"]["exportstats"] = "/static/img/exportstats.png"
            result["exports_repo"] = exports_repo
            result["imports_repo"] = imports_repo


            # END PROCESSING EXPORTS PER REPO

            ###########################

            # calculate totals based on values per repo
            total_import = 0
            try:
                for key, value in imports_repo.items():
                    if value:
                        try:
                            total_import += int(value)
                        except:
                            pass
            except:
                pass

            total_export = 0 
            try:
                for key, value in exports_repo.items():
                    if value:
                        try:
                            total_export += int(value)
                        except:
                            pass
            except:
                pass

            result["total_import"] = total_import
            result["total_export"] = total_export
            result["total_impex"] = total_import + total_export


            # prepare data for the chart
            ready = History.query.filter_by(
                            status="ready"
                            )

            xready = create_monthly(ready)
            if xready:
                monthly, cummulative = xready
            else:
                monthly, cummulative = 0, 0

            # generate the main chart
            plt.close()
            plt.plot(cummulative)
            plt.legend(["Total imports and exports"], loc="upper left", title="Usage of the SRDC")
            plt.xticks(rotation=35)
            plt.savefig("app/static/img/mainstats.png")
            plt.close()

            result["images"]["mainstats"] = "/static/img/mainstats.png"
        result = json.loads(str(result).replace("'",'"'))
    except Exception as e:
        message = f"An exception occured: {e}"
        logger.error(message)
        r_status = "BAD_REQUEST"
        result = message
        response.status_code = status.HTTP_400_BAD_REQUEST

    return {"status": r_status, "result": result}