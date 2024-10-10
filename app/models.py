import logging
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.sql import func
from flask_session import Session
import redis

logger = logging.getLogger()

app = Flask(__name__)

try:
    from app.globalvars import *
except:
    # for testing
    from globalvars import *

# os.urandom(24)
app.secret_key = b'SET YOUR OWN'

try:
    # check if redis host and port are configurered
    if 'redis_host' in all_vars and 'redis_port' in all_vars:
        # check if the configured redis server is available
        redis_port = redis_port.split(':')[1]
        # redis_host = "redis-helper-master"
        logger.error(redis_host)
        try:
            r = redis.Redis(host=redis_host, port=redis_port, socket_connect_timeout=1)
            r.ping()
            redis_available = True
            logger.error(f"1 - Redis server available for session storage.")
        except Exception as e:
            logger.error(f"Failed to connect to redis: {e}")
            redis_available = False

        if redis_available:
            try:
                # Configure Redis for storing the session data on the server-side
                app.config['SESSION_TYPE'] = 'redis'
                app.config['SESSION_REDIS'] = redis.Redis(host=redis_host, port=redis_port)
                # Create and initialize the Flask-Session object AFTER `app` has been configured
                server_session = Session()
                server_session.init_app(app)               
            except Exception as e:
                logger.error(f"2 - Redis server cannot be configured for session storage. {e}")
        else:
            logger.error(f"3 - Redis server not available for session storage. Will use client side storage instead")
    else:
        logger.error(f"4 - Redis host and port are not configured. Therefore redis server is not available for session storage. Will use client side storage instead")
except:
    logger.error(f"5 - Redis host and port are not configured. Therefore redis server is not available for session storage. Will use client side storage instead")


if 'use_sqlite' in locals():
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
else:
    try:
        app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_user}:{db_pass}@{db_host}{db_port}/{db_database}'
    except Exception as e:
        logger.error(f"Failed to configure database: {e}")

try:
    db = SQLAlchemy(app)
    migrate = Migrate(app, db)
except Exception as e:
    logger.error(f"Failed to migrate database: {e}")

class History(db.Model):
    """Defines the history model

    Args:
        db (SQLAlchemy): db object
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128))
    folder = db.Column(db.String(128))
    url = db.Column(db.String(128))
    status = db.Column(db.String(128))
    time_created = db.Column(db.DateTime(
        timezone=True), server_default=func.now())
    time_updated = db.Column(db.DateTime(timezone=True), onupdate=func.now())
