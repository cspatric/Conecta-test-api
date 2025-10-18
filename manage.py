from flask.cli import FlaskGroup
from app.main import create_app

def create_app_wrapper():
    return create_app()

cli = FlaskGroup(create_app=create_app_wrapper)

if __name__ == "__main__":
    cli()