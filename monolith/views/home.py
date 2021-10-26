from flask import Blueprint, render_template

from monolith.auth import current_user
from monolith.forms import MessageForm

home = Blueprint("home", __name__)


@home.route("/")
def index():
    form = None

    if current_user is not None and hasattr(current_user, "id"):
        form = MessageForm()

    return render_template("index.html", form=form)


@home.route("/error_page")
def to_error_page():
    return render_template("error_page.html", message="Fatal error")


@home.route("/settings")
def settings():
    return render_template("settings.html")
