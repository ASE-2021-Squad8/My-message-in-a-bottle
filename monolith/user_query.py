from monolith.database import User, db, BlackList


def get_recipients(sender_id):
    """Gets the list of possible recipients for a specific user,
    accounting for the blasklist

    :param sender_id: user id of the sender
    :type sender_id: int
    :return: resulting database query
    :rtype: Query
    """

    result = (
        db.session.query(User.id, User.email)
        .filter(User.id != sender_id)
        .filter(User.is_active)
        .filter(
            User.id.not_in(
                db.session.query(BlackList.member).filter(BlackList.owner == sender_id)
            )
        )
    )
    return result


def get_blacklist(owner_id):
    """Retrieves the blacklist owned by a specific user

    :param owner_id: user id for the blacklist owner
    :type owner_id: int
    :return: a list of blocked users
    :rtype: list[User]
    """

    result = []
    try:
        result = (
            db.session.query(BlackList.member, User.email)
            .filter(BlackList.owner == owner_id)
            .filter(BlackList.member == User.id)
            .all()
        )
    except Exception as e:
        print("Exception in get_black_list %r", e)

    return result


def add_to_blacklist(owner_id, members_id):
    """Adds a new user to a blacklist

    :param owner_id: the user id of the blacklist owner
    :type owner_id: int
    :param members_id: the user id to add to the blacklist
    :type members_id: int
    :return: True if the user was added to the blacklist, False otherwise
    :rtype: bool
    """

    result = False
    try:
        for member_id in members_id:
            entry = BlackList(owner=owner_id, member=member_id)
            db.session.add(entry)

        db.session.commit()
        result = True
    except Exception as e:
        db.session.rollback()
        print("Exception in add_user_to_black_list %r", e)

    return result


def get_blacklist_candidates(owner_id):
    """Computes a list of users that can be added to a blacklist, depending on the owner

    :param owner_id: the id for the user that owns the blacklist
    :type owner_id: int
    :return: list of blacklist-able users
    :rtype: list[User]
    """

    result = []
    try:
        result = (
            db.session.query(User.id, User.email)
            .filter(User.id != owner_id)
            .filter(
                User.id.not_in(
                    db.session.query(BlackList.member).filter(
                        BlackList.owner == owner_id
                    )
                )
            )
            .all()
        )
        result = [(usr.id, usr.email) for usr in result]
    except Exception as e:
        print("Exception in get_choices %r", e)

    return result


def remove_from_blacklist(owner_id, members_id):
    """Removes a user from a blacklist

    :param owner_id: the user id of the blacklist owner
    :type owner_id: int
    :param members_id: the user id to remove from the blacklist
    :type members_id: int
    :return: True if the user was removed from the blacklist, False otherwise
    :rtype: bool
    """

    result = False
    try:
        for member_id in members_id:
            db.session.query(BlackList).filter(BlackList.owner == owner_id).filter(
                BlackList.member == member_id
            ).delete()

        db.session.commit()
        result = True
    except Exception as e:
        db.session.rollback()
        print("Exception in delete_user_black_list %r", e)

    return result


def get_user_mail(user_id):
    """Retrieves the email address for a specific user

    :param user_id: the id of the user
    :type user_id: int
    :return: the user's email address
    :rtype: str
    """

    result = ""
    try:
        tmp = db.session.query(User.email).filter(User.id == user_id).first()
        result = tmp[0]
    except Exception as e:
        print("Exception in get_user_mail %r", e)

    return result


def get_user_by_email(user_email):
    """Checks if a user with the specified email already exists

    :param user_email: the email of the user
    :type user_email: string
    :return: True if the user exists, False otherwise
    :rtype: bool
    """

    user = db.session.query(User).filter(User.email == user_email).first()
    if user is None:
        return False
    else:
        return True


def get_all_users():
    """Returns all the users registered to the service
    
    :return: the list of all the users registered
    :rtype: list
    """

    return db.session.query(User)
