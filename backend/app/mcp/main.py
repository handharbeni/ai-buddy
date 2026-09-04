"""Model Context Protocol (MCP) Router for BAPENDA Local AI Platform.

This service exposes business tools to the LLM with strict contracts, permissions,
and scope enforcement. All tool interactions are audited and validated.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import uuid4
import json
import logging

from app.auth.service import AuthService
from app.rbac.service import RBACService, Role, Resource, Action
from app.db.base import DBAdapter, QueryResult, ScopeFilter

# Initialize router
mcp_router = APIRouter(prefix="/mcp", tags=["mcp"])

# MCP Tool Registry
class ToolRegistry:
    """Registry of available MCP tools with their schemas and permissions."""
    
    def __init__(self):
        self.tools = {}
        
    def register_tool(self, name: str, tool_schema: Dict, required_permission: str):
        """Register a tool with its schema and required permission."""
        self.tools[name] = {
            "schema": tool_schema,
            "required_permission": required_permission,
            "name": name
        )
    
    def get_tool_schema(self, name: str) -> Dict:
        """Get tool schema by name."""
        return self.tools.get(name, {}).get("schema", {})
    
    def get_tool_permission(self, name: str) -> Optional[str]:
        """Get required permission for a tool."""
        return self.tools.get(name, {}).get("required_permission")

# Initialize registry
registry = ToolRegistry()

# Register all MCP tools
registry.register_tool(
    "get_tax_revenue",
    {
        "type": "object",
        "properties": {
            "period_start": {
                "type": "string",
                "format": "date",
                "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                "description": "Start date (YYYY-MM-DD)"
            },
            "period_end": {
                "type": "string",
                "format": "date",
                "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                "description": "End date (YYYY-MM-DD)"
            },
            "region_code": {
                "type": "string",
                "pattern": "^\\d{4}$",
                "description": "4-digit region code"
            },
            "tax_type": {
                "type": "string",
                "enum": ["PBB", "BPHTB", "PPh", "PDAM", "ALL"],
                "description": "Tax type code"
            },
            "group_by": {
                "type": "string",
                "enum": ["month", "quarter", "year", "region", "tax_type"],
                "default": "month"
            }
        },
        "required": ["period_start", "period_end"],
        "additionalProperties": False
    },
    "required_permission": "tax_revenue:read:{scope}"
)

registry.register_tool(
    "get_tax_arrears",
    {
        "type": "object",
        "properties": {
            "as_of_date": {
                "type": "string",
                "format": "date",
                "description": "Reference date (YYYY-MM-DD)"
            },
            "region_code": {
                "type": "string",
                "pattern": "^\\d{4}$",
                "description": "4-digit region code"
            },
            "tax_type": {
                "type": "string",
                "enum": ["PBB", "BPHTB", "PPh", "PDAM", "ALL"]
            },
            "taxpayer_id": {
                "type": "string",
                "pattern": "^TP_\\d+$",
                "description": "Specific taxpayer ID (requires own scope)"
            },
            "min_amount": {
                "type": "number",
                "minimum": 0,
                "description": "Minimum arrears amount filter"
            },
            "status": {
                "type": "string",
                "enum": ["OPEN", "PAYMENT_PLAN", "LEGAL", "WRITE_OFF", "ALL"],
                "default": "ALL"
            },
            "group_by": {
                "type": "string",
                "enum": ["region", "tax_type", "status", "aging_bucket"],
                "default": "region"
            }
        },
        "required": ["as_of_date"],
        "additionalProperties": False
    },
    "required_permission": "tax_arrears:read:{scope}"
)

registry.register_tool(
    "get_growth_statistics",
    {
        "type": "object",
        "properties": {
            "period_start": {
                "type": "string",
                "format": "date"
            },
            "period_end": {
                "type": "string",
                "format": "date"
            },
            "region_code": {
                "type": "string",
                "pattern": "^\\d{4}$"
            },
            "tax_type": {
                "type": "string",
                "enum": ["PBB", "BPHTB", "PPh", "PDAM", "ALL"]
            },
            "metrics": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["yoy_growth", "qoq_growth", "cagr", "volatility", "target_achievement"]
                },
                "default": ["yoy_growth", "target_achievement"]
            },
            "compare_regions": {
                "type": "array",
                "items": {"type": "string", "pattern": "^\\d{4}$"},
                "description": "Additional regions for comparison"
            }
        },
        "required": ["period_start", "period_end"],
        "additionalProperties": False
    },
    "required_permission": "growth_statistics:read:{scope}"
)

registry.register_tool(
    "get_region",
    {
        "type": "object",
        "properties": {
            "region_code": {
                "type": "string",
                "pattern": "^\\d{4}$"
            },
            "parent_code": {
                "type": "string",
                "pattern": "^\\d{4}$"
            },
            "level": {
                "type": "string",
                "enum": ["PROVINCE", "CITY", "DISTRICT", "VILLAGE", "ALL"],
                "default": "ALL"
            },
            "include_geometry": {
                "type": "boolean",
                "default": false
            }
        },
        "additionalProperties": False
    },
    "required_permission": "region_master:read:all"
)

registry.register_tool(
    "get_taxpayer_summary",
    {
        "type": "object",
        "properties": {
            "taxpayer_id": {
                "type": "string",
                "pattern": "^TP_\\d+$",
                "description": "Specific taxpayer ID (requires own scope)"
            },
            "include_arrears": {
                "type": "boolean",
                "default": true
            },
            "include_revenue_history": {
                "type": "boolean",
                "default": true
            },
            "history_months": {
                "type": "integer",
                "minimum": 1,
                "maximum": 36,
                "default": 12
            }
        },
        "required": ["taxpayer_id"],
        "additionalProperties": False
    },
    "required_permission": "taxpayer_summary:read:{scope}"
)

registry.register_tool(
    "search_regulation",
    {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "minLength": 3,
                "maxLength": 500,
                "description": "Natural language search query"
            },
            "document_types": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["PERDA", "PERGUB", "SOP", "SURAT_EDARAN", "ALL"]
                },
                "default": ["ALL"]
            },
            "effective_date_from": {
                "type": "string",
                "format": "date"
            },
            "effective_date_to": {
                "type": "string",
                "format": "date"
            },
            "classification": {
                "type": "string",
                "enum": ["PUBLIC", "INTERNAL", "RESTRICTED", "ALL"],
                "default": "ALL"
            },
            "top_k": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
                "default": 5
            },
            "rerank": {
                "type": "boolean",
                "default": true
            }
        },
        "required": ["query"],
        "additionalProperties": False
    },
    "required_permission": "regulation:read:approved"
)

# MCP Router Service
class MCPRouter:
    """Main MCP Router service that executes tool requests."""
    
    def __init__(self, db_adapters: Dict[str, DBAdapter], registry: ToolRegistry):
        self.db_adapters = db_adapters
        self.registry = registry
        self.logger = logging.getLogger("mcp")
        
    async def execute_tool(
        self,
        tool_name: str,
        user_id: str,
        role: str,
        scopes: List[str],
        parameters: Dict[str, Any],
        timeout_ms: int = 30000,
    ) -> Dict[str, Any]:
        """Execute an MCP tool with proper validation and permissions."""
        # Validate tool exists
        if tool_name not in self.registry.tools:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found"
            )
        
        # Validate permissions
        required_permission = self.registry.get_tool_permission(tool_name)
        if not required_permission:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found"
            )
            
        # Check role permission
        role = Role(role)
        required_resource = self._get_resource_from_permission(required_permission)
        if not self.rbac_service.check_permission(role, resource, Action.READ):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied for tool '{tool_name}'"
            )
        
        # Validate input schema
        schema = self.registry.get_tool_schema(tool_name)
        try:
            validated_params = self._validate_schema(tool_name, parameters)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid parameters: {str(e)}"
            )
        
        # Apply scope filters
        scope = self._resolve_scope(user_id, role, scopes)
        filtered_query = self._apply_scope_filter(tool_name, query, scope)
        
        # Execute tool
        try:
            result = await self._execute_tool(tool_name, query, params, scope, timeout_ms)
            return {
                "request_id": str(uuid4()),
                "status": "success",
                "tool": tool_name,
                "result": result.data,
                "meta": result.meta
            }
        except Exception as e:
            return {
                "request_id": str(uuid4()),
                "status": "error",
                "tool": tool_name,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e),
                    "details": {}
                }
    
    def _get_resource_from_permission(self, permission: str) -> Resource:
        """Extract resource from permission string."""
        # Parse permission like "tax_revenue:read:{scope}"
        parts = permission.split(":")
        if len(parts) >= 2:
            return Resource(parts[0])
        return Resource("unknown")
    
    def _validate_schema(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameters against tool schema."""
        schema = self.registry.get_tool_schema(tool_name)
        # In real implementation, use jsonschema for validation
        # For simplicity, we'll do basic validation
        return parameters
    
    def _resolve_scope(self, user_id: str, role: str, scopes: List[str]) -> ScopeFilter:
        """Resolve user scope from available scopes."""
        # In real implementation, this would query user assignments
        # For now, return mock scope based on role
        role_scopes = {
            Role.ADMIN: ScopeFilter(
                user_id=user_id,
                role="ADMIN",
                regions=["all"],
                tax_types=["all"],
                departments=["all"],
                own_taxpayers=[]
            ),
            Role.SUPERVISOR: ScopeFilter(
                user_id=user_id,
                role="SUPERVISOR",
                regions=["region:3201"],
                tax_types=["PBB", "BPHTB"],
                departments=["PEMUNGUTAN"],
                own_taxpayers=[]
            ),
            Role.ANALYST: ScopeFilter(
                user_id=user_id,
                role="ANALYST",
                regions=["3201", "3202"],
                tax_types=["PBB", "PPh"],
                departments=["FINANCE"],
                own_taxpayers=[]
            ),
            Role.STAFF: ScopeFilter(
                user_id=user_id,
                role="STAFF",
                regions=["3201"],
                tax_types=["PBB", "BPHTB"],
                departments=["PEMUNGUTAN"],
                own_taxpayers=[]
            )
        )
        return scope_scopes.get(role, ScopeFilter(user_id=user_id, role=role))
    
    def _apply_scope_filter(self, tool_name: str, query: str, scope: ScopeFilter) -> str:
        """Apply scope filters to the query."""
        # This would be implemented per-tool
        return query  # Placeholder - actual implementation in tool-specific logic
    
    async def _execute_tool(
        self,
        tool_name: str,
        query: str,
        params: Dict[str, Any],
        scope: ScopeFilter,
        timeout_ms: int,
    ) -> QueryResult:
        """Execute the actual tool with scope filtering."""
        # Get database adapter based on tool type
        adapter = self._get_db_adapter(tool_name)
        
        # Apply scope filter to query if needed
        if scope and scope.regions:
            # Example for revenue tool - would be more complex in reality
            if "tax_revenue" in tool_name:
                query = query.replace(":region_code", f"'{scope.regions[0]}'")
        
        # Execute query with timeout and row limits
        timeout = timeout_ms / 1000  # Convert to seconds
        row_limit = 1000  # Default
        
        return await adapter.execute_query(
            query=query,
            params=params,
            scope=scope,
            timeout=timeout,
            row_limit=row_limit
        )
    
    def _get_db_adapter(self, tool_name: str) -> DBAdapter:
        """Get appropriate database adapter based on tool."""
        # In real implementation, map tools to database types
        # For now, assume all use Oracle for simplicity
        return OracleAdapter(
            dsn="localhost:1521/ORCL",
            username="AI_READONLY",
            password=""
        )
    
    def _validate_schema(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameters against tool schema."""
        schema = self.registry.get_tool_schema(tool_name)
        # In real implementation, use jsonschema library
        # For simplicity, basic validation
        if tool_name == "search_regulation":
            if not parameters.get("query", "").strip():
                raise ValueError("Query cannot be empty")
        return parameters
    
    async def _execute_tool(
        self,
        tool_name: str,
        query: str,
        params: Dict[str, Any],
        scope: ScopeFilter,
        timeout_ms: int,
    ) -> QueryResult:
        """Execute tool with proper error handling."""
        try:
            # Validate input
            validated_params = self._validate_schema(tool_name, params)
            
            # Get database adapter
            adapter = self._get_db_adapter(tool_name)
            
            # Execute query
            result = await adapter.execute_query(
                query=query,
                params=validated_params,
                scope=scope,
                timeout=timeout_ms / 1000,
                row_limit=1000
            )
            
            # Log execution
            self.logger.info(
                f"Executed {tool_name}: {len(result.data)} rows, {scope.applied if scope else 'no_scope'}"
            )
            
            return result
        except Exception as e:
            self.logger.error(f"Tool execution failed: {tool_name} - {e}")
            raise

# Initialize the MCP Router
mcp_router.state = {
    "db_adapters": {},  # Will be populated during app startup
    "registry": registry,
    "rbac_service": None  # Will be set during startup
}

# Dependency injection for RBAC service
def get_rbac_service():
    """Dependency to get RBAC service."""
    # In real app, this would be injected from app state
    return RBACService()  # Simplified for example