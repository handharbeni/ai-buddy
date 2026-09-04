"""MCP API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from uuid import uuid4

from app.mcp import MCPRouter, ToolResponse, ToolResult
from app.auth.service import AuthService
from app.rbac import RBACService
from app.auth import get_current_user

mcp_api = APIRouter(prefix="/mcp", tags=["mcp"])


class ToolExecuteRequest(BaseModel):
    """Request to execute an MCP tool."""
    tool: str = Field(..., description="Tool name")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    timeout_ms: Optional[int] = Field(None, description="Optional timeout override")


class ToolExecuteResponse(BaseModel):
    """Response from tool execution."""
    request_id: str
    status: str
    tool: str
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


async def get_mcp_router(request: Request) -> MCPRouter:
    """Dependency to get MCP router from app state."""
    return request.app.state.mcp_router


async def get_current_user_dependency(request: Request) -> Dict[str, Any]:
    """Get current authenticated user from request state."""
    user = await get_current_user(request)
    return user


@mcp_api.get("/tools")
async def list_tools(
    mcp: MCPRouter = Depends(get_mcp_router),
    user: Dict = Depends(get_current_user_dependency),
):
    """List all available MCP tools."""
    return {"tools": mcp.list_tools()}


@mcp_api.get("/tools/{tool_name}")
async def get_tool_info(
    tool_name: str,
    mcp: MCPRouter = Depends(get_mcp_router),
    user: Dict = Depends(get_current_user_dependency),
):
    """Get schema and metadata for a specific tool."""
    info = mcp.get_tool_info(tool_name)
    if not info:
        raise HTTPException(status_code=404, detail="Tool not found")
    return info


@mcp_api.post("/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    req: ToolExecuteRequest,
    request: Request,
    mcp: MCPRouter = Depends(get_mcp_router),
    user: Dict = Depends(get_current_user_dependency),
):
    """Execute an MCP tool with the provided parameters."""
    # Get user info - decode the actual token payload for accurate role/scope
    import jwt as _jwt
    auth = request.app.state.auth
    decoded = auth.verify_access_token(user.get("token", ""))
    payload = decoded or {}
    user_id = user.get("user_id") or payload.get("sub")
    role = payload.get("role", "STAFF")

    # Convert role string to Role enum
    from app.rbac import Role
    from app.db.base import ScopeFilter
    try:
        role_enum = Role(role) if isinstance(role, str) else role
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")

    # Build scope from token payload
    user_scope = payload.get("scope", {})
    scope_filter = ScopeFilter(
        user_id=user_id,
        role=role,
        regions=user_scope.get("regions"),
        tax_types=user_scope.get("tax_types"),
        departments=user_scope.get("departments"),
        own_taxpayers=user_scope.get("own_taxpayers"),
    )

    # Execute tool
    response = await mcp.execute(
        tool_name=req.tool,
        parameters=req.parameters,
        role=role_enum,
        scope=scope_filter,
    )

    return ToolExecuteResponse(
        request_id=response.request_id,
        status=response.status,
        tool=response.tool,
        result=response.result.data if response.result else None,
        error=response.error.model_dump() if response.error else None,
    )