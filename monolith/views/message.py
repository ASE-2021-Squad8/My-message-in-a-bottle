from flask import Blueprint, render_template

from monolith.database import User, db

message = Blueprint('message', __name__)


def get_recipients():
	return db.session.query(User)


@message.route('/sendmsg')
def _send():
    _users = get_recipients()
    return render_template("send_message.html", users=_users)
