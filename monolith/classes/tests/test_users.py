import unittest

from monolith.app import create_test_app
from monolith.database import User, db
from monolith.auth import current_user
import datetime


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

    def test_not_authenticated_update_data(self):
        reply = self.client.get("/update_data")
        assert reply.status_code == 401

    def test_update_data(self):
        reply = self.client.post(
            "/create_user",
            data=dict(
                email="test_update@test.com",
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
                email="test_update@test.com",
                password="test",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200
        reply = self.client.post(
            "/update_data",
            data=dict(
                textfirstname="test_new",
                textlastname="test_new",
                textbirth="2021-02-02",
                textemail="test_new@test.com",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200
        user = User.query.filter(User.email == "test_new@test.com").first()
        assert user is not None
        assert user.firstname == "test_new"
        assert user.lastname == "test_new"
        assert user.dateofbirth == datetime.datetime(2021, 2, 2)

    def test_not_authenticated_update_password(self):
        reply = self.client.get("/reset_password")
        assert reply.status_code == 401

    def test_update_password(self):
        reply = self.client.post(
            "/create_user",
            data=dict(
                email="pass_update@test.com",
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
                email="pass_update@test.com",
                password="test",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200
        reply = self.client.post(
            "/reset_password",
            data=dict(
                currentpassword="test",
                newpassword="test_new",
                confirmpassword="test_new",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200
        user = User.query.filter(User.email == "pass_update@test.com").first()
        assert user is not None
        assert user.authenticate("test_new")
