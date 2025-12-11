import os
import logging
from app.views import *
from app.models import app
from app.logs import *

if __name__ == "__main__":

    # flask_setup('flask_app.log')

    try:
        logger.info("running flask db init")
        os.system("flask db init")
    except Exception as e:
        logger.info(str(e))
    try:
        logger.info("running flask db upgrade")
        os.system("flask db upgrade")
    except Exception as e:
        logger.info(str(e))

    app.run(
        host="0.0.0.0",
        debug=True,
        port=80
    )



