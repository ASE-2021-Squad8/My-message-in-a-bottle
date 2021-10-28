from dataclasses import dataclass
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql.schema import ForeignKey
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(db.Model):

    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.Unicode(128), nullable=False)
    firstname = db.Column(db.Unicode(128))
    lastname = db.Column(db.Unicode(128))
    password = db.Column(db.Unicode(128))
    dateofbirth = db.Column(db.DateTime)
    reports = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    # state if the contnet_filter is active
    content_filter = db.Column(db.Boolean, default=False)

    is_anonymous = False

    def __init__(self, *args, **kw):
        super(User, self).__init__(*args, **kw)
        self._authenticated = False

    def set_password(self, password):
        self.password = generate_password_hash(password)

    @property
    def is_authenticated(self):
        return self._authenticated

    def authenticate(self, password):
        checked = check_password_hash(self.password, password)
        self._authenticated = checked
        return self._authenticated

    def get_id(self):
        return self.id

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def get_isactive(self):
        return self.is_active

    def get_firstname(self):
        return self.firstname

    def get_lastname(self):
        return self.lastname


@dataclass
class Message(db.Model):
    message_id: int
    text: str
    sender: int
    recipient: int
    is_draft: bool
    is_delivered: bool
    is_read: bool
    is_deleted: bool

    __tablename__ = "message"

    message_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    text = db.Column(db.String(4096))

    sender = db.Column(db.Integer, ForeignKey(User.id))
    recipient = db.Column(db.Integer, ForeignKey(User.id))
    is_draft = db.Column(db.Boolean, default=True)
    is_delivered = db.Column(db.Boolean, default=False)
    is_read = db.Column(db.Boolean, default=False)
    # to take into account only to received message
    is_deleted = db.Column(db.Boolean, default=False)

    def __init__(self, *args, **kw):
        super(Message, self).__init__(*args, **kw)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def get_sender(self):
        return self.sender

    def get_id(self):
        return self.message_id

    def get_text(self):
        return self.text


class Message_to_send(db.Model):
    message_id: int
    text: str
    sender: int
    receiver: int
    __tablename__ = "Message_to_send"

    message_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    text = db.Column(db.String(4096))

    sender = db.Column(db.Integer, ForeignKey(User.id))
    receiver = db.Column(db.Integer, ForeignKey(User.id))

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Black_list(db.Model):
    owner: int
    member: int
    __tablename__ = "Black_list"
    # user can own only one black list
    owner = db.Column(db.Integer, ForeignKey(User.id), primary_key=True)
    member = db.Column(db.Integer, ForeignKey(User.id), primary_key=True)
