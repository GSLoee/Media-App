from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

bcrypt = Bcrypt()
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text, nullable=False, unique=True)
    image_url = db.Column(db.Text, default='/static/images/default-pic.png')
    password = db.Column(db.Text, nullable=False)

 # One-to-Many relationship with Saved
    saved_media = db.relationship('Saved', backref='user', lazy=True)

    # One-to-Many relationship with Finished
    finished_media = db.relationship('Finished', backref='user', lazy=True)

    @classmethod 
    def signup(cls, username, password, image_url):
        hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')

        user = User(
            username=username, 
            password=hashed_pwd, 
            image_url=image_url,
        )
        db.session.add(user)
        return user

    @classmethod
    def authenticate(cls, username, password):
        user = cls.query.filter_by(username=username).first()

        if user:
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user
    
        return False  

class Saved(db.Model):
    __tablename__ = 'saved'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    media_id = db.Column(db.Integer, nullable=False)

class Finished(db.Model):
    __tablename__ = 'finished'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    media_id = db.Column(db.Integer, nullable=False)

  

def connect_db(app):
    db.app = app
    db.init_app(app)