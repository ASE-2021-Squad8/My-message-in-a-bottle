import unittest

from monolith.app import create_test_app
from monolith.database import User, db


class TestApp(unittest.TestCase):
    def setUp(self):
        self.app = create_test_app()
        self.client = self.app.test_client()
        self._ctx = self.app.test_request_context()
        self._ctx.push()

    def unregister_not_authenticated(self):
        reply = self.client.get("/unregister")
        assert reply.status_code == 401

    def create_dummy_user(self):
        reply = self.client.post(
            "/create_user",
            data=dict(
                email="test@test.com",
                firstname="test",
                lastname="test",
                password="test",
                dateofbirth="1/1/1111",
            ),
        )
        assert reply.status_code == 200

    def unregister_dummy_user(self):
        reply = self.client.post(
            "/login", data=dict(email="test@test.com", password="test")
        )
        assert reply.status_code == 200
        reply = self.client.get("/unregister", follow_redirects=True)
        assert reply.status_code == 200

    def check_unregistered_in_database(self):
        query = db.session.query(User).filter(User.email == "test@test.com")
        print("query")
        print(query)
        print(query.first())
        print("query")
        assert 1 == 2 # Just to test if pytest works. FIXME pytest does not fail
