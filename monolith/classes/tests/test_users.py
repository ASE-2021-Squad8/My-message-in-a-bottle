import unittest

from monolith.app import create_test_app
from monolith.database import User, db
from monolith.auth import current_user
import monolith.user_query
import datetime
import json


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
                dateofbirth="1111-1-1",
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
                dateofbirth="1111-1-1",
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

    def test_get_recipients(self):
        reply = self.client.post(
            "/create_user",
            data=dict(
                email="test_receiver@test.com",
                firstname="test",
                lastname="test",
                password="test",
                dateofbirth="1111-1-1",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200

        reply = self.client.post(
            "/create_user",
            data=dict(
                email="test_1@test.com",
                firstname="test",
                lastname="test",
                password="test",
                dateofbirth="1111-1-1",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200

        reply = self.client.post(
            "/login",
            data=dict(
                email="test_receiver@test.com",
                password="test",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200

        reply = self.client.get("/user/get_recipients")
        body = reply.get_json()
        # expect all other users except test
        assert body[0] == {"email": "example@example.com", "id": 1}
        assert body[1] == {"email": "test_1@test.com", "id": 4}

        """
        BLACK LIST TEST
        """

        # add user 3 into black list
        reply = self.client.post(
            "/user/black_list",
            data=json.dumps({"op": "add", "users": [4]}),
            content_type="application/json",
        )

        assert reply.status_code == 200

        reply = self.client.get("/user/get_recipients")
        body = reply.get_json()
        assert reply.status_code == 200
        # now expect only user 1
        assert body[0] == {"email": "example@example.com", "id": 1}

        # delete user 4 into black list
        reply = self.client.post(
            "/user/black_list",
            data=json.dumps({"op": "delete", "users": [4]}),
            content_type="application/json",
        )

        assert reply.status_code == 200

        reply = self.client.get("/user/get_recipients")
        body = reply.get_json()
        # now expect it among possible receiver
        assert body[0] == {"email": "example@example.com", "id": 1}
        assert body[1] == {"email": "test_1@test.com", "id": 4}

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
                dateofbirth="1111-1-1",
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
                textbirth="2222-2-2",
                textemail="test_new@test.com",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200
        user = User.query.filter(User.email == "test_new@test.com").first()
        assert user is not None
        assert user.firstname == "test_new"
        assert user.lastname == "test_new"
        assert user.dateofbirth == datetime.datetime(2222, 2, 2)

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
                dateofbirth="1111-1-1",
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

    def test_create_user_future_dateofbirth(self):
        reply = self.client.post(
            "/create_user",
            data=dict(
                email="test_future_dateofbirth@test.com",
                firstname="test",
                lastname="test",
                password="test",
                dateofbirth="2222-1-1",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200

        user = User.query.filter(
            User.email == "test_future_dateofbirth@test.com"
        ).first()
        assert user is None

    def test_create_user_used_email(self):
        reply = self.client.post(
            "/create_user",
            data=dict(
                email="example@example.com",
                firstname="test",
                lastname="test",
                password="test",
                dateofbirth="1111-1-1",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200

        user = User.query.filter(User.email == "example@example.com").all()
        assert len(user) == 1

    def test_content_filter(self):
        reply = self.client.post(
            "/login",
            data=dict(
                email="example@example.com",
                password="admin",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200

        # test filter activation
        filter = monolith.user_query.change_user_content_filter(current_user.id, True)
        assert filter == True

        # test filter deactivation
        filter = monolith.user_query.change_user_content_filter(current_user.id, False)
        assert filter == False
