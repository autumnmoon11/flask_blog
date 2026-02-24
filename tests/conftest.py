import os
import pytest
import shutil
from flaskblog import create_app, db
from flaskblog.config import Config
from flaskblog.models import User
from flask_bcrypt import generate_password_hash

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://' # In-memory database
    SECRET_KEY = 'test_secret_key'
    WTF_CSRF_ENABLED = False # Makes testing forms easier
    SERVER_NAME = "localhost.localdomain"

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth(client):
    # Creating a simple class to handle login/logout actions within tests
    class AuthActions:
        def __init__(self, client):
            self._client = client

        def login(self, email='test@test.com', password='password'):
            # Simulating a login by posting to login route
            return self._client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

        def logout(self):
            # Simulating a logout
            return self._client.get('/logout', follow_redirects=True)

    return AuthActions(client)

@pytest.fixture
def test_user(app):
    """I create a default user for testing purposes."""
    hashed_pw = generate_password_hash('password').decode('utf-8')
    user = User(username='TestUser', email='test@test.com', password=hashed_pw)
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def cleanup_test_images(app):
    # Setting up a specific path just for test uploads
    test_upload_dir = 'static/test_uploads'
    full_test_path = os.path.join(app.root_path, test_upload_dir)
    
    # Creating the directory if it doesn't exist yet
    if not os.path.exists(full_test_path):
        os.makedirs(full_test_path)
    
    # Overriding the app config to point to the test folder
    app.config['UPLOADED_PHOTOS_DEST'] = test_upload_dir
    
    yield # This is where the test actually runs
    
    # Wiping the entire test folder after the test finishes
    if os.path.exists(full_test_path):
        shutil.rmtree(full_test_path)

@pytest.fixture
def cleanup_search(app):
    """Ensure the Elasticsearch index is clean before and after tests."""
    # This runs before the test
    with app.app_context():
        if app.elasticsearch:
            # Delete the index if it exists to start fresh
            if app.elasticsearch.indices.exists(index='post'):
                app.elasticsearch.indices.delete(index='post')
            # Re-create it
            from flaskblog.models import Post
            Post.create_index()
            
    yield
    
    # This runs after the test
    with app.app_context():
        if app.elasticsearch and app.elasticsearch.indices.exists(index='post'):
            app.elasticsearch.indices.delete(index='post')


@pytest.fixture(autouse=True)
def eager_tasks(app):
    # This forces TaskTiger to run tasks immediately in the same process instead of sending them to Redis
    from flaskblog import tiger
    tiger.config['ALWAYS_EAGER'] = True
    yield
    tiger.config['ALWAYS_EAGER'] = False