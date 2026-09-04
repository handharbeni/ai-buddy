"""Tests for RBACService."""

import pytest
from app.rbac import RBACService, Role, Resource, Action


@pytest.fixture
def rbac_service():
    """Create an RBACService instance."""
    return RBACService()


class TestRBACService:
    """Tests for RBACService."""

    def test_admin_has_all_permissions(self, rbac_service):
        """Test that ADMIN has all permissions."""
        assert rbac_service.check_permission(Role.ADMIN, Resource.TAX_REVENUE, Action.READ)
        assert rbac_service.check_permission(Role.ADMIN, Resource.TAX_REVENUE, Action.EXPORT)
        assert rbac_service.check_permission(Role.ADMIN, Resource.TAX_REVENUE, Action.ANALYZE)
        assert rbac_service.check_permission(Role.ADMIN, Resource.TAX_REVENUE, Action.MANAGE)
        assert rbac_service.check_permission(Role.ADMIN, Resource.AUDIT_LOG, Action.READ)

    def test_supervisor_has_limited_permissions(self, rbac_service):
        """Test that SUPERVISOR has limited permissions."""
        assert rbac_service.check_permission(Role.SUPERVISOR, Resource.TAX_REVENUE, Action.READ)
        assert rbac_service.check_permission(Role.SUPERVISOR, Resource.TAX_REVENUE, Action.EXPORT)
        assert rbac_service.check_permission(Role.SUPERVISOR, Resource.TAX_REVENUE, Action.ANALYZE)
        # SUPERVISOR cannot MANAGE
        assert not rbac_service.check_permission(Role.SUPERVISOR, Resource.TAX_REVENUE, Action.MANAGE)
        # SUPERVISOR cannot access USER_MANAGEMENT
        assert not rbac_service.check_permission(Role.SUPERVISOR, Resource.USER_MANAGEMENT, Action.READ)

    def test_analyst_has_read_analyze(self, rbac_service):
        """Test that ANALYST has read and analyze permissions."""
        assert rbac_service.check_permission(Role.ANALYST, Resource.TAX_REVENUE, Action.READ)
        assert rbac_service.check_permission(Role.ANALYST, Resource.TAX_REVENUE, Action.ANALYZE)
        # ANALYST cannot EXPORT
        assert not rbac_service.check_permission(Role.ANALYST, Resource.TAX_REVENUE, Action.EXPORT)
        # ANALYST cannot MANAGE
        assert not rbac_service.check_permission(Role.ANALYST, Resource.TAX_REVENUE, Action.MANAGE)

    def test_staff_has_read_only(self, rbac_service):
        """Test that STAFF has only read permissions."""
        assert rbac_service.check_permission(Role.STAFF, Resource.TAX_REVENUE, Action.READ)
        assert rbac_service.check_permission(Role.STAFF, Resource.TAX_ARREARS, Action.READ)
        assert rbac_service.check_permission(Role.STAFF, Resource.GROWTH_STATISTICS, Action.READ)
        # STAFF cannot EXPORT
        assert not rbac_service.check_permission(Role.STAFF, Resource.TAX_REVENUE, Action.EXPORT)
        # STAFF cannot ANALYZE
        assert not rbac_service.check_permission(Role.STAFF, Resource.TAX_REVENUE, Action.ANALYZE)
        # STAFF cannot access AUDIT_LOG export
        assert not rbac_service.check_permission(Role.STAFF, Resource.AUDIT_LOG, Action.EXPORT)

    def test_all_roles_can_read_regulations(self, rbac_service):
        """Test that all roles can read regulations."""
        assert rbac_service.check_permission(Role.ADMIN, Resource.REGULATION, Action.READ)
        assert rbac_service.check_permission(Role.SUPERVISOR, Resource.REGULATION, Action.READ)
        assert rbac_service.check_permission(Role.ANALYST, Resource.REGULATION, Action.READ)
        assert rbac_service.check_permission(Role.STAFF, Resource.REGULATION, Action.READ)

    def test_enforce_raises_on_unauthorized(self, rbac_service):
        """Test that enforce raises PermissionError on unauthorized access."""
        with pytest.raises(PermissionError):
            rbac_service.enforce(Role.STAFF, Resource.USER_MANAGEMENT, Action.READ)

    def test_enforce_succeeds_on_authorized(self, rbac_service):
        """Test that enforce succeeds on authorized access."""
        # Should not raise
        rbac_service.enforce(Role.ADMIN, Resource.USER_MANAGEMENT, Action.READ)
        rbac_service.enforce(Role.STAFF, Resource.TAX_REVENUE, Action.READ)

    def test_get_allowed_resources(self, rbac_service):
        """Test getting allowed resources for a role."""
        staff_resources = rbac_service.get_allowed_resources(Role.STAFF)
        
        assert (Resource.TAX_REVENUE, Action.READ) in staff_resources
        assert (Resource.TAX_ARREARS, Action.READ) in staff_resources
        assert (Resource.USER_MANAGEMENT, Action.READ) not in staff_resources

    def test_role_check_methods(self, rbac_service):
        """Test role check helper methods."""
        assert rbac_service.is_admin(Role.ADMIN)
        assert not rbac_service.is_admin(Role.SUPERVISOR)
        assert rbac_service.is_supervisor(Role.SUPERVISOR)
        assert rbac_service.is_analyst(Role.ANALYST)
        assert rbac_service.is_staff(Role.STAFF)