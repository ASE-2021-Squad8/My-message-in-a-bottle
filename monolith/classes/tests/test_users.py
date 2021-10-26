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
                email="test_unregister@test.com",
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
                email="test_unregister@test.com",
                password="test",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200

        reply = self.client.get("/unregister", follow_redirects=True)
        assert reply.status_code == 200

        # Check the user in the db has is_active=False
        user = User.query.filter(User.email == "test_unregister@test.com").first()
        assert not user.get_isactive()

    def test_report_ban_dummy_user(self):
        reply = self.client.post(
            "/create_user",
            data=dict(
                email="test_ban@test.com",
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
                email="example@example.com",
                password="admin",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200

        for i in range(1, 4):
            reply = self.client.post(
                "/report_user",
                data=dict(
                    useremail="test_ban@test.com",
                ),
            )
            assert reply.status_code == 200
            # Check the user in the db has reports = i
            user = User.query.filter(User.email == "test_ban@test.com").first()
            assert user.reports == i

        # Check the user in the db has been banned (is_active=False)
        user = User.query.filter(User.email == "test_ban@test.com").first()
        assert not user.get_isactive()
