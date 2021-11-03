import json
import os
import traceback

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
from monolith.background import send_message as put_message_in_queque
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

    return "." in filename and filename.rsplit(".", 1)[1].lower() in {
        "png",
        "jpg",
        "jpeg",
        "gif",
    }


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
        message.sender = getattr(current_user, "id")
        if "recipient" in request.form and request.form["recipient"] != "":
            message.recipient = request.form["recipient"]
        message.is_draft = True

        if "attachment" in request.files:
            file = request.files["attachment"]
            # Make sure the filename is not dangerous for the system
            filename = secure_filename(file.filename)

            if _extension_allowed(filename):
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

                # If the draft already has a file, delete it
                if message.media != "":
                    os.unlink(os.path.join(app.config["UPLOAD_FOLDER"], message.media))
                message.media = filename
            else:
                _get_result(None, ERROR_PAGE, True, 400, "File extension not allowed")

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
    msg = None
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
    msg.recipient = int(request.form["recipient"])

    if "attachment" in request.files:
        file = request.files["attachment"]
        # Make sure the filename is not dangerous for the system
        filename = secure_filename(file.filename)

        if _extension_allowed(filename):
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

            # If the draft already has a file, delete it
            if msg.media != "":
                os.unlink(os.path.join(app.config["UPLOAD_FOLDER"], message.media))
            msg.media = filename
        else:
            _get_result(None, ERROR_PAGE, True, 400, "File extension not allowed")


    # when it will be delivered
    # delay = (delivery_date - now).total_seconds()
    try:
        id = monolith.messaging.save_message(msg)
        email_r = get_user_mail(msg.recipient)
        email_s = get_user_mail(msg.sender)
        put_message_in_queque.apply_async(
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
    except put_message_in_queque.OperationalError as e:
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


@msg.route("/message_received")
def message_receved():
    return render_template("message_received.html")


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


@msg.route("/api/message/read_message/<id>")
def read_msg(id):
    check_authenticated()
    if not monolith.messaging.set_message_is_read(id):
        return abort(404, "Message not found")
    return jsonify({"msg_read": True})
