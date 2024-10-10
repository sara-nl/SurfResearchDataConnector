import logging
import os
import sys
import configparser

logger = logging.getLogger()

# Set default global values in an env.ini file
# This can be used for local development without k8 / helm charts
# It can also be used to run tests locally.

EXCLUDE_APP_TYPE = 'RDR'
EXCLUDE_APP_TEST = 'TESTS'

try:
    config = configparser.ConfigParser()
    if os.path.isfile('env.ini'):
        config.read('env.ini')
    else:
        # for testing irods_repo
        print("testing")
        config.read('../env.ini')
except Exception as e:
    config = None
    logger.error(str(e))


# collect all vars in the all_vars dicttionary
all_vars = {'EXCLUDE_APP_TYPE': EXCLUDE_APP_TYPE}

#Getting default vars from the env.ini file
for section in config.sections():
    section = section.upper()
    if section.find(EXCLUDE_APP_TYPE)==-1 and section.find(EXCLUDE_APP_TEST)==-1:
        for k,v in config[section].items():
            expr = f"{k.lower()} = config.get('{section}', '{k.upper()}')"
            exec(expr)
            all_vars[k.lower()]=config.get(section, k.upper())
            if k.upper() in ['HIDDEN_SERVICES','TOKEN_BASED_SERVICES','OAUTH_SERVICES']:
                v = v.split(",")
                v = [value.strip() for value in v]
                all_vars[k.lower()]=v
                expr = f"{k.lower()}={v}"
                exec(expr)


# get all env vars from the environment in the pod, which are set in the helm charts
# This will overwrite any default values set in the env.ini file
for key in os.environ:
    try:
        value = os.getenv(key)
        if key.upper() in ['HIDDEN_SERVICES','TOKEN_BASED_SERVICES','OAUTH_SERVICES']:
            value = value.split(",")
            value = [v.strip() for v in value]
            all_vars[key.lower()]=value
            expr1 = f"{key.lower()}={value}"
            exec(expr1)
        else:
            all_vars[key.lower()]=value
            expr2 = f"{key.lower()}='{value}'"
            exec(expr2)
    except Exception as e:
        print(e)
        pass

if __name__ == "__main__":
    # from globalvars import *
    for item in all_vars:
        if item == 'oauth_services':
            print(item)