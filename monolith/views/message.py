from flask import Blueprint, request, abort, jsonify

from monolith.auth import current_user
from monolith.database import Message
import monolith.messaging

msg = Blueprint('message', __name__)

@msg.route("/api/message/draft", methods=["POST", "DELETE"])
def save_draft_message():
    if current_user is not None and hasattr(current_user, 'id'):
        if request.method == "POST":
            text = request.form["text"]
            if text is None or str.isspace(text) or text == '':
                abort(400, "Message to draft cannot be empty")

            message = Message()
            message.text = text
            message.sender = getattr(current_user, 'id')
            monolith.messaging.save_draft(message)

            return jsonify({"message_id": message.message_id})
        elif request.method == "DELETE":
            to_delete = request.form["message_id"]
            try:
                monolith.messaging.delete_user_draft(getattr(current_user, 'id'), to_delete)
                return jsonify({"message_id": to_delete})
            except:
                abort(404, "Draft not found")
                    
    else:
        abort(401, "You must be logged in to save a message draft")

@msg.route("/api/message/user_drafts", methods=["GET"])
def get_user_drafts():
    if current_user is not None and hasattr(current_user, 'id'):
        drafts = monolith.messaging.get_user_drafts(getattr(current_user, 'id'))
        return jsonify(drafts), 200
    else:
        abort(401, "You must be logged in to retrieve your drafts")
