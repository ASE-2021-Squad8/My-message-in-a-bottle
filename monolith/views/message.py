from flask import Blueprint, request, abort, jsonify, current_app as app
from werkzeug.utils import redirect
from monolith.auth import current_user, check_authenticated
from monolith.database import Message
import monolith.messaging

msg = Blueprint('message', __name__)

@msg.route("/api/message/draft", methods=["POST", "DELETE"])
def save_draft_message():
    check_authenticated()
    if request.method == "POST":
        text = request.form["text"]
        if text is None or str.isspace(text) or text == '':
            abort(400, "Message to draft cannot be empty")

        message = Message()
        message.text = text
        message.sender = getattr(current_user, 'id')
        monolith.messaging.save_draft(message)

        return _get_result(app.jsonify({"message_id": message.message_id}),"/")
    elif request.method == "DELETE":
        to_delete = request.form["message_id"]
        try:
            monolith.messaging.delete_user_draft(getattr(current_user, 'id'), to_delete)
            return _get_result(jsonify({"message_id": to_delete}),"/")
        except:
            abort(404, "Draft not found")
                    

@msg.route("/api/message/user_drafts", methods=["GET"])
def get_user_drafts():
    check_authenticated()

    drafts = monolith.messaging.get_user_drafts(getattr(current_user, 'id'))
    return jsonify(drafts) if TESTING else redirect

def _get_result(json_object, page):
    return json_object if current_app.config["TESTING"] else redirect(page)