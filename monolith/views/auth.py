from flask import Blueprint, redirect, render_template
from flask_login import login_user, logout_user

from monolith.database import User, db
from monolith.forms import LoginForm

auth = Blueprint("auth", __name__)


@auth.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email, password = form.data["email"], form.data["password"]
        q = db.session.query(User).filter(User.email == email)
        user = q.first()
        if not user.is_active:
            # If the user is not active, check if it has been banned or the account is deleted
            if user.reports >= 3:
                return render_template(
                    "login.html",
                    form=form,
                    error="You have been banned and you account has been deleted. All your messages will be delivered anyway.",
                )
            else:
                return render_template(
                    "login.html",
                    form=form,
                    error="You unregistered from the service. All your messages will be delivered anyway.",
                )
        if user is not None and user.authenticate(password):
            login_user(user)
            return redirect("/")
    return render_template("login.html", form=form)


@auth.route("/logout")
def logout():
    logout_user()
    return redirect("/")
