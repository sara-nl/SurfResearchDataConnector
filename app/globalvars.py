import os
import sys
import configparser
import json
import glob
import re

datastation_basicauth_token = None
code_version = None
dataverse_create_user_dataverse = 'No'

VALID_VAR_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

def _is_valid_variable_name(name):
    return bool(VALID_VAR_PATTERN.match(name))

all_vars = {}
for key in os.environ:
    try:
        value = os.getenv(key)
        var_name = key.lower()

        if not _is_valid_variable_name(var_name):
            continue

        if key.upper() in ['HIDDEN_SERVICES','TOKEN_BASED_SERVICES','OAUTH_SERVICES']:
            value = value.split(",")
            value = [v.strip() for v in value]
            all_vars[var_name] = value
        else:
            all_vars[var_name] = value

        if value is not None:
            setattr(sys.modules[__name__], var_name, value)
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