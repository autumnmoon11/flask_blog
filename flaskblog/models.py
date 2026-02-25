import jwt
from flask import current_app
from flaskblog import db, login_manager
from datetime import datetime, timedelta, timezone
from flask_login import UserMixin
from flaskblog.search import add_to_index, remove_from_index
from flaskblog import tiger


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        # Query the specific index for this model
        if not current_app.elasticsearch:
            return [], 0, []
        if not current_app.elasticsearch.indices.exists(index=cls.__tablename__):
            cls.create_index()  # Proactively fix the missing index
            return [], 0, []
        search = current_app.elasticsearch.search(
            index=cls.__tablename__,
            query={'multi_match': {'query': expression, 'fields': ['*'], 'fuzziness': 'AUTO'}},
            highlight={'fields': {'title': {},'content': {}}},
            from_=(page - 1) * per_page,
            size=per_page
        )
        ids = [int(hit['_id']) for hit in search['hits']['hits']]
        total = search['hits']['total']['value']
        hits = search['hits']['hits']

        return ids, total, hits
    
    @classmethod
    def add_to_index(cls, model):
        add_to_index(cls.__tablename__, model)

    @classmethod
    def remove_from_index(cls, model):
        remove_from_index(cls.__tablename__, model)

    @classmethod
    def create_index(cls):
        index = cls.__tablename__
        # Define the specialized settings for English stemming
        settings = {
            "settings": {
                "analysis": {
                    "analyzer": {
                        "default": {
                            "type": "english"
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "title": {"type": "text", "analyzer": "english"},
                    "content": {"type": "text", "analyzer": "english"}
                }
            }
        }
        
        if not current_app.elasticsearch.indices.exists(index=index):
            current_app.elasticsearch.indices.create(index=index, body=settings)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"
    
    def get_reset_token(self, expires_sec=1800):
        # Create a payload with an expiration time
        payload = {
            'user_id': self.id,
            'exp': datetime.now(tz=timezone.utc) + timedelta(seconds=expires_sec)
        }
        return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_reset_token(token):
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            return db.session.get(User, payload['user_id'])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None


class Post(SearchableMixin, db.Model):
    __searchable__ = ['title', 'content'] # Define fields for Elasticsearch
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(20), nullable=False, default='General')

    def __repr__(self):
        return f"Post('{self.title}', '{self.date_posted}')"
    
    @staticmethod
    def after_insert(mapper, connection, target):
        from flaskblog.tasks import update_index_task
        tiger.delay(update_index_task, args=(target.id,))

    @staticmethod
    def after_update(mapper, connection, target):
        from flaskblog.tasks import update_index_task
        tiger.delay(update_index_task, args=(target.id,))

    @staticmethod
    def after_delete(mapper, connection, target):
        from flaskblog.tasks import remove_index_task
        tiger.delay(remove_index_task, args=(target.id,))
    

# Register the listeners to the SQLAlchemy session
db.event.listen(Post, 'after_insert', Post.after_insert)
db.event.listen(Post, 'after_update', Post.after_update)
db.event.listen(Post, 'after_delete', Post.after_delete)