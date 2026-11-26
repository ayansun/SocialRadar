"""Make an existing user an admin.

Usage:  python -m app.create_admin user@example.com
(Register the user first with POST /auth/register.)
"""

import sys

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import User


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m app.create_admin <email>")
    email = sys.argv[1].lower()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(func.lower(User.email) == email))
        if user is None:
            sys.exit(f"No user with email {email}. Register first.")
        user.role = "admin"
        db.commit()
        print(f"{user.email} is now an admin")


if __name__ == "__main__":
    main()
