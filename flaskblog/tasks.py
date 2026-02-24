from flask_mail import Message
from flaskblog import mail, tiger


@tiger.task(retry=True, unique=True)
def update_index_task(model_id):
    from flaskblog import create_app, db
    from flaskblog.models import Post
    app = create_app()
    with app.app_context():
        # Force a session refresh to see the latest DB state
        db.session.expire_all()
        post = db.session.get(Post, model_id)
        if post:
            Post.add_to_index(post)

@tiger.task(retry=True)
def remove_index_task(post_id):
    from flaskblog.search import remove_from_index
    # Tell Elasticsearch to delete the document with this ID
    remove_from_index('post', post_id)

@tiger.task(retry=True, unique=True)
def send_async_email(subject, sender, recipients, text_body, html_body=None):
    from flaskblog import create_app
    app = create_app()
    with app.app_context():
        msg = Message(subject, sender=sender, recipients=recipients)
        msg.body = text_body
        msg.html = html_body
        mail.send(msg)