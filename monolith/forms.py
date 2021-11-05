import wtforms as f
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms.fields.simple import HiddenField
from wtforms.validators import DataRequired
from wtforms.fields.html5 import EmailField, DateField

class LoginForm(FlaskForm):
    email = f.StringField("email", validators=[DataRequired()])
    password = f.PasswordField("password", validators=[DataRequired()])
    display = ["email", "password"]


class UserForm(FlaskForm):
    email = EmailField("email", validators=[DataRequired()])
    firstname = f.StringField("firstname", validators=[DataRequired()])
    lastname = f.StringField("lastname", validators=[DataRequired()])
    password = f.PasswordField("password", validators=[DataRequired()])
    dateofbirth = DateField("dateofbirth", validators=[DataRequired()])
    display = ["email", "firstname", "lastname", "password", "dateofbirth"]


class MessageForm(FlaskForm):
    text = f.TextAreaField("Message text", validators=[DataRequired()], id="text")
    delivery_date = f.DateTimeField("delivery_date")
    recipient = f.SelectMultipleField("Recipient", id="recipient", validators=[DataRequired()])
    attachment = FileField("Attachment", id="attachment", validators=[FileAllowed(['jpg', "png", "jpeg", "gif"], "Only images can be uploaded")])
    draft_id = HiddenField("Draft ID", id="draft_id")
    display = ["text", "attachment"]


class ChangePassForm(FlaskForm):
    currentpassword = f.PasswordField("password", validators=[DataRequired()])
    newpassword = f.PasswordField("password", validators=[DataRequired()])
    confirmpassword = f.PasswordField("password", validators=[DataRequired()])
    display = ["currentpassword", "newpassword", "confirmpassword"]


class BlackListForm(FlaskForm):
    users = f.SelectMultipleField("users", validators=[DataRequired()])
    black_users = f.SelectMultipleField("users", validators=[DataRequired()])

    dispay = ["users"]
