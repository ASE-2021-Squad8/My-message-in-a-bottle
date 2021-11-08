import json
import os
from datetime import date, datetime
import traceback
import hashlib
import pathlib
import time
import pytz

from celery.utils.log import get_logger
from flask import Blueprint, abort
from flask import current_app as app
from flask import jsonify, render_template, request
from werkzeug.utils import redirect

import monolith.messaging
from monolith.auth import check_authenticated, current_user
from monolith.user_query import get_user_mail
from monolith.forms import MessageForm
from monolith.database import Message
from monolith.background import (
    send_message as put_message_in_queue,
    send_notification_task as put_email_in_queue,
)


msg = Blueprint("message", __name__)
ERROR_PAGE = "error_page"
logger = get_logger(__name__)


@msg.route("/send_message")
def _send_message():  # pragma: no cover
    return render_template("send_message.html", form=MessageForm())


@msg.route("/manage_drafts")
def _manage_drafts():  # pragma: no cover
    check_authenticated()

    return render_template("manage_drafts.html", user=getattr(current_user, "id"))


@msg.route("/mailbox")
def mailbox():  # pragma: no cover
    return render_template("mailbox.html")


@msg.route("/calendar")
def calendar():  # pragma: no cover
    return render_template("calendar.html")


def _extension_allowed(filename):
    """Checks if a file is allowed to be uploaded

    :param filename: name of the file
    :type filename: str
    :returns: True if allowed, false otherwise
    :rtype: bool
    """

    # Of course, this is a toy, nothing stops you from sending an .exe as a .png :)
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
    :returns: a filename suited for storage
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

    :returns: id of the saved message
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

        id = request.form["draft_id"]
        if id is not None and id != "":
            try:
                message = monolith.messaging.get_user_draft(
                    getattr(current_user, "id"), id
                )
            except:
                return _get_result(
                    None, ERROR_PAGE, True, 404, "Draft to edit cannot be found"
                )
        else:
            message = Message()

        message.text = text
        message.is_draft = True

        message.sender = getattr(current_user, "id")
        if "recipient" in request.form and request.form["recipient"] != "":
            message.recipient = request.form["recipient"]

        print("A")
        # check the attachment
        if "attachment" in request.files and request.files["attachment"].filename != "":
            file = request.files["attachment"]

            if _extension_allowed(file.filename):
                print("---------------we got here????")
                filename = _generate_filename(file)

                # if the draft already has a file, delete it
                if message.media is not None and message.media != "":
                    try:  # pragma: no cover
                        # very unlikely, ignore in coverage
                        os.unlink(
                            os.path.join(app.config["UPLOAD_FOLDER"], message.media)
                        )
                    except:
                        # if we failed to delete the file from the disk then something is wrong
                        return _get_result(
                            None, ERROR_PAGE, True, 500, "Internal server error"
                        )

                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                message.media = filename
            else:
                return _get_result(
                    None, ERROR_PAGE, True, 400, "File extension not allowed"
                )

        monolith.messaging.save_message(message)

        return _get_result(jsonify({"message_id": message.message_id}), "/send_message")


@msg.route("/api/message/draft/<id>", methods=["GET", "DELETE"])
def get_user_draft(id):
    """Get the draft #<id> from the current user

    :param id: the draft id to search
    :type id: int
    :returns: message id
    :rtype: json
    """
    check_authenticated()

    try:
        if request.method == "GET":
            draft = monolith.messaging.get_user_draft(getattr(current_user, "id"), id)
            return jsonify(draft)
        elif request.method == "DELETE":
            monolith.messaging.delete_user_message(getattr(current_user, "id"), id)
            return jsonify({"message_id": id})
    except KeyError:
        return _get_result(None, ERROR_PAGE, True, 404, "Draft not found")


@msg.route("/api/message/draft/<id>/attachment", methods=["DELETE"])
def get_user_draft_attachment(id):
    """Delete the attachment of the draft #<id> from the current user

    :param id: the draft id to search
    :type id: int
    :returns: message id
    :rtype: json
    """
    check_authenticated()

    if monolith.messaging.delete_draft_attachment(getattr(current_user, "id"), id):
        return jsonify({"message_id": id})
    else:
        _get_result(None, ERROR_PAGE, True, 404, "No attachment present")


@msg.route("/api/message/draft/all", methods=["GET"])
def get_user_drafts():
    """Get all the draft from the current user

    :returns: all the drafts
    :rtype: json
    """
    check_authenticated()

    drafts = monolith.messaging.get_user_drafts(getattr(current_user, "id"))
    return jsonify(drafts)


@msg.route("/api/message/", methods=["POST"])
def send_message():
    """Send a message from the current user

    :returns: json of the message in test mode, otherwise the page
    :rtype: json
    """
    check_authenticated()

    now = datetime.now()
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

    recipients = request.form.getlist("recipient")
    if recipients == [] or recipients is None:
        return _get_result(
            None, "/send_message", True, 400, "Message needs at least one recipient"
        )

    for recipient in recipients:
        try:
            # attempt to retrieve the draft, if present
            msg = monolith.messaging.unmark_draft(
                getattr(current_user, "id"), int(request.form["draft_id"])
            )
        except KeyError:
            # otherwise build the message from scratch
            msg = Message()
            msg.is_draft = False
            msg.is_delivered = False
            msg.is_read = False
            msg.delivery_date = delivery_date

        msg.text = request.form["text"]
        msg.sender = int(getattr(current_user, "id"))
        msg.recipient = int(recipient)

        if "attachment" in request.files:
            file = request.files["attachment"]

            if file.filename != "" and _extension_allowed(file.filename):
                filename = _generate_filename(file)

                # if the draft already has a file, delete it
                if msg.media is not None and msg.media != "":
                    try:  # pragma: no cover
                        # unlikely to ever happen, don't include in coverage
                        os.unlink(os.path.join(app.config["UPLOAD_FOLDER"], msg.media))
                    except:
                        # if we failed to delete the file from the disk then something is wrong
                        return _get_result(
                            None, ERROR_PAGE, True, 500, "Internal server error"
                        )

                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                msg.media = filename
            else:
                return _get_result(
                    None, ERROR_PAGE, True, 400, "File extension not allowed"
                )

        # send message via celery
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
                ],  #  convert to utc
                eta=delivery_date.astimezone(pytz.utc),  # task execution time
                routing_key="message",  # to specify the queue
                queue="message",
            )
        except put_message_in_queue.OperationalError as e:
            logger.exception("Send message task raised: %r", e)

    return _get_result(jsonify({"message sent": True}), "/send_message")


def _get_result(json_object, page, error=False, status=200, error_message=""):
    """Return the result of a function (a json in test mode or a rendered template)

    :param json_object: the json to be returned in test mode
    :type json_object: json
    :param page: the name of the page to be rendered
    :type page: text
    :param error: if an error has happened in the function (default=False)
    :type error: bool
    :param status: the status code to be returned (default=200)
    :type status: int
    :param error_message: the error message to be displayed (default="")
    :type error_message: text
    :returns: json in test mode or rendered template
    :rtype: json
    """
    testing = app.config["TESTING"]
    if error and testing:
        abort(status, error_message)
    elif error:  # pragma: no cover
        return render_template(
            page + ".html", message=error_message, form=MessageForm()
        )

    return json_object if testing else redirect(page)


def _not_valid_string(text):
    return text is None or text == "" or text.isspace()


@msg.route("/api/message/received/metadata", methods=["GET"])
def _get_received_messages_metadata():
    """Get all the messages received by the current user

    :returns: json of all the messages, 404 page if an exception happened
    :rtype: json
    """
    check_authenticated()

    try:
        messages = monolith.messaging.get_received_messages_metadata(
            getattr(current_user, "id")
        )
        return jsonify(messages)

    except Exception as e:
        print(str(e))
        traceback.print_exc()
        abort(404, "Message not found")


@msg.route("/api/message/received/<message_id>", methods=["GET"])
def _get_received_message(message_id):
    """Get the received message of id = <id>

    :param message_id: the id of the message to be returned
    :type message_id: int
    :returns: json of the message, 404 page if an exception happened
    :rtype: json
    """
    check_authenticated()

    try:
        message = monolith.messaging.get_received_message(
            getattr(current_user, "id"), message_id
        )
        return jsonify(message)

    except Exception as e:
        print(str(e))
        traceback.print_exc()
        abort(404, "Message not found")


@msg.route("/api/message/sent/metadata", methods=["GET"])
def _get_sent_messages_metadata():
    """Get all the messages sent by the current user

    :returns: json of all the messages, 404 page if an exception happened
    :rtype: json
    """
    check_authenticated()

    try:
        messages = monolith.messaging.get_sent_messages_metadata(
            getattr(current_user, "id")
        )
        return jsonify(messages)

    except Exception as e:
        print(str(e))
        traceback.print_exc()
        abort(404, "Message not found")


@msg.route("/api/message/sent/<message_id>", methods=["GET"])
def _get_sent_message(message_id):
    """Get the sent message of id = <id>

    :param message_id: the id of the message to be returned
    :type message_id: int
    :returns: json of the message, 404 page if an exception happened
    :rtype: json
    """
    check_authenticated()

    try:
        message = monolith.messaging.get_sent_message(
            getattr(current_user, "id"), message_id
        )
        return jsonify(message)

    except Exception as e:
        print(str(e))
        traceback.print_exc()
        abort(404, "Message not found")


@msg.route("/api/message/<message_id>", methods=["DELETE"])
def delete_msg(message_id):
    """Delete a message of id = <id>

    :param message_id: the id of the message to be deleted
    :type message_id: int
    :returns: json of the deleted message id, 404 page if an exception happened
    :rtype: json
    """
    check_authenticated()
    if monolith.messaging.set_message_is_deleted(message_id):
        return jsonify({"message_id": message_id})
    else:
        return _get_result(None, ERROR_PAGE, True, 404, "Message not found")


@msg.route("/api/lottery/message/<message_id>", methods=["DELETE"])
def lottery_delete_msg(message_id):
    """Delete a scheduled message of id = <id>

    :param message_id: the id of the message to be deleted
    :type message_id: int
    :returns: json of the deleted message id, otherwise -1
    :rtype: json
    """
    check_authenticated()
    result = monolith.messaging.set_message_is_deleted_lottery(message_id)

    return (
        jsonify({"message_id": message_id}) if result else jsonify({"message_id": -1})
    )


@msg.route("/api/message/read_message/<id>")
def read_msg(id):
    """Get a message of id = <id>

    :param message_id: the id of the message to be returned
    :type message_id: int
    :returns: True if the message has been correctly read, 404 page if the message has been deleted or does not exist
    :rtype: json
    """
    check_authenticated()
    msg = monolith.messaging.get_message(id)

    if msg is None or msg.is_deleted:
        return abort(404, json.dumps({"msg_read": False, "error": "message not found"}))

    if not msg.is_read:

        # updata msg.is_read
        monolith.messaging.update_message_state(msg.message_id, "is_read", True)

        # retrieve email of receiver and sender
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


@msg.route("/api/calendar/<int:day>/<int:month>/<int:year>")
def sent_messages_by_day(day, month, year):
    """Get all the messages for a specific date

    :param day: day
    :type day: int
    :param month: month
    :type month: int
    :param year: year
    :type year: int
    :returns: json of all the found messages id, 404 page if the date is invalid
    :rtype: json
    """
    check_authenticated()
    if day > 31 and month + 1 > 12:
        return _get_result(None, ERROR_PAGE, True, 404, "Invalid date")
    else:
        basedate = datetime(year, month + 1, day)
        if month + 1 == 12 and day == 31:
            upperdate = datetime(year + 1, 1, 1)
        else:
            try:
                upperdate = datetime(year, month + 1, day + 1)
            except ValueError:
                upperdate = date(year, month + 2, 1)
        userid = getattr(current_user, "id")

        messages = monolith.messaging.get_day_message(userid, basedate, upperdate)
        return jsonify(messages)
