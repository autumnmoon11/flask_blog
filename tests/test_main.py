from flaskblog.models import Post, User
from flaskblog import db

def test_home_page(client):
    """Test that the home page loads correctly."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Flask Blog" in response.data # Checks for text on the page

def test_about_page(client):
    """Test that the about page loads correctly."""
    response = client.get('/about')
    assert response.status_code == 200

def test_home_page_with_posts(client, app):
    """Test that posts appear on the home page."""
    with app.app_context():
        # 1. Arrange: Create a fake user and a post
        user = User(username='Tester', email='test@test.com', password='password')
        db.session.add(user)
        db.session.commit()
        
        post = Post(title='Testing Post Title', content='Testing Content', author=user)
        db.session.add(post)
        db.session.commit()

    # 2. Act: Visit the home page
    response = client.get('/')

    # 3. Assert: Check if the title we created is in the HTML
    assert response.status_code == 200
    assert b"Testing Post Title" in response.data