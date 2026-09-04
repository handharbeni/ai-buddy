"""MCP Router service for BAPENDA Local AI Platform.

Exposes business tools to the LLM with strict contracts, permissions,
and scope enforcement. All tool interactions are audited and validated.
"""

import logging
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field

from app.rbac.service import RBACService, Role, Resource, Action
from app.db.base import ScopeFilter

logger = logging.getLogger(__name__)


# ─── Tool Input Schemas ───────────────────────────────────────────────────────

class GetTaxRevenueInput(BaseModel):
    period_start: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Start date YYYY-MM-DD")
    period_end: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="End date YYYY-MM-DD")
    region_code: Optional[str] = Field(None, pattern=r"^\d{4}$", description="4-digit region code")
    tax_type: Optional[str] = Field("ALL", description="Tax type")
    group_by: Optional[str] = Field("month", description="Grouping")

    class Config:
        use_enum_values = True


class GetTaxArrearsInput(BaseModel):
    as_of_date: str = Field(..., description="Reference date YYYY-MM-DD")
    region_code: Optional[str] = Field(None, pattern=r"^\d{4}$")
    tax_type: Optional[str] = Field(None)
    taxpayer_id: Optional[str] = Field(None, pattern=r"^TP_\d+$")
    min_amount: Optional[float] = Field(None, ge=0)
    status: Optional[str] = Field("ALL")
    group_by: Optional[str] = Field("region")


class GetGrowthStatisticsInput(BaseModel):
    period_start: str = Field(..., description="Start date YYYY-MM-DD")
    period_end: str = Field(..., description="End date YYYY-MM-DD")
    region_code: Optional[str] = Field(None, pattern=r"^\d{4}$")
    tax_type: Optional[str] = Field("ALL")
    metrics: Optional[List[str]] = Field(default_factory=lambda: ["yoy_growth", "target_achievement"])
    compare_regions: Optional[List[str]] = Field(None)


class GetRegionInput(BaseModel):
    region_code: Optional[str] = Field(None, pattern=r"^\d{4}$")
    parent_code: Optional[str] = Field(None, pattern=r"^\d{4}$")
    level: Optional[str] = Field("ALL")
    include_geometry: Optional[bool] = Field(False)


class GetTaxpayerSummaryInput(BaseModel):
    taxpayer_id: str = Field(..., pattern=r"^TP_\d+$", description="Taxpayer ID")
    include_arrears: Optional[bool] = Field(True)
    include_revenue_history: Optional[bool] = Field(True)
    history_months: Optional[int] = Field(12, ge=1, le=36)


class SearchRegulationInput(BaseModel):
    query: str = Field(..., min_length=3, max_length=500, description="Search query")
    document_types: Optional[List[str]] = Field(default_factory=lambda: ["ALL"])
    effective_date_from: Optional[str] = Field(None)
    effective_date_to: Optional[str] = Field(None)
    classification: Optional[str] = Field("ALL")
    top_k: Optional[int] = Field(5, ge=1, le=20)
    rerank: Optional[bool] = Field(True)


# ─── Tool Output Schemas ──────────────────────────────────────────────────────

class ToolMeta(BaseModel):
    query_id: str
    executed_at: str
    row_count: int
    latency_ms: float
    scope_applied: Dict[str, Any] = {}


class ToolResult(BaseModel):
    data: List[Dict[str, Any]]
    meta: ToolMeta


class ToolError(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = {}


class ToolResponse(BaseModel):
    request_id: str
    status: str  # "success" or "error"
    tool: str
    result: Optional[ToolResult] = None
    error: Optional[ToolError] = None


# ─── Tool Registry ─────────────────────────────────────────────────────────────

# Tool metadata: permission, db_target, max_rows, timeout_s
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "get_tax_revenue": {
        "permission": (Resource.TAX_REVENUE, Action.READ),
        "db": "oracle",
        "max_rows": 1000,
        "timeout_s": 30,
        "input_model": GetTaxRevenueInput,
    },
    "get_tax_arrears": {
        "permission": (Resource.TAX_ARREARS, Action.READ),
        "db": "oracle",
        "max_rows": 1000,
        "timeout_s": 30,
        "input_model": GetTaxArrearsInput,
    },
    "get_growth_statistics": {
        "permission": (Resource.GROWTH_STATISTICS, Action.READ),
        "db": "postgresql",
        "max_rows": 500,
        "timeout_s": 30,
        "input_model": GetGrowthStatisticsInput,
    },
    "get_region": {
        "permission": (Resource.REGION_MASTER, Action.READ),
        "db": "mysql",
        "max_rows": 5000,
        "timeout_s": 10,
        "input_model": GetRegionInput,
    },
    "get_taxpayer_summary": {
        "permission": (Resource.TAXPAYER_SUMMARY, Action.READ),
        "db": "oracle",
        "max_rows": 1,
        "timeout_s": 15,
        "input_model": GetTaxpayerSummaryInput,
    },
    "search_regulation": {
        "permission": (Resource.REGULATION, Action.READ),
        "db": "qdrant",
        "max_rows": 20,
        "timeout_s": 10,
        "input_model": SearchRegulationInput,
    },
}


class MCPRouter:
    """Routes tool requests to the correct adapter with permission and scope checks."""

    def __init__(
        self,
        db_adapters: Dict[str, Any],
        rbac_service: RBACService,
    ):
        self.adapters = db_adapters
        self.rbac = rbac_service

    def list_tools(self) -> List[str]:
        """Return available tool names."""
        return list(TOOL_REGISTRY.keys())

    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Return metadata for a tool."""
        return TOOL_REGISTRY.get(tool_name)

    async def execute(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        role: Role,
        scope: ScopeFilter,
    ) -> ToolResponse:
        """Execute a tool with full validation, permission check, and scope enforcement."""
        request_id = str(uuid4())

        # 1. Validate tool exists
        tool_info = TOOL_REGISTRY.get(tool_name)
        if not tool_info:
            return ToolResponse(
                request_id=request_id,
                status="error",
                tool=tool_name,
                error=ToolError(
                    code="TOOL_NOT_FOUND",
                    message=f"Tool '{tool_name}' is not registered.",
                ),
            )

        # 2. Check permission
        resource, action = tool_info["permission"]
        if not self.rbac.check_permission(role, resource, action):
            logger.warning(
                f"Permission denied: role={role.value} tool={tool_name} "
                f"resource={resource.value} action={action.value}"
            )
            return ToolResponse(
                request_id=request_id,
                status="error",
                tool=tool_name,
                error=ToolError(
                    code="PERMISSION_DENIED",
                    message=f"Role '{role.value}' cannot perform '{action.value}' on '{resource.value}'.",
                ),
            )

        # 3. Validate input schema
        input_model = tool_info["input_model"]
        try:
            validated = input_model(**parameters)
        except Exception as e:
            return ToolResponse(
                request_id=request_id,
                status="error",
                tool=tool_name,
                error=ToolError(
                    code="INVALID_PARAMETER",
                    message=f"Parameter validation failed: {e}",
                ),
            )

        # 4. Check scope
        if not self._check_scope(tool_name, scope):
            return ToolResponse(
                request_id=request_id,
                status="error",
                tool=tool_name,
                error=ToolError(
                    code="SCOPE_VIOLATION",
                    message="Requested scope exceeds user assignment.",
                ),
            )

        # 5. Execute
        start = time.time()
        try:
            db_key = tool_info["db"]
            adapter = self.adapters.get(db_key)
            if not adapter:
                raise RuntimeError(f"Database adapter '{db_key}' not available")

            query, params = self._build_query(tool_name, validated, scope)
            result = await adapter.execute_query(
                query=query,
                params=params,
                scope=scope,
                timeout=tool_info["timeout_s"],
                row_limit=tool_info["max_rows"],
            )
            latency_ms = (time.time() - start) * 1000

            meta = ToolMeta(
                query_id=request_id,
                executed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                row_count=result.row_count,
                latency_ms=latency_ms,
                scope_applied=scope.model_dump() if hasattr(scope, "model_dump") else {},
            )

            return ToolResponse(
                request_id=request_id,
                status="success",
                tool=tool_name,
                result=ToolResult(data=result.data, meta=meta),
            )

        except TimeoutError:
            return ToolResponse(
                request_id=request_id,
                status="error",
                tool=tool_name,
                error=ToolError(
                    code="TIMEOUT",
                    message=f"Tool exceeded {tool_info['timeout_s']}s timeout.",
                ),
            )
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name} - {e}")
            return ToolResponse(
                request_id=request_id,
                status="error",
                tool=tool_name,
                error=ToolError(
                    code="INTERNAL_ERROR",
                    message="An internal error occurred.",
                    details={"error": str(e)} if logger.isEnabledFor(logging.DEBUG) else {},
                ),
            )

    def _check_scope(self, tool_name: str, scope: ScopeFilter) -> bool:
        """Verify user scope permits this tool call."""
        # ADMIN has all scopes
        if scope.role == "ADMIN":
            return True

        # For tools with region_code param, scope.regions must cover it
        # (Detailed scope filtering is done at query-build time)
        # Basic: user must have at least one region
        if scope.role in ("SUPERVISOR", "ANALYST", "STAFF"):
            if not scope.regions:
                return False
        return True

    def _build_query(
        self,
        tool_name: str,
        validated: Any,
        scope: ScopeFilter,
    ) -> tuple[str, Dict[str, Any]]:
        """Build a parameterized SQL query and params dict from validated input."""
        if tool_name == "get_tax_revenue":
            return self._build_tax_revenue_query(validated, scope)
        elif tool_name == "get_tax_arrears":
            return self._build_tax_arrears_query(validated, scope)
        elif tool_name == "get_growth_statistics":
            return self._build_growth_statistics_query(validated, scope)
        elif tool_name == "get_region":
            return self._build_region_query(validated, scope)
        elif tool_name == "get_taxpayer_summary":
            return self._build_taxpayer_summary_query(validated, scope)
        elif tool_name == "search_regulation":
            return self._build_search_regulation_query(validated, scope)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def _build_tax_revenue_query(self, v: Any, scope: ScopeFilter) -> tuple[str, Dict]:
        query = (
            "SELECT period, region_code, region_name, tax_type, "
            "target_amount, realization_amount, percentage "
            "FROM V_TAX_REVENUE_SCOPE "
            "WHERE period_start >= :period_start AND period_end <= :period_end"
        )
        params: Dict[str, Any] = {"period_start": v.period_start, "period_end": v.period_end}

        if v.region_code:
            query += " AND region_code = :region_code"
            params["region_code"] = v.region_code
        if v.tax_type and v.tax_type != "ALL":
            query += " AND tax_type = :tax_type"
            params["tax_type"] = v.tax_type
        if v.group_by:
            query += f" GROUP BY period, region_code, region_name, tax_type"

        return query, params

    def _build_tax_arrears_query(self, v: Any, scope: ScopeFilter) -> tuple[str, Dict]:
        query = (
            "SELECT taxpayer_id, taxpayer_name, region_code, region_name, tax_type, "
            "arrears_amount, aging_days, status, last_payment_date "
            "FROM V_TAX_ARREARS_SCOPE WHERE as_of_date = :as_of_date"
        )
        params: Dict[str, Any] = {"as_of_date": v.as_of_date}

        if v.region_code:
            query += " AND region_code = :region_code"
            params["region_code"] = v.region_code
        if v.tax_type and v.tax_type != "ALL":
            query += " AND tax_type = :tax_type"
            params["tax_type"] = v.tax_type
        if v.taxpayer_id:
            query += " AND taxpayer_id = :taxpayer_id"
            params["taxpayer_id"] = v.taxpayer_id
        if v.min_amount is not None:
            query += " AND arrears_amount >= :min_amount"
            params["min_amount"] = v.min_amount
        if v.status and v.status != "ALL":
            query += " AND status = :status"
            params["status"] = v.status

        return query, params

    def _build_growth_statistics_query(self, v: Any, scope: ScopeFilter) -> tuple[str, Dict]:
        query = (
            "SELECT region_code, region_name, tax_type, period, "
            "yoy_growth, qoq_growth, cagr, volatility, target_achievement, "
            "revenue_current, revenue_prior "
            "FROM v_growth_statistics_scope "
            "WHERE period_start >= :period_start AND period_end <= :period_end"
        )
        params: Dict[str, Any] = {"period_start": v.period_start, "period_end": v.period_end}

        if v.region_code:
            query += " AND region_code = :region_code"
            params["region_code"] = v.region_code
        if v.tax_type and v.tax_type != "ALL":
            query += " AND tax_type = :tax_type"
            params["tax_type"] = v.tax_type
        if v.compare_regions:
            regions = ", ".join(f"'{r}'" for r in v.compare_regions)
            query += f" AND region_code IN ({regions})"

        return query, params

    def _build_region_query(self, v: Any, scope: ScopeFilter) -> tuple[str, Dict]:
        query = "SELECT region_code, region_name, parent_code, level FROM V_REGION_HIERARCHY WHERE 1=1"
        params: Dict[str, Any] = {}

        if v.region_code:
            query += " AND region_code = :region_code"
            params["region_code"] = v.region_code
        if v.parent_code:
            query += " AND parent_code = :parent_code"
            params["parent_code"] = v.parent_code
        if v.level and v.level != "ALL":
            query += " AND level = :level"
            params["level"] = v.level

        return query, params

    def _build_taxpayer_summary_query(self, v: Any, scope: ScopeFilter) -> tuple[str, Dict]:
        query = (
            "SELECT t.taxpayer_id, t.taxpayer_name, t.npwpd, t.region_code, t.region_name, "
            "t.tax_types, t.current_arrears "
            "FROM V_TAXPAYER_SCOPE t WHERE t.taxpayer_id = :taxpayer_id"
        )
        params: Dict[str, Any] = {"taxpayer_id": v.taxpayer_id}

        if v.include_arrears:
            query += " AND t.include_arrears_detail = 1"
        if v.include_revenue_history:
            query += f" AND t.history_months = {v.history_months}"

        return query, params

    def _build_search_regulation_query(self, v: Any, scope: ScopeFilter) -> tuple[str, Dict]:
        """Build Qdrant vector search query (pseudo-SQL, handled by Qdrant adapter)."""
        query = "SEARCH regulation_documents"
        params: Dict[str, Any] = {
            "query_text": v.query,
            "top_k": v.top_k,
            "rerank": v.rerank,
            "filters": {
                "approval_status": "APPROVED",
            },
        }

        if v.document_types and "ALL" not in v.document_types:
            params["filters"]["document_type"] = v.document_types
        if v.classification and v.classification != "ALL":
            params["filters"]["classification"] = v.classification
        if v.effective_date_from:
            params["filters"]["effective_date_from"] = v.effective_date_from
        if v.effective_date_to:
            params["filters"]["effective_date_to"] = v.effective_date_to

        return query, params
