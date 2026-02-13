import io
from PIL import Image
from flask import url_for
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

def test_update_account_with_picture(app, client, auth, test_user, cleanup_test_images):
    # Authenticate via test_user fixture using plain text password
    auth.login(email=test_user.email, password='password')
    
    # Pre-generate target URL to avoid context build errors in client.post
    with app.app_context():
        target_url = url_for('users.account')
    
    # Generate mock image in memory to simulate user file upload
    file_name = "test_profile.jpg"
    data = io.BytesIO()
    img = Image.new('RGB', (100, 100), color='red')
    img.save(data, format='JPEG')
    data.seek(0) # Reset stream to start for reading

    # Post update request containing new username and profile picture
    response = client.post(target_url, data={
        'username': 'UpdatedUser',
        'email': 'updated@email.com',
        'picture': (data, file_name),
        'submit': True
    }, follow_redirects=True)


    assert response.status_code == 200
    assert b'Your account has been updated!' in response.data
    
    # Query database using scalar execution to confirm record persistence
    updated_user = db.session.execute(
        db.select(User).filter_by(email='updated@email.com')
        ).scalar_one()
    assert updated_user.image_file != 'default.jpg'
    assert updated_user.image_file.endswith('.jpg')