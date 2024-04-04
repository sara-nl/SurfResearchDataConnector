# import logging
import os
# import sys
# import configparser

# logger = logging.getLogger()

# EXCLUDE_APP_TYPE = 'LOCAL'
# EXCLUDE_APP_TEST = 'TEST'

# try:
#     config = configparser.ConfigParser()
#     if os.path.isfile('env.ini'):
#         config.read('env.ini')
#     else:
#         # for testing irods_repo
#         config.read('../../env.ini')
# except Exception as e:
#     config = None
#     logger.error(str(e))

# for section in config.sections():
#     if section.upper().find(EXCLUDE_APP_TYPE)==-1 and section.upper().find(EXCLUDE_APP_TEST)==-1:
#         for k,v in config[section].items():
#             expr = f"{k.lower()} = os.getenv('{k.upper()}', config.get('{section.upper()}', '{k.upper()}'))"
#             exec(expr)


# all_vars = {'EXCLUDE_APP_TYPE': EXCLUDE_APP_TYPE}
# for section in config.sections():
#     if section.upper().find(EXCLUDE_APP_TYPE)==-1 and section.upper().find(EXCLUDE_APP_TEST)==-1:
#         for k,v in config[section].items():
#             expr = f"all_vars['{k.lower()}']={k.lower()}"
#             exec(expr)

# get all env vars
all_vars = {}
for key in os.environ:
    value = os.getenv(key)
    if key.upper() == 'HIDDEN_SERVICES':
        value = value.split(",")
        value = [v.strip() for v in value]
        expr = f"{key.lower()}={value}"
    else:
        expr = f"{key.lower()}='{value}'"
    all_vars[key.lower()]=value
    exec(expr)


# if __name__ == "__main__":
#     all_vars = {'EXCLUDE_APP_TYPE': EXCLUDE_APP_TYPE}
#     for section in config.sections():
#         if section.upper().find(EXCLUDE_APP_TYPE)==-1 and section.upper().find(EXCLUDE_APP_TEST)==-1:
#             for k,v in config[section].items():
#                 expr = f"all_vars['{k.lower()}']={k.lower()}"
#                 exec(expr)
#     print(all_vars)
