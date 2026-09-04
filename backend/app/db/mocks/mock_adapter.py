"""Mock database adapter for testing."""

from typing import Dict, List, Any
from app.db.base import DBAdapter, QueryResult, ScopeFilter


class MockAdapter(DBAdapter):
    """Mock database adapter for development and testing."""

    def __init__(self):
        self._sample_data = {
            "tax_revenue": [],
            "tax_arrears": [],
            "growth_statistics": [],
        }
        self._load_sample_data()

    def _load_sample_data(self) -> None:
        """Load sample data for testing."""
        # Sample revenue data
        self._sample_data["tax_revenue"] = [
            {
                "period": "2025-01-01",
                "region_code": "3201",
                "region_name": "Kabupaten Bandung",
                "tax_type": "PBB",
                "target": 100000000.00,
                "realization": 85000000.00,
                "percentage": 85.0,
            },
            {
                "period": "2025-01-01",
                "region_code": "3202",
                "region_name": "Kota Bandung",
                "tax_type": "PBB",
                "target": 150000000.00,
                "realization": 135000000.00,
                "percentage": 90.0,
            },
        ]

        # Sample arrears data
        self._sample_data["tax_arrears"] = [
            {
                "taxpayer_id": "TP_001",
                "taxpayer_name": "PT Sample Usaha",
                "region_code": "3201",
                "region_name": "Kabupaten Bandung",
                "tax_type": "PBB",
                "arrears_amount": 5000000.00,
                "aging_days": 45,
                "status": "OPEN",
            },
            {
                "taxpayer_id": "TP_002",
                "taxpayer_name": "UD Lestari",
                "region_code": "3201",
                "region_name": "Kabupaten Bandung",
                "tax_type": "BPHTB",
                "arrears_amount": 2500000.00,
                "aging_days": 120,
                "status": "OPEN",
            },
        ]

        # Sample growth statistics
        self._sample_data["growth_statistics"] = [
            {
                "region_code": "3201",
                "region_name": "Kabupaten Bandung",
                "tax_type": "PBB",
                "period": "2025",
                "yoy_growth": 5.2,
                "target_achievement": 85.0,
                "revenue_current": 85000000.00,
                "revenue_prior": 81000000.00,
            },
            {
                "region_code": "3202",
                "region_name": "Kota Bandung",
                "tax_type": "PBB",
                "period": "2025",
                "yoy_growth": 7.8,
                "target_achievement": 90.0,
                "revenue_current": 135000000.00,
                "revenue_prior": 125000000.00,
            },
        ]

    async def execute_query(
        self,
        query: str,
        params: Dict = None,
        scope: ScopeFilter = None,
        timeout: int = None,
        row_limit: int = None,
    ) -> QueryResult:
        """Mock query execution - returns deterministic test data."""

        row_limit = row_limit or self.DEFAULT_ROW_LIMIT

        # Determine which table is being queried
        table_type = self._identify_table(query)
        data = self._sample_data.get(table_type, [])

        # Apply scope filters
        if scope:
            data = self._apply_scope_filters(data, scope, table_type)

        # Apply row limit
        data = data[:row_limit]

        import time

        return QueryResult(
            data=data,
            meta={
                "query_id": f"mock_{hash(query) % 1000000}",
                "executed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "scope_applied": scope.dict() if scope else {},
                "mock": True,
            },
            row_count=len(data),
            latency_ms=1.0,  # Always fast in mock
        )

    def _identify_table(self, query: str) -> str:
        """Identify which table is being queried."""
        query_lower = query.lower()
        if "tax_revenue" in query_lower or "realization" in query_lower:
            return "tax_revenue"
        elif "tax_arrears" in query_lower or "tunggakan" in query_lower:
            return "tax_arrears"
        elif "growth_statistics" in query_lower:
            return "growth_statistics"
        return "tax_revenue"

    def _apply_scope_filters(
        self, data: List[Dict], scope: ScopeFilter, table_type: str
    ) -> List[Dict]:
        """Apply scope filters to mock data."""
        result = []
        for row in data:
            # Filter by region
            if scope.regions and row.get("region_code") not in scope.regions:
                continue
            # Filter by tax type
            if scope.tax_types and row.get("tax_type") not in scope.tax_types:
                continue
            result.append(row)
        return result

    async def health_check(self) -> Dict[str, Any]:
        """Mock health check - always healthy."""
        return {"status": "healthy", "database": "mock"}

    async def close(self) -> None:
        """Mock close - nothing to close."""
        pass