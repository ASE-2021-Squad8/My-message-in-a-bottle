import json
import os
from datetime import datetime
from datetime import date, datetime
from monolith.auth import check_authenticated
from monolith.database import Message, db, User
import json
from datetime import datetime
from monolith.notifications import send_notification
from monolith.user_query import add_points, get_user_mail
from monolith.auth import current_user
from better_profanity import profanity
from flask.globals import current_app
from monolith.database import Message, User, db


def save_message(message):
    db.session.add(message)
    db.session.commit()
    return message.message_id


def get_user_drafts(user_id):
    q = db.session.query(Message).filter(Message.sender == user_id, Message.is_draft)
    return q.all()


def get_user_draft(user_id, draft_id):
    q = db.session.query(Message).filter(
        Message.sender == user_id, Message.is_draft, Message.message_id == draft_id
    )
    return q.first()


def unmark_draft(user_id, draft_id):
    message = (
        db.session.query(Message)
        .filter(
            Message.sender == user_id, Message.is_draft, Message.message_id == draft_id
        )
        .first()
    )

    if message is None:
        raise KeyError("Draft does not exist!")
    else:
        message.is_draft = False
        db.session.commit()
        return message


def delete_draft_attachment(user_id, message_id):
    """Removes an attachment from a draft

    :param user_id: id of the user who owns the draft
    :type user_id: int
    :param message_id: id of the drafted message
    :type message_id: int
    :return: True the attachment was removed, False otherwise
    :rtype: bool
    """

    draft = get_user_draft(user_id, message_id)
    if draft.media is not None or draft.media != "":
        os.unlink(os.path.join(current_app.config["UPLOAD_FOLDER"], draft.media))
        draft.media = ""
        db.session.commit()
        return True

    return False


def delete_user_message(user_id, message_id, is_draft=False):
    q = db.session.query(Message).filter(
        Message.sender == user_id, Message.message_id == message_id
    )
    message = q.first()
    if message is None:
        raise ValueError()

    db.session.delete(message)
    db.session.commit()


def get_received_messages_metadata(user_id):
    """Retrieves metadata for all messages received by an user

    :param user_id: id of the user
    :type user_id: int
    :return: a list of message metadata
    :rtype: list[json]
    """

    # Retrieve of all message for user_id
    q = db.session.query(Message).filter(
        Message.recipient == user_id,
        Message.is_draft == False,
        Message.is_delivered == True,
        Message.is_deleted == False,
    )
    list = []
    for msg in q:
        # retrieve the name of sender
        sender = db.session.query(User).filter(User.id == msg.sender).first()

        json_msg = json.dumps(
            {
                "sender_id": sender.id,
                "firstname": sender.firstname,
                "lastname": sender.lastname,
                "id_message": msg.message_id,
                "email": sender.email,
                "media": msg.media,
            }
        )

        list.append(json_msg)

    return list


def get_received_message(user_id, message_id):
    """Returns a specific message received by a user.
    Does not retrieve drafts or pending messages.

    :param user_id: user id
    :type user_id: int
    :param message_id: id of the received message
    :type message_id: int
    :raises KeyError: if no such message was received
    :return: the received message
    :rtype: Message
    """

    q = db.session.query(Message).filter(
        Message.recipient == user_id,
        Message.message_id == message_id,
        Message.is_draft == False,
        Message.is_delivered == True,
        Message.is_deleted == False,
    )

    message = q.first()
    if message is None:
        raise KeyError

    user = db.session.query(User).filter(User.id == user_id)
    if user.content_filter:
        message_copy = message
        message_copy.text = profanity.censor(message.text)
        return message_copy

    return message


def get_sent_message(user_id, message_id):
    """Returns a specific message sent by a user

    :param user_id: user id
    :type user_id: int
    :param message_id: id of the sent message
    :type message_id: int
    :raises KeyError: if no such message was received
    :return: the sent message
    :rtype: Message
    """

    q = db.session.query(Message).filter(
        Message.sender == user_id,
        Message.message_id == message_id,
        Message.is_draft == False,
    )

    message = q.first()
    if message is None:
        raise KeyError

    return message


def get_sent_messages_metadata(user_id):
    """Retrieves metadata for all messages sent by an user

    :param user_id: id of the user
    :type user_id: int
    :return: a list of sent message metadata
    :rtype: list[dict]
    """

    # Retrieve of all message for user_id
    q = db.session.query(Message).filter(
        Message.sender == user_id,
        Message.is_draft == False,
        Message.is_delivered == True,
    )
    list = []
    for msg in q:
        # retrieve the name of sender
        recipient = (
            db.session.query(User).filter(User.id == msg.get_recipient()).first()
        )
        json_msg = {
            "recipient_id": recipient.get_id(),
            "firstname": recipient.get_firstname(),
            "lastname": recipient.get_lastname(),
            "id_message": msg.message_id,
            "email": recipient.email,
            "media": msg.media,
        }

        list.append(json_msg)

    return list


def set_message_is_deleted(message_id):
    msg = (
        db.session.query(Message)
        .filter(
            Message.message_id == message_id,
            Message.recipient == int(getattr(current_user, "id")),
        )
        .first()
    )

    # only delete read messages
    if msg.is_read:
        setattr(msg, "is_deleted", True)
        db.session.commit()
        return True
    return False


def set_message_is_deleted_lottery(message_id):

    try:
        msg = db.session.query(Message).filter(Message.message_id == message_id).first()
        if msg.delivery_date > datetime.now():
            db.session.query(Message).filter(Message.message_id == message_id).delete()
            add_points(-60, msg.sender)
            db.session.commit()
            return True
        return False
    except Exception:
        db.session.rollback()
        return False


def get_message(message_id):
    # retrieve the message
    msg = db.session.query(Message).filter(Message.message_id == message_id).first()

    return msg


# update message state setting attr to state
def update_message_state(message_id, attr, state):
    result = False
    try:
        message = (
            db.session.query(Message).filter(Message.message_id == message_id).first()
        )
        if message is not None:
            setattr(message, attr, state)
            db.session.commit()
            result = True
    except Exception as e:
        db.session.rollback()
        print("Exception in update_message_state %r", e)
    return result


def check_message_to_send():
    ids = []
    # looking for messages that have not been sent but they should have been
    messages = (
        db.session.query(Message)
        .filter(Message.is_delivered == 0)
        .filter(Message.delivery_date < datetime.now())
        .all()
    )
    # updating state
    for msg in messages:
        ids.append((msg.sender, msg.recipient))
        setattr(msg, "is_delivered", 1)

    db.session.commit()
    return ids


def get_day_message(userid, baseDate, upperDate):
    check_authenticated()
    q = db.session.query(Message).filter(
        Message.sender == userid,
        Message.delivery_date >= baseDate,
        Message.delivery_date < upperDate,
        Message.is_draft == False,
    )

    list = []

    for msg in q:

        recipient = db.session.query(User).filter(User.id == msg.recipient).first()
        sender = db.session.query(User).filter(User.id == msg.sender).first()
        delivery_date = msg.delivery_date
        hour_deliver = delivery_date.hour
        minute_deliver = delivery_date.minute
        now = datetime.now()

        canDelete = delivery_date > now and sender.points >= 60
        future = delivery_date > now
        json_msg = json.dumps(
            {
                "message_id": msg.message_id,
                "firstname": recipient.firstname,
                "email": recipient.email,
                "text": msg.text,
                "hour": hour_deliver,
                "minute": minute_deliver,
                "candelete": canDelete,
                "future": future,
            }
        )

        list.append(json_msg)
    return list
