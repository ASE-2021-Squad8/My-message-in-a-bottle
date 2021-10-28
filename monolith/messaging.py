from re import M
from monolith.database import Message, db, User
import json


def save_message(message):
    db.session.add(message)
    db.session.commit()


def get_user_drafts(user_id):
    q = db.session.query(Message).filter(Message.sender == user_id and Message.is_draft)
    return q.all()


def get_user_draft(user_id, draft_id):
    q = db.session.query(Message).filter(
        Message.sender == user_id and Message.is_draft and Message.id == draft_id
    )
    return q.first()


def unmark_draft(user_id, draft_id):
    message = (
        db.session.query(Message)
        .filter(
            Message.sender == user_id and Message.is_draft and Message.id == draft_id
        )
        .first()
    )
    
    if message is None:
        raise KeyError("Draft does not exist!")
    else:
        message.is_draft = False
        db.session.commit()
        return message


def delete_user_message(user_id, message_id, is_draft=False):
    q = db.session.query(Message).filter(
        Message.sender == user_id and Message.message_id == message_id
    )
    message = q.first()
    if message is None:
        raise ValueError()

    db.session.delete(message)
    db.session.commit()


def get_all_messages(user_id):

    # Retrieve of all message for user_id
    q = db.session.query(Message).filter(
        Message.recipient == user_id and Message.is_draft == False
    )
    list = []
    for msg in q:
        setattr(msg, "is_read", True)
        # retrieve the name of senxder
        sender = db.session.query(User).filter(User.id == msg.get_sender()).first()
        json_msg = json.dumps(
            {
                "sender_id": sender.get_id(),
                "firstname": sender.get_firstname(),
                "lastname": sender.get_lastname(),
                "id_message": msg.message_id,
                "text": msg.text,
                "email": sender.email,
            }
        )

        list.append(json_msg)

    db.session.commit()

    return list
