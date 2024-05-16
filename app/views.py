from app.models import app, db, History
from app.connections import oauth, registered_services, oauth_services, token_based_services
from app.utils import run_import, make_connection, get_webdav_token
from app.utils import get_user_info, set_query_status, set_canceled
from app.utils import check_if_folder_exists, check_if_url_in_history, get_query_status_history, get_query_status, get_status_from_history
from app.utils import get_folders, get_folder_content, get_files_info, check_checksums, update_history, push_data, get_raw_folders
from app.utils import get_quota_text, repo_content_fits, get_doi_metadata, parse_doi_metadata, convert_size, check_permission
from app.repos import run_export, check_connection, get_private_metadata, get_repocontent
from threading import Thread, Event
from flask import request, session, flash, render_template, url_for, redirect
from app.globalvars import *
import logging
import math
import os
import requests
import json
from sqlalchemy import and_
from app.repos import run_private_import
import whois

logger = logging.getLogger()

@app.route('/')
def home():
    """Will render the home page

    Returns:
        str: html for the home page
    """
    try:
        data = session
        data['srdc_url'] = srdc_url
        data['hidden_services'] = hidden_services
        data['cloud_service'] = cloud_service
    except Exception as e:
        flash("something went wrong (1)")
        logger.error(e, exc_info=True)
    return render_template('home.html', data=data)


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
        flash("something went wrong (2)")
        logger.error(e, exc_info=True)
    return render_template('faq.html', data=session, faqitems=faqitems)


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
        flash("something went wrong (3)")
        logger.error(e, exc_info=True)
    return render_template('messages.html', data=session, messages=messages)


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
        if 'username' in session:
            username = session['username']
            if id:
                hist_of_id = History.query.filter_by(id=id).one()
                folder = hist_of_id.folder
                url = hist_of_id.url
                history = History.query.filter(
                    and_(
                        History.username == username,
                        History.folder == folder,
                        History.url == url
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
                    if [item.folder, item.url] != latest_folder_url:
                        tmp_hist.append(item)
                        latest_folder_url = [item.folder, item.url]
                history = tmp_hist
    except Exception as e:
        flash("something went wrong (4)")
        logger.error(e, exc_info=True)
    return render_template('history.html', data=session, history=history, drive_url=drive_url)


@app.route('/connect', methods=('GET', 'POST'))
def connect():
    """Will render the connect page

    Returns:
        str: html for the connect page
    """
    session['hidden_services'] = hidden_services
    if 'username' in session and 'password' in session and make_connection(session['username'], session['password']):
        session['connected'] = True
    else:
        session['connected'] = False
    try:
        if request.method == "POST":
            if 'disconnect' in request.form:
                session.clear()
                session.pop('_flashes', None)
                flash('research drive disconnected')
            elif 'username' in request.form and 'password' in request.form:
                # test the connection
                username = request.form['username']
                password = request.form['password']
                if make_connection(username, password):
                    session['username'] = username
                    session['password'] = password
                    session['connected'] = True
                    session.pop('_flashes', None)
                    flash('connected')
                else:
                    flash('failed to connect')

            ### BEGIN Oauth based service connections ###
            if 'figshare_disconnect' in request.form:
                if 'figshare_access_token' in session:
                    del session['figshare_access_token']
                    flash('figshare disconnected')
            if 'zenodo_disconnect' in request.form:
                if 'zenodo_access_token' in session:
                    del session['zenodo_access_token']
                    flash('zenodo disconnected')
            if 'osf_disconnect' in request.form:
                if 'osf_access_token' in session:
                    del session['osf_access_token']
                    flash('osf disconnected')
            ### END Oauth based service connections ###

            ### BEGIN token based service connections ###
            if 'figshare_disconnect' in request.form:
                if 'figshare_access_token' in session:
                    del session['figshare_access_token']
                    flash('figshare disconnected')
            elif 'figshare_access_token' in request.form:
                if check_connection(repo='figshare', api_key=request.form['figshare_access_token']):
                    session['figshare_access_token'] = request.form['figshare_access_token']
                    flash('figshare connected')
                else:
                    flash('could not connect to figshare')
            if 'zenodo_disconnect' in request.form:
                if 'zenodo_access_token' in session:
                    del session['zenodo_access_token']
                    flash('zenodo disconnected')
            elif 'zenodo_access_token' in request.form:
                if check_connection(repo='zenodo', api_key=request.form['zenodo_access_token']):
                    session['zenodo_access_token'] = request.form['zenodo_access_token']
                    flash('zenodo connected')
                else:
                    flash('could not connect to zenodo')
            if 'osf_disconnect' in request.form:
                if 'osf_access_token' in session:
                    del session['osf_access_token']
                    flash('osf disconnected')
            elif 'osf_access_token' in request.form:
                if check_connection(repo='osf', api_key=request.form['osf_access_token']):
                    session['osf_access_token'] = request.form['osf_access_token']
                    flash('osf connected')
                else:
                    flash('could not connect to osf')
            if 'dataverse_disconnect' in request.form:
                if 'dataverse_access_token' in session:
                    del session['dataverse_access_token']
                    flash('dataverse disconnected')
            elif 'dataverse_access_token' in request.form:
                if check_connection(repo='dataverse', api_key=request.form['dataverse_access_token']):
                    session['dataverse_access_token'] = request.form['dataverse_access_token']
                    flash('dataverse connected')
                else:
                    flash('could not connect to dataverse')
            if 'irods_disconnect' in request.form:
                if 'irods_access_token' in session:
                    del session['irods_access_token']
                    del session['irods_user']
                    flash('irods disconnected')
            elif 'irods_access_token' in request.form and 'irods_user' in request.form:
                if check_connection(repo='irods', api_key=request.form['irods_access_token'], user=request.form['irods_user']):
                    session['irods_user'] = request.form['irods_user']
                    session['irods_access_token'] = request.form['irods_access_token']
                    flash('irods connected')
                else:
                    flash('could not connect to irods')
            if 'sharekit_disconnect' in request.form:
                if 'sharekit_access_token' in session:
                    del session['sharekit_access_token']
                    flash('sharekit disconnected')
            elif 'sharekit_access_token' in request.form:
                if check_connection(repo='sharekit', api_key=request.form['sharekit_access_token']):
                    session['sharekit_access_token'] = request.form['sharekit_access_token']
                    flash('sharekit connected')
                else:
                    flash('could not connect to sharekit')
            ### END token based service connections ###
    except Exception as e:
        flash("something went wrong (5)")
        logger.error(e, exc_info=True)
    return render_template('connect.html',
                            data=session,
                            drive_url=drive_url,
                            oauth_services = oauth_services,
                            token_based_services = token_based_services,
                            all_vars = all_vars)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """Will render the upload page

    Returns:
        str: html for the upload page
    """
    preview = None
    repo = None
    session['repo'] = None
    metadata = {}
    if 'metadata' not in session:
        session['metadata'] = {}

    try:
        session['query_status'] = get_query_status(session['username'], session['complete_folder_path'], session['remote'])
    except Exception as e:
        session['query_status'] = None
        logger.error(f"Failed to get query_status: {e}")

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

                # get the metadata fields
                metadata = session['metadata']

                # validate the email domain here
                if email:
                    domain = email.split("@")[-1]
                    w = whois.whois(domain)
                    if w['domain_name'] == None:
                        flash(f"email domain {domain} name does not exist")
                        return render_template('upload.html',
                                                data=session,
                                                preview=preview,
                                                drive_url=drive_url)

                if 'preview' in request.form:
                    preview = True

                    if 'selected_repo' in request.form and request.form['selected_repo']!='none':
                        # get the repo
                        session['repo'] = request.form['selected_repo']

                        # needed for getting the right statusses remote can either be the url or repo
                        session['remote'] = request.form['selected_repo']
                    else:
                        flash('Please select a repository.')                
                    # get the folder and set it to session folder
                    session['folder_path'] = request.form['folder_path']
                    session['complete_folder_path'] = request.form['folder_path']
                    # will be loaded async based on session folder

                if 'start_upload' in request.form:
                    
                    username = session['username']
                    password = session['password']
                    complete_folder_path = request.form['folder_path']
                    repo = request.form['selected_repo']
                    repo_user = None
                    if repo == "irods":
                        repo_user = session['irods_user']
                    api_key=session[f'{repo}_access_token']
                    use_zip=False
                    if 'use_zip' in request.form:
                        use_zip=True
                    # setting the canceled status to false for this user
                    set_canceled(username, False)

                    # setting a tmp folder path name that does not interfere with other projects or the SRDC code itself.
                    tmp_folder_path_name = complete_folder_path.split("/")[-1]
                    if tmp_folder_path_name in ['', 'app', 'local', 'instance', 'migrations', 'surf-rdc-chart', 'tests']:
                        tmp_folder_path_name = tmp_folder_path_name + "_" + metadata['title'].replace(" ", "_")
                    
                    t = Thread(target=run_export, args=(
                        username, password, complete_folder_path, tmp_folder_path_name, repo, repo_user, api_key, metadata, use_zip))
                    t.start()
                    session['query_status'] = 'started'
                else:
                    preview = True
    except Exception as e:
        flash("something went wrong (6)")
        logger.error(e, exc_info=True)    
    return render_template('upload.html',
                            data=session,
                            preview=preview,
                            drive_url=drive_url)


@app.route('/retrieve', methods=['GET', 'POST'])
def retrieve():
    """Will render the retrieve page

    Returns:
        str: html for the retrieve page
    """
    check_accept_url_in_history_first = None
    check_accept_folder_first = None
    preview = False
    
    session['repo'] = None

    try:
        session['query_status'] = get_query_status(session['username'], session['complete_folder_path'], session['remote'])
    except Exception as e:
        session['query_status'] = None
        logger.error(f"Failed to get query_status: {e}")

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
            session['folder'] = folder
            if folder_path == "" or folder_path == None:
                complete_folder_path = "/" + folder
            elif folder_path == "/":
                complete_folder_path = folder
            else:
                complete_folder_path = folder_path + "/" + folder
            
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
                        "Data has already been downloaded from this url. Please check the box if you want to download again from this url.")
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
                    else:
                        preview = True
                        flash("Previewing data download.")
    except Exception as e:
        flash("something went wrong (7)")
        logger.error(e, exc_info=True)
    return render_template('retrieve.html',
                            data=session,
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
    check_accept_url_in_history_first = None
    check_accept_folder_first = None
    preview = False
    session['repo'] = None

    try:
        session['query_status'] = get_query_status(session['username'], session['complete_folder_path'], session['remote'])
    except Exception as e:
        session['query_status'] = None
        logger.error(f"Failed to get query_status: {e}")

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
            if folder_path == "" or folder_path == None:
                complete_folder_path = "/" + folder
            elif folder_path == "/":
                complete_folder_path = folder
            else:
                complete_folder_path = folder_path + "/" + folder
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
                        "Data has already been downloaded from this url. Please check the box if you want to download again from this url.")
                    check_accept_url_in_history_first = True

                if check_accept_folder_first or check_accept_url_in_history_first:
                    pass
                else:
                    if 'start_download' in request.form:
                        repo_user = None
                        if f'{repo}_user' in session:
                            repo_user = session[f'{repo}_user']
                        api_key=session[f'{repo}_access_token']
                        set_canceled(session['username'], False)
                        t = Thread(target=run_private_import, args=(
                                    username, password, complete_folder_path, url, repo, api_key, repo_user))
                        t.start()
                        session['query_status'] = 'started'
                    else:
                        preview = True
                        flash("Previewing data download.")
    except Exception as e:
        flash("something went wrong (8)")
        logger.error(e, exc_info=True)
    return render_template('download.html',
                            data=session,
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
                    flash('Process is ready. Will not cancel.')
                else:
                    update_history(username=session['username'], folder=session['complete_folder_path'], url=session['remote'], status='canceled by user')
                    set_query_status(session['username'], session['complete_folder_path'], session['remote'], 'ready')
                    session['query_status'] = 'ready'
                    set_canceled(session['username'], True)
                    preview = False
                    check_accept_folder_first=False
                    check_accept_url_in_history_first=False 
                    flash("Download was canceled by user.")
    except Exception as e:
        preview = False
        check_accept_folder_first = False
        check_accept_url_in_history_first = False
        flash("something went wrong (9)")
        logger.error(e, exc_info=True)
    return render_template('download.html',
                            data=session, 
                            preview=preview,
                            check_accept_folder_first=check_accept_folder_first,
                            check_accept_url_in_history_first=check_accept_url_in_history_first,
                            drive_url=drive_url)


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
                    flash('Process is ready. Will not cancel.')
                else:
                    update_history(username=session['username'], folder=session['complete_folder_path'], url=session['remote'], status='canceled by user')
                    set_query_status(session['username'], session['complete_folder_path'], session['remote'], 'ready')
                    session['query_status'] = 'ready'
                    set_canceled(session['username'], True)
                    preview = False
                    check_accept_folder_first=False
                    check_accept_url_in_history_first=False 
                    flash("Download was canceled by user.")
    except Exception as e:
        preview = None
        check_accept_folder_first = None
        check_accept_url_in_history_first = None
        flash("something went wrong (10)")
        logger.error(e, exc_info=True)
    return render_template('retrieve.html',
                            data=session,
                            preview=preview,
                            check_accept_folder_first=check_accept_folder_first,
                            check_accept_url_in_history_first=check_accept_url_in_history_first,
                            drive_url=drive_url)

@app.route('/cancel_upload', methods=['POST'])
def cancel_upload():
    try:
        if request.method == "POST":
            preview = request.form['preview']
            if 'cancel' in request.form:
                status = get_query_status(username=session['username'], folder=session['complete_folder_path'], url=session['remote'])
                if status == 'ready':
                    flash('Process is ready. Will not cancel.')
                else:
                    update_history(username=session['username'], folder=session['complete_folder_path'], url=session['remote'], status='canceled by user')
                    set_query_status(session['username'], session['complete_folder_path'], session['remote'], 'ready')
                    session['query_status'] = 'ready'
                    set_canceled(session['username'], True)
                    preview = False
                    flash("Upload was canceled by user.")
    except Exception as e:
        preview = None
        flash("something went wrong (11)")
        logger.error(e, exc_info=True)
    return render_template('upload.html',
                            data=session,
                            preview=preview,
                            drive_url=drive_url)


@app.route('/debug', methods=['GET'])
def debug():
    try:
        session['showall'] = False
        if request.args.get('showall').lower() == 'true':
            session['showall'] = True
    except Exception as e:
        flash("something went wrong (12)")
        logger.error(e, exc_info=True)
    return render_template('home.html',
                            data=session)


### BEGIN FILTERS ###

@app.template_filter("convert_size")
def convertsize(size_bytes):
    """will call the convert_size function and return the result

    Args:
        size_bytes (int): the amount of bytes to convert

    Returns:
        str: human readable size
    """
    return convert_size(size_bytes)

### END FILTERS ###

### BEGIN COMPONENTS ###

@app.route('/metadata', methods=['GET'])
def metadata():
    """Will render the metadata component

    Returns:
        str: html for the metadata component
    """
    disabled = request.args.get('disabled')
    repo = request.args.get('repo')
    session['repo'] = repo
    return render_template('metadata.html',
                            data=session,
                            disabled=disabled,
                            repo=repo)

@app.route('/check-connection', methods=['GET'])
def checkconnection():
    """Will render the check_connection component

    Returns:
        str: html for the check_connection component
    """  
    try:
        repo = session['repo']
        repo_user = None
        if repo == 'irods':
            repo_user = session[f'{repo}_user']
        api_key = session[f'{repo}_access_token']
        connection_ok = check_connection(repo=repo, api_key=api_key, user=repo_user)
    except:
        session['repo'] = 'None'
        connection_ok = None
    return render_template('check_connection.html',
                            data=session,
                            connection_ok=connection_ok)

@app.route('/repo-selection', methods=['GET'])
def repo_selection():
    """Will render the repo_selection component

    Returns:
        str: html for the repo_selection component
    """   
    session['hidden_services'] = hidden_services
    return render_template('repo_selection.html',
                            data=session,
                            registered_services = registered_services,
                            all_vars = all_vars)


@app.route('/folder-paths', methods=['GET'])
def folder_paths():
    """Will render the select_folder_path component

    Returns:
        str: html for the select_folder_path component
    """
    if 'username' in session and 'password' in session:
        folder_paths = get_folders(username = session['username'], password = session['password'], folder = '/')
    else:
        folder_paths = []
    return render_template('select_folder_path.html',
                            data=session,
                            folder_paths = folder_paths)


@app.route('/folder-content', methods=['GET'])
def folder_content():
    """Will render the folder_content component

    Returns:
        str: html for the folder_content component
    """
    if 'username' in session and 'password' in session and 'complete_folder_path' in session:
        folder_content = get_folder_content(session['username'], session['password'], session['complete_folder_path'])
    else:
        folder_content = []
    return render_template('folder_content.html',
                            data=session,
                            folder_content = folder_content)


@app.route('/folder-content-new', methods=['GET'])
def folder_content_new():
    """Will render the folder_content component

    Returns:
        str: html for the folder_content component
    """
    if 'username' in session and 'password' in session and 'complete_folder_path' in session:
        logger.error(session['complete_folder_path'])
        folder_content = get_raw_folders(session['username'], session['password'], session['complete_folder_path'])
    else:
        folder_content = []
    return render_template('folder_content_new.html',
                            data=session,
                            folder_content = folder_content)


@app.route('/repocontent', methods=['GET'])
def repocontent():
    """Will render the repocontent component

    Returns:
        str: html for the repocontent component
    """
    # currently just getting info from data hugger
    try:
        url = session['url']
        if 'repo' not in session or session['repo'] == None:
            repo_content = get_files_info(url)
        else:
            repo = session['repo']
            user = None
            if repo == 'figshare':
                api_key = session['figshare_access_token']
            if repo == 'zenodo':
                api_key = session['zenodo_access_token']
            if repo == 'osf':
                api_key = session['osf_access_token']
            if repo == 'dataverse':
                api_key = session['dataverse_access_token']
            if repo == 'irods':
                api_key = session['irods_access_token']
                user = session['irods_user']
            if repo == 'sharekit':
                api_key = session['sharekit_access_token']
            repo_content = get_repocontent(repo=repo, url=url, api_key=api_key, user=user)
    except Exception as e:
        logger.error(f'failed to get repo content: {e}')
        repo_content = [{'message' : f'failed to get repo content'}]
    try:
        quota_text = get_quota_text(session['username'], session['password'], session['complete_folder_path'])
        content_fits = repo_content_fits(repo_content, quota_text)
        # permission = check_permission(session['username'], session['password'], session['complete_folder_path'])
    except:
        content_fits = None
    return render_template('repocontent.html',
                            data=session,
                            repo_content = repo_content,
                            repo_content_fits = content_fits)
                            # permisssion = permission)


@app.route('/doi-metadata', methods=['GET'])
def doi_metadata():
    """Will render the doi-metadata component

    Returns:
        str: html for the doi-metadata component
    """
    try:
        doi_metadata = get_doi_metadata(session['url'])
        doi_metadata = parse_doi_metadata(doi_metadata)
    except:
        doi_metadata = {}
    return render_template('doi_metadata.html',
                            data=session,
                            doi_metadata = doi_metadata)

@app.route('/private-metadata', methods=['GET'])
def private_metadata():
    """Will render the private-metadata component

    Returns:
        str: html for the private-metadata component
    """
    try:
        repo = session['repo']
        url = session['url']
        user = None
        if repo == 'figshare':
            api_key = session['figshare_access_token']
        if repo == 'zenodo':
            api_key = session['zenodo_access_token']
        if repo == 'osf':
            api_key = session['osf_access_token']
        if repo == 'dataverse':
            api_key = session['dataverse_access_token']
        if repo == 'irods':
            api_key = session['irods_access_token']
            user = session['irods_user']
        if repo == 'sharekit':
            api_key = session['sharekit_access_token']
        private_metadata = get_private_metadata(repo=repo, url=url, api_key=api_key, user=user)
    except:
        private_metadata = {}
    return render_template('private_metadata.html',
                            data=session,
                            private_metadata = private_metadata)


@app.route('/quota-text', methods=['GET'])
def quote_text():
    """Will render the quota-text component

    Returns:
        str: html for the quota-text component
    """
    try:
        quota_text = get_quota_text(session['username'], session['password'], session['complete_folder_path'])
    except:
        quota_text = ""
    return render_template('quota_text.html', quota_text = quota_text)


@app.route('/status', methods=['GET'])
def status():
    """Will render the status component

    Returns:
        str: html for the status component
    """
    try:
        username = session['username']
        complete_folder_path = session['complete_folder_path']
        remote = session['remote']
        query_status_history = get_query_status_history(username, complete_folder_path, remote)
    except:
        query_status_history = {}
    return render_template('status.html',
                            data=session,
                            drive_url=drive_url,
                            query_status_history = query_status_history)

### END COMPONENTS ###


### BEGIN SERVICE CONNECTIONS ###

@app.route('/login/<service>', methods=['GET'])
@app.route('/login', methods=['GET'])
def login(service=None):
    """Will login to a service using Oauth

    Args:
        service (str, optional): the service name. Defaults to None.

    Returns:
        obj: Oauth object
    """
    if service == None:
        redirect_uri = f'{srdc_url}/authorize'
        return oauth.owncloud.authorize_redirect(redirect_uri)
    elif service in registered_services:
        redirect_uri = f'{srdc_url}/authorize/{service}'
        logger.error(redirect_uri)
        return eval(f"oauth.{service}.authorize_redirect(redirect_uri)")


@app.route('/authorize/<service>', methods=['GET'])
@app.route('/authorize', methods=['GET'])
def authorize(service=None):
    """Will authorize a service and store the access_token.

    Args:
        service (str, optional): the service name. Defaults to None.

    Returns:
        redirect: will redirect to the embed url
    """
    if service == None:
        try:
            oauth.owncloud.authorize_access_token()
            oauth_token = oauth.owncloud.token
            access_token = oauth_token['access_token']
            refresh_token = oauth_token['refresh_token']
            # user_info = get_user_info(access_token)
            # username = user_info['sub']
            if cloud_service.lower() == "owncloud":
                username = oauth_token['user_id']
            elif cloud_service.lower() == "nextcloud":
                # nextcloud has user_id i.o. username
                username = oauth_token['user_id']
            else:
                username = None
            password = get_webdav_token(access_token, username)
            session.clear()
            if username is None:
                flash('failed to get username')
            if password is None:
                flash('failed to get webdav token')
            if username is not None and password is not None:
                if make_connection(username, password):
                    session['username'] = username
                    session['password'] = password
                    session['access_token'] = access_token
                    session['refresh_token'] = refresh_token
                    session['connected'] = True
                    session['failed'] = False
                    session.pop('_flashes', None)
                    flash('research drive connected')
                else:
                    flash('failed to connect (1)')
                    session['failed'] = True
            else:
                flash('failed to connect (2)')
                session['failed'] = True
        except Exception as e:
            flash(f'failed to connect (3)')
            flash(str(e))
            session['failed'] = True
    elif service in registered_services:
        try:
            eval(f"oauth.{service}.authorize_access_token()")
            oauth_token = eval(f"oauth.{service}.token")

            access_token = oauth_token['access_token']
            session[f'{service}_access_token'] = access_token
            flash(f'{service} connected')
        except Exception as e:
            logger.error(f"failed at connecting {service}: {e}")
            flash('failed to connect')
    return redirect(embed_app_url)

### END SERVICE CONNECTIONS ###
