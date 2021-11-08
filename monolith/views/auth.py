from flask import Blueprint, redirect, render_template
from flask_login import login_user, logout_user

from monolith.database import User, db
from monolith.forms import LoginForm

auth = Blueprint("auth", __name__)


@auth.route("/login", methods=["GET", "POST"])
def login():
    """Login with a user

    :returns: the rendered template of the page
    :rtype: text
    """
    form = LoginForm()
    if form.validate_on_submit():
        # check the fields and login if successful
        email, password = form.data["email"], form.data["password"]
        q = db.session.query(User).filter(User.email == email)
        user = q.first()
        if user is not None:
            if user.authenticate(password):
                if user.is_active:
                    login_user(user)
                    return redirect("/")
                else:
                    # if the user is not active, check if it has been banned or the account is deleted
                    errorstring = ""
                    if user.reports >= 3:
                        errorstring = (
                            "You have been banned and you account has been deleted."
                        )
                    else:
                        errorstring = "You unregistered from the service."
                    return render_template(
                        "login.html",
                        form=form,
                        error=errorstring
                        + " All your messages will be delivered anyway.",
                    )
            else:
                form.password.errors.append("Invalid password")
        else:
            form.email.errors.append("Unknown email address")

    return render_template("login.html", form=form)


@auth.route("/logout")
def logout():
    logout_user()
    return redirect("/")
