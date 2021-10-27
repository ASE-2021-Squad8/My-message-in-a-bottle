import smtplib, ssl
from email.message import EmailMessage

smtp_server = "smtp.gmail.com"
port = 587
notifications_email = "mmiab.notifications@gmail.com"
with open("password.txt", "r") as pwfile:
        password = pwfile.readline()
        pwfile.close()

def send_notification(msg_sender, receiver, msg_body):
    # Create a secure SSL context
    context = ssl.create_default_context()

    # Log in to server and send email
    try:
        server = smtplib.SMTP(smtp_server, port)
        server.starttls(context=context)
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
