import pytest
from flaskblog import create_app, db
from flaskblog.config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://' # In-memory database
    SECRET_KEY = 'test_secret_key'
    WTF_CSRF_ENABLED = False # Makes testing forms easier

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()