import unittest

from monolith.app import create_test_app
from monolith.database import User, db
from monolith.auth import current_user


class TestApp(unittest.TestCase):
    def setUp(self):
        self.app = create_test_app()
        self.client = self.app.test_client()
        self._ctx = self.app.test_request_context()
        self._ctx.push()

    def test_unregister_not_authenticated(self):
        reply = self.client.get("/unregister")
        assert reply.status_code == 401

    def test_unregister_dummy_user(self):

        reply = self.client.post(
            "/create_user",
            data=dict(
                email="test@test.com",
                firstname="test",
                lastname="test",
                password="test",
                dateofbirth="1/1/1111",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200

        reply = self.client.post(
            "/login",
            data=dict(
                email="test@test.com",
                password="test",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200

        reply = self.client.get("/unregister", follow_redirects=True)
        assert reply.status_code == 200

        # Check the user in the db has is_active=False
        user = User.query.filter(User.email == "test@test.com").first()
        assert not user.get_isactive()

    def test_get_receiveers(self):
        reply = self.client.post(
            "/create_user",
            data=dict(
                email="test@test.com",
                firstname="test",
                lastname="test",
                password="test",
                dateofbirth="1/1/1111",
            ),
            follow_redirects=True,
        )

        assert reply.status_code == 200

        reply = self.client.post(
            "/create_user",
            data=dict(
                email="test1@test1.com",
                firstname="test1",
                lastname="test1",
                password="test1",
                dateofbirth="1/1/1111",
            ),
            follow_redirects=True,
        )

        assert reply.status_code == 200
        # login
        reply = self.client.post(
            "/login",
            data=dict(
                email="test@test.com",
                password="test",
            ),
            follow_redirects=True,
        )

        assert reply.status_code == 200

        reply = self.client.get("/user/get_recipients")

        body = reply.get_json()
        # expect all other users except test
        assert body[0] == {"email": "example@example.com", "id": 1}
        assert body[1] == {"email": "test1@test1.com", "id": 3}
