import io
import time
import unittest
import time
import json
from datetime import datetime, timedelta

from monolith.database import Message, db
from monolith.app import create_test_app
from monolith.message_query import (
    get_day_message,
    get_received_message,
    get_sent_message,
    set_message_is_deleted_lottery,
    unmark_draft,
    update_message_state,
)


class TestApp(unittest.TestCase):
    def setUp(self):
        self.app = create_test_app()
        self.client = self.app.test_client()
        self._ctx = self.app.test_request_context()
        self._ctx.push()

    def test_unauthorised_access(self):
        reply = self.client.post("/api/message/draft", data=dict(text=""))
        assert reply.status_code == 401

    def test_empty_draft(self):
        reply = self.client.post(
            "/login",
            data=dict(email="example@example.com", password="admin"),
            follow_redirects=True,
        )

        reply = self.client.post("/api/message/draft", data=dict(text=""))
        assert reply.status_code == 400

    def test_draft_insert_delete(self):
        reply = self.client.post(
            "/login",
            data=dict(email="example@example.com", password="admin"),
            follow_redirects=True,
        )

        reply = self.client.get("/api/message/draft/all")
        assert reply.status_code == 200

        data = {"text": "Lorem ipsum dolor..."}
        data["attachment"] = (
            io.BytesIO(b"This is a JPG file, I swear!"),
            "test.jpg",
        )
        data["draft_id"] = -1
        reply = self.client.post(
            "/api/message/draft",
            data=data,
            content_type="multipart/form-data",
        )
        assert reply.status_code == 404

        data = {"text": "Lorem ipsum dolor..."}
        data["attachment"] = (
            io.BytesIO(b"This is a JPG file, I swear!"),
            "test.jpg",
        )
        data["draft_id"] = ""
        reply = self.client.post(
            "/api/message/draft",
            data=data,
            content_type="multipart/form-data",
        )
        data = reply.get_json()
        assert reply.status_code == 200
        assert data["message_id"] == 1

        reply = self.client.get("/api/message/draft/all")
        data = reply.get_json()
        assert reply.status_code == 200
        assert data[0]["text"] == "Lorem ipsum dolor..."
        assert data[0]["media"] != ""

        old_id = data[0]["message_id"]
        reply = self.client.delete("/api/message/draft/" + str(old_id) + "/attachment")
        data = reply.get_json()
        assert reply.status_code == 200
        assert str(data["message_id"]) == str(old_id)

        reply = self.client.delete("/api/message/draft/" + str(old_id) + "/attachment")
        data = reply.get_json()
        assert reply.status_code == 404

        reply = self.client.get("/api/message/draft/all")
        data = reply.get_json()
        assert reply.status_code == 200
        assert data[0]["text"] == "Lorem ipsum dolor..."
        assert data[0]["media"] == ""

        reply = self.client.delete("/api/message/draft/1")
        data = reply.get_json()
        assert reply.status_code == 200
        assert int(data["message_id"]) == 1

        reply = self.client.delete("/api/message/draft/1")
        data = reply.get_json()
        assert reply.status_code == 404

    def test_send_draft(self):
        reply = self.client.post(
            "/create_user",
            data=dict(
                email="recipient@test.com",
                firstname="recipient",
                lastname="recipient",
                password="recipient",
                dateofbirth="1111-1-1",
            ),
            follow_redirects=True,
        )

        reply = self.client.post(
            "/login",
            data=dict(email="example@example.com", password="admin"),
            follow_redirects=True,
        )
        assert reply.status_code == 200
        reply = self.client.get("/api/user/recipients")
        assert reply.status_code == 200
        data = reply.get_json()

        now = datetime.now()
        delivery_date = now + timedelta(seconds=10)
        reply = self.client.post(
            "/api/message/draft",
            data=dict(
                {
                    "recipient": data[0]["id"],
                    "text": "Let's do it !",
                    "delivery_date": delivery_date,
                    "attachment": (
                        io.BytesIO(b"This is a JPG file, I swear!"),
                        "test.jpg",
                    ),
                    "draft_id": "",
                }
            ),
            follow_redirects=True,
        )
        message_id = reply.get_json()["message_id"]
        reply = self.client.get("/api/message/draft/" + str(message_id)).get_json()
        assert reply["text"] == "Let's do it !"
        assert reply["recipient"] == data[0]["id"]

        delivery_date = now + timedelta(seconds=5)
        reply = self.client.post(
            "/api/message/",
            data=dict(
                {
                    "recipient": data[0]["id"],
                    "text": "Let's do it now!",
                    "delivery_date": delivery_date,
                    "draft_id": message_id,
                }
            ),
            follow_redirects=True,
        )

        reply = self.client.get("/api/message/sent/metadata", follow_redirects=True)
        assert len(reply.get_json()) == 0

        print("Waiting for the message delivery", end=" ", flush=True)
        time.sleep(10)

        # get sent message
        reply = self.client.get("/api/message/sent/metadata", follow_redirects=True)
        data_message = reply.get_json()
        msg = data_message[0]
        id_message = msg["id_message"]

        # get recipient message
        reply = self.client.get(
            "/api/message/sent/" + str(id_message), follow_redirects=True
        )
        msg = reply.get_json()
        assert msg["text"] == "Let's do it now!"

        # logout
        reply = self.client.get("/logout", follow_redirects=True)
        assert reply.status_code == 200

        # login by recipient
        reply = self.client.post(
            "/login",
            data=dict(email=data[0]["email"], password="recipient"),
            follow_redirects=True,
        )
        assert reply.status_code == 200

        # get recipient message
        reply = self.client.get("/api/message/received/metadata", follow_redirects=True)
        assert reply.status_code == 200
        data = reply.get_json()
        msg = json.loads(data[0])
        id_message = msg["id_message"]

        # get recipient message
        reply = self.client.get(
            "/api/message/received/" + str(id_message), follow_redirects=True
        )
        msg = reply.get_json()
        assert msg["text"] == "Let's do it now!"

        # delete existing not read message
        reply = self.client.delete(
            "/api/message/" + str(id_message), follow_redirects=True
        )
        assert reply.status_code == 404

        # read received message
        reply = self.client.get(
            "/api/message/read_message/" + str(id_message), follow_redirects=True
        )
        assert reply.status_code == 200

        # delete existing message
        reply = self.client.delete(
            "/api/message/" + str(id_message), follow_redirects=True
        )
        assert reply.status_code == 200

        id_deleted = reply.get_json()["message_id"]
        assert str(id_deleted) == str(id_message)

        # read not-existing message
        reply = self.client.get(
            "/api/message/read_message/" + str(id_message), follow_redirects=True
        )
        assert reply.status_code == 404

        reply = self.client.get("/user/unregister", follow_redirects=True)
        assert reply.status_code == 200

    def test_delete_message(self):
        # inserting a test message in the db that must be deleted to test
        # the functionality of delete message
        test_msg = Message()
        test_msg.sender = 2
        test_msg.recipient = 1
        test_msg.text = "test_delete"
        test_msg.is_draft = False
        test_msg.is_delivered = True
        test_msg.is_read = True
        test_msg.is_deleted = False
        db.session.add(test_msg)
        db.session.commit()
        message_id = test_msg.message_id
        reply = self.client.post(
            "/login",
            data=dict(email="example@example.com", password="admin"),
            follow_redirects=True,
        )
        assert reply.status_code == 200

        end_point = "/api/message/" + str(message_id)
        reply = self.client.delete(end_point)
        data = reply.get_json()
        assert reply.status_code == 200
        assert int(data["message_id"]) == message_id
        reply = self.client.delete("/api/message/-1")
        data = reply.get_json()
        assert reply.status_code == 404

        db.session.query(Message).filter(Message.message_id == message_id).delete()
        db.session.commit()

    def test_fail_send_message(self):
        reply = self.client.post(
            "/login",
            data=dict(email="example@example.com", password="admin"),
            follow_redirects=True,
        )
        assert reply.status_code == 200

        # msg with recipients=[]
        reply = self.client.post(
            "/api/message/",
            data=dict(
                {
                    "recipient": [],
                    "text": "text",
                    "delivery_date": datetime.now() + timedelta(seconds=5),
                    "draft_id": "",
                }
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 400

        # msg with text=""
        reply = self.client.post(
            "/api/message/",
            data=dict(
                {
                    "recipient": [1],
                    "text": "",
                    "delivery_date": datetime.now() + timedelta(seconds=5),
                    "draft_id": "",
                }
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 400

        # msg with delivery_date in the past
        reply = self.client.post(
            "/api/message/",
            data=dict(
                {
                    "recipient": [1],
                    "text": "text",
                    "delivery_date": datetime.now() - timedelta(seconds=5),
                    "draft_id": "",
                }
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 400

    def test_fail_message_query(self):
        # assert errors and exceptions in some messaging.py functions
        assert (
            get_day_message(
                1,
                datetime.now() + timedelta(hours=1000),
                datetime.now() + timedelta(hours=5000),
            )
            == []
        )
        assert not update_message_state(None, None, None)
        assert not set_message_is_deleted_lottery(None)
        self.assertRaises(KeyError, get_sent_message, 1, 1000)
        self.assertRaises(KeyError, get_received_message, 1, 1000)
        self.assertRaises(KeyError, unmark_draft, 1, 1000)

    def test_fail_message(self):
        reply = self.client.post(
            "/login",
            data=dict(
                email="example@example.com",
                password="admin",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200
        
        reply = self.client.get("/api/message/received/99999")
        assert reply.status_code == 404

        reply = self.client.get("/api/message/sent/99999")
        assert reply.status_code == 404

    def test_delete_lottery_message(self):
        reply = self.client.post(
            "/login",
            data=dict(
                email="example@example.com",
                password="admin",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200

        reply = self.client.get("/api/calendar/32/13/2222")
        assert reply.status_code == 404

        reply = self.client.get("/api/calendar/1/1/2222")
        assert reply.get_json() == []
