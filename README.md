# SurfResearchDataConnector
The Research Data Connector App is a re-implementation of the [ScieboRDS](https://github.com/Sciebo-RDS/Sciebo-RDS) app. It allows Own Cloud users to connect to research  data repositories to upload their data to these repositories easily.


## Implementation description

### Python with Flask as framework
The SURF Research Data Connector app is setup as a Flask app. 

### Database
It can use flask migrate and a SQLite for user history data storage for local development. In production a MariaDB is used. You could also use Postgres if you want.

### Session storage
Flask sessions are used for temporary storage of variables like a.o. tokens and Research Drive (Owncloud) application passwords.

### Uploading data using webdav
The library pyocclient (https://pypi.org/project/pyocclient/) is used for connecting the app to Owncloud using the webdav protocol.

We can only login to Owncloud webdav using an application password.

Connecting to webdav using bearer tokens is not supported yet:

https://central.owncloud.org/t/how-to-authenticate-to-the-webdav-api/40049


### Retrieving open data using Datahugger
The app uses Datahugger to get open data.

## Repos tested using Datahugger (dec 2023)
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

To do so we need to enable the following Owncloud Plugins:
* External sites
* OAuth2

### Configure owncloud to run the app embedded
Go to Settings > Admin > Additional > External Sites

Add the name and url of the external app and select an icon.

This will add the icon and the name with link to the menu.

The app will be embedded here: /index.php/apps/external/1

Add the url to the env vars as EMBED_APP_URL.

Example:

EMBED_APP_URL: https://aperture.data.surfsara.nl/index.php/apps/external/1

### Provide the correct environment variables to the SRDC app.

Fill out  the variables in the env.ini.

## Local development setup

Everything needed for a local setup of the app is located in the ./local folder.

### Minikube
The setup can be done on a minikube cluster.
More info on minikube can be found here: https://minikube.sigs.k8s.io/docs/start/
First install minikube on your system.
On linux you can run the minikube.sh script, but you do need to customize it to match your setup.

### Run as local flask app in debug mode
To run the app simply as a local flask app run:
```
flask --app run run
```
If you go to http://127.0.0.1:5000/ the app will open the home page and try to automatically connect using Oauth2.
If this is not setup (yet) you can go to http://127.0.0.1:5000/connect and connect using an app password.

### Config
The app reads all the config variables from the env.ini file.
Make sure that you set all the LOCAL_XXX variables to match your local app.

### SQlite db
The app will try to find a sql database if you have this setup in the config.
If a database connection cannot be initiated the app will try to use a local sqlite database.
To create the sqlite database run:

```
flask db init
flask db upgrade
```

## TODO
* Complete deployment instructions
