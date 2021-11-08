from datetime import datetime
from dataclasses import dataclass
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql.schema import ForeignKey
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(db.Model):
    """User object for registered users"""

    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.Unicode(128), nullable=False)
    firstname = db.Column(db.Unicode(128))
    lastname = db.Column(db.Unicode(128))
    password = db.Column(db.Unicode(128))
    dateofbirth = db.Column(db.DateTime)
    reports = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    points = db.Column(db.Integer, default=0)
    content_filter = db.Column(db.Boolean, default=False)

    def __init__(self, *args, **kw):
        super(User, self).__init__(*args, **kw)
        self._authenticated = False

    def set_password(self, password):
        """Changes the user's password

        :param password: the new password
        :type password: str
        """
        self.password = generate_password_hash(password)

    @property
    def is_authenticated(self):
        """Checks if the user is logged in

        :returns: True when logged in, False otherwise
        :rtype: bool
        """

        return self._authenticated

    def authenticate(self, password):
        """Authenticates the user using the provided password

        :param password: the user's password
        :type password: str
        :returns: True on success, False otherwise (wrong password)
        :rtype: bool
        """

        checked = check_password_hash(self.password, password)
        self._authenticated = checked
        return self._authenticated

    def get_id(self):
        return self.id

    def get_isactive(self):
        return self.is_active

    def get_firstname(self):
        return self.firstname

    def get_lastname(self):
        return self.lastname


@dataclass
class Message(db.Model):
    """Final message object, used for initial delivery, drafts, composition"""

    message_id: int
    text: str
    sender: int
    recipient: int
    media: str
    delivery_date: datetime
    is_draft: bool
    is_delivered: bool
    is_read: bool
    is_deleted: bool

    __tablename__ = "message"

    message_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    text = db.Column(db.String())
    delivery_date = db.Column(db.DateTime)
    sender = db.Column(db.Integer, ForeignKey(User.id))
    recipient = db.Column(db.Integer, ForeignKey(User.id))
    media = db.Column(db.String(255))
    is_draft = db.Column(db.Boolean, default=True)
    is_delivered = db.Column(db.Boolean, default=False)
    is_read = db.Column(db.Boolean, default=False)
    # to take into account only to received message
    is_deleted = db.Column(db.Boolean, default=False)

    def __init__(self, *args, **kw):
        super(Message, self).__init__(*args, **kw)

    def get_recipient(self):
        return self.recipient


@dataclass
class BlackList(db.Model):
    """A user's blacklist"""

    __tablename__ = "blacklist"

    owner: int
    member: int

    # one blacklist per user
    owner = db.Column(db.Integer, ForeignKey(User.id), primary_key=True)
    member = db.Column(db.Integer, ForeignKey(User.id), primary_key=True)
