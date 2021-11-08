import json
import random
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab  # cronetab for lottery
from celery.utils.log import get_logger

from monolith.database import db
from monolith.messaging import check_message_to_send, update_message_state
from monolith.notifications import send_notification
from monolith.user_query import add_points, get_user_mail, get_lottery_participants, get_user_by_email


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

# set up period task
celery.conf.beat_schedule = {
    # for coping with faults during message delivery
    "check_message": {
        "task": "monolith.background.check_messages",
        "schedule": timedelta(minutes=15),  # every 15 minutes
        "args": [False],  # test mode
    },
    # lottery game
    "lottery": {
        "task": "monolith.background.lottery",
        "schedule": crontab(0, 0, day_of_month="1"),  # every 1st
        "args": [False],  # test mode
    },
}
# set timezone
celery.conf.timezone = "UTC"
_APP = None


@celery.task
# Don't include towards coverage as this needs to be tested via its endpoint
def send_message(json_message): # pragma: no cover
    """Deliver a message updating is_delivered to 1
    :param json_message: data to execute the task
    :type json_message: json format string
    :raises Exception: if an error occurs
    :returns: True in case update succeed otherwise False
    :rtype: bool
    """
    logger.info("Start send_message json_message: " + json_message)
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
        logger.exception("save_message raised ", e)
        raise e
    logger.info("End send_message result: " + str(result))
    return result


@celery.task
def check_messages(test_mode):
    """Check that messages have been sent correctly
    :param test_mode: determine the operating mode
    :type test_mode: bool
    :raises Exception: if an error occurs
    :returns: state of execution and number of messages sent
    :rtype: couple (bool,int)
    """
    global _APP
    # lazy init
    if _APP is None:
        from monolith.app import create_app

        app = create_app(test_mode)
        db.init_app(app)
    else:
        app = _APP
    logger.info("Start check_message test_mode: " + str(test_mode))
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
            logger.exception("check_messages raises ", e)
            raise e
    # state and number of sent messages
    couple = (result, len(ids))
    logger.info("End check_message couple: " + str(couple))
    return couple


@celery.task
def send_notification_task(json_message):
    """send email via celery on notification queue
    :param json_message: data to execute the task
    :type json_message: json string
    :raises Exception: if an error occurs
    :returns : True if email is sent correctly otherwise False
    :rtype: bool
    """
    logger.info("Start send_notification_task json_message: " + json_message)
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
        recipient = get_user_by_email(tmp["receiver"])
        # Banned/deleted users shouldn't receive any notifications 
        if recipient.is_active:
            send_notification(tmp["sender"], tmp["recipient"], tmp["body"])
            result = True
    except Exception as e:
        logger.exception("send_notification_task raises ", e)
        raise e
    logger.info("End send_notification_task result " + str(result))
    return result


@celery.task
def lottery(test_mode):
    """implement lottery game
    :param test_mode : determine the operating mode
    :type test_mode: bool
    :returns: False in case errors occur otherwise True
    :rtype: bool
    """
    logger.info("Lottery game start")
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
        # get all participants
        participants = get_lottery_participants()
        # extract the winner randomly
        winner = random.randint(0, len(participants) - 1)
        email_r = participants[winner].email
        sender = "Message in a bottle"
        json_message = build_json(
            sender, email_r, "You have just won 20 points!", app.config["TESTING"]
        )
        if add_points(20, participants[winner].id):
            # send mail to winner
            send_notification_task.apply_async(
                args=[json_message],
                routing_key="notification",
                queue="notification",
            )
            id_winner = participants[winner].id
            result = True
    logger.info("Lottery game end winner id: " + str(id_winner))
    return (result, id_winner)


def build_json(sender, email_r, body, testing):
    """build up json message to pass parameter via celery
    :param sender : sender of the message
    :type sender: string
    :param email_r: receiver's email address
    :type email_r: string
    :param body: content of the message
    :type body: string
    :param testing: test mode
    :type testing: bool
    :returns: False in case errors occur otherwise True
    :rtype: bool
    """
    return json.dumps(
        {
            "sender": sender,
            "recipient": email_r,
            "body": body,
            "TESTING": testing,
        }
    )
