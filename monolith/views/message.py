from flask import Blueprint, render_template

from monolith.database import User, db

message = Blueprint('message', __name__)


@message.route('/send_message')
def _send():
    # Only displaying recipients list for now
    _users = db.session.query(User)
    return render_template("send_message.html", users=_users)
