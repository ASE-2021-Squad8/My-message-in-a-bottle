from flask import Blueprint, render_template

from monolith.auth import current_user
from monolith.forms import MessageForm

home = Blueprint("home", __name__)


@home.route("/")
def index():
    form = None
    welcome = None

    if current_user is not None and hasattr(current_user, "id"):
        welcome = "Logged In!"
        form = MessageForm()

    return render_template("index.html", welcome=welcome, form=form)


@home.route("/settings")
def settings():
    return render_template("settings.html")
