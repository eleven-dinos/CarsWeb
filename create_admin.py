import getpass

from app import config
from app.database import SessionLocal
from app.models import User, create_tables
from app.security import hash_password
from app.validation import check_new_password, check_username


def main():
    create_tables()
    db = SessionLocal()
    try:
        admin_count = db.query(User).filter(User.role == "admin").count()
        if admin_count > 0:
            print("An admin account already exists. Log in to the website to manage users.")
            return

        username = input("Admin username: ").strip().lower()
        error = check_username(username)
        if error is not None:
            print(error)
            return

        password = getpass.getpass("Admin password: ")
        confirm = getpass.getpass("Type the password again: ")
        error = check_new_password(password, confirm, username, config.PASSWORD_MIN_LENGTH, config.PASSWORD_MAX_LENGTH)
        if error is not None:
            print(error)
            return

        admin = User(username=username, password_hash=hash_password(password), role="admin", is_enabled=True)
        db.add(admin)
        db.commit()
        print("Admin account created. You can now log in.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
