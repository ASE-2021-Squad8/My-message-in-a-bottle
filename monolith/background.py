import json
import random
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab  # cronetab for lottery
from celery.utils.log import get_logger

from monolith.database import db
from monolith.messaging import check_message_to_send, update_message_state
from monolith.notifications import send_notification
from monolith.user_query import add_points, get_user_mail, get_lottery_participants


logger = get_logger(__name__)
# broker's url and storing results
BACKEND = BROKER = "redis://localhost:6379"
# create celery instance
celery = Celery(__name__, backend=BACKEND, broker=BROKER)
# route tasks on their queue
celery.conf.task_route = {
    "monolith.background.send_message": {"queue": "message"},  # key message
    "monolith.background.send_notification_task": {
        "queue": "notification"
    },  # key notification
}

# set up period task for checking messages
celery.conf.beat_schedule = {
    "check_message": {
        "task": "monolith.background.check_messages",
        "schedule": timedelta(minutes=15),  # every 15 minutes
        "args": [False],  # test mode
    },
    "lottery": {
        "task": "monolith.background.lottery",
        "schedule": crontab(0, 0, day_of_month="1"),  # every 1st timedelta(seconds=20),
        "args": [False],  # test mode
    },
}
celery.conf.timezone = "UTC"
_APP = None

# change state message to delivered
@celery.task
def send_message(json_message):
    logger.info("Message: " + json_message)
    global _APP
    tmp = json.loads(json_message)
    # lazy init
    if _APP is None:
        from monolith.app import create_app

        app = create_app(tmp["TESTING"])
        db.init_app(app)
    else:
        app = _APP
    # update message state
    try:
        with app.app_context():
            result = update_message_state(tmp["id"], "is_delivered", 1)
            if result and not tmp["TESTING"]:
                # send notification via celery
                send_notification_task.apply_async(
                    args=[json_message],
                    routing_key="notification",
                    queue="notification",
                )
    except Exception as e:
        logger.exception("save_message raised %r", e)
        raise e
    logger.info("end")
    return result


# periodic task to manage possible fault
@celery.task
def check_messages(test_mode):
    global _APP
    # lazy init
    if _APP is None:
        from monolith.app import create_app

        app = create_app(test_mode)
        db.init_app(app)
    else:
        app = _APP
    logger.info("check_message start")
    result = False
    with app.app_context():
        try:
            ids = check_message_to_send()
            # for each message has been found as undelivered send notification
            for id in ids:
                email_s = get_user_mail(id[0])
                email_r = get_user_mail(id[1])
                json_message = build_json(
                    email_s,
                    email_r,
                    "You have just received a message",
                    app.config["TESTING"],
                )
                # send notification via celery
                send_notification_task.apply_async(
                    args=[json_message],
                    routing_key="notification",
                    queue="notification",
                )
            result = True
        except Exception as e:
            logger.exception("check_messages raises %r", e)
            raise e
    return (result, len(ids))  # state and number of sent message


# send email via celery on notification queue
@celery.task
def send_notification_task(json_message):
    logger.info("Message task: " + json_message)
    global _APP
    result = False
    tmp = json.loads(json_message)
    # lazy init
    if _APP is None:
        from monolith.app import create_app

        app = create_app(tmp["TESTING"])
        db.init_app(app)
    else:
        app = _APP
    try:
        send_notification(tmp["sender"], tmp["recipient"], tmp["body"])
        result = True
    except Exception as e:
        logger.exception("send_notification_task raises ", e)
        raise e
    return result


@celery.task
def lottery(test_mode):
    global _APP
    result = False
    id_winner = -1
    # lazy init
    if _APP is None:
        from monolith.app import create_app

        app = create_app(test_mode)
        db.init_app(app)
    else:
        app = _APP

    with app.app_context():
        participants = get_lottery_participants()
        winner = random.randint(0, len(participants) - 1)
        email_r = participants[winner].email
        sender = "Message in a bottle"
        json_message = build_json(
            sender, email_r, "You have just won 20 points!", app.config["TESTING"]
        )
        if add_points(20, participants[winner].id):
            send_notification_task.apply_async(
                args=[json_message],
                routing_key="notification",
                queue="notification",
            )
            id_winner = participants[winner].id
            result = True
    return (result, id_winner)


def build_json(email_s, email_r, body, testing):
    return json.dumps(
        {
            "sender": email_s,
            "recipient": email_r,
            "body": body,
            "TESTING": testing,
        }
    )
