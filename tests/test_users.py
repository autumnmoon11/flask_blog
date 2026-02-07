from flaskblog.models import User
from flaskblog import db, bcrypt


def test_user_registration(client, app):
    """Test that a user can register."""
    response = client.post('/register', data={
        'username': 'testuser',
        'email': 'test@test.com',
        'password': 'password',
        'confirm_password': 'password'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    with app.app_context():
        from flaskblog.models import User
        user = User.query.filter_by(username='testuser').first()
        assert user is not None
        assert user.email == 'test@test.com'

def test_login(client, app):
    # First, I need to get a test user into my in-memory database
    with app.app_context():
        # I'll hash the password here so it matches my app's security logic
        hashed_pw = bcrypt.generate_password_hash('password123').decode('utf-8')
        user = User(username='NoahTest', email='noah@test.com', password=hashed_pw)
        db.session.add(user)
        db.session.commit()

    # Now I'll try to log in with the credentials I just created
    # I'm using follow_redirects so I can see the final page after the login redirect
    response = client.post('/login', data={
        'email': 'noah@test.com',
        'password': 'password123',
        'remember': False
    }, follow_redirects=True)

    # I expect to be back on the home page with a success message
    assert response.status_code == 200
    assert b"You have been logged in!" in response.data

def test_logout(client, app):
    # First I'll log in to establish a session
    with app.app_context():
        hashed_pw = bcrypt.generate_password_hash('password123').decode('utf-8')
        user = User(username='LogoutTester', email='logout@test.com', password=hashed_pw)
        db.session.add(user)
        db.session.commit()

    # I'll perform the login action
    client.post('/login', data={
        'email': 'logout@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Now I'll act by hitting the logout route
    response = client.get('/logout', follow_redirects=True)

    # I'll assert that the session is cleared and I see the 'Login' link again
    assert response.status_code == 200
    assert b"Login" in response.data
    assert b"Logout" not in response.data