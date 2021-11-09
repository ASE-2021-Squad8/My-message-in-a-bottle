import datetime
from flask import (
    Blueprint,
    json,
    redirect,
    render_template,
    request,
    jsonify,
    make_response,
    abort,
)
from flask_login import logout_user

from monolith.database import User, db
from monolith.forms import BlackListForm, UserForm, ChangePassForm
from monolith.auth import check_authenticated, current_user
import monolith.user_query

users = Blueprint("users", __name__)


@users.route("/users")
def _users():  # pragma: no cover
    _users = db.session.query(User)
    return render_template("users.html", users=_users)


@users.route("/content_filter")
def content_filter():  # pragma: no cover
    return render_template("content_filter.html", feedback="")


@users.route("/search_user")
def _search_user():  # pragma: no cover
    return render_template("search_user.html")


@users.route("/user/account", methods=["GET"])
def _user():  # pragma: no cover
    check_authenticated()
    data = current_user.dateofbirth
    date_of_birth = data.strftime("%a, %d %B, %Y")
    return render_template("account_data.html", user=current_user, date=date_of_birth)


@users.route("/create_user", methods=["POST", "GET"])
def create_user():
    """Create a user

    :returns: the rendered template of the page
    :rtype: text
    """
    form = UserForm()

    if request.method == "POST":
        if form.validate_on_submit():
            # check if date of birth is valid (in the past)
            inputdate = form.dateofbirth.data
            if inputdate is None or inputdate > datetime.date.today():
                return render_template(
                    "create_user.html",
                    form=form,
                    error="Date of birth cannot be empty or in the future",
                )

            # check if a user with the same email already exists
            email = form.email.data
            if monolith.user_query.get_user_by_email(email) is not None:
                return render_template(
                    "create_user.html",
                    form=form,
                    error="A user with that email already exists",
                )

            # create the user
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
    elif request.method == "GET":  # pragma: no cover
        return render_template("create_user.html", form=form, error="")


@users.route("/user/recipients", methods=["GET"])
def get_recipients():
    """Get all the possible message recipients for the current user

    :returns: the json of all the possible recipients
    :rtype: json
    """
    result = monolith.user_query.get_recipients(getattr(current_user, "id"))
    l = [{"id": i.id, "email": i.email} for i in result]
    return jsonify(l)


@users.route("/user/unregister")
def unregister():
    """Unregister the current user from the service

    :returns: redirect to landing page
    :rtype: response
    """
    check_authenticated()
    userid = getattr(current_user, "id")
    logout_user()
    user = User.query.filter(User.id == userid).first()
    user.is_active = False
    db.session.commit()
    return redirect("/")


@users.route("/user/data", methods=["POST", "GET"])
def change_data_user():
    """Update the data of the current user

    :returns: the rendered template of the page
    :rtype: text
    """
    check_authenticated()
    form = UserForm()

    if request.method == "POST":
        # check if inputs are valid
        check_mail_db = db.session.query(User).filter(User.email == request.form["textemail"]).first()
        print(check_mail_db)
        if (
            request.form["textfirstname"] == ""
            or request.form["textlastname"] == ""
            or request.form["textemail"] == ""
            or request.form["textbirth"] == ""
            or (check_mail_db is not None and check_mail_db.id != getattr(current_user, "id"))
        ):
            return render_template(
                "edit_profile.html",
                form=form,
                user=current_user,
                error="All fields must be completed or the email is already associated to an account",
            )

        # update the user data
        userid = getattr(current_user, "id")
        user = User.query.filter(User.id == userid).first()
        user.firstname = request.form["textfirstname"]
        user.lastname = request.form["textlastname"]
        user.email = request.form["textemail"]
        data = request.form["textbirth"]
        date_as_datetime = datetime.datetime.strptime(data, "%Y-%m-%d")
        user.dateofbirth = date_as_datetime

        db.session.commit()
        return redirect("/user/account")
    elif request.method == "GET":  # pragma: no cover
        return render_template("edit_profile.html", form=form, user=current_user)


@users.route("/user/password", methods=["POST", "GET"])
def change_pass_user():
    """Change the password of the current user

    :returns: the rendered template of the page
    :rtype: text
    """
    check_authenticated()
    form = ChangePassForm()
    stringError = ""

    if request.method == "POST":
        userid = getattr(current_user, "id")
        user = User.query.filter(User.id == userid).first()
        current_password = form.currentpassword.data
        new_pass = form.newpassword.data
        confirmpass = form.confirmpassword.data

        # check that current and confirmation password are correct
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
    elif request.method == "GET":  # pragma: no cover
        return render_template("reset_password.html", form=form)


@users.route("/user/report", methods=["GET", "POST"])
def report():
    """Report a user

    :returns: the rendered template of the page
    :rtype: text
    """
    check_authenticated()
    if request.method == "GET":  # pragma: no cover
        return render_template("report_user.html")
    else:
        # get the mail of the user to be reported and report it
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
            # if the user has 3 or more reports ban the account deactivating it
            if user.reports >= 3:
                user.is_active = False
                banned = " and banned"
            db.session.commit()
            return render_template(
                "report_user.html",
                error="",
                reported=mail + " has been reported" + banned + ".",
            )
        else:  # pragma: no cover
            return render_template(
                "report_user.html",
                error="You have to specify an email to report a user.",
                reported="",
            )


@users.route("/user/black_list", methods=["GET", "POST"])
def handle_black_list():
    """Get all the users blacklisted by the current user or add/remove users to the blacklist

    :returns: the response from the server or the rendered template
    :rtype: text
    """
    check_authenticated()
    owner_id = getattr(current_user, "id")
    if request.method == "POST":
        # remove or add users to the blacklist
        result = False
        json_data = json.loads(request.data)
        members_id = json_data["users"]
        if json_data["op"] == "delete":
            result = monolith.user_query.remove_from_blacklist(owner_id, members_id)
        elif json_data["op"] == "add":
            result = monolith.user_query.add_to_blacklist(owner_id, members_id)

        return _prepare_json_response(owner_id, 200 if result else 500)
    elif request.method == "GET":  # pragma: no cover
        # get all the blacklisted users
        f = BlackListForm()
        result = monolith.user_query.get_blacklist(owner_id)
        black_list = [usr[1] for usr in result]
        f.users.choices = monolith.user_query.get_blacklist_candidates(owner_id)
        f.black_users.choices = result
        return render_template(
            "black_list.html", form=f, black_list=black_list, size=len(black_list)
        )


def _prepare_json_response(owner_id, status):
    """Create and make the json response from server

    :param owner_id: the id of the user to retrieve the data of
    :type owner_id: int
    :param status: the status code to be returned
    :type status: int
    :returns: the response from the server
    :rtype: Response
    """
    body = dict()
    choices = monolith.user_query.get_blacklist_candidates(owner_id)
    body.update({"users": [{"id": i[0], "email": i[1]} for i in choices]})
    black_list = monolith.user_query.get_blacklist(owner_id)
    body.update({"black_users": [{"id": i[0], "email": i[1]} for i in black_list]})
    return make_response(jsonify(body), status)


@users.route("/api/user/<user_id>", methods=["GET"])
def get_user_details(user_id):
    """Retrieve public profile details for a specific user

    :param user_id: the id of the user to retrieve the information of
    :type user_id: int
    :returns: an object containing email, first and last name
    :rtype: json
    """
    check_authenticated()

    q = db.session.query(User).filter(User.id == user_id)
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


@users.route("/api/users/list")
def get_users_list_json():
    """Get all the users registered to the service

    :returns: the json of the users
    :rtype: json
    """
    users = monolith.user_query.get_all_users()
    userlist = [
        {"email": u.email, "firstname": u.firstname, "lastname": u.lastname}
        for u in users
    ]
    return jsonify(userlist)


@users.route("/api/content_filter/", methods=["POST"])
def set_content_filter():
    """Set the content filter or the current user to the value read from the form (1 True, 0 False)

    :returns: True if filter is now set to True, False otherwise
    :rtype: bool
    """
    check_authenticated()
    value = request.form["filter"]
    value = int(value) == 1
    set = monolith.user_query.change_user_content_filter(current_user.id, value)

    if set:
        feedback = "Your content filter is enabled"
    else:
        feedback = "Your content filter is disabled"
    return render_template("content_filter.html", feedback=feedback)
