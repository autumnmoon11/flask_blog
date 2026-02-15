from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flaskblog.config import Config
from elasticsearch import Elasticsearch
import click
from flask.cli import with_appcontext

# 1. Initialize extensions without the 'app' yet
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'users.login'
login_manager.login_message_category = 'info'
mail = Mail()
migrate = Migrate()


def create_app(config_class=Config):
    app = Flask(__name__)
    
    # Load configurations
    app.config.from_object(config_class)

    # Bind extensions to the app
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    # Add Elasticsearch to the app instance
    app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']]) \
        if app.config['ELASTICSEARCH_URL'] else None


    @app.cli.command("reindex")
    @with_appcontext
    def reindex():
        """Sync all database posts with the Elasticsearch index."""
        from flaskblog.models import Post
        from flaskblog.search import add_to_index
        
        # Optionally delete the index first to start fresh
        # app.elasticsearch.indices.delete(index='post', ignore=[400, 404])
        
        count = 0
        for post in Post.query.all():
            add_to_index('post', post)
            count += 1
        
        click.echo(f"Successfully indexed {count} posts to Elasticsearch.")

    # Import and Register Blueprints inside the function
    from flaskblog.users.routes import users
    from flaskblog.posts.routes import posts
    from flaskblog.main.routes import main
    from flaskblog.errors.handlers import errors  
    app.register_blueprint(users)
    app.register_blueprint(posts)
    app.register_blueprint(main)
    app.register_blueprint(errors)

    return app