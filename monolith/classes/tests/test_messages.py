import io
import time
import unittest
from datetime import datetime, timedelta

from flask import url_for
from monolith.app import create_test_app
from monolith.database import Message


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
        with self.client:
            reply = self.client.post(
                "/login",
                data=dict(email="example@example.com", password="admin"),
                follow_redirects=True,
            )

            reply = self.client.post("/api/message/draft", data=dict(text=""))
            assert reply.status_code == 400

    def test_draft_insert_delete(self):
        with self.client:
            reply = self.client.post(
                "/login",
                data=dict(email="example@example.com", password="admin"),
                follow_redirects=True,
            )

            reply = self.client.get("/api/message/draft/all")
            assert reply.status_code == 200

            data = {"text": "Lorem ipsum dolor..."}
            data["attachment"] = (io.BytesIO(b"This is a JPG file, I swear!"), "test.jpg")
            reply = self.client.post(
                "/api/message/draft",
                data=data,
                content_type='multipart/form-data',
            )
            data = reply.get_json()
            assert reply.status_code == 200
            assert data["message_id"] == 1

            reply = self.client.get("/api/message/draft/all")
            data = reply.get_json()
            assert reply.status_code == 200
            assert data[0]["text"] == "Lorem ipsum dolor..."
            assert data[0]["media"] != ""

            reply = self.client.delete("/api/message/draft/1/attachment")
            data = reply.get_json()
            assert reply.status_code == 200
            assert int(data["message_id"]) == 1

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

    def test_send_message(self):

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

        # assert reply.status_code == 0
        reply = self.client.post(
            "/login",
            data=dict(email="example@example.com", password="admin"),
            follow_redirects=True,
        )
        assert reply.status_code == 200
        reply = self.client.get("/user/get_recipients")
        assert reply.status_code == 200
        data = reply.get_json()
        now = datetime.now()
        delivery_date = now + timedelta(minutes=1)

        reply = self.client.post(
            "/api/message/send_message",
            data=dict(
                {
                    "recipient": data[0]["id"],
                    "text": "Let's do it !",
                    "delivery_date": delivery_date,
                    "draft_id": "",
                }
            ),
            follow_redirects=True,
        )

        print("Sleeping for 62 seconds")
        time.sleep(62)  # waiting for task
        msg = (
            Message.query.filter(
                Message.recipient == int(data[0]["id"]), Message.sender == 1
            )
            .filter(Message.is_delivered == 1)
            .first()
        )

        assert msg.text == "Let's do it !"

        reply = self.client.get("/logout", follow_redirects=True)

        assert reply.status_code == 200

        reply = self.client.post(
            "/login",
            data=dict(email="example@example.com", password="admin"),
            follow_redirects=True,
        )
        assert reply.status_code == 200
        reply = self.client.post(
            "/login",
            data=dict(email="recipient@test.com", password="recipient"),
            follow_redirects=True,
        )

        reply = self.client.get("/unregister", follow_redirects=True)
