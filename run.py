import os
import logging
from app.views import *
from app.models import app

log = logging.getLogger()

if __name__ == "__main__":
    try:
        log.info("running flask db init")
        os.system("flask db init")
    except Exception as e:
        log.info(str(e))
    try:
        log.info("running flask db upgrade")
        os.system("flask db upgrade")
    except Exception as e:
        log.info(str(e))

    app.run(
        host="0.0.0.0",
        debug=False,
        port=80
    )



