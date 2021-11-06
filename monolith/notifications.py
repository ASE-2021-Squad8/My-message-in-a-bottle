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
    """Sends an email from a specific sender to a certain recipient.

    :param msg_sender: sender email address
    :type msg_sender: str
    :param receiver: recipient email address
    :type receiver: str
    :param msg_body: contents of the message
    :type msg_body: str
    :param config: email configuration settings, defaults to DefaultEmailConfig
    :type config: EmailConfig, optional
    :raises e: if SMTP connection times out
    """

    try:
        with smtplib.SMTP(config.server, config.port, timeout=10) as server:
            if config.password != "":
                server.starttls()
                server.login(config.email, config.password)

            mail = EmailMessage()
            mail["Subject"] = "MMIAB - Message from " + msg_sender
            mail.set_content(msg_body)

            server.sendmail(config.email, receiver, mail.as_string())
    except socket.timeout as e: # pragma: no cover
        raise e
