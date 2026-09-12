"""Tests for Authentication: registration, Argon2id hashing, and login."""
import pytest
from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import verify_password
from app.schemas.schemas import UserLogin, UserRegister
from app.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_user_registration_and_argon2_hashing(test_db_session):
    service = AuthService(test_db_session)
    reg_req = UserRegister(
        email="author1@example.com",
        password="SecurePassword2026!",
        full_name="Alice Author",
        organization_name="Alice Tech Blogs",
    )

    resp = await service.register(reg_req)
    assert resp.email == "author1@example.com"
    assert resp.full_name == "Alice Author"
    assert resp.role == "AUTHOR"
    assert resp.access_token is not None

    # Verify duplicate registration is rejected
    with pytest.raises(ConflictError):
        await service.register(reg_req)


@pytest.mark.asyncio
async def test_user_login_success_and_failure(test_db_session):
    service = AuthService(test_db_session)
    # Register user
    await service.register(
        UserRegister(
            email="author2@example.com",
            password="AuthorPassword123!",
            full_name="Bob Author",
        )
    )

    # Valid login
    login_resp = await service.login(
        UserLogin(email="author2@example.com", password="AuthorPassword123!")
    )
    assert login_resp.email == "author2@example.com"
    assert login_resp.access_token is not None

    # Invalid password
    with pytest.raises(UnauthorizedError):
        await service.login(
            UserLogin(email="author2@example.com", password="WrongPassword!")
        )

    # Non-existent email
    with pytest.raises(UnauthorizedError):
        await service.login(
            UserLogin(email="ghost@example.com", password="AnyPassword123!")
        )
