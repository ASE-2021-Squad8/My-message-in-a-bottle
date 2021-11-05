import json
import os
import traceback
import hashlib
import pathlib
import time

# utility import
from datetime import datetime
from datetime import datetime as d

import monolith.messaging
import pytz
from celery.utils.log import get_logger
from flask import Blueprint, abort
from flask import current_app as app
from flask import jsonify, render_template, request
from monolith.auth import check_authenticated, current_user

# import queue task

from monolith.background import (
    send_message as put_message_in_queue,
    send_notification_task as put_email_in_queue,
)

# utility import
from datetime import datetime as d


from monolith.database import Message, db
from monolith.forms import MessageForm

from monolith.user_query import get_user_mail
from werkzeug.utils import redirect, secure_filename

msg = Blueprint("message", __name__)
ERROR_PAGE = "index"
logger = get_logger(__name__)


@msg.route("/send_message")
def _send_message():
    return render_template("send_message.html", form=MessageForm())


def _extension_allowed(filename):
    """Checks if a file is allowed to be uploaded

    :param filename: name of the file
    :type filename: str
    :return: True if allowed, false otherwise
    :rtype: bool
    """

    return pathlib.Path(filename).suffix.lower() in {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
    }


def _generate_filename(file):
    """Generates a filename for an uploaded file

    :param file: file handle
    :type file: file
    :return: a filename suited for storage
    :rtype: str
    """

    # To avoid clashes, generate a filename by hashing
    # the file's contents, the sender and the time
    sha1 = hashlib.sha1()
    while True:
        # Read in chunks of 64kb to contain memory usage
        data = file.read(65536)
        if not data:
            break
        sha1.update(data)
    sha1.update(getattr(current_user, "email").encode("utf-8"))
    sha1.update(str(int(time.time())).encode("utf-8"))

    # Seek back to the origin of the file (otherwise save will fail)
    file.seek(0)

    return sha1.hexdigest() + pathlib.Path(file.filename).suffix.lower()


@msg.route("/api/message/draft", methods=["POST"])
def save_draft_message():
    """Saves a message as draft

    :return: id of the saved message
    :rtype: json
    """

    check_authenticated()
    if request.method == "POST":
        text = request.form["text"]
        if _not_valid_string(text):
            return _get_result(
                None, ERROR_PAGE, True, 400, "Message to draft cannot be empty"
            )

        message = None

        if "draft_id" in request.form and request.form["draft_id"] != "":
            id = request.form["draft_id"]
            message = monolith.messaging.get_user_draft(getattr(current_user, "id"), id)
        else:
            message = Message()

        message.text = text
        message.is_draft = True

        message.sender = getattr(current_user, "id")
        if "recipient" in request.form and request.form["recipient"] != "":
            message.recipient = request.form["recipient"]

        if "attachment" in request.files:
            file = request.files["attachment"]

            if not _extension_allowed(file.filename):
                _get_result(None, ERROR_PAGE, True, 400, "File extension not allowed")

            filename = _generate_filename(file)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

            # If the draft already has a file, delete it
            if message.media is not None and message.media != "":
                os.unlink(os.path.join(app.config["UPLOAD_FOLDER"], message.media))
            message.media = filename

        monolith.messaging.save_message(message)

        return _get_result(jsonify({"message_id": message.message_id}), "/send_message")


@msg.route("/api/message/draft/<id>", methods=["GET", "DELETE"])
def get_user_draft(id):
    check_authenticated()

    if request.method == "GET":
        draft = monolith.messaging.get_user_draft(getattr(current_user, "id"), id)
        return jsonify(draft)
    elif request.method == "DELETE":
        try:
            monolith.messaging.delete_user_message(
                getattr(current_user, "id"), id, True
            )
            return jsonify({"message_id": id})
        except:
            _get_result(None, ERROR_PAGE, True, 404, "Draft not found")


@msg.route("/api/message/draft/<id>/attachment", methods=["DELETE"])
def get_user_draft_attachment(id):
    check_authenticated()

    if monolith.messaging.delete_draft_attachment(getattr(current_user, "id"), id):
        return jsonify({"message_id": id})
    else:
        _get_result(None, ERROR_PAGE, True, 404, "No attachment present")


@msg.route("/api/message/draft/all", methods=["GET"])
def get_user_drafts():
    check_authenticated()

    drafts = monolith.messaging.get_user_drafts(getattr(current_user, "id"))
    return jsonify(drafts)


@msg.route("/manage_drafts")
def _manage_drafts():
    check_authenticated()

    return render_template("manage_drafts.html", user=getattr(current_user, "id"))


@msg.route("/api/message/send_message", methods=["POST"])
def send_message():
    check_authenticated()

    now = d.now()
    s_date = request.form["delivery_date"]
    delivery_date = (
        datetime.fromisoformat(s_date) if not _not_valid_string(s_date) else None
    )
    # check parameters
    if delivery_date is None or delivery_date < now:
        return _get_result(
            None, "/send_message", True, 400, "Delivery date in the past"
        )
    if _not_valid_string(request.form["text"]):
        return _get_result(
            None, "/send_message", True, 400, "Message to send cannot be empty"
        )

    recipients= request.form.getlist("recipient")

    for recipient in recipients:
        if request.form["draft_id"] is None or request.form["draft_id"] == "":
            # record to insert
            msg = Message()
            msg.text = request.form["text"]
            msg.is_draft = False
            msg.is_delivered = False
            msg.is_read = False
            msg.delivery_date = delivery_date

        else:
            msg = monolith.messaging.unmark_draft(
                getattr(current_user, "id"), int(request.form["draft_id"])
            )

        msg.sender = int(getattr(current_user, "id"))
        msg.recipient = int(recipient)

        if "attachment" in request.files:
            file = request.files["attachment"]

            if not _extension_allowed(file.filename):
                _get_result(None, ERROR_PAGE, True, 400, "File extension not allowed")

            filename = _generate_filename(file)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

            # If the message already has a file, delete it
            if msg.media is not None and msg.media != "":
                os.unlink(os.path.join(app.config["UPLOAD_FOLDER"], msg.media))
            msg.media = filename

        # when it will be delivered
        # delay = (delivery_date - now).total_seconds()
        try:
            id = monolith.messaging.save_message(msg)
            email_r = get_user_mail(msg.recipient)
            email_s = get_user_mail(msg.sender)
            put_message_in_queue.apply_async(
                args=[
                    json.dumps(
                        {
                            "id": id,
                            "TESTING": app.config["TESTING"],
                            "body": "You have just received a massage",
                            "recipient": email_r,
                            "sender": email_s,
                        }
                    )
                ],
                eta=delivery_date.astimezone(pytz.utc),  # cover to utc
                routing_key="message",  # to specify the queue
                queue="message",
            )
        except put_message_in_queue.OperationalError as e:
            logger.exception("Send message task raised: %r", e)

    return _get_result(jsonify({"message sent": True}), "/send_message")


# json object in test mode otherwise page pinted from page
def _get_result(json_object, page, error=False, status=200, error_message=""):
    testing = app.config["TESTING"]
    if error and testing:
        abort(status, error_message)
    elif error:
        return render_template(
            page + ".html", message=error_message, form=MessageForm()
        )

    return json_object if testing else redirect(page)


def _not_valid_string(text):
    return text is None or text == "" or text.isspace()


@msg.route("/api/message/received", methods=["GET"])
def _get_received_messages():
    check_authenticated()

    try:
        messages = monolith.messaging.get_received_messages(getattr(current_user, "id"))
        return jsonify(messages)

    except Exception as e:
        print(str(e))
        traceback.print_exc()
        abort(404, "Message not found")


@msg.route("/api/message/sent", methods=["GET"])
def _get_sent_messages():
    check_authenticated()

    try:
        messages = monolith.messaging.get_sent_messages(getattr(current_user, "id"))
        return jsonify(messages)

    except Exception as e:
        print(str(e))
        traceback.print_exc()
        abort(404, "Message not found")


@msg.route("/mailbox")
def mailbox():
    return render_template("mailbox.html")


# Il tasto di elimina deve apparire solo nella sezione dei messaggi ricevuti, è possibile eliminare
# solo i messaggi che sono stati letti
@msg.route("/api/message/delete/<message_id>", methods=["DELETE"])
def delete_msg(message_id):
    check_authenticated()
    if monolith.messaging.set_message_is_deleted(message_id):
        return jsonify({"message_id": message_id})
    else:
        return _get_result(None, ERROR_PAGE, True, 404, "Message not found")


@msg.route("/api/message/read_message/<id>", methods=["GET"])
def read_msg(id):
    check_authenticated()
    msg = monolith.messaging.get_message(id)

    if msg is None or msg.is_deleted:
        return abort(404, json.dumps({"msg_read": False, "error": "message not found"}))

    if not msg.is_read:

        # updata msg.is_read
        monolith.messaging.update_message_state(msg.message_id, "is_read", True)

        # Retrieve email of receiver and sender
        email_r = get_user_mail(msg.sender)
        email_s = get_user_mail(msg.recipient)
        json_message = json.dumps(
            {
                "TESTING": app.config["TESTING"],
                "body": str(email_s) + " has just read the message",
                "recipient": email_r,
                "sender": email_s,
            }
        )
        put_email_in_queue.apply_async(
            args=[json_message],
            routing_key="notification",
            queue="notification",
        )

    return jsonify({"msg_read": True})
