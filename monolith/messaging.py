from re import M
from monolith.database import Message, db

def save_draft(message):
    db.session.add(message)
    db.session.commit()

def get_user_drafts(user_id):
    q = db.session.query(Message).filter(Message.sender == user_id and Message.is_draft)
    return q.all()

def delete_user_draft(user_id, message_id):
    q = db.session.query(Message).filter(Message.sender == user_id and Message.message_id == message_id)
    message = q.first()
    if message is None or not message.is_draft:
        raise ValueError

    db.session.delete(message)
    db.session.commit()
