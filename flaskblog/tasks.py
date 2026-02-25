import os
from flask_mail import Message
from flaskblog import mail, tiger, create_app, db
from flaskblog.models import Post
from flaskblog.search import remove_from_index
from PIL import Image
from flask import current_app


@tiger.task(retry=True, unique=True)
def update_index_task(model_id):
    app = create_app()
    with app.app_context():
        # Force a session refresh to see the latest DB state
        db.session.expire_all()
        post = db.session.get(Post, model_id)
        if post:
            Post.add_to_index(post)

@tiger.task(retry=True)
def remove_index_task(post_id):
    # Tell Elasticsearch to delete the document with this ID
    remove_from_index('post', post_id)

@tiger.task(retry=True, unique=True)
def send_async_email(subject, sender, recipients, text_body, html_body=None):
    app = create_app()
    with app.app_context():
        msg = Message(subject, sender=sender, recipients=recipients)
        msg.body = text_body
        msg.html = html_body
        mail.send(msg)

@tiger.task(retry=True)
def process_profile_pic_task(user_id, picture_fn, old_picture):
    from flaskblog.models import User
    from flaskblog import create_app, db

    app = current_app._get_current_object() if current_app else create_app()
    
    with app.app_context():
        # Define paths
        temp_path = os.path.join(app.root_path, 'static/profile_pics/processing', picture_fn)
        final_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)
        
        # Resize the image (Heavy Lifting)
        try:
            output_size = (125, 125)
            i = Image.open(temp_path)
            i.thumbnail(output_size)
            i.save(final_path)
            
            # Update the database
            user = db.session.get(User, user_id)
            if user:
                user.image_file = picture_fn
                db.session.commit()
                
            # Cleanup: Remove the raw temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
            # Cleanup: Remove old picture if it's not the default
            if old_picture and old_picture != 'default.jpg':
                old_path = os.path.join(app.root_path, 'static/profile_pics', old_picture)
                if os.path.exists(old_path):
                    os.remove(old_path)
        except Exception as e:
            # Might want to log this in a real production app
            print(f"Error processing image: {e}")