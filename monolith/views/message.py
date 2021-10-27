from datetime import datetime
from flask import (
    Blueprint,
    request,
    abort,
    jsonify,
    current_app as app,
    render_template,
)
from werkzeug.utils import redirect
from monolith.auth import current_user, check_authenticated
from monolith.database import Message
from monolith.forms import MessageForm
import monolith.messaging
import json
from celery.utils.log import get_logger

# import queue task
from monolith.background import send_message as put_message_in_queque

# utility import
from datetime import datetime as d

msg = Blueprint("message", __name__)
ERROR_PAGE = "index.html"
logger = get_logger(__name__)


@msg.route("/send_message")
def _send_message():
    return render_template("send_message.html", form=MessageForm())


@msg.route("/api/message/draft", methods=["POST", "DELETE"])
def save_draft_message():
    check_authenticated()
    if request.method == "POST":
        text = request.form["text"]
        if _not_valid_string(text):
            return _get_result(
                None, ERROR_PAGE, True, 400, "Message to draft cannot be empty"
            )

        message = None
        if request.form["draft_id"] is None:
            message = Message()
        else:
            message = monolith.messaging.get_user_draft(getattr(current_user, "id"), id)

        message.text = text
        message.sender = getattr(current_user, "id")
        if request.form["recipient"] is not None:
            message.recipient = request.form["recipient"]
        message.is_draft = True
        monolith.messaging.save_message(message)

        return _get_result(jsonify({"message_id": message.message_id}), "/send_message")
    elif request.method == "DELETE":
        to_delete = request.json["message_id"]
        try:
            monolith.messaging.delete_user_message(
                getattr(current_user, "id"), to_delete, True
            )
            return jsonify({"message_id": to_delete})
        except:
            _get_result(None, ERROR_PAGE, True, 404, "Draft not found")


@msg.route("/api/message/draft/<id>", methods=["GET"])
def get_user_draft(id):
    check_authenticated()

    draft = monolith.messaging.get_user_draft(getattr(current_user, "id"), id)
    return jsonify(draft)


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
    if request.form["draft_id"] is None:
        # record to insert
        msg = Message()
        msg.text = request.form["text"]
        msg.is_draft = False
        msg.is_delivered = True
        msg.is_read = False
    else:
        msg = monolith.messaging.unmark_draft(
            getattr(current_user, "id"), int(request.form["draft_id"])
        )

    msg.sender = int(getattr(current_user, "id"))
    msg.recipient = int(request.form["recipient"])

    # when it will be delivered
    delay = (delivery_date - now).total_seconds()
    try:
        put_message_in_queque.apply_async(
            args=[json.dumps(msg.as_dict())],
            countdown=delay,
        )
        monolith.messaging.delete_user_message
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


@msg.route("/api/message/all", methods=["GET"])
def get_all_mesages():
    check_authenticated()

    try:
        messages = monolith.messaging.get_all_messages(getattr(current_user, "id"))
        return jsonify(messages)

    except Exception:
        print(Exception)
        abort(404, "Message not found")


@msg.route("/message_received")
def message_receved():
    return render_template("message_received.html")
