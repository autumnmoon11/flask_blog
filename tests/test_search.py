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
    
    # 1. Create the post
    client.post('/post/new', data={
        'title': 'Docker Magic', 
        'content': 'Containers are cool', 
        'category': 'Tech'
    }, follow_redirects=True)

    # 2. MANUALLY push to Elasticsearch
    # Since background tasks are unreliable in a synchronous test suite,
    # we fetch the post we just made and index it ourselves.
    from flaskblog.models import Post
    with app.app_context():
        post = Post.query.filter_by(title='Docker Magic').first()
        # We call the indexing method directly
        Post.add_to_index(post) 
        # Refresh ensures ES makes the data available for search IMMEDIATELY
        app.elasticsearch.indices.refresh(index='post')

    # 3. Search for the unique word
    response = client.get('/search?q=Magic')
    
    # Check if the highlight is there
    assert b'Docker <em>Magic</em>' in response.data

def test_search_intelligence_and_highlights(client, app, auth, test_user, cleanup_search):
    """Test that stemming (post/posted) and highlighting work together."""
    auth.login()
    
    # 1. Create the post
    client.post('/post/new', data={
        'title': 'Building with Flask', 
        'content': 'I am currently building a blog platform.', 
        'category': 'Tech'
    }, follow_redirects=True)
    
    # 2. MANUALLY push to Elasticsearch 
    # This replaces the sleep(1) with a guaranteed action
    from flaskblog.models import Post
    with app.app_context():
        post = Post.query.filter_by(title='Building with Flask').first()
        Post.add_to_index(post)
        app.elasticsearch.indices.refresh(index='post')

    # 3. Test Stemming & Highlighing: Search for 'build' (root) to find 'building' (stored)
    response = client.get('/search?q=build')
    
    # Lowercase the data for easier assertion comparison
    response_text = response.data.lower()
    assert b'<em>building</em>' in response_text
    assert b'flask' in response_text