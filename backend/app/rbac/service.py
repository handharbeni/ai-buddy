"""RBAC service for role-based access control."""

from typing import Dict, List, Optional, Set
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """User roles."""
    ADMIN = "ADMIN"
    SUPERVISOR = "SUPERVISOR"
    ANALYST = "ANALYST"
    STAFF = "STAFF"


class Resource(str, Enum):
    """Available resources."""
    TAX_REVENUE = "tax_revenue"
    TAX_ARREARS = "tax_arrears"
    GROWTH_STATISTICS = "growth_statistics"
    REGION_MASTER = "region_master"
    TAXPAYER_SUMMARY = "taxpayer_summary"
    REGULATION = "regulation"
    AUDIT_LOG = "audit_log"
    USER_MANAGEMENT = "user_management"
    SYSTEM_CONFIG = "system_config"


class Action(str, Enum):
    """Available actions."""
    READ = "read"
    EXPORT = "export"
    ANALYZE = "analyze"
    MANAGE = "manage"


# Permission matrix mapping (role, resource) -> allowed actions
PERMISSION_MATRIX = {
    (Role.ADMIN, Resource.TAX_REVENUE): {Action.READ, Action.EXPORT, Action.ANALYZE, Action.MANAGE},
    (Role.ADMIN, Resource.TAX_ARREARS): {Action.READ, Action.EXPORT, Action.ANALYZE, Action.MANAGE},
    (Role.ADMIN, Resource.GROWTH_STATISTICS): {Action.READ, Action.EXPORT, Action.ANALYZE, Action.MANAGE},
    (Role.ADMIN, Resource.REGION_MASTER): {Action.READ, Action.MANAGE},
    (Role.ADMIN, Resource.TAXPAYER_SUMMARY): {Action.READ, Action.EXPORT, Action.ANALYZE},
    (Role.ADMIN, Resource.REGULATION): {Action.READ, Action.MANAGE},
    (Role.ADMIN, Resource.AUDIT_LOG): {Action.READ, Action.EXPORT},
    (Role.ADMIN, Resource.USER_MANAGEMENT): {Action.READ, Action.MANAGE},
    (Role.ADMIN, Resource.SYSTEM_CONFIG): {Action.READ, Action.MANAGE},
    
    (Role.SUPERVISOR, Resource.TAX_REVENUE): {Action.READ, Action.EXPORT, Action.ANALYZE},
    (Role.SUPERVISOR, Resource.TAX_ARREARS): {Action.READ, Action.EXPORT, Action.ANALYZE},
    (Role.SUPERVISOR, Resource.GROWTH_STATISTICS): {Action.READ, Action.EXPORT, Action.ANALYZE},
    (Role.SUPERVISOR, Resource.REGION_MASTER): {Action.READ},
    (Role.SUPERVISOR, Resource.TAXPAYER_SUMMARY): {Action.READ, Action.EXPORT},
    (Role.SUPERVISOR, Resource.REGULATION): {Action.READ},
    (Role.SUPERVISOR, Resource.AUDIT_LOG): {Action.READ},
    (Role.SUPERVISOR, Resource.USER_MANAGEMENT): set(),
    (Role.SUPERVISOR, Resource.SYSTEM_CONFIG): set(),
    
    (Role.ANALYST, Resource.TAX_REVENUE): {Action.READ, Action.ANALYZE},
    (Role.ANALYST, Resource.TAX_ARREARS): {Action.READ, Action.ANALYZE},
    (Role.ANALYST, Resource.GROWTH_STATISTICS): {Action.READ, Action.ANALYZE},
    (Role.ANALYST, Resource.REGION_MASTER): {Action.READ},
    (Role.ANALYST, Resource.TAXPAYER_SUMMARY): {Action.READ},
    (Role.ANALYST, Resource.REGULATION): {Action.READ},
    (Role.ANALYST, Resource.AUDIT_LOG): set(),
    (Role.ANALYST, Resource.USER_MANAGEMENT): set(),
    (Role.ANALYST, Resource.SYSTEM_CONFIG): set(),
    
    (Role.STAFF, Resource.TAX_REVENUE): {Action.READ},
    (Role.STAFF, Resource.TAX_ARREARS): {Action.READ},
    (Role.STAFF, Resource.GROWTH_STATISTICS): {Action.READ},
    (Role.STAFF, Resource.REGION_MASTER): {Action.READ},
    (Role.STAFF, Resource.TAXPAYER_SUMMARY): {Action.READ},
    (Role.STAFF, Resource.REGULATION): {Action.READ},
    (Role.STAFF, Resource.AUDIT_LOG): {Action.READ},
    (Role.STAFF, Resource.USER_MANAGEMENT): set(),
    (Role.STAFF, Resource.SYSTEM_CONFIG): set(),
}


class RBACService:
    """Role-Based Access Control service."""

    def __init__(self, db_connections=None):
        self.db = db_connections

    def check_permission(
        self,
        role: Role,
        resource: Resource,
        action: Action,
    ) -> bool:
        """Check if a role has permission for a resource and action."""
        allowed_actions = PERMISSION_MATRIX.get((role, resource), set())
        return action in allowed_actions

    def get_allowed_resources(
        self,
        role: Role,
    ) -> Dict[Resource, Set[Action]]:
        """Get all resources and actions allowed for a role."""
        return {
            (resource, action)
            for (r, resource), action in PERMISSION_MATRIX.items()
            if r == role
        }

    def enforce(
        self,
        role: Role,
        resource: Resource,
        action: Action,
    ) -> None:
        """Enforce permission check. Raises if unauthorized."""
        if not self.check_permission(role, resource, action):
            raise PermissionError(
                f"Role {role.value} does not have {action.value} permission on {resource.value}"
            )

    def is_admin(self, role: Role) -> bool:
        """Check if role is admin."""
        return role == Role.ADMIN

    def is_supervisor(self, role: Role) -> bool:
        """Check if role is supervisor."""
        return role == Role.SUPERVISOR

    def is_analyst(self, role: Role) -> bool:
        """Check if role is analyst."""
        return role == Role.ANALYST

    def is_staff(self, role: Role) -> bool:
        """Check if role is staff."""
        return role == Role.STAFF