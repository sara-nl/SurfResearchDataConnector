import logging
import os
import sys
import configparser
import json
import glob

logger = logging.getLogger()

datastation_basicauth_token = None
code_version = None
dataverse_create_user_dataverse = 'No'
# get all env vars from the environment in the pod, which are set in the helm charts

all_vars = {}
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

srdc_lang = 'en'

languages = {}
language_list = glob.glob("app/languages/*.json")
for lang in language_list:
    filename = lang.split('/')[-1]
    lang_code = filename.split('.')[0]
    with open(lang, 'r', encoding='utf8') as file:
        languages[lang_code] = json.loads(file.read())


if __name__ == "__main__":
    pass