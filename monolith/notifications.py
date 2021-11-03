import smtplib
from email.message import EmailMessage
import os

smtp_server = (
    "smtp.gmail.com"
    if not "MAIL_SERVER" in os.environ
    else os.environ.get("MAIL_SERVER")
)
port = 587 if not "MAIL_PORT" in os.environ else int(os.environ.get("MAIL_PORT"))
notifications_email = "mmiab.notifications@gmail.com"


def send_notification(msg_sender, receiver, msg_body):

    # Log in to server and send email
    server = None
    try:
        with open("password.txt", "r") as pwfile:
            password = pwfile.readline()
            pwfile.close()
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()
        server.login(notifications_email, password)
        mail = EmailMessage()
        mail["Subject"] = "MMIAB - Message from " + msg_sender
        mail.set_content(msg_body)
        server.sendmail(notifications_email, receiver, mail.as_string())
    except Exception as e:
        # Print any error messages
        print(e)
    finally:
        if server != None:
            server.quit()
