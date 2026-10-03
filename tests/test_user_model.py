import uuid
from app.models.user import User


def test_user_model_attributes():
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="test@example.com",
        username="testuser",
        hashed_password="argon2_hashed_secret",
    )

    assert user.__tablename__ == "users"
    assert user.id == user_id
    assert user.email == "test@example.com"
    assert user.username == "testuser"
    assert user.hashed_password == "argon2_hashed_secret"
    assert user.is_active is True
    assert repr(user) == "<User username='testuser' email='test@example.com'>"


def test_user_password_property():
    user = User(
        email="test@example.com",
        username="testuser",
        password="my_hashed_password",
    )
    assert user.hashed_password == "my_hashed_password"
    assert user.password == "my_hashed_password"

    user.password = "new_hash"
    assert user.hashed_password == "new_hash"
