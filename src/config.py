import os
from pathlib import Path
from flask import current_app

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR}/instance/app.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'instance/uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'gif'}
    STATIC_FOLDER = os.path.join(BASE_DIR, 'instance/uploads')
    STATIC_URL_PATH = '/static'

def get_allowed_extensions():
    return current_app.config['ALLOWED_EXTENSIONS']


def get_upload_folder():
    return current_app.config['UPLOAD_FOLDER']