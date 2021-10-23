import functools

from flask import abort
from flask_login import LoginManager, current_user

from monolith.database import User

login_manager = LoginManager()


def check_authenticated():
    if current_user is None or not hasattr(current_user, "id"):
        abort(401, "Unauthenticated API usage is not allowed.")


def admin_required(func):
    @functools.wraps(func)
    def _admin_required(*args, **kw):
        admin = current_user.is_authenticated and current_user.is_admin
        if not admin:
            return login_manager.unauthorized()
        return func(*args, **kw)

    return _admin_required


@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(user_id)
    if user is not None:
        user._authenticated = True
    return user
