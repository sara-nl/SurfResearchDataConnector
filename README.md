# SurfResearchDataConnector

The Research Data Connector App is a re-implementation of the [ScieboRDS](https://github.com/Sciebo-RDS/Sciebo-RDS) app. It allows Own Cloud users to connect to research  data repositories to upload their data to these repositories easily.

<!-- TOC -->

- [SurfResearchDataConnector](#surfresearchdataconnector)
    - [Implementation description](#implementation-description)
        - [Python with Flask as backend framework](#python-with-flask-as-backend-framework)
        - [Flask Jinja templates with Bootstrap, JS, JQuery and Vue as frontend](#flask-jinja-templates-with-bootstrap-js-jquery-and-vue-as-frontend)
        - [Deployment setup](#deployment-setup)
        - [Database](#database)
        - [Session storage](#session-storage)
    - [Connections](#connections)
        - [Connection to Owncloud or Nextcloud using webdav](#connection-to-owncloud-or-nextcloud-using-webdav)
        - [Importing open data using Datahugger](#importing-open-data-using-datahugger)
    - [How to embed the SRC app](#how-to-embed-the-src-app)
        - [Configure owncloud / nextcloud to run the app embedded](#configure-owncloud--nextcloud-to-run-the-app-embedded)
        - [Provide the correct environment variables to the SRDC app.](#provide-the-correct-environment-variables-to-the-srdc-app)
    - [Local development setup](#local-development-setup)
        - [Minikube](#minikube)
        - [Run as local flask app in debug mode](#run-as-local-flask-app-in-debug-mode)
        - [Config](#config)
        - [SQlite db](#sqlite-db)
    - [Testing](#testing)
    - [Configuring the SRDC app](#configuring-the-srdc-app)
            - [Local / general configuration](#local--general-configuration)
            - [Surf deployment configuration](#surf-deployment-configuration)
        - [General config](#general-config)
        - [Database config](#database-config)
        - [OSF repository config](#osf-repository-config)
        - [Zenodo repository config](#zenodo-repository-config)
        - [Figshare repository config](#figshare-repository-config)
        - [TU.ResearchData repository config](#turesearchdata-repository-config)
        - [Dataverse or Datastation repository config](#dataverse-or-datastation-repository-config)
        - [iRods / Yoda repository config](#irods--yoda-repository-config)
        - [Sharekit repository config](#sharekit-repository-config)
    - [TODO](#todo)

<!-- /TOC -->

## Implementation description

### Python with Flask as backend framework

The SURF Research Data Connector app is setup as a Flask app. MVC is used as the principle design pattern.

- Model: the model is very small and is implemented in the app/models.py file.
- View: the views are implemented in the app/views.py file.
- Controller: the controlling logic is implemented in various places. Logic pertaining to the connectors are implemented in seperate libraries in the app/repos folder. General logic is implemented in the app/utils.py file. Logic that is linked to a specific view is implemented in the view itself or in it's template.

For more info on Python and Flask please refer to: https://www.python.org and https://flask.palletsprojects.com

### Flask Jinja templates with Bootstrap, JS, JQuery and Vue as frontend

The frontend is rendered by the Flask framework using Jinja Templating. Jquery is used to load parts of pages asynchronously as components. This is done to spead up the loading of the pages and to make sure pages will alwys load even if a component fails to load. Jquery, JS and Vue is also used to create on page interacivity.

Note: in due time we may transition to a Single Page Application setup using a frontend framework (like Vue, or React). We could do this by transforming all the Flasks views that currently render templates, to views that return json. This could potentially create a more mordern fluid user experience.

For more info on the templating engine and the libraries used for the frontend used see:

- Jinja: https://jinja.palletsprojects.com
- Bootstrap: https://getbootstrap.com
- Jquery: https://jquery.com
- Vue: https://vuejs.org

### Deployment setup

The app has been build to run on a kubernetes cluster. Deployment to the cluster is done by helm charts. The app can be configured in the main values.yaml file that is part of the helm charts.

For more info on Kubernetes and Helm Charts please refer to: https://kubernetes.io and https://helm.sh

### Database

The app uses flask migrate to manage the models migration to the database.
An SQLite database is used for user history data storage for local development.
In order to use an SQLite DB you can set the following env var in the local helm chart values.yaml file:

```yaml
  - name: USE_SQLITE
    value: ok
```

In production a MariaDB is used. The database connection can be configured in the helm chart values.yaml file:

```yaml
  # Database connection
  - name: DB_USER
    value: ABCD
  - name: DB_PASS
    value: your-password-here
  - name: DB_HOST
    value: 111.111.111.1
  - name: DB_PORT
    value: :3306
  - name: DB_DATABASE
    value: your-database-name
```

Please take note of the colon before the port number. This is needed for proper configuration.

### Session storage

Flask sessions are used for temporary storage of variables like a.o. tokens and Research Drive (Owncloud / Nextcloud) application passwords. You can also configure redis to be used for session storage. This is recommended as it will help to persist session data. If you configure a redis host in the helm chart values.yaml it will be used for session storage.

```yaml
  # redis
  - name: REDIS_HOST
    value: redis-helper-master
  - name: REDIS_PORT
    value: :6379
```

## Connections

The app connects to Owncloud or Nextcloud and to one or more external repositories.

Currently the following connections are supported:

- Datahugger
- OSF
- Zenodo
- Figshare
- Dataverse / Dans Datastations
- iRods
- Sharekit
- 4TU.ResearchData

### Connection to Owncloud or Nextcloud using webdav

OWNCLOUD

The library pyocclient (https://pypi.org/project/pyocclient/) is used for connecting the app to Owncloud using the webdav protocol.

We can only login to Owncloud webdav using an application password.

Connecting to Owncloud webdav using bearer tokens is not supported yet:

https://central.owncloud.org/t/how-to-authenticate-to-the-webdav-api/40049

NEXTCLOUD

For connecting to the webdav of Nextcloud the app uses the library pyncclient (https://github.com/pragmaticindustries/pyncclient). Nextcloud does provide the ability to connect to webdav using a bearer token. The initial connecting to Nextcloud is setup using the bearer token that is obtained via the Oauth connection flow. The bearer token will expire. The user can also obtain a persistent connection to Nextcloud, which is based on an application password.
The user can set this up manually or by entering a second authentication flow that will create the app password and use that for the connection.

### Importing open data using Datahugger

The app uses Datahugger to get open data. This is always available and the user does not neet to set this connection up.

Repos tested using Datahugger (dec 2023)

* Figshare - OK
* Zenodo - OK
* Dryad - OK
* OSF - OK
* Dataverse - OK
* Mendeley - OK
* DataOne - OK, but only the ones with DOI, as it looks for view/doi:(.*) in the url. There are many implementations with view/urn:uuid:. We could implement a solution in a fork of datahugger for those as well.
* Github - OK, but it specifically will download only master.zip downloads. We can update the datahugger code to improve on this.
* Hugging face - Not OK

## How to embed the SRC app

We can embed the SRC app as an external app.

To do so we need to enable the following Owncloud / Nextcloud Plugins:

* External sites
* OAuth2

### Configure owncloud / nextcloud to run the app embedded

Go to Settings > Admin > Additional > External Sites

Add the name and url of the external app and select an icon.

This will add the icon and the name with link to the menu.

The app will be embedded here: /index.php/apps/external/1

### Provide the correct environment variables to the SRDC app.

Fill out  the variables in the helm chart values.yaml file.

## Local development setup

Everything needed for a local setup of the app is located in the ./local folder.

### Minikube

The setup can be done on a minikube cluster.
More info on minikube can be found here: https://minikube.sigs.k8s.io/docs/start/
First install minikube on your system.
On linux you can run the minikube.sh script, but you do need to customize it to match your setup.
Running the app locally using minikube it the prefered way.

### Run as local flask app in debug mode

To run the app simply as a local flask app run:

```
flask --app run run
```

If you go to http://127.0.0.1:5000/ the app will open the home page and try to automatically connect using Oauth2.
If this is not setup (yet) you can go to http://127.0.0.1:5000/connect and connect using an app password.

This is not the prefered way to run the app for development. Your millage may vary.

### Config

The app reads all the config variables from the environment variables set by the helm chart deployment. If you run the app locally as a flask app, then you can set the variables in the env.ini file.
Make sure that you set all the LOCAL_XXX variables to match your local app. Also for testing purposes you can configure the variables in the env.ini file.

### SQlite db

The app will try to find an sql database if you have this setup in the config.
If a database connection cannot be initiated the app will try to use a local sqlite database.
When the app starts it will try to create the db and migrate the models to it by running:

```
flask db init
flask db upgrade
```

## Testing

The code has tests that can be run by the following comamand from the root directory:

```
pytest
```

Make sure you have setup a virtualenvironment, have this environment activated, and have installed all the pip dependenies. The easiest way to do this is by using pipenv with these commands:

```
# create a virtual environment and install all dependencies
pipenv install
# activate the enviromnent in a shell
pipenv shell
# runn all tests available in the /tests folder
pytest
```

The tests should look something like this example below:

```bash
dave@dave-Latitude-7430:~/Projects/data-retriever/local(main)$ pipenv install
To activate this project's virtualenv, run pipenv shell.
Alternatively, run a command inside the virtualenv with pipenv run.
To activate this project's virtualenv, run pipenv shell.
Alternatively, run a command inside the virtualenv with pipenv run.
Installing dependencies from Pipfile.lock (e4eef2)...
dave@dave-Latitude-7430:~/Projects/data-retriever/local(main)$ pipenv shell
Launching subshell in virtual environment...
dave@dave-Latitude-7430:~/Projects/data-retriever(main)$  source /home/dave/.local/share/virtualenvs/data-retriever-C4CSjHYm/bin/activate
(data-retriever) dave@dave-Latitude-7430:~/Projects/data-retriever(main)$ pytest
=================================================================================================================== test session starts ====================================================================================================================
platform linux -- Python 3.11.11, pytest-7.4.0, pluggy-1.2.0
rootdir: /home/dave/Projects/data-retriever
plugins: pactman-2.30.0
collected 72 items  

test-datahugger/data/test_all.py ..                                                                                               [  2%]
tests/test_utils.py .F                                                                                                            [  5%]
tests/repos/test_repos_Mocked_api_figshare.py ..............                                                                      [ 25%]
tests/repos/test_repos_dataverse.py ...s....s..                                                                                   [ 40%]
tests/repos/test_repos_figshare.py ..........s.....                                                                               [ 62%]
tests/repos/test_repos_irods.py s.FFFssFF                                                                                         [ 75%]
tests/repos/test_repos_mocked_api_dataverse.py s                                                                                  [ 76%]
tests/repos/test_repos_mocked_api_zenodo.py ..sss..s                                                                              [ 87%]
tests/repos/test_repos_sharekit.py .FF.....s                                                                                      [100%]
```

## Configuring the SRDC app

Below we describe the configuration of the SRDC app. Basically there are two configurations:

#### Local / general configuration

This is all done in the main values.yaml file of the helm charts.

#### Surf deployment configuration

The Surf deployment configuration has been set up with enheritance. There is the default configuration that can be overwritten or be added to by configurations specific for each SRDC instance.

Everything is managed by and configured in the Service-Vars private repository. Please refer to documentation in that repo for specific info on the setup at Surf.

Below description os for the general configuration in the main values.yaml file in the helm charts.

We will describe all the variables that can be configured. If a variable is optional we will indicate that. Values of optional variables can be left blank or can be left out of the confiuration entirely.

### General config
DRIVE_URL: This is the url of the cloudservice the SRDC app will connect to.

SRDC_URL: This is the url where the app will be available at.

CLOUD_SERVICE: This can be 'owncloud' or 'nextcloud'.

CLOUD_CLIENT_ID: This is the client id for the Oauth connection to the cloudservice.

CLOUD_CLIENT_SECRET: This is the client secret for the Oauth connection to the cloudservice.

HIDDEN_SERVICES (optional): This is a comma seperated list of the services you want to be hidden.

OAUTH_SERVICES (optional): This is a comma seperated list of the Oauth services you want to be shown.

TOKEN_BASED_SERVICES (optional): This is a comma seperated list of the token based authentication services you want to be shown.

USE_SQLITE (optional): Set the value to 'OK' if you want the app to use a local SQLite database. Useful for development. Do not use in production.


By default the app will show OAuth and Token based connections to all repositories. So if you do not setup the OAuth connection to a repository, it is best to not show this connection by omitting it from the OAUTH_SERVICES and TOKEN_BASED_SERVICES vars. You can also hide the service completely by adding it to the HIDDEN_SERVICES var.

You will only need to configure the repositories that you want to support. And hide or not include them. If you do not configure a repository connection and it does show up in the SRDC connections, then it will be configured with some blank, or dummy settings and therefore might not work. 

Example config:

```yaml
  - name: DRIVE_URL
    value: https://acc-aperture.data.surfsara.nl
  - name: SRDC_URL
    value: https://local-srdr-rd-app-acc.data.surfsara.nl
  - name: CLOUD_SERVICE
    value: owncloud
  - name: CLOUD_CLIENT_ID
    value: ABC
  - name: CLOUD_CLIENT_SECRET
    value: ABC
  - name: HIDDEN_SERVICES
    value: zenodo,osf
  - name: OAUTH_SERVICES
    value: figshare,zenodo,osf
  - name: TOKEN_BASED_SERVICES
    value: dataverse,irods,figshare,zenodo,osf,sharekit,data4tu
  - name: USE_SQLITE
    value: ok
```

### Database config
DB_USER: The username of the database connection.

DB_PASS: The pass word of the database connection.

DB_HOST: The host endpoint of the database connection.

DB_PORT: The port of the database connection.

DB_DATABASE: The name of the database.

REDIS_HOST (optional): The host endpoint of the redis connection.

REDIS_PORT (optional): The port of the redis connection.

Example config:

```yaml
  - name: DB_USER
    value: aperture_tst_srdr
  - name: DB_PASS
    value: ABC
  - name: DB_HOST
    value: 192.168.1.1
  - name: DB_PORT
    value: :3306
  - name: DB_DATABASE
    value: aperture_tst_srdr
  - name: REDIS_HOST
    value: redis-helper-master
  - name: REDIS_PORT
    value: :6379
```

### OSF repository config
OSF_API_URL: The base url for all api calls. 

OSF_AUTHORIZE_URL: The url for authenticating per OAuth.

OSF_ACCESSTOKEN_URL: The url for retrieving the OAuth access token.

OSF_CLIENT_ID: The client id for authentication  per OAuth.

OSF_CLIENT_SECRET: The client secret for authentication  per OAuth.

OSF_DESCRIPTION: The repository description to show the user.

OSF_WEBSITE: Link to the website of the repository portal.


Example config:
```yaml
  - name: OSF_API_URL
    value: https://api.osf.io/v2
  - name: OSF_AUTHORIZE_URL
    value: https://accounts.osf.io/oauth2/authorize
  - name: OSF_ACCESSTOKEN_URL
    value: https://accounts.osf.io/oauth2/token
  - name: OSF_CLIENT_ID
    value: ABC
  - name: OSF_CLIENT_SECRET
    value: ABC
  - name: OSF_DESCRIPTION
    value: Connection to the test environment of OSF.
  - name: OSF_WEBSITE
    value: https://osf.io
```

### Zenodo repository config
ZENODO_API_URL: The base url for all api calls. 

ZENODO_AUTHORIZE_URL: The url for authenticating per OAuth.

ZENODO_ACCESSTOKEN_URL: The url for retrieving the OAuth access token.

ZENODO_CLIENT_ID: The client id for authentication  per OAuth.

ZENODO_CLIENT_SECRET: The client secret for authentication  per OAuth.

ZENODO_DESCRIPTION: The repository description to show the user.

ZENODO_WEBSITE: Link to the website of the repository portal.

Example config:
```yaml
  - name: ZENODO_API_URL
    value: https://zenodo.org/api
  - name: ZENODO_AUTHORIZE_URL
    value: https://zenodo.org/oauth/authorize
  - name: ZENODO_ACCESSTOKEN_URL
    value: https://zenodo.org/oauth/token
  - name: ZENODO_CLIENT_ID
    value: ABC
  - name: ZENODO_CLIENT_SECRET
    value: ABC
  - name: ZENODO_DESCRIPTION
    value: Connection to Zenodo.
  - name: ZENODO_WEBSITE
    value: https://zenodo.org
```

### Figshare repository config
FIGSHARE_API_URL: The base url for all api calls. 

FIGSHARE_AUTHORIZE_URL: The url for authenticating per OAuth.

FIGSHARE_ACCESSTOKEN_URL: The url for retrieving the OAuth access token.

FIGSHARE_CLIENT_ID: The client id for authentication  per OAuth.

FIGSHARE_CLIENT_SECRET: The client secret for authentication  per OAuth.

FIGSHARE_DESCRIPTION: The repository description to show the user.

FIGSHARE_WEBSITE: Link to the website of the repository portal.

Example config:
```yaml
  - name: FIGSHARE_API_URL
    value: https://api.figshare.com/v2
  - name: FIGSHARE_AUTHORIZE_URL
    value: https://figshare.com/account/applications/authorize
  - name: FIGSHARE_CLIENT_ID
    value: ABC
  - name: FIGSHARE_CLIENT_SECRET
    value: ABC
  - name: FIGSHARE_DESCRIPTION
    value: Connection to Figshare.
  - name: FIGSHARE_WEBSITE
    value: https://figshare.com
```

### 4TU.ResearchData repository config
DATA4TU_API_URL: The base url for all api calls. 

DATA4TU_DESCRIPTION: The repository description to show the user.

DATA4TU_WEBSITE: Link to the website of the repository portal.

Example config:
```yaml
  - name: DATA4TU_API_URL
    value: https://data.4tu.nl/v2
  - name: DATA4TU_DESCRIPTION
    value: Connection to 4TU.ResearchData
  - name: DATA4TU_WEBSITE
    value: https://data.4tu.nl
```

### Dataverse or Datastation repository config
DATAVERSE_API_URL: The base url for all api calls. 

DATAVERSE_DESCRIPTION: The repository description to show the user.

DATAVERSE_WEBSITE: Link to the website of the repository portal.

DATAVERSE_PARENT_DATAVERSE: The value here will be the base dataverse the user will have access to.

DATAVERSE_CREATE_USER_DATAVERSE (optional): Set to OK to create a user specific dataverse.

DATASTATION (optional): Set to OK to have specific DANS Datastation features activated.

DATASTATION_BASICAUTH_TOKEN (optional): Set the auth token to access datastations behind a basic auth

Example config:
```yaml
  - name: DATAVERSE_API_URL
    value: https://demo.ssh.datastations.nl/api
  - name: DATAVERSE_DESCRIPTION
    value: Connection to demo.ssh.datastations.nl.
  - name: DATAVERSE_WEBSITE
    value: https://demo.ssh.datastations.nl
  - name: DATAVERSE_PARENT_DATAVERSE
    value: root
  - name: DATAVERSE_CREATE_USER_DATAVERSE
    value: ok
  - name: DATASTATION
    value: OK
  - name: DATASTATION_BASICAUTH_TOKEN
    value: ABC
```

### iRods / Yoda repository config

IRODS_API_URL: The base url for all api calls. 

IRODS_DESCRIPTION: The repository description to show the user.

IRODS_WEBSITE: Link to the website of the repository portal.

IRODS_ZONE: The iRods zone to work in.

IRODS_BASE_FOLDER: The base iRods folder to work with.

Example config:
```yaml
  - name: IRODS_API_URL
    value: surf-yoda.irods.surfsara.nl
  - name: IRODS_DESCRIPTION
    value: Connection to surf-yoda.irods.surfsara.nl.
  - name: IRODS_WEBSITE
    value: https://surf-yoda.irods.surfsara.nl
  - name: IRODS_ZONE
    value: yoda
  - name: IRODS_BASE_FOLDER
    value: research-fmtest1
```

### Sharekit repository config

SHAREKIT_API_URL: The base url for all api calls. 

SHAREKIT_DESCRIPTION: The repository description to show the user.

SHAREKIT_WEBSITE: Link to the website of the repository portal.

SHAREKIT_API_KEY: No longer needed. Authentication is now done by client_id and client secret.

SHAREKIT_CLIENT_ID: The client id for authentication of the app connection.

SHAREKIT_CLIENT_SECRET: The client secret for authentication of the app connection.

SHAREKIT_INSTITUTE: ID of the instititute to upload as.

SHAREKIT_OWNER: ID of the default / fall back owner to upload as.

Example config:
```yaml
  - name: SHAREKIT_API_URL
    value: https://api.acc.surfsharekit.nl/api
  - name: SHAREKIT_DESCRIPTION
    value: Connection to ACC environment of Sharekit.
  - name: SHAREKIT_WEBSITE
    value: https://acc.surfsharekit.nl
  - name: SHAREKIT_API_KEY
    value: ABC
  - name: SHAREKIT_CLIENT_ID
    value: ABC
  - name: SHAREKIT_CLIENT_SECRET
    value: ABC
  - name: SHAREKIT_INSTITUTE
    value: 1cb21e78-6d07-4d21-ba5d-f722dd2ba1bd
  - name: SHAREKIT_OWNER
    value: 5b289b2c-8fd3-420b-be5f-6d21036360b3
```

## TODO

* Complete deployment instructions
* Describe config per connector
