import json
import os
import json
from datetime import datetime

from better_profanity import profanity
from flask.globals import current_app

from monolith.database import Message, db, User
from monolith.user_query import add_points
from monolith.auth import current_user
from monolith.database import Message, User, db


def save_message(message):
    """Insert a new message in the db

    :param message: the message to add to the db
    :type message: Message
    :returns: the id of the new message
    :rtype: int
    """
    db.session.add(message)
    db.session.commit()
    return message.message_id


def get_user_drafts(user_id):
    """Get all the drafts for a user

    :param user_id: the id of the user to get its drafts
    :type user_id: Message
    :returns: the list of all the drafts
    :rtype: List[Message]
    """
    q = db.session.query(Message).filter(Message.sender == user_id, Message.is_draft)
    return q.all()


def get_user_draft(user_id, draft_id):
    """Returns a specific draft for a user

    :param user_id: user id
    :type user_id: int
    :param draft_id: draft id
    :type draft_id: id
    :raises KeyError: if the draft cannot be found
    :returns: the draft message object
    :rtype: Message
    """

    q = db.session.query(Message).filter(
        Message.sender == user_id, Message.is_draft, Message.message_id == draft_id
    )

    draft = q.first()
    if draft is None:
        raise KeyError()

    return draft


def unmark_draft(user_id, draft_id):
    """Sets a message as 'not a draft'

    :param user_id: id of the draft owner
    :type user_id: int
    :param draft_id: id of the draft
    :type draft_id: int
    :raises KeyError: if the draft was not found
    :returns: the message object, no longer a draft
    :rtype: Message
    """

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
    :raises KeyError: if the draft is not found
    :returns: True the attachment was removed, False otherwise
    :rtype: bool
    """

    draft = get_user_draft(user_id, message_id)
    if draft.media == "":
        # no attachment to remove
        return False

    try:
        os.unlink(os.path.join(current_app.config["UPLOAD_FOLDER"], draft.media))
        draft.media = ""
        db.session.commit()
    except FileNotFoundError:
        return False

    return True


def delete_user_message(user_id, message_id):
    """Delete the message_id of the user_id

    :param user_id: the id of the user that wrote the message
    :type user_id: int
    :param message_id: the id of the message to be deleted
    :type message_id: int
    :returns: None of raise KeyError if message_id does not exist
    """
    q = db.session.query(Message).filter(
        Message.sender == user_id, Message.message_id == message_id
    )
    message = q.first()
    if message is None:
        raise KeyError()

    db.session.delete(message)
    db.session.commit()


def get_received_messages_metadata(user_id):
    """Retrieves metadata for all messages received by an user

    :param user_id: id of the user
    :type user_id: int
    :returns: a list of message metadata
    :rtype: list[json]
    """

    # retrieve all messages for user_id
    q = db.session.query(Message).filter(
        Message.recipient == user_id,
        Message.is_draft == False,
        Message.is_delivered == True,
        Message.is_deleted == False,
    )
    list = []
    for msg in q:
        # retrieve the name of the sender
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
    :returns: the received message
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

    # censor a message if the content filter is activated
    user = db.session.query(User).filter(User.id == user_id).first()
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
    :returns: the sent message
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
    :returns: a list of sent message metadata
    :rtype: list[dict]
    """

    # retrieve of all messages for user_id
    q = db.session.query(Message).filter(
        Message.sender == user_id,
        Message.is_draft == False,
        Message.is_delivered == True,
    )
    list = []
    for msg in q:
        # retrieve the name of the sender
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
    """Delete a message (set is_deleted=True)

    :param message_id: the id of the message to delete
    :type message_id: int
    :returns: True if the message has been deleted, False otherwise
    :rtype: bool
    """

    msg = (
        db.session.query(Message)
        .filter(
            Message.message_id == message_id,
            Message.recipient == int(getattr(current_user, "id")),
        )
        .first()
    )
    if msg is None:
        return False

    # only delete read messages
    if msg.is_read:
        setattr(msg, "is_deleted", True)
        db.session.commit()
        return True
    return False


def set_message_is_deleted_lottery(message_id):
    """Delete a scheduled message if the user has at least 20 60 points

    :param message_id: the id of the message to delete
    :type message_id: int
    :returns: True if the message has been deleted, False otherwise
    :rtype: bool
    """

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
    """Get the message #message_id

    :param message_id: the id of the message to return
    :type message_id: int
    :returns: the message
    :rtype: Message
    """
    msg = db.session.query(Message).filter(Message.message_id == message_id).first()

    return msg


def update_message_state(message_id, attr, state):
    """Update a message state setting attr to state (message.attr = state)

    :param message_id: the id of the message to update
    :type message_id: int
    :param attr: the attribute of the message to update
    :type attr: int
    :param value: the updated value
    :type value: Any
    :returns: True if the message has been updated, False otherwise
    :rtype: bool
    """
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
    """Check if all the messages have been correctly sent.
    If an error is occurred (with Celery), set the messages in the past to delivered.
    """
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
    """Gets the outgoing messages in a time interval for a specific user

    :param userid: user id
    :type userid: int
    :param baseDate: start date
    :type baseDate: datetime
    :param upperDate: end date
    :type upperDate: datetime
    :returns: a list of messages
    :rtype: list[dict]
    """

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
        now = datetime.now()

        canDelete = delivery_date > now and sender.points >= 60
        future = delivery_date > now
        msg = {
            "message_id": msg.message_id,
            "firstname": recipient.firstname,
            "email": recipient.email,
            "text": msg.text,
            "delivered": delivery_date,
            "candelete": canDelete,
            "future": future,
        }

        list.append(msg)

    return list
