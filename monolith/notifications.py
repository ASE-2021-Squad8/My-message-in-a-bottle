import os
import smtplib
from email.message import EmailMessage


def send_notification(msg_sender, receiver, msg_body):
    PORT = int(os.environ.get("MAIL_PORT", 1025))
    NOTIFICATIONS_EMAIL = os.environ.get(
        "MAIL_NOREPLY_ADDRESS", "noreply@mmiab.localhost"
    )
    SMTP_SERVER = os.environ.get("MAIL_SERVER", "localhost")
    SMTP_PASSWORD = os.environ.get("MAIL_SERVER_PASSWORD", "")

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
        print(str(e))
        raise Exception(str(e))
    finally:
        if server != None:
            server.quit()
