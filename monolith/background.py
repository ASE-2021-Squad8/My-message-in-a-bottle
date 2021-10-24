from celery import Celery
from monolith.messaging import save_message
from monolith.database import User, db, Message
import json
from types import SimpleNamespace
#broker's url and storing results
BACKEND = BROKER = 'redis://localhost:6379'
#create celery instance
celery = Celery(__name__, backend=BACKEND, broker=BROKER)

_APP = None

#queue task
@celery.task
def send_message(json_message):
    global _APP
    # lazy init
    if _APP is None:
        from monolith.app import create_app
        app = create_app()
        db.init_app(app)
    else:
        app = _APP
    print(json_message)
    with app.app_context():
        tmp = json.loads(json_message)
        msg = Message()
        msg.text = tmp["text"]
        msg.sender = tmp["sender"]
        msg.recipient = tmp["recipient"]
        msg.is_draft = tmp["is_draft"]
        msg.is_read = tmp["is_read"]
        msg.is_delivered = tmp["is_delivered"]
        save_message(msg)
    return "execution ok"

