import smtplib
from email.message import EmailMessage

smtp_server = "smtp.gmail.com"
port = 587
notifications_email = "mmiab.notifications@gmail.com"


def send_notification(msg_sender, receiver, msg_body):

    # Log in to server and send email
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
        server.quit()
