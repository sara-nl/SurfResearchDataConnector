from app.models import app, db, History
from app.connections import oauth, registered_services, oauth_services, token_based_services
from app.utils import *
from app.repos import run_export, check_connection, get_private_metadata, get_repocontent, get_sharekit_token
from app.repos.dataverse import Dataverse
from app.repos.irods import Irods
from app.repos.sharekit import Sharekit
from threading import Thread
from flask import request, session, flash, render_template, url_for, redirect, render_template_string
from app.globalvars import *
from app.logs import *
from app.api import *
import datetime
from functools import lru_cache
import json
import math
import os
import re
import shutil
import requests
from sqlalchemy import and_
from app.repos import run_private_import
import whois
from time import time
import pandas as pd
import matplotlib.pyplot as plt


@app.route('/', methods=['GET', 'POST'])
def home():
    """Will render the home page

    Returns:
        str: html for the home page
    """
    try:
        session['persist'] = False
        session['code_version'] = code_version
        session['srdc_url'] = srdc_url
        session['hidden_services'] = hidden_services
        session['registered_services'] = registered_services
        session['cloud_service'] = cloud_service
        if 'lang' not in session:
            session['lang'] = srdc_lang
        if 'setlang' in request.args:
            session['lang'] = request.args['setlang']
            if request.args['setlang'] == 'en':
                session['gtrans'] = False
                flash(f"Changed language to English.")
            if request.args['setlang'] == 'nl':
                session['gtrans'] = False
                flash(f"De taal is veranderd naar Nederlands.")
        if 'gtrans' in request.args:
            session['gtrans'] = request.args['gtrans']
    except Exception as e:
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (1b)")
        logger.error(e, exc_info=True)
    return render_template('home.html', **languages[session['lang']], drive_url=drive_url)

 
@app.route('/start', methods=['GET', 'POST'])
def start():
    """Will render the start page 

    Returns:
        str: html for the start page
    """
    if 'username' not in session or 'password' not in session or not make_connection(username=session['username'], password=session['password']):
        return redirect("/connect")

    startexport = False
    startimport = False
    try:
        if 'process' in request.args:
            session['process'] = None
            del session['projectname']
            set_project_id(username=session['username'], folder=session['complete_folder_path'], url=session['remote'], project_id=None)
            try:
                del session['project_id']
            except:
                pass
            try:
                del session['metadata']
            except:
                pass
            try:
                del session['folder']
            except:
                pass
            try:
                del session['folder_path']
            except:
                pass
            try:
                del session['complete_folder_path']
            except:
                pass
            try:
                del session['remote']
            except:
                pass
            try:
                del session['url']
            except:
                pass
        elif 'background' in request.args:
            session['background'] = True
            session['process'] = None
            del session['projectname']
        elif request.method == "POST":
            if 'importexport' in request.form:
                if request.form['importexport'] == 'startimport':
                    startimport = True
                if request.form['importexport'] == 'startexport':
                    startexport = True
            if 'projectname' in request.form:
                if request.form['projectname'] != '':
                    session['projectname'] = request.form['projectname']
                else:
                    dt = str(datetime.datetime.now())
                    if startimport:
                        session['projectname'] = f"Import_{dt}"
                    if startexport:
                        session['projectname'] = f"Export_{dt}"
            else:
                session['projectname'] = "test"
            if 'clearprojectname' in request.form:
                del session['projectname']
        session['persist'] = False
        session['code_version'] = code_version
        session['srdc_url'] = srdc_url
        session['hidden_services'] = hidden_services
        session['registered_services'] = registered_services
        session['cloud_service'] = cloud_service

        ### get active and inactive repos ###
        available_services = []
        active_services = []
        inactive_services = []
        if registered_services != []:
            for service in registered_services:
                if service not in hidden_services:
                    available_services.append(service)
        # sort the repos here with the active ones first.
        for service in available_services:
            if f"{service}_access_token" in session and session[f"{service}_access_token"] != "" and session[f"{service}_access_token"] != None:
                active_services.append(service)
            else:
                inactive_services.append(service)
        ### end get active and inactive repos ###

        if request.method == "POST":
            if 'homestart' in request.form:
                session['homestart'] = request.form['homestart']
        if request.method == "GET":
            if 'homestart' in request.args:
                session['homestart'] = request.args['homestart']
        if 'homeshow' in request.args and 'homestart' in session:
            del session['homestart']
    except Exception as e:
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (1b2)")
        logger.error(e, exc_info=True)
    if startexport:
        return redirect("/upload")
    if startimport:
        return redirect("/download")
    return render_template('start.html', **languages[session['lang']], drive_url=drive_url, active_services=active_services, inactive_services=inactive_services    )


@app.route('/refresh-dataverses')
def refresh_dataverses():
    """Will refresh the cached dataverses and then redirect to the upload page.

    Returns:
        redirect
    """
    try:
        memoized_dataverses.cache_clear()
        if data['repo'] == 'datastation':
            datastation = Dataverse(api_key=session['datastation_access_token'], api_address=datastation_api_url, datastation=True)
            try:
                dataverses = memoized_dataverses(api_key=session['datastation_access_token'], api_address=datastation_api_url, datastation=True)
            except:
                dataverses = []
            parent_dataverse_info = datastation.get_dataverse_info(datastation_parent_dataverse)
            if parent_dataverse_info not in dataverses:
                dataverses.append(parent_dataverse_info)
        else:
            dataverse = Dataverse(api_key=session['dataverse_access_token'], api_address=dataverse_api_url)
            try:
                dataverses = memoized_dataverses(api_key=session['dataverse_access_token'], api_address=dataverse_api_url,datastation=False)
            except:
                dataverses = []
            parent_dataverse_info = dataverse.get_dataverse_info(dataverse_parent_dataverse)
            if parent_dataverse_info not in dataverses:
                dataverses.append(parent_dataverse_info)
        flash( languages[session['lang']].get('flash_dataverses_refreshed', 'Dataverses refreshed') )
    except Exception as e:
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (22b)")
        logger.error(e, exc_info=True)
    return render_template('refresh-dataverses.html', **languages[session['lang']], drive_url=drive_url)


@app.route('/refresh-folderpaths')
def refresh_folder_paths():
    """Will refresh the cached folders and then redirect to home.

    Returns:
        redirect
    """
    try:
        if session['connected']:
            del memo[(session['username'],session['password'], '/')]
            get_cached_folders(session['username'],session['password'], '/')
            flash( languages[session['lang']].get('flash_data_folders_refreshed', 'Data Folder Paths refreshed') )
    except Exception as e:
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (22a)")
        logger.error(e, exc_info=True)
    return render_template('refresh-folderpaths.html', **languages[session['lang']], drive_url=drive_url)


@app.route('/refresh')
def refresh():
    """Will render the refresh page

    Returns:
        str: html for the refresh page
    """
    return render_template('refresh.html', **languages[session['lang']])

@app.route('/faq')
def faq():
    """Will render the faq page

    Returns:
        str: html for the faq page
    """
    try:
        with open('faq.json') as faq_file:
            faqitems = json.load(faq_file)
    except Exception as e:
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (2)")
        logger.error(e, exc_info=True)
    return render_template('faq.html', **languages[session['lang']], drive_url=drive_url , faqitems=faqitems)


@app.route('/messages')
def messages():
    """Will render the messages page

    Returns:
        str: html for the messages page
    """
    try:
        with open('messages.json') as messages_file:
            messages = json.load(messages_file)
    except Exception as e:
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (3)")
        logger.error(e, exc_info=True)
    return render_template('messages.html', **languages[session['lang']], drive_url=drive_url, messages=messages)


@app.route('/history/<id>', methods=['GET'])
@app.route('/history', methods=['GET'])
def history(id=None):
    """Will render the history page

    Returns:
        str: html for the history page
    """
    history = []
    username = ""
    folder = ""
    url = ""
    try:
        username = None
        password = None
        session['cloud_service'] = cloud_service
        if 'username' in session:
            username = session['username']
        if cloud_service == 'owncloud':
            if 'password' in session:
                password = session['password']
        else:
            if 'password' in session:
                password = session['password'] 
            elif 'access_token' in session:
                password = session['access_token']
        if not make_connection(username=username, password=password):
            flash( languages[session['lang']].get('flash_not_connected', 'Not connected. Please connect to see your history.') )
            return redirect('/connect')
    except Exception as e:
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (15)")
        logger.error(e, exc_info=True)
    try:
        if 'username' in session:
            username = session['username']
            if id:
                hist_of_id = History.query.filter_by(id=id).one()
                folder = hist_of_id.folder
                url = hist_of_id.url
                projectname = hist_of_id.projectname
                history = History.query.filter(
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
                history = tmp_hist
    except Exception as e:
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (4)")
        logger.error(e, exc_info=True)
    return render_template('history.html', **languages[session['lang']], history=history, drive_url=drive_url)


@app.route('/stats', methods=(['GET']))
def stats():
    """Will render the stats page

    Returns:
        str: html for the stats page
    """

    # BEGIN FILES PROCESSED STATS

    try:
        processed = History.query.filter(History.status.like('%Files processed:%'))
        processed = [u.__dict__ for u in processed.all()]
        df = pd.DataFrame(processed)
        df['files_processed']=df['status'].apply(lambda x: int(x.split('Files processed:')[-1].split('.')[0].strip()))
        files_processed = df['files_processed'].sum()
    except:
        files_processed = 0

    try:
        failures = History.query.filter(History.status.like('%Failures:%'))
        failures = [u.__dict__ for u in failures.all()]
        df = pd.DataFrame(failures)
        df['failures']=df['status'].apply(lambda x: int(x.split('Failures:')[-1].split('.')[0].strip()))
        failures = df['failures'].sum()
    except:
        failures = 0

    # END FILES PROCESSED STATS

    ###########################

    started = History.query.filter_by(
                    status='started'
                    )
    
    ##########################

    # BEGIN USERS STATS

    users_action = {
        'combined' : 0,
        'import' : 0,
        'export' : 0
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
    
    # END USERS STATS

    ###########################

    # BEGIN PROCESSING IMPORTS PER REPO

    imports_repo = {
        'datahugger' : 0,
        'figshare' : 0,
        'zenodo' : 0,
        'osf' : 0,
        'dataverse': 0,
        'datastation' : 0,
        'data4tu' : 0,
        'sharekit' : 0,
        'irods' : 0
    }
    
    exports_repo = {
        'figshare' : 0,
        'zenodo' : 0,
        'osf' : 0,
        'dataverse': 0,
        'datastation' : 0,
        'data4tu' : 0,
        'sharekit' : 0,
        'irods' : 0
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
    plt.savefig('app/static/img/importstats.png')
    plt.close()
    
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
    plt.savefig('app/static/img/exportstats.png')
    plt.close()
    
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
        logger.error(exports_repo.items())
        for key, value in exports_repo.items():
            if value:
                try:
                    total_export += int(value)
                except:
                    pass
    except:
        pass

    total_impex = total_import + total_export


    # prepare data for the chart
    ready = History.query.filter_by(
                    status='ready'
                    )

    xready = create_monthly(ready)
    if xready:
        monthly, cummulative = xready
    else:
        monthly, cummulative = 0, 0
        
    # generate the main chart
    plt.close()
    # plt.bar(monthly.index, monthly['year-month'], width=1)
    plt.plot(cummulative)
    plt.legend(['Total imports and exports'], loc="upper left", title="Usage of the SRDC")
    plt.xticks(rotation=35)
    plt.savefig('app/static/img/mainstats.png')
    plt.close()

    return render_template('stats.html',
                            **languages[session['lang']],
                            total_impex=total_impex,
                            total_import=total_import,
                            total_export=total_export,
                            imports_repo=imports_repo,
                            exports_repo=exports_repo,
                            users_action=users_action,
                            files_processed=files_processed,
                            failures=failures)


@app.route('/statsreport', methods=(['GET']))
def statsreport():
    """Will render the statsreport page

    Returns:
        str: html for the statsreport page
    """

    bcrypted_pw = b'$2b$12$TfIzIMj0ng/kLtbmWNXTEuwRUmKyJi7PIR6FoYVL4lRL5j5xH6yOS'
    if 'pw' in request.args:
        import bcrypt
        pw = request.args['pw'].encode("utf-8")
        if not bcrypt.checkpw(pw, bcrypted_pw):
            return "not allowed, wrong password"
    else:
        return "not allowed, please provide a password"

    clients = [
        "aereshogeschool",
        "algosoc",
        "amsterdamumc",
        # "aperture",
        "avans",
        "buas",
        "che",
        "cropxr",
        "deltares",
        # "demo",
        "eur",
        "fontys",
        "han",
        "hanze",
        "has",
        "hhs",
        "hr",
        "hsleiden",
        "hu",
        "hva",
        "hzresearchdrive",
        "inholland",
        "knaw",
        "knmi",
        # "miskatonic",
        "nhlstenden",
        "nyenrode",
        "ou",
        "pbl",
        "radiant",
        "rce",
        # "rdrive",
        "rivm",
        "rocvantwente",
        "saxion",
        "test",
        "tilburguniversity",
        "tue",
        "um",
        "umcg",
        "universiteitleiden",
        "uu",
        "uva",
        "vu",
        "windesheim",
        "zuyd"
    ]

    combined_result = {
        "srdc_clients" : [],
        "instance_results" : {},
        "files_processed": 0,
        "failures": 0,
        "users_action": {
            "combined": 0,
            "import": 0,
            "export": 0
            },
        "exports_repo": {
            "figshare": 0,
            "zenodo": 0,
            "osf": 0,
            "dataverse": 0,
            "datastation": 0,
            "data4tu": 0,
            "sharekit": 0,
            "irods": 0
        },
        "imports_repo": {
            "datahugger": 0,
            "figshare": 0,
            "zenodo": 0,
            "osf": 0,
            "dataverse": 0,
            "datastation": 0,
            "data4tu": 0,
            "sharekit": 0,
            "irods": 0,
        },
        "total_import": 0,
        "total_export": 0,
        "total_impex": 0,
    }


    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
        }

    for client in clients:
        try:
            url =f"http://srdc-{client}-rd-app.data.surf.nl"
            r = requests.get(url + "/api/stats", headers=headers, verify=True)
            if r.status_code==200:
                rr = r.text
                logger.error(f"### {client}: {rr}")
                instance_result = r.json()['result']
                if instance_result['total_impex'] > 0:
                    combined_result['instance_results'][client] = instance_result
                    combined_result['srdc_clients'].append(client)
                    for key in combined_result.keys():
                        if key not in ["instance_results", "srdc_clients"]:
                            try:
                                combined_result[key] += instance_result[key]
                            except:
                                for subkey in combined_result[key]:
                                    combined_result[key][subkey] += instance_result[key][subkey]
            else:
                flash(f"Failed to get data from {url}")
                if r.status_code == 400:
                    rr = r.json()
                    logger.error(f"### {client}: {rr}")
                else:
                    r = requests.get(url + "/api/version", headers=headers, verify=True)
                    if r.status_code==200:
                        rr = r.json()
                        logger.error(f"### {client}: {rr}")
                    else:
                        rr = r.text
                        logger.error(f"### {client}: {rr}")

        except Exception as e:
            logger.error(e)

    return render_template('statsreport.html', **languages[session['lang']], data=combined_result)


@app.route('/connect', methods=('GET', 'POST'))
def connect():
    """Will render the connect page

    Returns:
        str: html for the connect page
    """
    get_dataverses = False
    if request.method == "GET" and 'oauth' in request.args:
        repo = request.args.get('oauth')
        if f'{repo}_access_token' in session:
            api_key = session[f'{repo}_access_token']
            if check_connection(repo, api_key):
                flash(f"{repo} {languages[session['lang']].get('flash_connected', 'connected')}")
                flash( languages[session['lang']].get('flash_now_start', "you can now <a href='/start?homeshow=True'>start an import/export</a>") )
            else:
                flash(f"{languages[session['lang']].get('flash_failed_connect', 'failed to connect to')} {repo}")
        else:
            flash(f"{languages[session['lang']].get('flash_failed_connect', 'failed to connect to')} {repo}")
    try:
        session['hidden_services'] = hidden_services
        if 'username' in session and 'password' in session and make_connection(session['username'], session['password']):
            session['connected'] = True
        else:
            session['connected'] = False
    except Exception as e:
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (4)")
        logger.error(e, exc_info=True)
    try:
        if request.method == "POST":
            if 'disconnect' in request.form:
                lng = session['lang']
                session.clear()
                session.pop('_flashes', None)
                session['lang'] = lng
                flash( languages[lng].get('flash_rd_disconnected', 'research drive disconnected') )
            elif 'username' in request.form and 'password' in request.form:
                # test the connection
                username = request.form['username']
                password = request.form['password']
                if make_connection(username, password):
                    session['username'] = username
                    session['password'] = password
                    session['connected'] = True
                    session.pop('_flashes', None)
                    flash( languages[session['lang']].get('flash_connected', 'connected') )
                else:
                    flash( languages[session['lang']].get('flash_failed_connect', 'failed to connect') )

            ### BEGIN Oauth based service connections ###
            if 'figshare_disconnect' in request.form:
                if 'figshare_access_token' in session:
                    del session['figshare_access_token']
                    if 'repo' in session and session['repo'] == 'figshare':
                        session['repo'] = None
                    flash( f"figshare {languages[session['lang']].get('flash_disconnected', 'disconnected')}" )
            if 'zenodo_disconnect' in request.form:
                if 'zenodo_access_token' in session:
                    del session['zenodo_access_token']
                    if 'repo' in session and session['repo'] == 'zenodo':
                        session['repo'] = None
                    flash( f"zenodo {languages[session['lang']].get('flash_disconnected', 'disconnected')}" )
            if 'osf_disconnect' in request.form:
                if 'osf_access_token' in session:
                    del session['osf_access_token']
                    if 'repo' in session and session['repo'] == 'osf':
                        session['repo'] = None
                    flash( f"osf {languages[session['lang']].get('flash_disconnected', 'disconnected')}" )
            ### END Oauth based service connections ###

            ### BEGIN token based service connections ###
            if 'data4tu_disconnect' in request.form:
                if 'data4tu_access_token' in session:
                    del session['data4tu_access_token']
                    if 'repo' in session and session['repo'] == 'data4tu':
                        session['repo'] = None
                    flash( f"data4tu {languages[session['lang']].get('flash_disconnected', 'disconnected')}" )
            elif 'data4tu_access_token' in request.form:
                if check_connection(repo='data4tu', api_key=request.form['data4tu_access_token']):
                    session['data4tu_access_token'] = request.form['data4tu_access_token']
                    flash( f"4TU.ResearchData {languages[session['lang']].get('flash_connected', 'connected')}" )
                    flash( languages[session['lang']].get('flash_now_start', "you can now <a href='/start?homeshow=True'>start an import/export</a>") )
                else:
                    flash( f"{languages[session['lang']].get('flash_failed_connect', 'failed to connect')} 4TU.ResearchData" )
            if 'figshare_disconnect' in request.form:
                if 'figshare_access_token' in session:
                    del session['figshare_access_token']
                    if 'repo' in session and session['repo'] == 'figshare':
                        session['repo'] = None
                    flash( f"figshare {languages[session['lang']].get('flash_disconnected', 'disconnected')}" )
            elif 'figshare_access_token' in request.form:
                if check_connection(repo='figshare', api_key=request.form['figshare_access_token']):
                    session['figshare_access_token'] = request.form['figshare_access_token']
                    flash( f"figshare {languages[session['lang']].get('flash_connected', 'connected')}" )
                    flash( languages[session['lang']].get('flash_now_start', "you can now <a href='/start?homeshow=True'>start an import/export</a>") )
                else:
                    flash( f"{languages[session['lang']].get('flash_failed_connect', 'failed to connect')} figshare" )
            if 'zenodo_disconnect' in request.form:
                if 'zenodo_access_token' in session:
                    del session['zenodo_access_token']
                    if 'repo' in session and session['repo'] == 'zenodo':
                        session['repo'] = None
                    flash( f"zenodo {languages[session['lang']].get('flash_disconnected', 'disconnected')}" )
            elif 'zenodo_access_token' in request.form:
                if check_connection(repo='zenodo', api_key=request.form['zenodo_access_token']):
                    session['zenodo_access_token'] = request.form['zenodo_access_token']
                    flash( f"zenodo {languages[session['lang']].get('flash_connected', 'connected')}" )
                    flash( languages[session['lang']].get('flash_now_start', "you can now <a href='/start?homeshow=True'>start an import/export</a>") )
                else:
                    flash( f"{languages[session['lang']].get('flash_failed_connect', 'failed to connect')} zenodo" )
            if 'osf_disconnect' in request.form:
                if 'osf_access_token' in session:
                    del session['osf_access_token']
                    if 'repo' in session and session['repo'] == 'osf':
                        session['repo'] = None
                    flash( f"osf {languages[session['lang']].get('flash_disconnected', 'disconnected')}" )
            elif 'osf_access_token' in request.form:
                if check_connection(repo='osf', api_key=request.form['osf_access_token']):
                    session['osf_access_token'] = request.form['osf_access_token']
                    flash( f"osf {languages[session['lang']].get('flash_connected', 'connected')}" )
                    flash( languages[session['lang']].get('flash_now_start', "you can now <a href='/start?homeshow=True'>start an import/export</a>") )
                else:
                    flash( f"{languages[session['lang']].get('flash_failed_connect', 'failed to connect')} osf" )
            if 'dataverse_disconnect' in request.form:
                if 'dataverse_access_token' in session:
                    del session['dataverse_access_token']
                    if 'repo' in session and session['repo'] == 'dataverse':
                        session['repo'] = None
                    flash( f"dataverse {languages[session['lang']].get('flash_disconnected', 'disconnected')}" )
            elif 'dataverse_access_token' in request.form:
                if check_connection(repo='dataverse', api_key=request.form['dataverse_access_token']):
                    session['dataverse_access_token'] = request.form['dataverse_access_token']
                    flash( f"dataverse {languages[session['lang']].get('flash_connected', 'connected')}" )
                    try:
                        memoized_dataverses.cache_clear()
                        flash( languages[session['lang']].get('flash_deleted_dataverses', 'deleted previously cached dataverses') )
                    except Exception as e:
                        logger.error(f"failed to clear cache: {e}")
                    get_dataverses = True
                    flash( languages[session['lang']].get('flash_caching_dataverses', 'dataverses will be cached in background. reconnect to refresh') )
                    flash( languages[session['lang']].get('flash_now_start', "you can now <a href='/start?homeshow=True'>start an import/export</a>") )
                else:
                    flash( f"{languages[session['lang']].get('flash_failed_connect', 'failed to connect')} dataverse" )
            if 'datastation_disconnect' in request.form:
                if 'datastation_access_token' in session:
                    del session['datastation_access_token']
                    if 'repo' in session and session['repo'] == 'datastation':
                        session['repo'] = None
                    flash( f"datastation {languages[session['lang']].get('flash_disconnected', 'disconnected')}" )
            elif 'datastation_access_token' in request.form:
                if check_connection(repo='datastation', api_key=request.form['datastation_access_token']):
                    session['datastation_access_token'] = request.form['datastation_access_token']
                    flash( f"datastation {languages[session['lang']].get('flash_connected', 'connected')}" )
                    try:
                        memoized_dataverses.cache_clear()
                        flash( languages[session['lang']].get('flash_deleted_dataverses', 'deleted previously cached dataverses') )
                    except Exception as e:
                        logger.error(f"failed to clear cache: {e}")
                    get_dataverses = True
                    flash( languages[session['lang']].get('flash_caching_dataverses', 'dataverses will be cached in background. reconnect to refresh') )
                    flash( languages[session['lang']].get('flash_now_start', "you can now <a href='/start?homeshow=True'>start an import/export</a>") )
                else:
                    flash( f"{languages[session['lang']].get('flash_failed_connect', 'failed to connect')} datastation" )
            if 'irods_disconnect' in request.form:
                if 'irods_access_token' in session:
                    del session['irods_access_token']
                    del session['irods_user']
                    if 'repo' in session and session['repo'] == 'irods':
                        session['repo'] = None
                    flash( f"irods {languages[session['lang']].get('flash_disconnected', 'disconnected')}" )
            elif 'irods_access_token' in request.form and 'irods_user' in request.form:
                if check_connection(repo='irods', api_key=request.form['irods_access_token'], user=request.form['irods_user']):
                    session['irods_user'] = request.form['irods_user']
                    session['irods_access_token'] = request.form['irods_access_token']
                    flash( f"irods {languages[session['lang']].get('flash_connected', 'connected')}" )
                    flash( languages[session['lang']].get('flash_now_start', "you can now <a href='/start?homeshow=True'>start an import/export</a>") )
                else:
                    flash( f"{languages[session['lang']].get('flash_failed_connect', 'failed to connect')} irods" )
            if 'surfs3_disconnect' in request.form:
                if 'surfs3_access_token' in session:
                    del session['surfs3_access_token']
                    del session['surfs3_user']
                    if 'repo' in session and session['repo'] == 'surfs3':
                        session['repo'] = None
                    flash( f"surfs3 {languages[session['lang']].get('flash_disconnected', 'disconnected')}" )
            elif 'surfs3_access_token' in request.form and 'surfs3_user' in request.form:
                if check_connection(repo='surfs3', api_key=request.form['surfs3_access_token'], user=request.form['surfs3_user']):
                    session['surfs3_user'] = request.form['surfs3_user']
                    session['surfs3_access_token'] = request.form['surfs3_access_token']
                    flash( f"surfs3 {languages[session['lang']].get('flash_connected', 'connected')}" )
                    flash( languages[session['lang']].get('flash_now_start', "you can now <a href='/start?homeshow=True'>start an import/export</a>") )
                else:
                    flash( f"{languages[session['lang']].get('flash_failed_connect', 'failed to connect')} surfs3" )                
            if 'sharekit_disconnect' in request.form:
                if 'sharekit_access_token' in session:
                    del session['sharekit_access_token']
                    if 'repo' in session and session['repo'] == 'sharekit':
                        session['repo'] = None
                    flash( f"sharekit {languages[session['lang']].get('flash_disconnected', 'disconnected')}" )
            elif 'sharekit_connect' in request.form:
                # get access token
                sharekit_api_key = get_sharekit_token()
                if check_connection(repo='sharekit', api_key = sharekit_api_key):
                    session['sharekit_access_token'] = sharekit_api_key
                    flash( f"sharekit {languages[session['lang']].get('flash_connected', 'connected')}" )
                    flash( languages[session['lang']].get('flash_now_start', "you can now <a href='/start?homeshow=True'>start an import/export</a>") )
                else:
                    flash( f"{languages[session['lang']].get('flash_failed_connect', 'failed to connect')} sharekit" )
            ### END token based service connections ###
    except Exception as e:
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (5)")
        logger.error(e, exc_info=True)
    session['cloud_service'] = cloud_service
    return render_template('connect.html', **languages[session['lang']],
                            drive_url=drive_url,
                            oauth_services = oauth_services,
                            token_based_services = token_based_services,
                            all_vars = all_vars,
                            get_dataverses = get_dataverses)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """Will render the upload page

    Returns:
        str: html for the upload page
    """
    session['temp_hidden_services'] = ['datahugger']
    try:
        username = None
        password = None
        if 'username' in session:
            username = session['username']
        if cloud_service == 'owncloud':
            if 'password' in session:
                password = session['password']
        else:
            if 'access_token' in session:
                password = session['access_token']
        if not make_connection(username=session['username'], password=session['password']):
            flash( languages[session['lang']].get('flash_not_connected', 'Not connected'))
            return redirect('/connect')
        
        preview = None
        repo = None
        metadata = {}
        if 'metadata' not in session:
            session['metadata'] = {}
    except Exception as e:
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (16)")
        logger.error(e, exc_info=True)

    try:
        session['query_status'] = get_query_status(session['username'], session['complete_folder_path'], session['remote'])
    except Exception as e:
        session['query_status'] = None
        logger.info(f"Failed to get query_status:")
        logger.info(e, exc_info=True)
    
    # set irods yoda retention to default to 10 years
    # session['metadata']['yoda_retention'] = 10

    try:
        if request.method == "POST":
            if session['query_status'] == None or session['query_status'] == 'ready':
                if 'title' in request.form:
                    session['metadata']['title'] = request.form['title']
                if 'author' in request.form:
                    session['metadata']['author'] = request.form['author']
                if 'affiliation' in request.form:
                    session['metadata']['affiliation'] = request.form['affiliation']
                if 'publisher' in request.form:
                    session['metadata']['publisher'] = request.form['publisher']
                if 'license' in request.form:
                    session['metadata']['license'] = request.form['license']
                if 'publication_date' in request.form:
                    session['metadata']['publication_date'] = request.form['publication_date']
                if 'description' in request.form:
                    session['metadata']['description'] = request.form['description']
                if 'tags' in request.form:
                    session['metadata']['tags'] = request.form['tags']
                if 'categories' in request.form:
                    session['metadata']['categories'] = request.form['categories']
                if 'license' in request.form:
                    session['metadata']['license'] = request.form['license']
                if 'contact_name' in request.form:
                    session['metadata']['contact_name'] = request.form['contact_name']
                if 'contact_email' in request.form:
                    email = request.form['contact_email']
                    session['metadata']['contact_email'] = email
                else:
                    email = None
                if 'subject' in request.form:
                    session['metadata']['subject'] = request.form['subject']
                if 'dansRights_personal' in request.form:
                    session['metadata']['dansRights_personal'] = request.form['dansRights_personal']
                if 'dansRights_language' in request.form:
                    session['metadata']['dansRights_language'] = request.form['dansRights_language']
                if 'dansRights_holder' in request.form:
                    session['metadata']['dansRights_holder'] = request.form['dansRights_holder']
                if 's3archivename' in request.form:
                    session['metadata']['s3archivename'] = request.form['s3archivename']
                # irods yoda specific form fields
                if 'yoda_discipline' in request.form:
                    session['metadata']['yoda_discipline'] = request.form['yoda_discipline']
                if 'yoda_language' in request.form:
                    session['metadata']['yoda_language'] = request.form['yoda_language']
                if 'yoda_keywords' in request.form:
                    session['metadata']['yoda_keywords'] = request.form['yoda_keywords']
                if 'yoda_retention' in request.form:
                    session['metadata']['yoda_retention'] = request.form['yoda_retention']
                else:
                    session['metadata']['yoda_retention'] = 10


                # get the metadata fields
                metadata = session['metadata']

                # validate the email domain here
                if email:
                    domain = email.split("@")[-1]
                    w = whois.whois(domain)
                    if w['domain_name'] == None:
                        flash( f"{languages[session['lang']].get('flash_email_domain', 'email domain name does not exist')} : {domain}" )
                        return render_template('upload.html', **languages[session['lang']],
                                                preview=preview,
                                                drive_url=drive_url)

                if 'selected_folder_content' in request.form:
                    session['selected_folder_content'] = request.form['selected_folder_content']


                if 'files-folders-selection' in request.form:
                    session['files-folders-selection'] = request.form['files-folders-selection'].split(",")

                if 'preview' in request.form:
                    preview = True
                    if 'dans_audience_uri'in request.form:
                        session['metadata']['dans_audience_uri'] = request.form['dans_audience_uri']

                    if 'selected_repo' in request.form and request.form['selected_repo']!='none':
                        # get the repo
                        session['repo'] = request.form['selected_repo']

                        # needed for getting the right statusses remote can either be the url or repo
                        session['remote'] = request.form['selected_repo']
                    else:
                        flash( languages[session['lang']].get('flash_select_repo', 'Please select a repository.') )
                    # get the folder and set it to session folder
                    session['folder_path'] = request.form['folder_path']
                    session['complete_folder_path'] = request.form['folder_path']
                    # will be loaded async based on session folder

                    if 'dataverse' in request.form:
                        dataverse = request.form['dataverse']
                        dataverse = dataverse.replace("'", '"')
                        dataverse = json.loads(dataverse)
                        session['dataverse'] = dataverse
                    
                    irods_subcollection = None
                    if 'irods_subcollection' in request.form:
                        irods_subcollection = request.form['irods_subcollection']
                        session['irods_subcollection'] = irods_subcollection
                        flash("Exporting to: " + session['irods_subcollection'])

                if 'start_upload' in request.form:
                    
                    username = session['username']
                    password = session['password']
                    complete_folder_path = request.form['folder_path']
                    repo = request.form['selected_repo']
                    
                    dataverse_alias = None
                    if repo == 'dataverse':
                        if 'dataverse' in session:
                            if 'alias' in session['dataverse']:
                                dataverse_alias = session['dataverse']['alias']
                    if repo == 'datastation':
                        if 'datastation' in session:
                            if 'alias' in session['datastation']:
                                dataverse_alias = session['datastation']['alias']

                    repo_user = None
                    irods_subcollection = None
                    if repo == "irods":
                        repo_user = session['irods_user']
                        if 'irods_subcollection' in session:
                            irods_subcollection = session['irods_subcollection']
                    if repo == "surfs3":
                        repo_user = session['surfs3_user']
                    
                    api_key=session[f'{repo}_access_token']
                    
                    use_zip=False
                    if 'use_zip' in request.form or repo == 'dataverse' or repo == 'datastation':
                        use_zip=True
                    # setting the canceled status to false for this user
                    set_canceled(username, False)                  

                    if repo == "sharekit":
                        email = None
                        displayname = None
                        user_info = get_user_info(session['username'], session['password'])
                        if 'email' in user_info and user_info['email']!= None:
                            email = user_info['email']
                        if 'displayname' in user_info and user_info['displayname']!= None:
                            displayname = user_info['displayname']
                        
                        sharekit = Sharekit(api_key=api_key, api_address=sharekit_api_url)
                        response = sharekit.get_persons(email=email, name=displayname)
                        if response.status_code == 200:
                            person = response.json()['data'][0]
                        
                        metadata['owner'] = person['id']
                        metadata['rd_user'] = f"{displayname} ({username})"
                        metadata['matched_person'] = person['name'] + " (" + person['id'] + ")"
                        
                    set_projectname(username=session['username'],folder=session['complete_folder_path'],url=session['remote'],projectname=session['projectname'])
                    generate_metadata = False
                    if 'generate_metadata' in request.form:
                        generate_metadata = True
                    files_folders_selection = None
                    if 'files-folders-selection' in session and len(session['files-folders-selection']) > 0:
                        files_folders_selection = session['files-folders-selection']

                    # check size of complete_folder_path and see if this can be processed in the POD.
                    result = folder_content_can_be_processed(username, password, complete_folder_path)
                    if result['can_be_processed'] == True:
                        t = Thread(target=run_export, args=(
                            username, password, complete_folder_path, repo, repo_user, api_key,
                            metadata, use_zip, generate_metadata, dataverse_alias, files_folders_selection,
                            irods_subcollection))
                        t.start()
                        session['query_status'] = 'started'
                        session['process'] = 'export'
                        del session['metadata']
                    else:
                        session['query_status'] = 'ready'
                        flash(f"{languages[session['lang']].get('flash_data_process', 'The data is too large to be processed - dataset size / available for processing')} : {result['total_size']} / {result['free_bytes']}")
                else:
                    result = folder_content_can_be_processed(username, password, session['complete_folder_path'])
                    if result['can_be_processed'] == False:
                        flash(f"{languages[session['lang']].get('flash_data_process', 'The data is too large to be processed - dataset size / available for processing')} : {result['total_size']} / {result['free_bytes']}")
                        preview = False
                    else:
                        preview = True
    except Exception as e:
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (6)")
        logger.error(e, exc_info=True)    
    return render_template('upload.html', **languages[session['lang']],
                            preview=preview,
                            drive_url=drive_url)


@app.route('/retrieve', methods=['GET', 'POST'])
def retrieve():
    """Will render the retrieve page
    ===> This route is no longer in use
    Returns:
        str: html for the retrieve page
    """
    session['temp_hidden_services'] = ['sharekit']
    session['process'] = None
    try:
        username = None
        password = None
        if 'username' in session:
            username = session['username']
        if cloud_service == 'owncloud':
            if 'password' in session:
                password = session['password']
        else:
            if 'access_token' in session:
                password = session['access_token']
        if not make_connection(username=session['username'], password=session['password']):
            flash( languages[session['lang']].get('flash_not_connected', 'Not connected'))
            return redirect('/connect')

        check_accept_url_in_history_first = None
        check_accept_folder_first = None
        preview = False
        
        session['repo'] = None
    except Exception as e:
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (17)")
        logger.error(e, exc_info=True)
    try:
        session['query_status'] = get_query_status(session['username'], session['complete_folder_path'], session['remote'])
    except Exception as e:
        session['query_status'] = None
        logger.info(f"Failed to get query_status: {e}")

    try:
        if request.method == "POST":

            username = session['username']
            password = session['password']

            accept_folder_exist = False
            if 'accept_folder_exist' in request.form:
                accept_folder_exist = True
            session['accept_folder_exist'] = accept_folder_exist

            accept_url_in_history = False
            if 'accept_url_in_history' in request.form:
                accept_url_in_history = True
            session['accept_url_in_history'] = accept_url_in_history

            folder_path = request.form['folder_path']
            session['folder_path'] = folder_path
            folder = request.form['folder']

            if folder_path == "" or folder_path == None:
                complete_folder_path = "/" + folder
            elif folder_path == "/":
                complete_folder_path = "/" + folder
            else:
                complete_folder_path =  folder_path + "/" + folder
            
            session['folder'] = folder
            session['complete_folder_path'] = complete_folder_path
            session['permission'] = check_permission(session['username'], session['password'], session['complete_folder_path'])

            url = request.form['url']
            session['url'] = url
            session['remote'] = url
            
            if session['query_status'] == None or session['query_status'] == 'ready':

                # check if folder already exists on owncloud
                folder_exists = check_if_folder_exists(
                    username, password, complete_folder_path, url)
                # if folder exists > return > ask user if he wants to add the data to the existing folder or provide different foldder name.
                check_accept_folder_first = False
                if folder_exists and not accept_folder_exist:
                    flash(
                        "Data folder already exists on your drive. Please check the box if you want to use this folder.")
                    check_accept_folder_first = True

                # check if url already exists with status ready in history table
                url_in_history = check_if_url_in_history(username, url)
                # if url exists > return > ask user if he want to download the data again.
                check_accept_url_in_history_first = False
                if url_in_history and not accept_url_in_history:
                    flash(
                        "Data has already been imported from this url. Please check the box if you want to import again from this url.")
                    check_accept_url_in_history_first = True

                if check_accept_folder_first or check_accept_url_in_history_first:
                    pass
                else:
                    if 'start_download' in request.form:
                        set_canceled(username, False)
                        t = Thread(target=run_import, args=(
                            username, password, complete_folder_path, url))
                        t.start()
                        session['query_status'] = 'started'
                        session['process'] = 'import'
                    else:
                        preview = True
                        # flash("Previewing data import.")
    except Exception as e:
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (7)")
        logger.error(e, exc_info=True)
    return render_template('retrieve.html', **languages[session['lang']],
                            preview=preview,
                            check_accept_folder_first=check_accept_folder_first,
                            check_accept_url_in_history_first=check_accept_url_in_history_first,
                            drive_url=drive_url)


@app.route('/download', methods=['GET', 'POST'])
def download():
    """Will render the download page

    Returns:
        str: html for the download page
    """
    session['temp_hidden_services'] = ['sharekit']
    try:
        username = None
        password = None
        if 'username' in session:
            username = session['username']
        if cloud_service == 'owncloud':
            if 'password' in session:
                password = session['password']
        else:
            if 'access_token' in session:
                password = session['access_token']
        if not make_connection(username=session['username'], password=session['password']):
            flash( languages[session['lang']].get('flash_not_connected', 'Not connected'))
            return redirect('/connect')

        check_accept_url_in_history_first = None
        check_accept_folder_first = None
        preview = False
    except Exception as e:
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (18)")
        logger.error(e, exc_info=True)
    try:
        session['query_status'] = get_query_status(session['username'], session['complete_folder_path'], session['remote'])
    except Exception as e:
        session['query_status'] = None
        logger.info(f"Failed to get query_status:")
        logger.info(e, exc_info=True)

    try:
        if request.method == "POST":

            # getting vars from session
            username = session['username']
            password = session['password']
            status = session['query_status']

            # getting forms data an do some logic
            url = request.form['url']
            accept_folder_exist = False
            if 'accept_folder_exist' in request.form:
                accept_folder_exist = True
            accept_url_in_history = False
            if 'accept_url_in_history' in request.form:
                accept_url_in_history = True
            folder_path = request.form['folder_path']
            folder = request.form['folder']
            if folder_path == "" or folder_path == None or folder_path == "/":
                if folder != "" and folder != None and folder != "/":
                    complete_folder_path = "/" + folder
                else:
                    complete_folder_path = "/"
            else:
                if folder != "" and folder != None and folder != "/":
                    complete_folder_path = folder_path + "/" + folder
                else:
                    complete_folder_path = folder_path
            repo = request.form['selected_repo']

            # storing all variables back into session
            session['repo'] = repo
            session['url'] = url
            # setting the remote session to the url
            session['remote'] = url
            session['accept_folder_exist'] = accept_folder_exist
            session['accept_url_in_history'] = accept_url_in_history
            session['complete_folder_path'] = complete_folder_path
            session['folder_path'] = folder_path
            session['folder'] = folder
            session['permission'] = check_permission(username, password, complete_folder_path)

            if status == None or status == 'ready':
                # check if folder already exists on owncloud
                folder_exists = check_if_folder_exists(
                    username, password, complete_folder_path, url)
                # if folder exists > return > ask user if he wants to add the data to the existing folder or provide different foldder name.
                check_accept_folder_first = False
                if folder_exists and not accept_folder_exist:
                    flash(
                        "Data folder already exists on your drive. Please check the box if you want to use this folder.")
                    check_accept_folder_first = True

                # check if url already exists with status ready in history table
                url_in_history = check_if_url_in_history(username, url)
                # if url exists > return > ask user if he want to download the data again.
                check_accept_url_in_history_first = False
                if url_in_history and not accept_url_in_history:
                    flash(
                        "Data has already been imported from this url. Please check the box if you want to import again from this url.")
                    check_accept_url_in_history_first = True

                if check_accept_folder_first or check_accept_url_in_history_first:
                    pass
                else:
                    if 'start_download' in request.form:
                        set_projectname(username=session['username'],folder=session['complete_folder_path'],url=session['remote'],projectname=session['projectname'])
                        if repo == 'datahugger':
                            set_canceled(username, False)
                            t = Thread(target=run_import, args=(
                                username, password, complete_folder_path, url))
                            t.start()
                        else:
                            repo_user = None
                            if f'{repo}_user' in session:
                                repo_user = session[f'{repo}_user']
                            api_key=session[f'{repo}_access_token']
                            set_canceled(session['username'], False)
                            # get metadata from session
                            metadata = {}
                            if 'private_metadata' in session:
                                metadata = session['private_metadata']
                            elif 'doi_metadata' in session:
                                metadata = session['doi_metadata']
                            # get repo_content from session
                            if 'repo_content' in session:
                                repo_content = session['repo_content']
                            t = Thread(target=run_private_import, args=(
                                        username, password, complete_folder_path, url, repo, api_key, repo_user, metadata, repo_content))
                            t.start()
                        session['query_status'] = 'started'
                        session['process'] = 'import'
                    else:
                        preview = True
                        # flash("Previewing data import.")
    except Exception as e:
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (8)")
        logger.error(e, exc_info=True)
    return render_template('download.html', **languages[session['lang']],
                                preview=preview,
                                check_accept_folder_first=check_accept_folder_first,
                                check_accept_url_in_history_first=check_accept_url_in_history_first,
                                drive_url=drive_url)


@app.route('/cancel_download', methods=['POST'])
def cancel_download():
    try:
        if request.method == "POST":
            preview = request.form['preview']
            check_accept_folder_first = request.form['check_accept_folder_first']
            check_accept_url_in_history_first = request.form['check_accept_url_in_history_first']
            if 'cancel' in request.form:
                status = get_query_status(username=session['username'], folder=session['complete_folder_path'], url=session['remote'])
                if status == 'ready':
                    flash( languages[session['lang']].get('flash_process_ready', 'Process is ready. Will not cancel.') )
                else:
                    set_projectname(username=session['username'], folder=session['complete_folder_path'], url=session['remote'], projectname=session['projectname'])
                    update_history(username=session['username'], folder=session['complete_folder_path'], url=session['remote'], status='canceled by user')
                    set_query_status(session['username'], session['complete_folder_path'], session['remote'], 'ready')
                    session['query_status'] = 'ready'
                    set_canceled(session['username'], True)
                    preview = False
                    check_accept_folder_first=False
                    check_accept_url_in_history_first=False
                    flash( languages[session['lang']].get('flash_import_canceled', 'Import was canceled by user.') )
                    # do some clean up
                    tmp_zip_file = session['complete_folder_path'].split("/")[-1] + ".zip"
                    try:
                        if os.path.isfile(tmp_zip_file):
                            os.remove(tmp_zip_file)
                    except Exception as ee:
                        flash( f"{languages[session['lang']].get('flash_fail_remove_file', 'Failed to remove temporary file')} : {tmp_zip_file} - {ee}")
                    
                    # remove the temp folder
                    tmp_unzipped_path = "/" + session['complete_folder_path'].split("/")[-1]
                    try:
                        if os.path.isdir(tmp_unzipped_path):
                            shutil.rmtree(tmp_unzipped_path)
                    except Exception as e:
                        flash( f"{languages[session['lang']].get('flash_fail_remove_folder', 'Failed to remove temporary folder')} : {tmp_unzipped_path} - {e}")
    except Exception as e:
        preview = False
        check_accept_folder_first = False
        check_accept_url_in_history_first = False
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (9)")
        logger.error(e, exc_info=True)
    return redirect("/download")


@app.route('/cancel_retrieval', methods=['POST'])
def cancel_retrieval():
    try:
        if request.method == "POST":
            preview = request.form['preview']
            check_accept_folder_first = request.form['check_accept_folder_first']
            check_accept_url_in_history_first = request.form['check_accept_url_in_history_first']
            if 'cancel' in request.form:
                status = get_query_status(username=session['username'], folder=session['complete_folder_path'], url=session['remote'])
                if status == 'ready':
                    flash( languages[session['lang']].get('flash_process_ready', 'Process is ready. Will not cancel.') )
                else:
                    set_projectname(username=session['username'], folder=session['complete_folder_path'], url=session['remote'], projectname=session['projectname'])
                    update_history(username=session['username'], folder=session['complete_folder_path'], url=session['remote'], status='canceled by user')
                    set_query_status(session['username'], session['complete_folder_path'], session['remote'], 'ready')
                    session['query_status'] = 'ready'
                    set_canceled(session['username'], True)
                    preview = False
                    check_accept_folder_first=False
                    check_accept_url_in_history_first=False
                    flash( languages[session['lang']].get('flash_import_canceled', 'Import was canceled by user.') )
                    # do some clean up
                    tmp_zip_file = session['complete_folder_path'].split("/")[-1] + ".zip"
                    try:
                        if os.path.isfile(tmp_zip_file):
                            os.remove(tmp_zip_file)
                    except Exception as ee:
                        flash( f"{languages[session['lang']].get('flash_fail_remove_file', 'Failed to remove temporary file')} : {tmp_zip_file} - {ee}")
                    
                    # remove the temp folder
                    tmp_unzipped_path = "/" + session['complete_folder_path'].split("/")[-1]
                    try:
                        if os.path.isdir(tmp_unzipped_path):
                            shutil.rmtree(tmp_unzipped_path)
                    except Exception as e:
                        flash( f"{languages[session['lang']].get('flash_fail_remove_folder', 'Failed to remove temporary folder')} : {tmp_unzipped_path} - {e}")
    except Exception as e:
        preview = None
        check_accept_folder_first = None
        check_accept_url_in_history_first = None
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (10)")
        logger.error(e, exc_info=True)
    return redirect("/retrieve")


@app.route('/cancel_upload', methods=['POST'])
def cancel_upload():
    try:
        if request.method == "POST":
            preview = request.form['preview']
            if 'cancel' in request.form:
                status = get_query_status(username=session['username'], folder=session['complete_folder_path'], url=session['remote'])
                if status == 'ready':
                    flash( languages[session['lang']].get('flash_process_ready', 'Process is ready. Will not cancel.') )
                else:
                    set_projectname(username=session['username'], folder=session['complete_folder_path'], url=session['remote'], projectname=session['projectname'])
                    update_history(username=session['username'], folder=session['complete_folder_path'], url=session['remote'], status='canceled by user')
                    set_query_status(session['username'], session['complete_folder_path'], session['remote'], 'ready')
                    session['query_status'] = 'ready'
                    set_canceled(session['username'], True)
                    preview = False
                    flash( languages[session['lang']].get('flash_export_canceled', 'Export was canceled by user.') )
                    # do some clean up
                    tmp_zip_file = session['complete_folder_path'].split("/")[-1] + ".zip"
                    try:
                        if os.path.isfile(tmp_zip_file):
                            os.remove(tmp_zip_file)
                    except Exception as ee:
                        flash( f"{languages[session['lang']].get('flash_fail_remove_file', 'Failed to remove temporary file')} : {tmp_zip_file} - {ee}")
                    
                    # remove the temp folder
                    tmp_unzipped_path = "/" + session['complete_folder_path'].split("/")[-1]
                    try:
                        if os.path.isdir(tmp_unzipped_path):
                            shutil.rmtree(tmp_unzipped_path)
                    except Exception as e:
                        flash( f"{languages[session['lang']].get('flash_fail_remove_folder', 'Failed to remove temporary folder')} : {tmp_unzipped_path} - {e}")
    except Exception as e:
        preview = None
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (11)")
        logger.error(e, exc_info=True)
    return redirect("/upload")


@app.route('/debug', methods=['GET'])
def debug():
    try:
        session['showall'] = False
        if 'showall' in request.args and request.args.get('showall').lower() == 'true':
            session['showall'] = True
    except Exception as e:
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (12)")
        logger.error(e, exc_info=True)
    try:
        session['showversion'] = False
        if 'showversion' in request.args and request.args.get('showversion').lower() == 'true':
            flash("Release 20241125")
    except Exception as e:
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (13)")
        logger.error(e, exc_info=True)
    try:
        session['showallvars'] = False
        if 'showallvars' in request.args and request.args.get('showallvars').lower() == 'true':
            try:
                flash(all_vars)
            except:
                flash("not showing all_vars")
    except Exception as e:
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (13)")
        logger.error(e, exc_info=True)
    return render_template('connect.html', **languages[session['lang']],drive_url=drive_url)


### BEGIN FILTERS ###

@app.template_filter("convert_size")
def convertsize(size_bytes):
    """will call the convert_size function and return the result

    Args:
        size_bytes (int): the amount of bytes to convert

    Returns:
        str: human readable size
    """
    try:
        return convert_size(size_bytes)
    except Exception as e:
        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (19)")
        logger.error(e, exc_info=True)

### END FILTERS ###

### BEGIN COMPONENTS ###

@app.route('/s3archive', methods=['GET'])
def s3archive():
    """Will render the s3archive component

    Returns:
        str: html for the s3archive component
    """
    # Load available
    return render_template('s3archive.html')

@lru_cache(maxsize=None)
def memoized_dataverses(api_key, api_address, datastation):
    dv = Dataverse(api_key=api_key, api_address=api_address, datastation=datastation)
    return dv.get_all_sub_dataverses(root_dataverse=dataverse_parent_dataverse)


@app.route('/dataverses', methods=['GET'])
def dataverses():
    """Will render the dataverses component

    Returns:
        str: html for the dataverses component
    """
    try:
        if 'datastation' in request.args:
            session['repo'] = 'datastation'
            datastation = Dataverse(api_key=session['datastation_access_token'], api_address=datastation_api_url, datastation=True)
            try:
                dataverses = memoized_dataverses(api_key=session['datastation_access_token'], api_address=datastation_api_url, datastation=True)
            except:
                dataverses = []
            parent_dataverse_info = datastation.get_dataverse_info(datastation_parent_dataverse)
            if parent_dataverse_info not in dataverses:
                dataverses.append(parent_dataverse_info)
        else:
            session['repo'] = 'dataverse'
            dataverse = Dataverse(api_key=session['dataverse_access_token'], api_address=dataverse_api_url)
            try:
                dataverses = memoized_dataverses(api_key=session['dataverse_access_token'], api_address=dataverse_api_url,datastation=False)
            except:
                dataverses = []
            parent_dataverse_info = dataverse.get_dataverse_info(dataverse_parent_dataverse)
            if parent_dataverse_info not in dataverses:
                dataverses.append(parent_dataverse_info)
    except Exception as e: 
        logger.error(f"Failed at dataverses component view:")
        logger.error(e, exc_info=True)
        return render_template('component_load_failure.html', **languages[session['lang']],
                                   drive_url=drive_url,
                                   name="dataverses")
    return render_template('dataverses.html', **languages[session['lang']],
                            drive_url=drive_url,
                            dataverses = dataverses)


@app.route('/irods-subcollections', methods=['GET'])
def irods_subcollections():
    """Will render the irods-subcollections component

    Returns:
        str: html for the irods-subcollections component
    """
    try:
        session['repo'] = 'irods'
        irods = Irods(api_key=session['irods_access_token'], user=session['irods_user'], api_address=irods_api_url)
        home = irods.settings['irods_home']
        try:
            subcollections = []
            collections = irods.get_collection_internal(home)
            for col in collections:
                subcollections += col['subcollections']
                subcollections += [col['path']]
        except:
            subcollections = []
    except Exception as e: 
        logger.error(f"Failed at irods-subcollections component view:")
        logger.error(e, exc_info=True)
        return render_template('component_load_failure.html', **languages[session['lang']],
                                   drive_url=drive_url,
                                   name="irods-subcollections")
    return render_template('irods-subcollections.html', **languages[session['lang']],
                            drive_url=drive_url,
                            subcollections = subcollections)


@app.route('/metadata', methods=['GET'])
def metadata():
    """Will render the metadata component

    Returns:
        str: html for the metadata component
    """
    try:
        disabled = request.args.get('disabled')
        repo = request.args.get('repo')
        session['repo'] = repo

        headers = {}
        if repo == 'datastation' and datastation_basicauth_token:
            headers['X-Authorization'] = datastation_basicauth_token            


        dataverse_subjects = [
            "### Below are some defaults as we could not retrieve the subjects from the service API. ###",
            "Agricultural Sciences",
            "Arts and Humanities",
            "Astronomy and Astrophysics",
            "Business and Management",
            "Chemistry",
            "Computer and Information Science",
            "Earth and Environmental Sciences",
            "Engineering",
            "Law",
            "Mathematical Sciences",
            "Medicine, Health and Life Sciences",
            "Physics",
            "Social Sciences",
            "Other"
        ]
        dansRights_languages = None
        dansRights_personal_data = None
        dansRelationMetadata_audiences = []

        if repo == 'datastation':
            dansRights_languages = [
                "### Below are some defaults as we could not retrieve the languages from the service API. ###",
                "Abkhaz",
                "Afar",
                "Afrikaans",
                "Akan",
                "Albanian",
                "Amharic",
                "Arabic",
                "Aragonese",
                "Armenian",
                "Assamese",
                "Avaric",
                "Avestan",
                "Aymara",
                "Azerbaijani",
                "Bambara",
                "Bashkir",
                "Basque",
                "Belarusian",
                "Bengali, Bangla",
                "Bihari",
                "Bislama",
                "Bosnian",
                "Breton",
                "Bulgarian",
                "Burmese",
                "Catalan,Valencian",
                "Chamorro",
                "Chechen",
                "Chichewa, Chewa, Nyanja",
                "Chinese",
                "Chuvash",
                "Cornish",
                "Corsican",
                "Cree",
                "Croatian",
                "Czech",
                "Danish",
                "Divehi, Dhivehi, Maldivian",
                "Dutch",
                "Dzongkha",
                "English",
                "Esperanto",
                "Estonian",
                "Ewe",
                "Faroese",
                "Fijian",
                "Finnish",
                "French",
                "Fula, Fulah, Pulaar, Pular",
                "Galician",
                "Georgian",
                "German",
                "Greek (modern)",
                "Guaraní",
                "Gujarati",
                "Haitian, Haitian Creole",
                "Hausa",
                "Hebrew (modern)",
                "Herero",
                "Hindi",
                "Hiri Motu",
                "Hungarian",
                "Interlingua",
                "Indonesian",
                "Interlingue",
                "Irish",
                "Igbo",
                "Inupiaq",
                "Ido",
                "Icelandic",
                "Italian",
                "Inuktitut",
                "Japanese",
                "Javanese",
                "Kalaallisut, Greenlandic",
                "Kannada",
                "Kanuri",
                "Kashmiri",
                "Kazakh",
                "Khmer",
                "Kikuyu, Gikuyu",
                "Kinyarwanda",
                "Kyrgyz",
                "Komi",
                "Kongo",
                "Korean",
                "Kurdish",
                "Kwanyama, Kuanyama",
                "Latin",
                "Luxembourgish, Letzeburgesch",
                "Ganda",
                "Limburgish, Limburgan, Limburger",
                "Lingala",
                "Lao",
                "Lithuanian",
                "Luba-Katanga",
                "Latvian",
                "Manx",
                "Macedonian",
                "Malagasy",
                "Malay",
                "Malayalam",
                "Maltese",
                "Māori",
                "Marathi (Marāṭhī)",
                "Marshallese",
                "Mixtepec Mixtec",
                "Mongolian",
                "Nauru",
                "Navajo, Navaho",
                "Northern Ndebele",
                "Nepali",
                "Ndonga",
                "Norwegian Bokmål",
                "Norwegian Nynorsk",
                "Norwegian",
                "Nuosu",
                "Southern Ndebele",
                "Occitan",
                "Ojibwe, Ojibwa",
                "Old Church Slavonic,Church Slavonic,Old Bulgarian",
                "Oromo",
                "Oriya",
                "Ossetian, Ossetic",
                "Panjabi, Punjabi",
                "Pāli",
                "Persian (Farsi)",
                "Polish",
                "Pashto, Pushto",
                "Portuguese",
                "Quechua",
                "Romansh",
                "Kirundi",
                "Romanian",
                "Russian",
                "Sanskrit (Saṁskṛta)",
                "Sardinian",
                "Sindhi",
                "Northern Sami",
                "Samoan",
                "Sango",
                "Serbian",
                "Scottish Gaelic, Gaelic",
                "Shona",
                "Sinhala, Sinhalese",
                "Slovak",
                "Slovene",
                "Somali",
                "Southern Sotho",
                "Spanish, Castilian",
                "Sundanese",
                "Swahili",
                "Swati",
                "Swedish",
                "Tamil",
                "Telugu",
                "Tajik",
                "Thai",
                "Tigrinya",
                "Tibetan Standard, Tibetan, Central",
                "Turkmen",
                "Tagalog",
                "Tswana",
                "Tonga (Tonga Islands)",
                "Turkish",
                "Tsonga",
                "Tatar",
                "Twi",
                "Tahitian",
                "Uyghur, Uighur",
                "Ukrainian",
                "Urdu",
                "Uzbek",
                "Venda",
                "Vietnamese",
                "Volapük",
                "Walloon",
                "Welsh",
                "Wolof",
                "Western Frisian",
                "Xhosa",
                "Yiddish",
                "Yoruba",
                "Zhuang, Chuang",
                "Zulu",
                "Not applicable"
            ]
            dansRights_personal_data = ['### Below are some defaults as we could not retrieve the languages from the service API. ###', 'Yes', 'No', 'Unknown']
            dansRelationMetadata_audiences = get_dans_audiences()

            url = f"{datastation_api_url}/metadatablocks/dansRights"
            logger.error(url)
            response = memoize(requests.get(url, headers=headers))
            logger.error(response)
            if response.status_code == 200:
                dansRights_data = response.json()
                dansRights_languages = dansRights_data['data']['fields']['dansMetadataLanguage']['controlledVocabularyValues']
                dansRights_personal_data = dansRights_data['data']['fields']['dansPersonalDataPresent']['controlledVocabularyValues']
        try:
            dataurl = ''
            if repo == 'dataverse':
                dataurl = f"{dataverse_api_url}/metadatablocks/citation"
            if repo == 'datastation':
                dataurl = f"{datastation_api_url}/metadatablocks/citation"
            if dataurl != '':
                response = memoize(requests.get(dataurl, headers=headers))
                if response.status_code == 200:
                    dataverse_citation_data = response.json()
                    dataverse_subjects = dataverse_citation_data['data']['fields']['subject']['controlledVocabularyValues']
        except:
            pass

        schema_url = "https://yoda.uu.nl/schemas/default-3/metadata.json"
        irods_schema = requests.get(schema_url).json()

        return render_template('metadata.html', **languages[session['lang']],
                                drive_url=drive_url,
                                disabled=disabled,
                                repo=repo,
                                dataverse_subjects=dataverse_subjects,
                                dansRights_languages=dansRights_languages,
                                dansRights_personal_data=dansRights_personal_data,
                                dansRelationMetadata_audiences=dansRelationMetadata_audiences,
                                irods_schema=irods_schema)
    except Exception as e:
        logger.error(e, exc_info=True)
        return render_template('component_load_failure.html', **languages[session['lang']],
                                    drive_url=drive_url,
                                    name="metadata")

@app.route('/check-connection/<repo>', methods=['GET'])
def checkconnection(repo=None):
    """Will render the check_connection component

    Returns:
        str: html for the check_connection component
    """
    try:
        # always get a fresh sharekit token that will last again for 1 hr
        if repo == 'sharekit':
            session['sharekit_access_token'] = get_sharekit_token()
        try:
            if repo == 'datahugger':
                connection_ok = True
            else:
                repo_user = None
                if repo == 'irods' or repo == 'surfs3':
                    repo_user = session[f'{repo}_user']
                api_key = session[f'{repo}_access_token']
                connection_ok = check_connection(repo=repo, api_key=api_key, user=repo_user)
        except Exception as e:
            logger.info(e, exc_info=True)
            connection_ok = None
        return render_template('check_connection.html', **languages[session['lang']],
                                drive_url=drive_url,
                                connection_ok=connection_ok)
    except Exception as e:
        logger.error(e, exc_info=True)
        return render_template('component_load_failure.html', **languages[session['lang']],
                                    drive_url=drive_url,             
                                    name="check connection")
                                    
@app.route('/repo-selection', methods=['GET'])
def repo_selection():
    """Will render the repo_selection component

    Returns:
        str: html for the repo_selection component
    """
    try:
        session['hidden_services'] = hidden_services
        if registered_services == []:
            return render_template('component_load_failure.html', **languages[session['lang']],
                                    drive_url=drive_url,
                                    name="No repositories have been configured")
        available_services = []
        for service in registered_services:
            if service not in hidden_services:
                available_services.append(service)
        if available_services == []:
            session['repo'] = ''
            return render_template('component_load_failure.html', **languages[session['lang']],
                                    drive_url=drive_url,
                                    name="No repositories have been configured")
        # sort the repos here with the active ones first.
        active_services = []
        inactive_services = []
        for service in available_services:
            if f"{service}_access_token" in session and session[f"{service}_access_token"] != "" and session[f"{service}_access_token"] != None:
                active_services.append(service)
            else:
                inactive_services.append(service)
        
        active_services = sorted(['datahugger'] + active_services, key=str.lower)
        inactive_services = sorted(inactive_services, key=str.lower)
        sorted_services =  active_services + inactive_services

        return render_template('repo_selection.html', **languages[session['lang']],
                                drive_url=drive_url,
                                registered_services = sorted_services,
                                all_vars = all_vars)
    except Exception as e:
        logger.error(e, exc_info=True)
        return render_template('component_load_failure.html', **languages[session['lang']],
                                    name="repo selection")

@app.route('/folder-paths/<direction>', methods=['GET'])
def folder_paths(direction=None):
    """Will render the select_folder_path component

    Returns:
        str: html for the select_folder_path component
    """
    try:
        if 'files-folders-selection' in session:
            del session['files-folders-selection']
        if 'username' in session and 'password' in session:
            folder_paths = get_cached_folders(session['username'], session['password'], '/')
            if folder_paths == None or folder_paths == []:
                return render_template('component_load_failure.html', **languages[session['lang']],
                                        name="folder paths")
        else:
            return render_template('component_load_failure.html', **languages[session['lang']],
                                    name="folder paths")
        return render_template('select_folder_path.html', **languages[session['lang']],
                                drive_url=drive_url,
                                folder_paths = folder_paths,
                                direction=direction)
    except Exception as e:
        logger.error(e, exc_info=True)
        return render_template('component_load_failure.html', **languages[session['lang']],
                                    drive_url=drive_url,
                                    name="folder paths")

@app.route('/folder-content/<direction>', methods=['GET'])
def folder_content(direction=None):
    """Will render the folder_content component

    Returns:
        str: html for the folder_content component
    """
    try:
        if 'files-folders-selection' in session and len(session['files-folders-selection']) > 0:
            folder_content = session['files-folders-selection']
            if direction == 'up':
                content_can_be_processed = folder_content_can_be_processed(session['username'], session['password'], session['complete_folder_path'])
            else:
                content_can_be_processed = {'can_be_processed': None, 'total_size': None, 'free_bytes': None}
        elif 'username' in session and 'password' in session and 'complete_folder_path' in session:
            folder_content = get_folder_content(session['username'], session['password'], session['complete_folder_path'])
            if direction == 'up':
                content_can_be_processed = folder_content_can_be_processed(session['username'], session['password'], session['complete_folder_path'])
            else:
                content_can_be_processed = {'can_be_processed': None, 'total_size': None, 'free_bytes': None}
        else:
            return render_template('component_load_failure.html', **languages[session['lang']],
                                        drive_url=drive_url,
                                        name="folder content")
        
        return render_template('folder_content.html', **languages[session['lang']],
                                drive_url=drive_url,
                                folder_content = folder_content,
                                folder_content_can_be_processed = content_can_be_processed,
                                direction = direction)
    except Exception as e:
        logger.error(e)
        return render_template('component_load_failure.html', **languages[session['lang']],
                                    drive_url=drive_url,
                                    name="folder content")



@app.route('/select-folder-content', methods=['POST'])
def select_folder_content():
    """Will render the select_folder_content component

    Returns:
        str: html for the select_folder_content component
    """
    try:
        if "complete_folder_path" in request.values:
            session['complete_folder_path'] = request.values["complete_folder_path"]

        if 'username' in session and 'password' in session and 'complete_folder_path' in session:
            folder_content = get_folder_content(session['username'], session['password'], session['complete_folder_path'], files_only=True)
        else:
            return render_template('component_load_failure.html', **languages[session['lang']],
                                        drive_url=drive_url,
                                        name="select folder content")

        return render_template('select_folder_content.html', **languages[session['lang']],
                                folder_content = folder_content)
    except Exception as e:
        logger.error(e)
        return render_template('component_load_failure.html', **languages[session['lang']],
                                    drive_url=drive_url,
                                    name="select folder content")


@app.route('/repocontent', methods=['GET'])
def repocontent():
    """Will render the repocontent component

    Returns:
        str: html for the repocontent component
    """
    try:
        try:
            url = session['url']
            if 'repo' not in session or session['repo'] == 'datahugger' or session['repo'] == None:
                repo_content = get_files_info(url)
            else:
                repo = session['repo']
                user = None
                if repo == 'figshare':
                    api_key = session['figshare_access_token']
                if repo == 'data4tu':
                    api_key = session['data4tu_access_token']
                if repo == 'zenodo':
                    api_key = session['zenodo_access_token']
                if repo == 'osf':
                    api_key = session['osf_access_token']
                if repo == 'dataverse':
                    api_key = session['dataverse_access_token']
                if repo == 'datastation':
                    api_key = session['datastation_access_token']
                if repo == 'irods':
                    api_key = session['irods_access_token']
                    user = session['irods_user']
                if repo == 'sharekit':
                    api_key = session['sharekit_access_token']
                if repo == 'surfs3':
                    user = session['surfs3_user']
                    api_key = session['surfs3_access_token']
                repo_content = get_repocontent(repo=repo, url=url, api_key=api_key, user=user)
        except Exception as e:
            logger.error(f'failed to get repo content (1): {e}')
            repo_content = [{'message' : f'failed to get repo content'}]
        session['repo_content'] = repo_content
        try:
            if 'repo' in session and session['repo'] != 'surfs3':
                content_fits = repo_content_fits(repo_content, session['username'], session['password'], session['complete_folder_path'])
                content_can_be_processed = repo_content_can_be_processed(repo_content)
                permission = check_permission(session['username'], session['password'], session['complete_folder_path'])
            else:
                content_fits = True
                content_can_be_processed = True
                permission = True
        except Exception as e:
            logger.error("Exception at repocontent")
            logger.error(e)
            content_fits = False
            content_can_be_processed = False
            permission = False
        if content_fits == False:
            flash( languages[session['lang']].get('flash_content_not_fit', 'Content will not fit to your drive.') )
        if content_can_be_processed == False:
            flash( languages[session['lang']].get('flash_not_enough_resources', 'The SRDC does not have enough free resources to process the data.') )
        if permission == False:
            flash( languages[session['lang']].get('flash_no_write_permission', 'You do not have permission to write to the selected location.') )
        return render_template('repocontent.html', **languages[session['lang']],
                                drive_url=drive_url,
                                repo_content = repo_content,
                                repo_content_fits = content_fits,
                                repo_content_can_be_processed = content_can_be_processed)
    except Exception as e:
        logger.error(f'failed to get repo content (2): {e}')
        return render_template('component_load_failure.html', **languages[session['lang']],
                                    name="repo content")

@app.route('/doi-metadata', methods=['GET'])
def doi_metadata():
    """Will render the doi-metadata component

    Returns:
        str: html for the doi-metadata component
    """
    try:
        doi_metadata = {}
        if 'doi_metadata' in session:
            del session['doi_metadata']
        try:
            if session['repo'] != 'surfs3':
                doi_metadata = get_doi_metadata(session['url'])
                doi_metadata = parse_doi_metadata(doi_metadata)
        except Exception as e:
            logger.error(e, exc_info=True)    
        session['doi_metadata'] = doi_metadata
        return render_template('doi_metadata.html', **languages[session['lang']],
                                drive_url=drive_url,
                                doi_metadata = doi_metadata)
    except Exception as e:
        logger.error(e, exc_info=True)
        return render_template('component_load_failure.html', **languages[session['lang']],
                                    drive_url=drive_url,
                                    name="doi metadata")

@app.route('/private-metadata', methods=['GET'])
def private_metadata():
    """Will render the private-metadata component

    Returns:
        str: html for the private-metadata component
    """
    try:
        private_metadata = {}
        if 'private_metadata' in session:
            del session['private_metadata']
        try:
            repo = session['repo']
            url = session['url']
            user = None
            if repo == 'figshare':
                api_key = session['figshare_access_token']
            if repo == 'data4tu':
                api_key = session['data4tu_access_token']
            if repo == 'zenodo':
                api_key = session['zenodo_access_token']
            if repo == 'osf':
                api_key = session['osf_access_token']
            if repo == 'dataverse':
                api_key = session['dataverse_access_token']
            if repo == 'datastation':
                api_key = session['datastation_access_token']
            if repo == 'irods':
                api_key = session['irods_access_token']
                user = session['irods_user']
            if repo == 'sharekit':
                api_key = session['sharekit_access_token']
            if repo == 'surfs3':
                api_key = session['surfs3_access_token']
            private_metadata = get_private_metadata(repo=repo, url=url, api_key=api_key, user=user)
        except Exception as e:
            logger.error(e, exc_info=True)
        session['private_metadata'] = private_metadata
        return render_template('private_metadata.html', **languages[session['lang']],
                                drive_url=drive_url,
                                private_metadata = private_metadata)
    except Exception as e:
        logger.error(e, exc_info=True)
        return render_template('component_load_failure.html', **languages[session['lang']],
                                    name="private metadata")

@app.route('/quota-text', methods=['GET'])
def quote_text():
    """Will render the quota-text component

    Returns:
        str: html for the quota-text component
    """
    try:
        try:
            quota_text = get_quota_text(session['username'], session['password'], session['complete_folder_path'])
        except Exception as e:
            logger.error(e, exc_info=True)
            quota_text = ""
        return render_template('quota_text.html', **languages[session['lang']], quota_text = quota_text)
    except Exception as e:
        logger.error(e, exc_info=True)
        return render_template('component_load_failure.html', **languages[session['lang']],
                                    drive_url=drive_url,
                                    name="quote text")

@app.route('/status', methods=['GET'])
def status():
    """Will render the status component

    Returns:
        str: html for the status component
    """
    try:
        query_status_history = {}
        progress = 0
        project_id = None
        project_url = None
        try:
            username = session['username']
            complete_folder_path = session['complete_folder_path']
            remote = session['remote']
            try:
                query_status_history = get_query_status_history(username, complete_folder_path, remote)
            except Exception as e:
                logger.error(e, exc_info=True)
                query_status_history = {}     
            
            # check where we are in the process and based on that send a percentage to the status.html
            # in the status.html add a progress bar showing the percentage.
            def get_progress(n):
                """check where we are in the process and based on that return a number

                Args:
                    n (int): index of the status to use for the progress check

                Returns:
                    int: the progress percentage
                """

                progress = None

                ### general progress ###
                if query_status_history[n].status == 'started':
                    progress = 1
                elif query_status_history[n].status.find('uploaded file') != -1:
                    progress = 60
                    try:
                        filecount =  re.findall(r'\d+', query_status_history[n].status)
                        additional_progress = int(25 * (int(filecount[0]) / int(filecount[1]) ))
                        if additional_progress <= 25:
                            progress += additional_progress
                    except Exception as e:
                        logger.error(e)
                elif query_status_history[n].status.find('failed to upload file') != -1:
                    logger.error('failed to upload file')
                    progress = 60
                    try:
                        filecount =  re.findall(r'\d+', query_status_history[n].status)
                        additional_progress = int(25 * (int(filecount[0]) / int(filecount[1]) ))
                        if additional_progress <= 25:
                            progress += additional_progress
                    except Exception as e:
                        logger.error(e)
                elif query_status_history[n].status == 'ready':
                    progress = 100
                elif query_status_history[n].status.find('Completed with issues') != -1:
                    progress = 100
                elif query_status_history[n].status.find('Success!') != -1:
                    progress = 100
                ### end general progress ###

                ### Upload specific progress ###
                elif query_status_history[n].status.find('start downloading project as zipfile') != -1:
                    progress = 5
                elif query_status_history[n].status.find('done downloading project as zipfile') != -1:
                    progress = 10
                elif query_status_history[n].status.find('unzipping the zipfile') != -1:
                    progress = 15
                elif query_status_history[n].status.find('removing the zipfile') != -1:
                    progress = 20
                elif query_status_history[n].status.find("creating ro-crate file") != -1:
                    progress = 25
                elif query_status_history[n].status.find('upload finished') != -1:
                    progress = 85
                elif query_status_history[n].status.find('removing temporary files') != -1:
                    progress = 95
                ### end upload specific progress ###

                ### opendata download specific ###
                elif query_status_history[n].status.find('start data retrieval') != -1:
                    progress = 5
                ### end opendata download specific ###

                ### download specific progress ###
                elif query_status_history[n].status.find("getting file data") != -1:
                    progress = 20
                elif query_status_history[n].status.find("getting file data done") != -1:
                    progress = 30
                elif query_status_history[n].status.find("hecksum") != -1:
                    progress = 40
                elif query_status_history[n].status.find("start pushing dataset to storage") != -1:
                    progress = 40
                elif query_status_history[n].status.find('Removing temporary data') != -1:
                    progress = 95
                ### end download specific progress ###

                return progress
            
            progress = None
            for n in range(0,1):
                try:
                    progress = get_progress(n)
                    if progress and type(progress)=='int':
                        break
                except Exception as e:
                    progress = 0
                    logger.error(e)

            project_url = None

            try:
                project_id = get_project_id(username=session['username'], folder=session['complete_folder_path'], url=session['remote'])
            except Exception as e:
                logger.error(e, exc_info=True)
                project_id = None

            if project_id:
                if session['repo'] == 'dataverse':
                    project_url = f"{dataverse_website}/dataset.xhtml?persistentId={project_id}"
                elif session['repo'] == 'datastation':
                    project_url = f"{datastation_website}/dataset.xhtml?persistentId={project_id}"
                elif session['repo'] == 'figshare':
                    project_url = f"{figshare_website}/account/items/{project_id}/edit"
                elif session['repo'] == 'zenodo':
                    project_url = f"{zenodo_website}/uploads/{project_id}"
                elif session['repo'] == 'osf':
                    project_url = f"{osf_website}/{project_id}"
                elif session['repo'] == 'data4tu':
                    project_url = f"{data4tu_website}/my/datasets/{project_id}/edit"
                elif session['repo'] == 'irods':
                    project_url = f"{irods_website}"
                elif session['repo'] == 'sharekit':
                    project_url = f"{sharekit_website}"
        except Exception as e:
            logger.error(e, exc_info=True)
        return render_template('status.html', **languages[session['lang']],
                                drive_url=drive_url,
                                query_status_history = query_status_history,
                                progress = progress,
                                project_id=project_id,
                                project_url=project_url)
    except Exception as e:
        logger.error(e, exc_info=True)
        return render_template('component_load_failure.html', **languages[session['lang']],
                                    drive_url=drive_url,
                                    name="status")


@app.route('/metavox', methods=['GET'])
def metavox(folder=None):
    """Will render the metavox component

    Returns:
        str: html for the metavox component
    """
    try:
        metavoxdata = []
        metavoxfiles = []
        metavoxfilesdata = {}
        folder = None
        try:
            if 'folder' in request.args:
                folder = request.args['folder']
                mount_point = folder[1:]
                team_folders = metavox_get_team_folders(user=session['username'],token=session['password'])
                for groupfolder in team_folders['ocs']['data']:
                    if groupfolder['mount_point'] == mount_point:
                        groupfolderId = groupfolder['id']
                        metavoxdata = metavox_get_folder_meatadata(user=session['username'],token=session['password'], groupfolderId=groupfolderId)['ocs']['data']
                        metavoxfiles = get_folder_content_props(username=session['username'], password=session['password'], folder=folder, properties=['nc:fileid'])
                        for file_path in metavoxfiles:
                            fileId = metavox_get_file_id(user=session['username'], token=session['password'], folder=file_path['path'])
                            data = metavox_get_file_metadata(user=session['username'], token=session['password'], groupfolderId=groupfolderId, fileId=fileId)['ocs']['data']
                            if data != []:
                                metavoxfilesdata[file_path['path']]= data
        except Exception as e:
            logger.error(e)
        return render_template('metavox.html', **languages[session['lang']], metavoxdata = metavoxdata, folder=folder, metavoxfilesdata=metavoxfilesdata)
    except Exception as e:
        logger.error(e, exc_info=True)
        return render_template('component_load_failure.html', **languages[session['lang']],
                                    drive_url=drive_url,
                                    name="metavox") 

# @app.route("/logs", methods=('GET', 'POST'))
# def logs():
#     loglines = []
#     count = None
#     logtype = None
#     if 'count' in request.args:
#         count = int(request.args['count'])
#     if 'type' in request.args:
#         logtype = request.args['type']
#     try:
#         with open('flask_app.log', 'r') as file:
#             loglines = file.readlines()
#     except:
#         flash("No logs file is found. A new one will be created.")
#         with open('flask_app.log', 'w') as file:
#             file.write("")
#     if logtype:
#         lines = []
#         for logline in loglines:
#             if logline.find(logtype.upper()) != -1:
#                 lines.append(logline)
#         if count:
#             lines = lines[-count:]
#         return render_template('logs.html', loglines=lines)        
#     if count:
#         loglines = loglines[-count:]

#     return render_template('logs.html', loglines=loglines)


### END COMPONENTS ###


### BEGIN SERVICE CONNECTIONS ###

@app.route('/persistent-connection', methods=['GET'])
def persistent_connection(persist=None):
    session['persist'] = True
    session['persistent_connection'] = False
    try:
        if cloud_service.lower() == 'nextcloud':
            if 'poll_info' in session:
                result = get_webdav_token_nc(session['poll_info']['poll_endpoint'])
                if result:
                    password = result['appPassword']
                    if make_connection(session['username'], password):
                        session['password'] = password
                        session['persistent_connection'] = True
                        session['persist'] = False
                        # return render_template('connect.html', **languages[session['lang']])
                    else:
                        flash( languages[session['lang']].get('flash_fail_persist', 'Failed to make connection to research drive persistent.') )
            else:
                session['poll_info'] = get_webdav_poll_info_nc(session['access_token'])
    except Exception as e:
        logger.error(e)
    return render_template('persistent-connection.html', **languages[session['lang']],
                                drive_url=drive_url )

@app.route('/login/<service>', methods=['GET'])
@app.route('/login', methods=['GET'])
def login(service=None):
    """Will login to a service using Oauth

    Args:
        service (str, optional): the service name. Defaults to None.

    Returns:
        obj: Oauth object
    """
    try:
        if service == None:
            redirect_uri = f'{srdc_url}/authorize'
            return oauth.rdrive.authorize_redirect(redirect_uri)
        elif service in registered_services:
            redirect_uri = f'{srdc_url}/authorize/{service}'
            return eval(f"oauth.{service}.authorize_redirect(redirect_uri)")
    except Exception as e:
        logger.error(e, exc_info=True)

@app.route('/authorize/<service>', methods=['GET'])
@app.route('/authorize', methods=['GET'])
def authorize(service=None):
    """Will authorize a service and store the access_token.

    Args:
        service (str, optional): the service name. Defaults to None.

    Returns:
        redirect: will redirect to the embed url
    """
    try:
        if service == None:
            try:
                oauth.rdrive.authorize_access_token()
                oauth_token = oauth.rdrive.token
                access_token = oauth_token['access_token']
                refresh_token = oauth_token['refresh_token']
                if cloud_service.lower() == "owncloud":
                    username = oauth_token['user_id']
                    password = get_webdav_token(access_token, username)
                elif cloud_service.lower() == "nextcloud":
                    username = oauth_token['user_id']
                    password = access_token
                else:
                    username = None
                    password = access_token
                if username is None:
                    flash( languages[session['lang']].get('flash_fail_userid', 'failed to get user_id') )
                if password is None:
                    flash( languages[session['lang']].get('flash_fail_access_token', 'failed to get access_token') )
                if username is not None and password is not None:
                    if make_connection(username, password):
                        session['cloud_token'] = oauth_token
                        session['username'] = username
                        session['password'] = password
                        session['access_token'] = access_token
                        session['refresh_token'] = refresh_token
                        session['connected'] = True
                        session['failed'] = False
                        session.pop('_flashes', None)
                        flash( f"research drive {languages[session['lang']].get('flash_connected', 'connected')}" )
                        flash( languages[session['lang']].get('flash_now_connect', 'now <a href="/start?homeshow=True">get started</a> and connect to one ore more repositories') )
                        # get_cached_folders async
                        t = Thread(target = get_cached_folders,
                           args = (session['username'], session['password'], '/'))
                        t.start()
                    else:
                        flash(f"{languages[session['lang']].get('flash_something_wrong', 'Something went wrong')} (1b)")
                        flash(f"{languages[session['lang']].get('flash_failed_connect', 'failed to connect')} (1)")
                        session['failed'] = True
                else:
                    flash(f"{languages[session['lang']].get('flash_failed_connect', 'failed to connect')} (2)")
                    session['failed'] = True
            except Exception as e:
                flash(f"{languages[session['lang']].get('flash_failed_connect', 'failed to connect')} (3)")
                flash(str(e))
                session['failed'] = True
            # return home
            return redirect("/")
        elif service in registered_services:
            try:
                eval(f"oauth.{service}.authorize_access_token()")
                oauth_token = eval(f"oauth.{service}.token")

                access_token = oauth_token['access_token']
                session[f'{service}_access_token'] = access_token
                flash(f"{service} {languages[session['lang']].get('flash_connected', 'connected')}")                
            except Exception as e:
                logger.error(f"failed at connecting {service}: {e}")
                flash( languages[session['lang']].get('flash_failed_connect', 'failed to connect') )
    except Exception as e:
        logger.error(e, exc_info=True)
    return render_template("close.html", drive_url=drive_url)

@app.route('/refresh-token', methods=['GET'])
def refresh_token():
    """Will render the refresh token component

    Returns:
        str: html for the refresh token component
    """
    try:
        new_token = old_token = session['access_token']
        if session['password'] == None or session['password'] == "" or session['password'] == session['access_token']:
            # only refresh the token when it is about to expire
            if time() + 600 > session['cloud_token']['expires_at']:
                token_data = refresh_cloud_token(session['cloud_token'])
                if token_data:
                    session['cloud_token'] = token_data
                    new_token = session['password'] = session['access_token'] = token_data['access_token']
                    session['refresh_token'] = token_data['refresh_token']
    except Exception as e:
        logger.error(f"Failed at refresh token component view:")
        logger.error(e, exc_info=True)
        return render_template('component_load_failure.html', **languages[session['lang']],
                                drive_url=drive_url,
                                name=str(e))
    return render_template('refresh-token.html', **languages[session['lang']],
                            drive_url=drive_url,
                            old_token=old_token,
                            new_token=new_token)

### END SERVICE CONNECTIONS ###

### BEGIN CUSTOM TEMPLATE FILTERS ###

@app.template_filter()
def translate(text):
    if 'lang' in session:
        lang = session['lang']
    else:
        lang = 'EN'
    # TODO implement auto translation maybe using libretranslate
    return text


### END CUSTOM TEMPLATE FILTERS ###