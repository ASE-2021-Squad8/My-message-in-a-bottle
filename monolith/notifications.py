import smtplib
from email.message import EmailMessage
import os

PORT = int(os.environ.get("MAIL_PORT", 587))
NOTIFICATIONS_EMAIL = os.environ.get(
    "MAIL_NOREPLY_ADDRESS", "mmiab.notifications@gmail.com"
)
SMTP_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
SMTP_PASSWORD = os.environ.get("MAIL_SERVER_PASSWORD", "")


def send_notification(msg_sender, receiver, msg_body):
    # Log in to server and send email
    server = None
    try:
        server = smtplib.SMTP(SMTP_SERVER, PORT)
        if SMTP_PASSWORD != "":
            server.starttls()
            server.login(NOTIFICATIONS_EMAIL, SMTP_PASSWORD)
        mail = EmailMessage()
        mail["Subject"] = "MMIAB - Message from " + msg_sender
        mail.set_content(msg_body)
        server.sendmail(NOTIFICATIONS_EMAIL, receiver, mail.as_string())
    except Exception as e:
        # Print any error messages
        print(e)
    finally:
        if server != None:
            server.quit()
