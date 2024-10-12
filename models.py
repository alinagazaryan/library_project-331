
import sqlalchemy as sa
from flask import url_for, current_app
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.dialects.mysql import YEAR
import markdown
import bleach

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData
from datetime import datetime
from user_policy import UsersPolicy


class Base(DeclarativeBase):
  metadata = MetaData(naming_convention={
        "ix": 'ix_%(column_0_label)s',
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    })

db = SQLAlchemy(model_class=Base)



class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(256), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    last_name = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(256), nullable=False)
    middle_name = db.Column(db.String(256))
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)

    role = db.relationship("Role")
    reviews = db.relationship("Review")

    def is_admin(self):
        return self.role_id == current_app.config['ADMIN_ROLE_ID']

    def is_moderator(self):
        return self.role_id == current_app.config['MODERATOR_ROLE_ID']

    def is_user(self):
        return self.role_id == current_app.config['USER_ROLE_ID']

    def can(self, action, record=None):
        users_policy = UsersPolicy(record)
        method = getattr(users_policy, action, None)
        if method:
            return method()
        return False

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        return " ".join([self.last_name,
                         self.first_name,
                         self.middle_name or ""])

    
    def __repr__(self):
        return "<User %r>" % self.login
    

class Role(db.Model):

    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return "<Role %r>" % self.login
    
books_genres = db.Table(
    "books_genres",
    db.Column("book_id", db.Integer, db.ForeignKey("books.id", ondelete='CASCADE')),
    db.Column("genre_id", db.Integer, db.ForeignKey("genres.id", ondelete='CASCADE')),
)

class Book(db.Model):
    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    short_desc = db.Column(db.Text, nullable=False)
    year_release = db.Column(db.Integer, nullable=False)
    publisher = db.Column(db.String(256), nullable=False)
    author = db.Column(db.String(256), nullable=False)
    pages_volume = db.Column(db.Integer, nullable=False)
    image_id = db.Column(db.String(256), db.ForeignKey("images.id"), nullable=False)
    rating_sum = db.Column(db.Integer, nullable=False, default=0)
    rating_num = db.Column(db.Integer, nullable=False, default=0)
    genres = db.relationship("Genre", secondary=books_genres, backref="books")
    image = db.relationship("Image", backref="bookss")
    reviews = db.relationship("Review", backref="booksss")
   

    def prepare_to_save(self):
        self.short_desc = bleach.clean(self.short_desc)

    def prepare_to_html(self):
        self.short_desc = markdown.markdown(self.short_desc)

    @property
    def rating(self):
        if self.rating_num > 0:
            return self.rating_sum / self.rating_num
        return 0

    def __repr__(self):
        return "<Book %r>" % self.name

    

class Genre(db.Model):

    __tablename__ = "genres"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), unique=True, nullable=False)

    def __repr__(self):
        return "<Genre %r>" % self.name
    

class Image(db.Model):

    __tablename__ = "images"

    id = db.Column(db.String(256), primary_key=True)
    file_name = db.Column(db.String(256), nullable=False)
    mime_type = db.Column(db.String(256), nullable=False)
    md5_hash = db.Column(db.String(256), nullable=False, unique=True)

    @property
    def url(self):
        return url_for("image", image_id=self.id)

    def __repr__(self):
        return "<Image %r>" % self.file_name


class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    book = db.relationship('Book', back_populates='reviews')
    user = db.relationship('User', back_populates='reviews')

    def prepare_to_save(self):
        self.text = bleach.clean(self.text)

    def prepare_to_html(self):
        self.text = markdown.markdown(self.text)

    def __repr__(self):
        return f'<Review {self.rating} by User {self.user_id}>'

    @property
    def rating_name(self):
        return self.rating.name
    

class AllBookVisits(db.Model):
    __tablename__ = 'all_book_visits'

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    book = db.relationship('Book')
    user = db.relationship('User')

    def __repr__(self):
        return '<Visit %r>' % self.id
    

class LastBookVisits(db.Model):
    __tablename__ = 'last_book_visits'

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    book = db.relationship('Book')  
    user = db.relationship('User')

    def __repr__(self):
        return '<Visit %r>' % self.id
