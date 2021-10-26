from monolith.database import User, db


def get_recipients(sender_id):
    result = db.session.query(User).filter(User.id != sender_id).filter(User.is_active)
    return result