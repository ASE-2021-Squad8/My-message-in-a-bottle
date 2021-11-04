import unittest
from monolith.background import check_messages, send_notification_task, lottery
from monolith.database import User, db, Message
from datetime import datetime, timedelta
from monolith.app import create_test_app
import random


class TestPeriodicTask(unittest.TestCase):
    def setUp(self):
        self.app = create_test_app()
        self.client = self.app.test_client()
        self._ctx = self.app.test_request_context()
        self._ctx.push()

    def test_check_messages(self):
        now = datetime.now()
        with self.app.app_context():
            # add messages that should have been already delivered
            for i in range(1, 6):
                msg = Message()
                msg.sender = 1
                msg.recipient = 2
                msg.text = "Hello how are you? " + str(i)
                msg.delivery_date = now - timedelta(days=random.randint(1, 30))
                db.session.add(msg)
                db.session.commit()

            # expect success state and number of message sent equal to 5
            expected_result = (True, 5)
            assert check_messages(0, 0) == expected_result

    """
    def test_send_notification_task(self):
        recipient_mail = (
            "pioppoj@gmail.com"  # insert here your mail to get the notification
        )
        json_message = json.dumps(
            {
                "sender": "squad 8",
                "recipient": recipient_mail,
                "body": "test was executed successfully",
                "TESTING": True,
            }
        )
        assert send_notification_task(json_message)
        """
    """
    def test_lottery(self):
        result = lottery(True)
        assert result[0]
        with self.app.app_context():
            winner = db.session.query(User).filter(User.id == result[1]).first()
            assert winner.points == 20
    """
