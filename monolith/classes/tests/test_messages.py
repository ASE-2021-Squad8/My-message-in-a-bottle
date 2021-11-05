import io
import time
import unittest
from datetime import datetime, timedelta

from flask import url_for
from monolith.app import create_test_app
import time
import json

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
            data["attachment"] = (
                io.BytesIO(b"This is a JPG file, I swear!"),
                "test.jpg",
            )
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

    def test_message(self):

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
        delivery_date = now + timedelta(seconds=4)

        # test send with msg empty
        reply = self.client.post(
            "/api/message/send_message",
            data=dict(
                {
                    "recipient": data[0]["id"],
                    "text": "",
                    "delivery_date": delivery_date,
                    "draft_id": "",
                }
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 400

        delivery_date_past = now - timedelta(days=1)
        # test send with data in the past
        reply = self.client.post(
            "/api/message/send_message",
            data=dict(
                {
                    "recipient": data[0]["id"],
                    "text": "",
                    "delivery_date": delivery_date_past,
                    "draft_id": "",
                }
            ),
            follow_redirects=True,
        )

        assert reply.status_code == 400

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

        reply = self.client.get("/api/message/sent/metadata", follow_redirects=True)
        assert len(reply.get_json()) == 0

        print("Waiting for the message delivery", end="")
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
        assert msg["text"] == "Let's do it !"

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
        assert msg["text"] == "Let's do it !"

        # delete existing not read message
        reply = self.client.delete(
            "api/message/delete/" + str(id_message), follow_redirects=True
        )
        assert reply.status_code == 404

        # read received message
        reply = self.client.get(
            "api/message/read_message/" + str(id_message), follow_redirects=True
        )
        assert reply.status_code == 200

        # delete existing message
        reply = self.client.delete(
            "api/message/delete/" + str(id_message), follow_redirects=True
        )
        assert reply.status_code == 200

        id_deleted = reply.get_json()["message_id"]
        assert str(id_deleted) == str(id_message)

        # read not-existing message
        reply = self.client.get(
            "api/message/read_message/" + str(id_message), follow_redirects=True
        )
        assert reply.status_code == 404

        reply = self.client.get("/unregister", follow_redirects=True)
        assert reply.status_code == 200
