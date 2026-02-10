from flaskblog.models import Post, User
from flaskblog import db

def test_create_post_redirect_anon(client):
    """Test that unauthorized users are redirected when trying to create a post."""
    # 1. Act: Try to go to the 'new post' page without logging in
    response = client.get('/post/new', follow_redirects=True)

    # 2. Assert: Check that we ended up at the login page
    # Note: Flask-Login redirects to 'users.login' (which maps to /login)
    assert response.status_code == 200
    assert b"Please log in to access this page." in response.data

def test_update_post_category(client, app):
    # Start by creating a user and a post with 'General' category
    with app.app_context():
        # Use the bcrypt helper we established earlier to ensure log in functionality
        from flaskblog import bcrypt
        hashed_pw = bcrypt.generate_password_hash('password').decode('utf-8')
        user = User(username='UpdateTester', email='update@test.com', password=hashed_pw)
        db.session.add(user)
        db.session.commit()
        
        post = Post(title='Old Title', content='Old Content', author=user, category='General')
        db.session.add(post)
        db.session.commit()
        post_id = post.id

    # Log in
    client.post('/login', data={'email': 'update@test.com', 'password': 'password'}, follow_redirects=True)

    # Changing the category from 'General' to 'Tech'
    response = client.post(f'/post/{post_id}/update', data={
        'title': 'Updated Title',
        'content': 'Updated Content',
        'category': 'Tech'
    }, follow_redirects=True)

    # Assert that the database actually updated the category
    assert response.status_code == 200
    with app.app_context():
        updated_post = db.get_or_404(Post, post_id)
        assert updated_post.category == 'Tech'