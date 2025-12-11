import os
import logging

flask_logfile_name = 'flask_app_sets_flask_logfile_name.log'
logger = logging.getLogger()
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
logger.setLevel(logging.ERROR)

def flask_setup(new_flask_logfile_name):
    global flask_logfile_name
    flask_logfile_name = new_flask_logfile_name
    logfile = "./" + flask_logfile_name
    hdlr = logging.FileHandler(logfile)
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.debug('Flask app started')