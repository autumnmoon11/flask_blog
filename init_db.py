from flaskblog import app, db

def initialize():
    with app.app_context():
        db.create_all()
        print("Database tables initialized successfully!")

if __name__ == "__main__":
    initialize()