import unittest

from monolith.app import create_test_app
from monolith.database import User, db


class TestApp(unittest.TestCase):
    def setUp(self):
        self.app = create_test_app()
        self.client = self.app.test_client()
        self._ctx = self.app.test_request_context()
        self._ctx.push()

    def test_unregister_not_authenticated(self):
        reply = self.client.get("/unregister")
        assert reply.status_code == 401

    def test_create_dummy_user(self):
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

    def test_unregister_dummy_user(self):
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

    def test_check_unregistered_in_database(self):
        query = db.session.query(User).filter(User.email == "test@test.com")
        assert query.first() == None
