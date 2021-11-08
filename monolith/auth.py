from flask import abort
from flask_login import LoginManager, current_user

from monolith.database import User

login_manager = LoginManager()


def check_authenticated():
    if current_user is None or not hasattr(current_user, 'id'):
        abort(401, "Unauthenticated API usage is not allowed.")


@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(user_id)
    if user is not None:
        user._authenticated = True
    return user
