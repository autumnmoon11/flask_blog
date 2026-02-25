import os
import secrets
from flask import url_for, current_app
from flaskblog.tasks import send_async_email
from flaskblog import tiger


def save_picture(form_picture):
    """Saves the raw uploaded image to a temporary processing folder."""
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext

    # Save to a 'processing' subdirectory so the main folder stays clean
    upload_folder = os.path.join(current_app.root_path, 'static/profile_pics/processing')
    
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        
    picture_path = os.path.join(upload_folder, picture_fn)
    form_picture.save(picture_path)

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