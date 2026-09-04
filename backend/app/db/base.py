"""Database adapter base interface for BAPENDA Local AI Platform."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class QueryResult(BaseModel):
    """Result from a database query."""
    data: List[Dict[str, Any]]
    meta: Dict[str, Any] = {}
    row_count: int = 0
    latency_ms: float = 0.0


class ScopeFilter(BaseModel):
    """Scope information for access control."""
    user_id: str
    role: str
    regions: Optional[List[str]] = None
    tax_types: Optional[List[str]] = None
    departments: Optional[List[str]] = None
    own_taxpayers: Optional[List[str]] = None


class DBAdapter(ABC):
    """Base database adapter interface.
    
    All adapters must:
    - Use read-only connections (AI_READONLY user)
    - Enforce scope filters at query time
    - Apply timeout limits (default 30 seconds)
    - Apply row limits (default 1000 rows)
    - Use parameterized queries
    - Log all queries (no parameters in logs)
    """

    DEFAULT_TIMEOUT = 30  # seconds
    DEFAULT_ROW_LIMIT = 1000

    @abstractmethod
    async def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        scope: Optional[ScopeFilter] = None,
        timeout: Optional[int] = None,
        row_limit: Optional[int] = None,
    ) -> QueryResult:
        """Execute a query against the database."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check database connectivity and health."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close all connections gracefully."""
        pass

    def _build_scope_filter(self, scope: Optional[ScopeFilter]) -> str:
        """Build WHERE clause from scope filters."""
        if not scope:
            return ""
        
        conditions = []
        
        if scope.regions:
            regions = ", ".join(f"'{r}'" for r in scope.regions)
            conditions.append(f"region_code IN ({regions})")
        
        if scope.tax_types:
            types = ", ".join(f"'{t}'" for t in scope.tax_types)
            conditions.append(f"tax_type IN ({types})")
        
        if conditions:
            return " AND " + " AND ".join(conditions)
        return ""
