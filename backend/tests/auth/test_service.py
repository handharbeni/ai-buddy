"""Tests for AuthService."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import jwt

from app.auth.service import AuthService, UserSession


@pytest.fixture
def auth_service():
    """Create an AuthService instance."""
    return AuthService()


class TestAuthService:
    """Tests for AuthService."""

    def test_create_access_token(self, auth_service):
        """Test creating an access token."""
        token = auth_service.create_access_token(
            user_id="STAFF_001",
            role="STAFF",
            scope={"regions": ["3201"], "tax_types": ["PBB"]},
        )
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token structure
        decoded = jwt.decode(
            token,
            auth_service._public_key,
            algorithms=["RS256"],
            options={"verify_exp": False},
        )
        assert decoded["sub"] == "STAFF_001"
        assert decoded["role"] == "STAFF"
        assert "scope" in decoded
        assert "jti" in decoded

    def test_create_refresh_token(self, auth_service):
        """Test creating a refresh token."""
        token = auth_service.create_refresh_token("STAFF_001")
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        decoded = jwt.decode(
            token,
            auth_service._public_key,
            algorithms=["RS256"],
            options={"verify_exp": False},
        )
        assert decoded["sub"] == "STAFF_001"
        assert decoded["type"] == "refresh"

    def test_verify_access_token_valid(self, auth_service):
        """Test verifying a valid access token."""
        token = auth_service.create_access_token(
            user_id="STAFF_001",
            role="STAFF",
            scope={"regions": ["3201"]},
        )
        
        payload = auth_service.verify_access_token(token)
        
        assert payload is not None
        assert payload["sub"] == "STAFF_001"
        assert payload["role"] == "STAFF"

    def test_verify_access_token_expired(self, auth_service):
        """Test verifying an expired token."""
        # Create token with very short expiry
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "STAFF_001",
            "role": "STAFF",
            "scope": {},
            "iat": now - timedelta(minutes=20),
            "exp": now - timedelta(minutes=10),
            "jti": "test",
        }
        expired_token = jwt.encode(payload, auth_service._private_key, algorithm="RS256")
        
        result = auth_service.verify_access_token(expired_token)
        
        assert result is None

    def test_verify_refresh_token_valid(self, auth_service):
        """Test verifying a valid refresh token."""
        token = auth_service.create_refresh_token("STAFF_001")
        
        payload = auth_service.verify_refresh_token(token)
        
        assert payload is not None
        assert payload["sub"] == "STAFF_001"
        assert payload["type"] == "refresh"

    def test_verify_refresh_token_wrong_type(self, auth_service):
        """Test verifying access token as refresh token fails."""
        access_token = auth_service.create_access_token(
            user_id="STAFF_001",
            role="STAFF",
            scope={},
        )
        
        result = auth_service.verify_refresh_token(access_token)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_success(self, auth_service):
        """Test successful authentication."""
        session = await auth_service.authenticate("test", "test")
        
        assert session is not None
        assert isinstance(session, UserSession)
        assert session.user_id == "STAFF_001"
        assert session.role == "STAFF"

    @pytest.mark.asyncio
    async def test_authenticate_failure(self, auth_service):
        """Test failed authentication."""
        session = await auth_service.authenticate("wrong", "wrong")
        
        assert session is None

    @pytest.mark.asyncio
    async def test_refresh_session(self, auth_service):
        """Test refreshing a session."""
        refresh_token = auth_service.create_refresh_token("STAFF_001")
        
        session = await auth_service.refresh_session(refresh_token)
        
        assert session is not None
        assert session.user_id == "STAFF_001"

    @pytest.mark.asyncio
    async def test_get_user_scope(self, auth_service):
        """Test getting user scope."""
        scope = await auth_service.get_user_scope("STAFF_001")
        
        assert scope is not None
        assert scope["user_id"] == "STAFF_001"
        assert "regions" in scope
        assert "tax_types" in scope