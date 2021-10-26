import wtforms as f
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired


class LoginForm(FlaskForm):
    email = f.StringField("email", validators=[DataRequired()])
    password = f.PasswordField("password", validators=[DataRequired()])
    display = ["email", "password"]


class UserForm(FlaskForm):
    email = f.StringField("email", validators=[DataRequired()])
    firstname = f.StringField("firstname", validators=[DataRequired()])
    lastname = f.StringField("lastname", validators=[DataRequired()])
    password = f.PasswordField("password", validators=[DataRequired()])
    dateofbirth = f.DateField("dateofbirth", format="%d/%m/%Y")
    display = ["email", "firstname", "lastname", "password", "dateofbirth"]


class MessageForm(FlaskForm):
    text = f.TextAreaField("text", validators=[DataRequired()])
    delivery_date = f.DateTimeField("delivery_date")
    recipient = f.SelectField("recipient", id="recipient")
    display = ["text", "recipient"]

class ChangePassForm(FlaskForm):
    currentpassword = f.PasswordField('password', validators=[DataRequired()])
    newpassword = f.PasswordField('password', validators=[DataRequired()])
    confirmpassword = f.PasswordField('password', validators=[DataRequired()])
    display =['currentpassword', 'newpassword', 'confirmpassword']

