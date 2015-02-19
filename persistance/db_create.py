import sqlite3
from migrate.versioning import api
from config import DATABASE_URI
from config import SQLALCHEMY_MIGRATE_REPO


import os.path
from persistance import db

sqlite3.connect(os.path.abspath("app.db"))

db.create_all()
if not os.path.exists(SQLALCHEMY_MIGRATE_REPO):
    api.create(SQLALCHEMY_MIGRATE_REPO, 'database repository')
    api.version_control(DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
else:
    api.version_control(DATABASE_URI, SQLALCHEMY_MIGRATE_REPO,
                        api.version(SQLALCHEMY_MIGRATE_REPO))