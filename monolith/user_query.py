from monolith.database import User, db, Black_list


def get_recipients(sender_id):
    result = (
        db.session.query(User.id, User.email)
        .filter(User.id != sender_id)
        .filter(User.is_active)
        .filter(
            User.id.not_in(
                db.session.query(Black_list.member).filter(
                    Black_list.owner == sender_id
                )
            )
        )
    )
    return result


def get_black_list(owner_id):
    result_ = []
    try:
        result_ = (
            db.session.query(Black_list.member, User.email)
            .filter(Black_list.owner == owner_id)
            .filter(Black_list.member == User.id)
            .all()
        )
    except Exception as e:
        print("Exception in get_black_list %r", e)

    return result_


def add_users_to_black_list(owner_id, members_id):
    _result = False
    try:
        for member_id in members_id:
            entry = Black_list()
            entry.owner = owner_id
            entry.member = member_id
            db.session.add(entry)

        db.session.commit()
        _result = True
    except Exception as e:
        db.session.rollback()
        print("Exception in add_user_to_black_list %r", e)

    return _result


def get_choices(owner_id):
    _result = []
    try:
        result = (
            db.session.query(User.id, User.email)
            .filter(User.id != owner_id)
            .filter(User.is_admin == 0)
            .filter(
                User.id.not_in(
                    db.session.query(Black_list.member).filter(
                        Black_list.owner == owner_id
                    )
                )
            )
            .all()
        )
        _result = [(usr.id, usr.email) for usr in result]
    except Exception as e:
        print("Exception in get_choices %r", e)
    return _result


def delete_users_black_list(owner_id, members_id):
    _result = False
    try:
        for member_id in members_id:
            db.session.query(Black_list).filter(Black_list.owner == owner_id).filter(
                Black_list.member == member_id
            ).delete()

        db.session.commit()
        _result = True
    except Exception as e:
        db.session.rollback()
        print("Exception in delete_user_black_list %r", e)

    return _result


def get_user_mail(user_id):
    result = ""
    try:
        tmp = db.session.query(User.email).filter(User.id == user_id).first()
        result = tmp[0]
    except Exception as e:
        print("Exception in get_user_mail %r", e)
    return result
