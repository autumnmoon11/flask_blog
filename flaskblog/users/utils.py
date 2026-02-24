import os
import secrets
from PIL import Image
from flask import url_for, current_app
from flaskblog.tasks import send_async_email
from flaskblog import tiger


def save_picture(form_picture, old_picture=None):
    # Generate a random name to prevent filename collisions
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext

    # Retrieve upload folder from config to ensure test/prod isolation
    upload_folder = current_app.config.get('UPLOADED_PHOTOS_DEST', 'static/profile_pics')
    picture_path = os.path.join(current_app.root_path, upload_folder, picture_fn)

    # Resize and thumbnail image to 125x125 for storage efficiency
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    # Delete existing profile picture from filesystem if not the default image
    if old_picture and old_picture != 'default.jpg':
        old_picture_path = os.path.join(current_app.root_path, 'static', 'profile_pics', old_picture)
        if os.path.exists(old_picture_path):
            os.remove(old_picture_path)

    return picture_fn


def send_reset_email(user):
    token = user.get_reset_token()

    subject = 'Password Reset Request'
    sender = 'noreply@demo.com'
    recipients = [user.email]
    text_body = f'''To reset your password, visit the following link:
{url_for('users.reset_token', token=token, _external=True)}

If you did not make this request, then simply ignore this email and no changes will be made.
'''

    # Hand it off to TaskTiger/Redis
    send_async_email.delay(subject, sender, recipients, text_body)