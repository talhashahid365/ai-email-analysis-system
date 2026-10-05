import json
import os
import sys
from datetime import datetime, timezone

# Add parent directory to path so imports work cleanly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import models, security
from app.database import Base, SessionLocal, engine
from app.services import bootstrap, pipeline


def seed_database():
    print("Initializing Database tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Seed default categories
        bootstrap.seed_defaults(db)

        # Create Default Test Users if not exist
        admin_user = db.query(models.User).filter(models.User.email == "talha@example.com").first()
        if not admin_user:
            print("Creating test admin user: talha@example.com / password123")
            admin_user = models.User(
                email="talha@example.com",
                hashed_password=security.hash_password("password123"),
                full_name="Talha Ahmed (Admin)",
                role="admin",
                is_active=True,
                is_verified=True,
            )
            db.add(admin_user)

        manager_user = db.query(models.User).filter(models.User.email == "manager@example.com").first()
        if not manager_user:
            print("Creating test manager user: manager@example.com / password123")
            manager_user = models.User(
                email="manager@example.com",
                hashed_password=security.hash_password("password123"),
                full_name="Manager User",
                role="manager",
                is_active=True,
                is_verified=True,
            )
            db.add(manager_user)

        reg_user = db.query(models.User).filter(models.User.email == "user@example.com").first()
        if not reg_user:
            print("Creating test regular user: user@example.com / password123")
            reg_user = models.User(
                email="user@example.com",
                hashed_password=security.hash_password("password123"),
                full_name="Regular User",
                role="user",
                is_active=True,
                is_verified=True,
            )
            db.add(reg_user)

        db.commit()
        db.refresh(admin_user)

        # Check existing emails
        existing_count = db.query(models.Email).filter(models.Email.user_id == admin_user.id).count()
        if existing_count > 0:
            print(f"User talha@example.com already has {existing_count} emails. Skipping seed.")
            return

        json_path = os.path.join(os.path.dirname(__file__), "sample_100_emails.json")
        with open(json_path, "r", encoding="utf-8") as f:
            emails_data = json.load(f)

        print(f"Ingesting and analyzing {len(emails_data)} benchmark emails via pipeline...")
        success_count = 0
        for idx, item in enumerate(emails_data, 1):
            try:
                res = pipeline.ingest_email(
                    db,
                    admin_user,
                    {
                        "sender_name": item["sender_name"],
                        "sender_email": item["sender_email"],
                        "recipient_email": "talha@example.com",
                        "subject": item["subject"],
                        "body_plain": item["body_plain"],
                    },
                )
                if not res.duplicate:
                    pipeline.process_email(res.email.id, db=db, notify=True)
                    success_count += 1
            except Exception as exc:
                print(f"Error processing email #{idx}: {exc}")

        print(f"Successfully seeded and processed {success_count} benchmark emails!")
    finally:
        db.close()


if __name__ == "__main__":
    if "--demo" not in sys.argv:
        print("This script creates DEMO users (password123) and sample emails.\n"
              "Do not run it on a real deployment. To load the demo data deliberately run:\n"
              "    python datasets/seed_data.py --demo")
        sys.exit(0)
    seed_database()
