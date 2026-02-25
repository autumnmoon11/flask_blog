import pytest
import io
from PIL import Image
from unittest.mock import patch
from flaskblog import db, tiger
from flaskblog.models import Post, User
from flaskblog.tasks import process_profile_pic_task
import os

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

def test_upload_queues_image_processing(client, auth, app, test_user):
    auth.login(email=test_user.email, password='password')
    
    # 1. Create a dummy image in memory
    file_name = 'test.jpg'
    image = Image.new('RGB', (200, 200), color='red')
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    
    # 2. Mock the tiger delay to ensure the task is queued
    tiger.config['ALWAYS_EAGER'] = False
    with patch('flaskblog.users.routes.tiger.delay') as mocked_delay:
        client.post('/account', data={
            'username': 'UpdatedName',
            'email': 'test@test.com',
            'picture': (img_byte_arr, file_name)
        }, content_type='multipart/form-data', follow_redirects=True)
        
        assert mocked_delay.called
        # Verify the task function name
        assert mocked_delay.call_args[0][0].__name__ == 'process_profile_pic_task'
    
    tiger.config['ALWAYS_EAGER'] = True

def test_image_processing_task_updates_db(app, test_user):
    # This test runs the task function directly to verify the logic
    # 1. Setup paths and a "raw" image in the processing folder
    raw_filename = 'raw_test.jpg'
    proc_dir = os.path.join(app.root_path, 'static/profile_pics/processing')
    if not os.path.exists(proc_dir):
        os.makedirs(proc_dir)
        
    temp_path = os.path.join(proc_dir, raw_filename)
    image = Image.new('RGB', (500, 500), color='blue')
    image.save(temp_path)

    # 2. Run the task manually
    process_profile_pic_task(test_user.id, raw_filename, 'default.jpg')

    # 3. Assertions
    with app.app_context():
        # Force the session to refresh data from the DB
        db.session.expire_all()

        user = db.session.get(User, test_user.id)
        # Check DB update
        assert user.image_file == raw_filename
        
        # Check file resizing
        final_path = os.path.join(app.root_path, 'static/profile_pics', raw_filename)
        assert os.path.exists(final_path)
        with Image.open(final_path) as img:
            assert img.size == (125, 125)
            
        # Check cleanup
        assert not os.path.exists(temp_path)