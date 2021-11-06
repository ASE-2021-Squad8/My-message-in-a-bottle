import os
import smtplib
from email.message import EmailMessage
import socket
from collections import namedtuple

EmailConfig = namedtuple("EmailConfig", ["server", "port", "email", "password"])
DefaultEmailConfig = EmailConfig(
    os.environ.get("MAIL_SERVER", "localhost"),
    int(os.environ.get("MAIL_PORT", 1025)),
    os.environ.get("MAIL_NOREPLY_ADDRESS", "noreply@mmiab.localhost"),
    os.environ.get("MAIL_SERVER_PASSWORD", ""),
)


def send_notification(msg_sender, receiver, msg_body, config=DefaultEmailConfig):

    try:
        with smtplib.SMTP(config.server, config.port, timeout=10) as server:
            if config.password != "":
                server.starttls()
                server.login(config.email, config.password)

            mail = EmailMessage()
            mail["Subject"] = "MMIAB - Message from " + msg_sender
            mail.set_content(msg_body)

            server.sendmail(config.email, receiver, mail.as_string())
    except socket.timeout as e:
        raise e
