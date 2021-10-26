from flask import Blueprint, redirect, render_template, request, jsonify
from flask_login import logout_user


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
            return redirect("/login")
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
    # delete unwanted data
    for usr in result:
        d = usr.as_dict()
        d.pop("password")
        d.pop("dateofbirth")
        d.pop("is_active")
        d.pop("is_admin")
        d.pop("firstname")
        d.pop("lastname")
        d.pop("reports")
        l.append(d)

    return jsonify(l)


@users.route("/unregister")
def unregister():
    check_authenticated()
    userid = getattr(current_user, "id")
    logout_user()
    user = User.query.filter(User.id == userid).first()
    user.is_active = False
    db.session.commit()
    return redirect("/")


@users.route("/report_user", methods=["GET", "POST"])
def report():
    check_authenticated()
    if request.method == "GET":
        return render_template("report_user.html")
    else:
        mail = str(request.form["useremail"])
        if mail is not None and not mail.isspace():
            user = User.query.filter(User.email == mail).first()
            if user is None:
                return render_template(
                    "report_user.html",
                    error=mail + " does not exist.",
                    reported="",
                )
            user.reports += 1
            banned = ""
            # If the user has 3 or more reports ban the account deactivating it
            if user.reports >= 3:
                user.is_active = False
                banned = " and banned"
            db.session.commit()
            return render_template(
                "report_user.html",
                error="",
                reported=mail + " has been reported" + banned + ".",
            )
        else:
            return render_template(
                "report_user.html",
                error="You have to specify an email to report a user.",
                reported="",
            )
