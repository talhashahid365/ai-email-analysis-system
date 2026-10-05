"""Promote or list accounts using the app's own database settings.

Run from the backend folder:
    python make_admin.py                    # show database + all users
    python make_admin.py you@example.com    # make that user an admin
"""
import sys

from app.database import SessionLocal, engine
from app import models

db = SessionLocal()
print("Database:", engine.url)
if len(sys.argv) > 1:
    email = sys.argv[1].strip().lower()
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        print(f"No user with email {email!r}. Sign up first, then run this again.")
    else:
        user.role = "admin"
        db.commit()
        print(f"{user.email} is now admin. Log out and log in again.")
print("Users:", [(u.email, u.role) for u in db.query(models.User).all()])
