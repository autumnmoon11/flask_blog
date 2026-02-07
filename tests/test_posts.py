def test_create_post_redirect_anon(client):
    """Test that unauthorized users are redirected when trying to create a post."""
    # 1. Act: Try to go to the 'new post' page without logging in
    response = client.get('/post/new', follow_redirects=True)

    # 2. Assert: Check that we ended up at the login page
    # Note: Flask-Login redirects to 'users.login' (which maps to /login)
    assert response.status_code == 200
    assert b"Please log in to access this page." in response.data