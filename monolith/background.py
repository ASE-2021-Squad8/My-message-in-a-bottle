from os import name
from celery import Celery
from monolith.messaging import check_message_to_send, save_message, update_message_state
from monolith.database import User, db, Message
import json
from celery.utils.log import get_logger


logger = get_logger(__name__)
# broker's url and storing results
BACKEND = BROKER = "redis://localhost:6379"
# create celery instance
celery = Celery(__name__, backend=BACKEND, broker=BROKER)

# set up period task for checking messages
celery.conf.beat_schedule = {
    "check_message": {
        "task": "monolith.background.check_messages",
        "schedule": 900,  # 15 minutes
        "args": (0, 0),
    }
}
celery.conf.timezone = "UTC"
# CELERY_IMPORTS = ["background"]
_APP = None

# queue task
@celery.task
def send_message(json_message):
    logger.info("Message: " + json_message)
    global _APP
    # lazy init
    if _APP is None:
        from monolith.app import create_app

        app = create_app()
        db.init_app(app)
    else:
        app = _APP
    # update message state
    try:
        with app.app_context():
            tmp = json.loads(json_message)
            result = update_message_state(tmp["id"], "is_delivered", 1)
    except Exception as e:
        logger.exception("save_message raised %r", e)
        raise e
    logger.info("end")
    return result


@celery.task
def check_messages(self, message):
    global _APP
    # lazy init
    if _APP is None:
        from monolith.app import create_app

        app = create_app()
        db.init_app(app)
    else:
        app = _APP
    logger.info("check_message start")
    result = False
    with app.app_context():
        try:
            check_message_to_send()
            result = True
        except Exception as e:
            logger.exception("check_messages raises %r", e)
    return result
