import datetime

from flask import Flask

from monolith.auth import login_manager
from monolith.database import User, db
from monolith.views import blueprints


def create_test_app():
    """Utility that creates an instance of the application to be run in testing

    Returns:
        Flask: application instance
    """

    return create_app(True)


def create_app(test_mode=False):
    """Creates an instance of the application.

    Args:
        test_mode (bool, optional): creates an application instance for testing. Defaults to False.

    Returns:
        Flask: application instance
    """

    app = Flask(__name__)
    if test_mode:
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///../mmiab-test.db"
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///../mmiab.db"
        app.config["WTF_CSRF_SECRET_KEY"] = "A SECRET KEY"
    app.config["SECRET_KEY"] = "ANOTHER ONE"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    for bp in blueprints:
        app.register_blueprint(bp)
        bp.app = app

    db.init_app(app)
    login_manager.init_app(app)
    db.create_all(app=app)

    # create a first admin user
    with app.app_context():
        q = db.session.query(User).filter(User.email == "example@example.com")
        user = q.first()
        if user is None:
            example = User()
            example.firstname = "Admin"
            example.lastname = "Admin"
            example.email = "example@example.com"
            example.dateofbirth = datetime.datetime(2020, 10, 5)
            example.is_admin = True
            example.set_password("admin")
            db.session.add(example)
            db.session.commit()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run()
