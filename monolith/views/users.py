from flask import (
    Blueprint,
    json,
    redirect,
    render_template,
    request,
    jsonify,
    make_response,
    abort
)

from flask_login import logout_user


from monolith.database import User, db
from monolith.forms import BlackListForm, UserForm, ChangePassForm
from monolith.auth import check_authenticated, current_user
import monolith.user_query
import datetime

users = Blueprint("users", __name__)


@users.route("/users")
def _users():
    _users = db.session.query(User)
    return render_template("users.html", users=_users)


@users.route("/account_data", methods=["GET"])
def _user():
    check_authenticated()
    data = current_user.dateofbirth
    date_of_birth = data.strftime("%a, %d %B, %Y")
    return render_template("account_data.html", user=current_user, date=date_of_birth)


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
    l = [{"id": i.id, "email": i.email} for i in result]
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


@users.route("/update_data", methods=["POST", "GET"])
def change_data_user():
    check_authenticated()
    form = UserForm()

    if request.method == "POST":
        userid = getattr(current_user, "id")
        user = User.query.filter(User.id == userid).first()
        user.firstname = request.form["textfirstname"]
        user.lastname = request.form["textlastname"]
        user.email = request.form["textemail"]
        data = request.form["textbirth"]
        date_as_datetime = datetime.datetime.strptime(data, "%Y-%m-%d")
        user.dateofbirth = date_as_datetime

        if (
            user.firstname == ""
            or user.lastname == ""
            or user.email == ""
            or user.dateofbirth == ""
        ):
            return render_template(
                "edit_profile.html",
                form=form,
                user=current_user,
                error="All fields must be completed!",
            )

        db.session.commit()
        return redirect("/account_data")
    elif request.method == "GET":
        return render_template("edit_profile.html", form=form, user=current_user)
    else:
        raise RuntimeError("This should not happen!")


@users.route("/reset_password", methods=["POST", "GET"])
def change_pass_user():
    check_authenticated()
    form = ChangePassForm()
    stringError = ""

    if request.method == "POST":
        userid = getattr(current_user, "id")
        user = User.query.filter(User.id == userid).first()
        current_password = form.currentpassword.data
        new_pass = form.newpassword.data
        confirmpass = form.confirmpassword.data

        if user.authenticate(current_password):
            if new_pass == confirmpass:
                user.set_password(new_pass)
            else:
                stringError = "Check the correctness of the confirmation password!"
                return render_template(
                    "reset_password.html", form=form, error=stringError
                )
        else:
            stringError = "Wrong current password!"
            return render_template("reset_password.html", form=form, error=stringError)

        db.session.commit()
        return render_template(
            "reset_password.html", form=form, success="Password updated!"
        )

    elif request.method == "GET":
        return render_template("reset_password.html", form=form)
    else:
        raise RuntimeError("This should not happen!")


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



@users.route("/user/black_list", methods=["POST", "GET"])
def display_black_list():
    check_authenticated()
    owner_id = getattr(current_user, "id")
    if request.method == "POST":
        result = False
        json_data = json.loads(request.data)
        members_id = json_data["users"]
        # print(json_data)
        if json_data["op"] == "delete":
            result = monolith.user_query.delete_users_black_list(owner_id, members_id)
        elif json_data["op"] == "add":
            result = monolith.user_query.add_users_to_black_list(owner_id, members_id)

        return _prepare_json_response(owner_id, 200 if result else 5000)

    # via get it resturn jut the page
    return _prepare_black_list(owner_id)


def _prepare_black_list(owner_id):
    f = BlackListForm()

    result = monolith.user_query.get_black_list(owner_id)
    black_list = [usr[1] for usr in result]
    f.users.choices = monolith.user_query.get_choices(owner_id)
    f.black_users.choices = result
    return render_template(
        "black_list.html", form=f, black_list=black_list, size=len(black_list)
    )


def _prepare_json_response(owner_id, status):
    body = dict()
    choices = monolith.user_query.get_choices(owner_id)
    body.update({"users": [{"id": i[0], "email": i[1]} for i in choices]})
    black_list = monolith.user_query.get_black_list(owner_id)
    body.update({"black_users": [{"id": i[0], "email": i[1]} for i in black_list]})
    return make_response(jsonify(body), status)

@users.route("/api/user/<id>", methods=["GET"])
def get_email(id):
    check_authenticated()

    q = db.session.query(User).filter(User.id == id)
    user = q.first()

    if user is not None:
        return jsonify(
            {
                "email": getattr(user, "email"),
                "firstname": getattr(user, "firstname"),
                "lastname": getattr(user, "lastname"),
            }
        )
    else:
        abort(404, "User not found")
