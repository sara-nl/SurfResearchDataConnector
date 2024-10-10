from authlib.integrations.flask_client import OAuth

try:
    from app.models import app
    from app.globalvars import *
except:
    # for testing this file locally
    from models import app, db, History
    from globalvars import *
    print("testing")

oauth = OAuth(app)

# Oauth connection config for owncloud
try:
    oauth.register(
        name='rdrive',
        client_id=cloud_client_id,
        client_secret=cloud_client_secret,
        access_token_url=f'{drive_url}/index.php/apps/oauth2/api/v1/token',
        access_token_params=None,
        authorize_url=f'{drive_url}/index.php/apps/oauth2/authorize',
        authorize_params=None,
        api_base_url=f'{drive_url}',
        client_kwargs={},
    )
except:
    pass


# Oauth connection config for figshare
try:
    oauth.register(
        name='figshare',
        client_id=figshare_client_id,
        client_secret=figshare_client_secret,
        access_token_url=f'{figshare_api_url}/token',
        access_token_params={'client_id': figshare_client_id, 'client_secret': figshare_client_secret},
        access_token_method = 'POST',
        authorize_url=figshare_authorize_url,
        authorize_params=None,
        api_base_url=f'{figshare_api_url}',
        client_kwargs={'scope': 'all',
                        'grant_type': 'authorization_code'},
    )
except:
    pass

# Oauth connection config for zenodo
try:
    oauth.register(
        name='zenodo',
        client_id=zenodo_client_id,
        client_secret=zenodo_client_secret,
        access_token_url=zenodo_accesstoken_url,
        access_token_params={'client_id': zenodo_client_id, 'client_secret': zenodo_client_secret},
        access_token_method = 'POST',
        authorize_url=zenodo_authorize_url,
        authorize_params=None,
        api_base_url=f'{zenodo_api_url}',
        client_kwargs={'scope': 'deposit:write',
                        'grant_type': 'authorization_code'},
    )
except:
    pass

# Oauth connection config for osf
try:
    oauth.register(
        name='osf',
        client_id=osf_client_id,
        client_secret=osf_client_secret,
        access_token_url=osf_accesstoken_url,
        access_token_params={'client_id': osf_client_id, 'client_secret': osf_client_secret},
        access_token_method = 'POST',
        authorize_url=osf_authorize_url,
        authorize_params=None,
        api_base_url=osf_api_url,
        client_kwargs={'scope': 'osf.full_write',
                        'grant_type': 'authorization_code'},
    )
except:
    pass


if 'token_based_services' not in all_vars:
    token_based_services = ['figshare','zenodo','osf','dataverse', 'irods', 'sharekit']

if 'oauth_services' not in all_vars:
    try:
        oauth_services = list(oauth._registry.keys())
        oauth_services.remove('owncloud')
    except:
        oauth_services = []

# remove items that are empty string
if '' in oauth_services:
    try:
        oauth_services.remove('')
    except Exception as e:
        logger.error(e)
if '' in token_based_services:
    try:
        token_based_services.remove('')
    except Exception as e:
        logger.error(e)
        
registered_services = list(set(token_based_services + oauth_services))


if __name__ == "__main__":
    pass