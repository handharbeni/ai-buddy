# Phase 2: Database Adapters & Mock Layer

**Status**: ⏳ In Progress
**Objective**: Implement read-only database connectors with mock layer for dev/test.

## Overview

Database layer provides unified interface to Oracle, PostgreSQL, and MySQL systems using read-only connections. Includes mock adapters for development and testing.

## Design

### Base Adapter Interface

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from dataclasses import dataclass

@dataclass
class QueryResult:
    data: List[Dict[str, Any]]
    meta: Dict[str, Any]
    row_count: int
    latency_ms: float

class DBAdapter(ABC):
    """Base database adapter interface."""

    @abstractmethod
    async def execute_query(self, query: str, params: Dict = None, scope: Dict = None) -> QueryResult:
        """Execute a query against the database."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check database connectivity."""
        pass

    @abstractmethod
    async def close(self):
        """Close connections."""
        pass
```

### Scope Filtering

Scope information is passed from RBAC middleware to adapters:

```python
@dataclass
class ScopeFilter:
    user_id: str
    role: str
    regions: List[str] = None
    tax_types: List[str] = None
    departments: List[str] = None
    own_taxpayers: List[str] = None
```

## Implementation Plan

### 1. Oracle Adapter

```python
# backend/app/db/oracle.py
import oracledb
from typing import Dict, List, Any
from .base import DBAdapter, QueryResult, ScopeFilter

class OracleAdapter(DBAdapter):
    def __init__(self, dsn: str, username: str, password: str):
        self.dsn = dsn
        self.username = username
        self.password = password
        self.connection_pool = None

    async def _get_connection(self):
        # Connection pooling
        pass

    async def execute_query(self, query: str, params: Dict = None, scope: ScopeFilter = None):
        # Apply scope filters to query
        # Execute with parameterized queries
        pass
```

### 2. PostgreSQL Adapter

```python
# backend/app/db/postgresql.py
import asyncpg
from typing import Dict, List, Any
from .base import DBAdapter, QueryResult, ScopeFilter

class PostgreSQLAdapter(DBAdapter):
    def __init__(self, dsn: str, username: str, password: str):
        self.dsn = dsn
        self.username = username
        self.password = password
        self.connection_pool = None
```

### 3. MySQL Adapter

```python
# backend/app/db/mysql.py
import aiomysql
from typing import Dict, List, Any
from .base import DBAdapter, QueryResult, ScopeFilter

class MySQLAdapter(DBAdapter):
    def __init__(self, dsn: str, username: str, password: str):
        self.dsn = dsn
        self.username = username
        self.password = password
        self.connection_pool = None
```

### 4. Mock Adapter (for Testing)

```python
# backend/app/db/mocks/test_db.py
from typing import Dict, List, Any
from ..base import DBAdapter, QueryResult, ScopeFilter

class MockAdapter(DBAdapter):
    def __init__(self):
        self.data = self._load_mock_data()

    async def execute_query(self, query: str, params: Dict = None, scope: ScopeFilter = None):
        # Return deterministic test data
        pass

    def _load_mock_data(self):
        # Load from fixtures/test_data/
        pass
```

## Scope Filter Injection

### Row-Level Security Views

Database views enforce data access controls:

```sql
-- Oracle View for revenue scope
CREATE OR REPLACE VIEW V_TAX_REVENUE_SCOPE AS
SELECT revenue_id, taxpayer_id, region_code, tax_type, tax_period,
       target_amount, realization_amount, percentage
FROM TAX_REVENUE_FACT
WHERE region_code IN (:user_regions)
  AND tax_type IN (:user_tax_types)
;

-- PostgreSQL View for arrears scope
CREATE OR REPLACE VIEW v_tax_arrears_scope AS
SELECT arrears_id, taxpayer_id, region_code, tax_type, tax_period,
       principal_amount, penalty_amount, interest_amount, aging_days, status
FROM tax_arrears_fact
WHERE region_code IN (:user_regions)
  AND tax_type IN (:user_tax_types)
;
```

### Scope-Aware Query Builder

```python
# backend/app/db/scope_builder.py
class ScopeQueryBuilder:
    def __init__(self, base_query: str, scope: ScopeFilter):
        self.base_query = base_query
        self.scope = scope

    def build_scope_filter(self) -> str:
        filters = []
        
        if self.scope.regions:
            regions = ', '.join(f"'{r}'" for r in self.scope.regions)
            filters.append(f"region_code IN ({regions})")
        
        if self.scope.tax_types:
            tax_types = ', '.join(f"'{t}'" for t in self.scope.tax_types)
            filters.append(f"tax_type IN ({tax_types})")
        
        if self.scope.own_taxpayers:
            taxpayers = ', '.join(f"'{t}'" for t in self.scope.own_taxpayers)
            filters.append(f"taxpayer_id IN ({taxpayers})")
        
        if filters:
            return f" WHERE {' AND '.join(filters)}"
        return ""
```

## Connection Pooling

### Configuration

```python
# backend/app/db/connection_pool.py
from typing import Dict, Any
import asyncio
from contextlib import asynccontextmanager

class ConnectionPoolManager:
    def __init__(self):
        self.pools = {}

    async def get_pool(self, db_type: str, config: Dict[str, Any]):
        if db_type not in self.pools:
            pool = await self._create_pool(db_type, config)
            self.pools[db_type] = pool
        return self.pools[db_type]

    async def _create_pool(self, db_type: str, config: Dict[str, Any]):n        # Create connection pool based on database type
        # Implement retry logic, timeout, and health checks
        pass
```

## Query Constraints Enforcement

### Timeout Enforcement

```python
# backend/app/db/query_timeout.py
import asyncio
from typing import Any, Callable

class QueryTimeout:
    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds

    async def execute_with_timeout(self, func: Callable, *args, **kwargs):
        try:
            return await asyncio.wait_for(func(*args, **kwargs), self.timeout_seconds)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Query exceeded {self.timeout_seconds} seconds")
```

### Row Limit Enforcement

```python
# backend/app/db/row_limiter.py
class RowLimitEnforcer:
    def __init__(self, default_limit: int = 1000):
        self.default_limit = default_limit

    def limit_query(self, query: str, row_limit: int = None) -> str:
        limit = row_limit or self.default_limit
        # Append LIMIT clause for SQL databases
        # Handle different database dialects
        if "LIMIT" not in query.upper():
            query += f" LIMIT {limit}"
        return query
```

## Testing Strategy

### Unit Tests

```python
# backend/tests/db/test_oracle_adapter.py
import pytest
from unittest.mock import AsyncMock, patch
from app.db.oracle import OracleAdapter

@pytest.fixture
def mock_connection():
    # Mock database connection
    pass

@pytest.mark.asyncio
async def test_query_execution():
    # Test successful query
    pass

@pytest.mark.asyncio
async def test_scope_filtering():
    # Test row-level security
    pass

@pytest.mark.asyncio
async def test_timeout():
    # Test timeout enforcement
    pass

@pytest.mark.asyncio
async def test_row_limit():
    # Test row limiting
    pass
```

### Integration Tests

```python
# backend/tests/db/integration_test.py
def test_with_mock_db():
    """Test with mock adapter"""
    from app.db.mocks.test_db import MockAdapter
    adapter = MockAdapter()
    # Test queries against mock data
    pass
```

## Migration Scripts

### Scope Views Creation

```sql
-- backend/sql/0001_create_scope_views.sql
-- Oracle
CREATE OR REPLACE VIEW V_TAX_REVENUE_SCOPE AS
SELECT r.revenue_id, r.taxpayer_id, r.region_code, r.tax_type, r.tax_period,
       r.target_amount, r.realization_amount, r.percentage
FROM TAX_REVENUE_FACT r
JOIN V_TAXPAYER_SCOPE t ON r.taxpayer_id = t.taxpayer_id
;

-- PostgreSQL
CREATE OR REPLACE VIEW v_tax_revenue_scope AS
SELECT r.revenue_id, r.taxpayer_id, r.region_code, r.tax_type, r.tax_period,
       r.target_amount, r.realization_amount, r.percentage
FROM tax_revenue_fact r
JOIN v_taxpayer_scope t ON r.taxpayer_id = t.taxpayer_id
;

-- MySQL (similar with appropriate syntax)
```

## Database Setup Documentation

### Local Development

```bash
# Oracle
export ORACLE_DSN="(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=localhost)(PORT=1521))(CONNECT_DATA=(SERVICE_NAME=ORCL)))"
export ORACLE_USER="AI_READONLY"
export ORACLE_PASSWORD="your_password"

# PostgreSQL
export POSTGRESQL_DSN="postgresql://AI_READONLY@localhost:5432/bapenda_analytics"

# MySQL
export MYSQL_DSN="mysql://AI_READONLY@localhost:3306/bapenda_master"
```

### Production Setup

- Use Oracle wallet or TNS_ADMIN for production connections
- PostgreSQL and MySQL require SSL certificates
- All connections must use AI_READONLY user
- Row-level security views must be created
- Regular backups recommended

## Approval Requirements

### Testing Requirements
- [ ] Unit tests for Oracle adapter
- [ ] Unit tests for PostgreSQL adapter
- [ ] Unit tests for MySQL adapter
- [ ] Unit tests for Mock adapter
- [ ] Integration tests with all database types
- [ ] Scope filtering tests
- [ ] Timeout enforcement tests
- [ ] Row limit tests
- [ ] SQL injection tests
- [ ] Connection pool tests

### Security Requirements
- [ ] All connections use AI_READONLY user
- [ ] Parameterized queries enforced
- [ ] Row-level security via views
- [ ] No write operations allowed
- [ ] SSL/TLS encryption for connections
- [ ] Connection timeout enforcement

### Performance Requirements
- [ ] Connection pooling implemented
- [ ] Query timeout < 30 seconds
- [ ] Row limits enforced
- [ ] Connection reuse
- [ ] Query result caching

## Files Created

```
backend/
├── app/
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── oracle.py
│   │   ├── postgresql.py
│   │   ├── mysql.py
│   │   ├── mocks/
│   │   │   ├── __init__.py
│   │   │   └── test_db.py
│   │   ├── connection_pool.py
│   │   ├── query_timeout.py
│   │   ├── row_limiter.py
│   │   └── scope_builder.py
│   └── main.py
├── tests/
│   ├── db/
│   │   ├── __init__.py
│   │   ├── test_oracle_adapter.py
│   │   ├── test_postgresql_adapter.py
│   │   ├── test_mysql_adapter.py
│   │   ├── test_mock_adapter.py
│   │   └── integration_test.py
│   └── sql/
│       └── 0001_create_scope_views.sql
└── docker/
    ├── oracle/
    │   └── Dockerfile
    ├── postgresql/
    │   └── Dockerfile
    └── mysql/
        └── Dockerfile
```

## Next Steps

After Phase 2 approval, proceed to:

**Phase 3: Auth/RBAC Service**
- JWT token validation
- OIDC integration
- Role assignment
- Scope resolution
- Permission matrix
- Rate limiting
- Audit logging

**Ready for your approval.**