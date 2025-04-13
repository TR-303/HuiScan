import click
from src.extensions import db

@click.command('init-db')
def init_db():
    """Initialize the database"""
    db.create_all()
    click.echo('Database initialized')