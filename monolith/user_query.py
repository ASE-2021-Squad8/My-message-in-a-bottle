from database import User,db

def get_users(sender_id):
    result = db.session.query(User).filter(User.id != sender_id)
    return result