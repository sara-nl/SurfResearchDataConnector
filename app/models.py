from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.sql import func
try:
    from app.globalvars import *
except:
    # for testing
    from globalvars import *

app = Flask(__name__)

try:
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_user}:{db_pass}@{db_host}/{db_database}'
except:
    # local db for development only
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'

db = SQLAlchemy(app)
migrate = Migrate(app, db)

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
