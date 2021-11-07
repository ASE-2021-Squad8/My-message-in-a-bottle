import unittest

from monolith.app import create_test_app
from monolith.database import User, db
from monolith.auth import current_user
from flask import jsonify
import monolith.user_query
import datetime
import json


class TestApp(unittest.TestCase):
    def setUp(self):
        self.app = create_test_app()
        self.client = self.app.test_client()
        self._ctx = self.app.test_request_context()
        self._ctx.push()

    def test_wrong_login(self):
        # Test email does not exist
        reply = self.client.post(
            "/login",
            data=dict(
                email="test_user_not_exists@test.com",
                password="test",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200
        assert not current_user.is_authenticated

        # Test wrong password
        reply = self.client.post(
            "/login",
            data=dict(
                email="example@example.com",
                password="WRONGPW",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200
        assert not current_user.is_authenticated

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

        # Try logging in with the unregistered user
        reply = self.client.post(
            "/login",
            data=dict(
                email="test_unregister@test.com",
                password="test",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200
        assert not current_user.is_authenticated

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

        # test reporting a user that does not exist
        reply = self.client.post(
            "/report_user",
            data=dict(
                useremail="test_user_not_exists@test.com",
            ),
        )
        assert reply.status_code == 200
        user = User.query.filter(User.email == "test_user_not_exists@test.com").first()
        assert user is None

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

        # Try logging in with banned account
        reply = self.client.post(
            "/login",
            data=dict(
                email="test_ban@test.com",
                password="test",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200
        assert not current_user.is_authenticated

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
                textfirstname="",
                textlastname="test_new",
                textbirth="2222-2-2",
                textemail="test_new@test.com",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200
        user = User.query.filter(User.email == "test_update@test.com").first()
        assert user.firstname == "test"

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
                currentpassword="WRONGPW",
                newpassword="test_new",
                confirmpassword="test_new",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200
        user = User.query.filter(User.email == "pass_update@test.com").first()
        assert user.authenticate("test")

        reply = self.client.post(
            "/reset_password",
            data=dict(
                currentpassword="test",
                newpassword="test_new",
                confirmpassword="WRONGPW",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200
        user = User.query.filter(User.email == "pass_update@test.com").first()
        assert user.authenticate("test")

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
        # test filter enable/disable on a non existent user
        self.assertRaises(
            Exception, monolith.user_query.change_user_content_filter, 9999, True
        )

        # test filter activation function
        filter = monolith.user_query.change_user_content_filter(1, True)
        assert filter == True

        # test filter deactivation function
        filter = monolith.user_query.change_user_content_filter(1, False)
        assert filter == False

        reply = self.client.post(
            "/login",
            data=dict(
                email="example@example.com",
                password="admin",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200

        # test filter activation api
        reply = self.client.get("/api/content_filter/1")
        assert reply.status_code == 200
        user = db.session.query(User).filter(User.id == 1).first()
        assert user.content_filter

        # test filter deactivation api
        reply = self.client.get("/api/content_filter/0")
        assert reply.status_code == 200
        user = db.session.query(User).filter(User.id == 1).first()
        assert not user.content_filter

    def test_get_user_details(self):
        reply = self.client.post(
            "/login",
            data=dict(
                email="example@example.com",
                password="admin",
            ),
            follow_redirects=True,
        )
        assert reply.status_code == 200

        reply = self.client.get("/api/user/1")
        assert reply.status_code
        data = reply.get_json()
        assert data["email"] == "example@example.com"
        assert data["firstname"] == "Admin"
        assert data["lastname"] == "Admin"

        reply = self.client.get("/api/user/999999")
        assert reply.status_code == 404

    def test_get_users_list(self):
        reply = self.client.get("/api/users/list")
        data = reply.get_json()
        users = db.session.query(User)
        userlist = [
            {"email": u.email, "firstname": u.firstname, "lastname": u.lastname}
            for u in users
        ]
        assert userlist == data

    def test_exception_user_query(self):
        assert not monolith.user_query.add_to_blacklist(None, None)
        assert not monolith.user_query.remove_from_blacklist(None, None)
        assert not monolith.user_query.add_points(0, None)
        assert monolith.user_query.get_user_mail(None) == ""
