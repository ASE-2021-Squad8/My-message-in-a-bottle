from flask import Blueprint, redirect, render_template, request, jsonify

from monolith.database import User, db
from monolith.forms import UserForm
from monolith.auth import check_authenticated, current_user
import monolith.user_query

users = Blueprint("users", __name__)


@users.route("/users")
def _users():
    _users = db.session.query(User)
    return render_template("users.html", users=_users)


@users.route("/account_data", methods=["GET"])
def _user():
    check_authenticated()
    return render_template("account_data.html", user=current_user)


@users.route("/create_user", methods=["POST", "GET"])
def create_user():
    form = UserForm()

    if request.method == "POST":
        if form.validate_on_submit():
            new_user = User()
            form.populate_obj(new_user)
            """
            Password should be hashed with some salt. For example if you choose a hash function x, 
            where x is in [md5, sha1, bcrypt], the hashed_password should be = x(password + s) where
            s is a secret key.
            """
            new_user.set_password(form.password.data)
            db.session.add(new_user)
            db.session.commit()
            return redirect("/users")
        else:
            return render_template("create_user.html", form=form)
    elif request.method == "GET":
        return render_template("create_user.html", form=form)
    else:
        raise RuntimeError("This should not happen!")


@users.route("/user/get_recipients", methods=["GET"])
def get_recipients():
    result = monolith.user_query.get_recipients(getattr(current_user, "id"))
    l = []
    for usr in result:
        l.append(usr.as_dict())
    return jsonify(l)
