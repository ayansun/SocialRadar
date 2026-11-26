"""Registration and login rules."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ConflictError
from app.models import User
from app.schemas.user import UserCreate
from app.security import hash_password, verify_password


def register_user(db: Session, data: UserCreate) -> User:
    email = data.email.lower()
    if db.scalar(select(User.id).where(func.lower(User.email) == email)) is not None:
        raise ConflictError("A user with this email already exists")
    if db.scalar(select(User.id).where(func.lower(User.username) == data.username.lower())):
        raise ConflictError("A user with this username already exists")

    # Everyone who registers is a regular user. An admin is made with
    # `python -m app.create_admin <email>`.
    user = User(
        email=email,
        username=data.username,
        hashed_password=hash_password(data.password),
        role="user",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # two identical registrations at the same moment
        db.rollback()
        raise ConflictError("A user with this email or username already exists")
    return user


def authenticate(db: Session, login: str, password: str) -> User | None:
    """`login` is an email or a username. Returns None if the credentials are wrong."""
    login = login.strip().lower()
    user = db.scalar(
        select(User).where(
            (func.lower(User.email) == login) | (func.lower(User.username) == login)
        )
    )
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user
