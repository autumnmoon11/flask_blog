import jwt
from flask import current_app
from flaskblog import db, login_manager
from datetime import datetime, timedelta, timezone
from flask_login import UserMixin
from flaskblog.search import add_to_index, remove_from_index

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

    @classmethod
    def before_commit(cls, session):
        # Store pending changes in the session for use after commit
        session._changes = {
            'add': [obj for obj in session.new if isinstance(obj, cls)],
            'update': [obj for obj in session.dirty if isinstance(obj, cls)],
            'delete': [obj for obj in session.deleted if isinstance(obj, cls)]
        }

    @classmethod
    def after_commit(cls, session):
        # Sync database changes to Elasticsearch index
        for obj in session._changes['add']:
            add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            remove_from_index(obj.__tablename__, obj)
        session._changes = None


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
    

# Register the listeners to the SQLAlchemy session
db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)