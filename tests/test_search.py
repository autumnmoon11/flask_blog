import pytest
from flaskblog.models import Post

def test_search_results_page(client, app, cleanup_search):
    """Test that the search route returns 200."""
    response = client.get('/search?q=test')
    assert response.status_code == 200

def test_search_empty_query(client):
    """Test that an empty query redirects home."""
    response = client.get('/search?q=', follow_redirects=True)
    assert b"Latest Posts" in response.data

def test_elasticsearch_integration(client, app, auth, test_user, cleanup_search):
    """Test that a created post is actually searchable."""
    auth.login()
    # Create a post
    response = client.post('/post/new', data={'title': 'Docker Magic', 'content': 'Containers are cool', 'category': 'Tech'}, follow_redirects=True)

    if b'Your post has been created!' not in response.data:
        print(response.data.decode())

    assert response.status_code == 200
    assert b'Your post has been created!' in response.data
    
    # Force Elasticsearch to refresh the index immediately
    with app.app_context():
        import time
        # Give the event listener a tiny heartbeat to fire
        time.sleep(0.5) 
        # Manually refresh the index so it's searchable NOW
        app.elasticsearch.indices.refresh(index='post')
    
    # Search for the unique word
    response = client.get('/search?q=Magic')
    assert b'Docker Magic' in response.data