import wtforms as f
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired
from wtforms import validators
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
    text = f.TextAreaField("text", validators=[DataRequired()])
    delivery_date = f.DateTimeField("delivery_date")
    recipient = f.SelectField("recipient", id="recipient")
    display = ["recipient", "text"]
