"""Tests for AuthService - additional tests."""

import pytest
from app.auth.service import AuthService


@pytest.fixture
def auth_service():
    """Create an AuthService instance."""
    return AuthService()


class TestAuthServiceBasics:
    """Basic tests for AuthService."""

    def test_auth_service_initialization(self, auth_service):
        """Test that AuthService initializes correctly."""
        assert auth_service is not None
        assert auth_service._private_key is not None
        assert auth_service._public_key is not None

    def test_key_pair_generated(self, auth_service):
        """Test that key pair is generated for development."""
        # In dev mode, keys are generated
        assert auth_service._private_key is not None
        assert auth_service._public_key is not None

    def test_token_contains_jti(self, auth_service):
        """Test that tokens contain a unique JTI."""
        token1 = auth_service.create_access_token(
            user_id="STAFF_001",
            role="STAFF",
            scope={},
        )
        token2 = auth_service.create_access_token(
            user_id="STAFF_001",
            role="STAFF",
            scope={},
        )
        
        # Each token should have a different JTI
        assert token1 != token2

    def test_token_contains_role(self, auth_service):
        """Test that tokens contain role information."""
        token = auth_service.create_access_token(
            user_id="STAFF_001",
            role="STAFF",
            scope={"regions": ["3201"]},
        )
        
        import jwt
        decoded = jwt.decode(
            token,
            auth_service._public_key,
            algorithms=["RS256"],
            options={"verify_exp": False},
        )
        assert decoded["role"] == "STAFF"

    def test_token_contains_scope(self, auth_service):
        """Test that tokens contain scope information."""
        scope = {"regions": ["3201"], "tax_types": ["PBB"]}
        token = auth_service.create_access_token(
            user_id="STAFF_001",
            role="STAFF",
            scope=scope,
        )
        
        import jwt
        decoded = jwt.decode(
            token,
            auth_service._public_key,
            algorithms=["RS256"],
            options={"verify_exp": False},
        )
        assert decoded["scope"] == scope

    def test_invalid_token_returns_none(self, auth_service):
        """Test that invalid tokens return None."""
        result = auth_service.verify_access_token("invalid.token.here")
        assert result is None

    def test_token_with_wrong_algorithm(self, auth_service):
        """Test that tokens with wrong algorithm fail."""
        import jwt
        # Create token with HS256 instead of RS256
        token = jwt.encode(
            {"sub": "STAFF_001", "role": "STAFF"},
            "secret",
            algorithm="HS256",
        )
        
        result = auth_service.verify_access_token(token)
        assert result is None