import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base, get_db
from app.main import app as fastapi_app
from app import security, models
from app.services import bootstrap

TEST_DATABASE_URL = "sqlite:///:memory:"


from sqlalchemy.pool import StaticPool

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    bootstrap.seed_defaults(session)
    try:
        yield session
    finally:
        session.close()


import app.database
import app.main

app.database.engine = engine
app.database.SessionLocal = TestingSessionLocal
app.main.engine = engine
app.main.SessionLocal = TestingSessionLocal


@pytest.fixture(scope="module")
def client(db):
    def _get_test_db():
        try:
            yield db
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = _get_test_db
    with TestClient(fastapi_app) as c:
        yield c




@pytest.fixture(scope="module")
def admin_user(db):
    user = models.User(
        email="admin.test@example.com",
        hashed_password=security.hash_password("adminPassword123"),
        full_name="Admin Test User",
        role="admin",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = security.create_access_token(user.id)
    return {"user": user, "token": token}


@pytest.fixture(scope="module")
def manager_user(db):
    user = models.User(
        email="manager.test@example.com",
        hashed_password=security.hash_password("managerPassword123"),
        full_name="Manager Test User",
        role="manager",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = security.create_access_token(user.id)
    return {"user": user, "token": token}


@pytest.fixture(scope="module")
def user_a(db):
    user = models.User(
        email="usera.test@example.com",
        hashed_password=security.hash_password("passwordA123"),
        full_name="User A",
        role="user",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = security.create_access_token(user.id)
    return {"user": user, "token": token}


@pytest.fixture(scope="module")
def user_b(db):
    user = models.User(
        email="userb.test@example.com",
        hashed_password=security.hash_password("passwordB123"),
        full_name="User B",
        role="user",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = security.create_access_token(user.id)
    return {"user": user, "token": token}
