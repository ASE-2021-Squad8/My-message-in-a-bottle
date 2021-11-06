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
def to_error_page(msg):  # pragma: no cover
    return render_template(
        "error_page.html", message="Ooops something went wrong! {0}".format(msg)
    )


@home.route("/settings")
def settings():  # pragma: no cover
    return render_template("settings.html")
