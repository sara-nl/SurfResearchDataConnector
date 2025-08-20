import logging
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.sql import func
from flask_session import Session
import redis

# FASTAPI imports
from fastapi import FastAPI
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from a2wsgi import ASGIMiddleware

logger = logging.getLogger()

app = Flask(__name__)


# Fast API mounting on flask
# https://stackoverflow.com/questions/70506231/is-it-possible-to-mount-an-instance-of-fastapi-onto-a-flask-application
fast_app = FastAPI()

app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/flask': app,
    '/api': ASGIMiddleware(fast_app),
})

try:
    from app.globalvars import *
except:
    # for testing
    from globalvars import *

# os.urandom(24)
app.secret_key = b'V\x8b\x100\xfa\x01)\xd6\xe4`\x10\x16\xef9\x1b\xba\x128N\xf6\xe3\xbb\x90\xec'

try:
    redis_port = 6379
    redis_host = "localhost"
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
    username = db.Column(db.String(256))
    projectname = db.Column(db.String(256))
    folder = db.Column(db.Text())
    url = db.Column(db.String(256))
    status = db.Column(db.String(256))
    time_created = db.Column(db.DateTime(
        timezone=True), server_default=func.now())
    time_updated = db.Column(db.DateTime(timezone=True), onupdate=func.now())
