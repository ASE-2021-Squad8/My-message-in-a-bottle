from celery import Celery
from monolith.messaging import save_message
from monolith.database import User, db, Message
import json
from celery.utils.log import get_logger

logger = get_logger(__name__)
# broker's url and storing results
BACKEND = BROKER = "redis://localhost:6379"
# create celery instance
celery = Celery(__name__, backend=BACKEND, broker=BROKER)

_APP = None

# queue task
@celery.task
def send_message(json_message):
    logger.info("message: " + json_message)
    global _APP
    # lazy init
    if _APP is None:
        from monolith.app import create_app

        app = create_app()
        db.init_app(app)
    else:
        app = _APP
    # decode json and insert message into data base
    try:
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
    except Exception as e:
        logger.exception("save_message raised %r", e)
        raise e
    logger.info("end")
    return "execution ok"
