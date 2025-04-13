import os
import shutil
import click
from flask import current_app

from .extensions import db


@click.command('init-db')
def init_db():
    """Initialize the database"""
    db.create_all()
    click.echo('Database initialized')


@click.command('reset-db')
def reset_db():
    """Reset the database"""
    with current_app.app_context():
        upload_folder = current_app.config['UPLOAD_FOLDER']
        if os.path.exists(upload_folder):
            shutil.rmtree(upload_folder)
    db.drop_all()
    db.create_all()
    click.echo('Database reset')
