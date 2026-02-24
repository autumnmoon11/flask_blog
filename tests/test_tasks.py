import pytest
from unittest.mock import patch
from flaskblog import db, tiger
from flaskblog.models import Post

def test_new_post_queues_indexing_task(client, auth, app, test_user):
    auth.login(email=test_user.email, password='password')
    
    tiger.config['ALWAYS_EAGER'] = False 

    with patch('flaskblog.models.tiger.delay') as mocked_delay:
        response = client.post('/post/new', data={
            'title': 'Testing Tasks',
            'content': 'Content here',
            'category': 'General'
        }, follow_redirects=True)
        
        assert b'Please log in' not in response.data
        assert mocked_delay.called
    
    tiger.config['ALWAYS_EAGER'] = True

def test_delete_post_queues_removal_task(client, auth, app, test_user):
    auth.login(email=test_user.email, password='password')
    
    # 1. Create a post to delete
    with app.app_context():
        # "Merge" test_user into the current session
        user = db.session.merge(test_user)
        
        post = Post(title='Delete Me', content='Temp', author=user)
        db.session.add(post)
        db.session.commit()
        post_id = post.id

    # 2. Setup the mock and run the delete
    from flaskblog import tiger
    tiger.config['ALWAYS_EAGER'] = False
    with patch('flaskblog.models.tiger.delay') as mocked_delay:
        client.post(f'/post/{post_id}/delete', follow_redirects=True)
        
        assert mocked_delay.called
        # Check that we are calling remove_index_task
        args, kwargs = mocked_delay.call_args
        assert args[0].__name__ == 'remove_index_task'
    
    tiger.config['ALWAYS_EAGER'] = True

def test_send_reset_email_queues_task(client, app, test_user):
    tiger.config['ALWAYS_EAGER'] = False

    with patch('flaskblog.users.utils.send_async_email.delay') as mocked_email_delay:
        # Use the actual email of the test_user we just created
        client.post('/reset_password', data={'email': test_user.email})
        assert mocked_email_delay.called

    tiger.config['ALWAYS_EAGER'] = True