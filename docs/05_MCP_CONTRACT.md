# MCP Contract

## Overview

The Model Context Protocol (MCP) Router exposes a controlled set of business tools to the LLM. Each tool is a deterministic, auditable function with strict input/output contracts, permission requirements, and scope enforcement.

## MCP Tool Registry

### 1. get_tax_revenue

**Description**: Retrieve tax revenue realization data for specified period, region, and tax type.

**Permission**: `tax_revenue:read:{scope}`

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "period_start": {
      "type": "string",
      "format": "date",
      "description": "Start date (YYYY-MM-DD)",
      "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
    },
    "period_end": {
      "type": "string",
      "format": "date",
      "description": "End date (YYYY-MM-DD)",
      "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
    },
    "region_code": {
      "type": "string",
      "pattern": "^\\d{4}$",
      "description": "4-digit region code (e.g., 3201)"
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
  "additionalProperties": false
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "data": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "period": {"type": "string"},
          "region_code": {"type": "string"},
          "region_name": {"type": "string"},
          "tax_type": {"type": "string"},
          "target": {"type": "number", "minimum": 0},
          "realization": {"type": "number", "minimum": 0},
          "percentage": {"type": "number", "minimum": 0, "maximum": 100}
        },
        "required": ["period", "region_code", "tax_type", "target", "realization", "percentage"]
      }
    },
    "meta": {
      "type": "object",
      "properties": {
        "query_id": {"type": "string"},
        "executed_at": {"type": "string", "format": "date-time"},
        "row_count": {"type": "integer", "minimum": 0},
        "scope_applied": {"type": "object"}
      },
      "required": ["query_id", "executed_at", "row_count"]
    }
  },
  "required": ["data", "meta"]
}
```

**Constraints**:
- Max date range: 2 years
- Max rows returned: 1000
- Timeout: 30 seconds
- Scope filter applied automatically on `region_code`

---

### 2. get_tax_arrears

**Description**: Retrieve outstanding tax arrears (tunggakan) data.

**Permission**: `tax_arrears:read:{scope}`

**Input Schema**:
```json
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
      "pattern": "^\\d{4}$"
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
  "additionalProperties": false
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "data": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "taxpayer_id": {"type": "string"},
          "taxpayer_name": {"type": "string"},
          "region_code": {"type": "string"},
          "region_name": {"type": "string"},
          "tax_type": {"type": "string"},
          "arrears_amount": {"type": "number", "minimum": 0},
          "aging_days": {"type": "integer", "minimum": 0},
          "status": {"type": "string"},
          "last_payment_date": {"type": ["string", "null"], "format": "date"}
        },
        "required": ["taxpayer_id", "region_code", "tax_type", "arrears_amount", "aging_days", "status"]
      }
    },
    "meta": {
      "type": "object",
      "properties": {
        "query_id": {"type": "string"},
        "executed_at": {"type": "string", "format": "date-time"},
        "row_count": {"type": "integer", "minimum": 0},
        "total_arrears": {"type": "number", "minimum": 0},
        "scope_applied": {"type": "object"}
      },
      "required": ["query_id", "executed_at", "row_count", "total_arrears"]
    }
  },
  "required": ["data", "meta"]
}
```

**Constraints**:
- Max rows returned: 1000
- Timeout: 30 seconds
- `taxpayer_id` requires `own` scope
- Scope filter applied on `region_code`

---

### 3. get_growth_statistics

**Description**: Retrieve regional tax growth statistics and trends.

**Permission**: `growth_statistics:read:{scope}`

**Input Schema**:
```json
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
  "additionalProperties": false
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "data": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "region_code": {"type": "string"},
          "region_name": {"type": "string"},
          "tax_type": {"type": "string"},
          "period": {"type": "string"},
          "yoy_growth": {"type": ["number", "null"]},
          "qoq_growth": {"type": ["number", "null"]},
          "cagr": {"type": ["number", "null"]},
          "volatility": {"type": ["number", "null"]},
          "target_achievement": {"type": ["number", "null"]},
          "revenue_current": {"type": "number", "minimum": 0},
          "revenue_prior": {"type": "number", "minimum": 0}
        },
        "required": ["region_code", "tax_type", "period", "revenue_current", "revenue_prior"]
      }
    },
    "meta": {
      "type": "object",
      "properties": {
        "query_id": {"type": "string"},
        "executed_at": {"type": "string", "format": "date-time"},
        "row_count": {"type": "integer", "minimum": 0},
        "scope_applied": {"type": "object"}
      },
      "required": ["query_id", "executed_at", "row_count"]
    }
  },
  "required": ["data", "meta"]
}
```

**Constraints**:
- Max date range: 5 years
- Max rows returned: 500
- Timeout: 30 seconds
- Scope filter on `region_code`

---

### 4. get_region

**Description**: Retrieve administrative region master data.

**Permission**: `region_master:read:all`

**Input Schema**:
```json
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
  "additionalProperties": false
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "data": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "region_code": {"type": "string"},
          "region_name": {"type": "string"},
          "parent_code": {"type": ["string", "null"]},
          "level": {"type": "string"},
          "geometry": {"type": ["object", "null"]}
        },
        "required": ["region_code", "region_name", "level"]
      }
    },
    "meta": {
      "type": "object",
      "properties": {
        "query_id": {"type": "string"},
        "executed_at": {"type": "string", "format": "date-time"},
        "row_count": {"type": "integer", "minimum": 0}
      },
      "required": ["query_id", "executed_at", "row_count"]
    }
  },
  "required": ["data", "meta"]
}
```

**Constraints**:
- Max rows returned: 5000
- Timeout: 10 seconds
- No scope filter (reference data)

---

### 5. get_taxpayer_summary

**Description**: Retrieve summary profile for a specific taxpayer.

**Permission**: `taxpayer_summary:read:{scope}`

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "taxpayer_id": {
      "type": "string",
      "pattern": "^TP_\\d+$"
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
  "additionalProperties": false
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "data": {
      "type": "object",
      "properties": {
        "taxpayer_id": {"type": "string"},
        "taxpayer_name": {"type": "string"},
        "npwpd": {"type": "string"},
        "region_code": {"type": "string"},
        "region_name": {"type": "string"},
        "address": {"type": "string"},
        "tax_types": {
          "type": "array",
          "items": {"type": "string"}
        },
        "current_arrears": {"type": "number", "minimum": 0},
        "arrears_detail": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "tax_type": {"type": "string"},
              "amount": {"type": "number", "minimum": 0},
              "aging_days": {"type": "integer", "minimum": 0},
              "status": {"type": "string"}
            },
            "required": ["tax_type", "amount", "aging_days", "status"]
          }
        },
        "revenue_history": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "period": {"type": "string"},
              "tax_type": {"type": "string"},
              "amount": {"type": "number", "minimum": 0}
            },
            "required": ["period", "tax_type", "amount"]
          }
        }
      },
      "required": ["taxpayer_id", "taxpayer_name", "npwpd", "region_code", "tax_types"]
    },
    "meta": {
      "type": "object",
      "properties": {
        "query_id": {"type": "string"},
        "executed_at": {"type": "string", "format": "date-time"},
        "scope_applied": {"type": "object"}
      },
      "required": ["query_id", "executed_at"]
    }
  },
  "required": ["data", "meta"]
}
```

**Constraints**:
- Requires `own` scope or region scope
- Max history: 36 months
- Timeout: 15 seconds
- PII fields included (name, address) - scope enforced

---

### 6. search_regulation

**Description**: Search approved regulations (Perda, Pergub, SOP, Surat Edaran) using semantic search.

**Permission**: `regulation:read:approved`

**Input Schema**:
```json
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
  "additionalProperties": false
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "data": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "document_id": {"type": "string"},
          "title": {"type": "string"},
          "document_type": {"type": "string"},
          "document_number": {"type": "string"},
          "effective_date": {"type": "string", "format": "date"},
          "classification": {"type": "string"},
          "approval_status": {"type": "string"},
          "excerpt": {"type": "string"},
          "relevance_score": {"type": "number", "minimum": 0, "maximum": 1},
          "source_url": {"type": ["string", "null"]}
        },
        "required": ["document_id", "title", "document_type", "document_number", "effective_date", "approval_status", "excerpt", "relevance_score"]
      }
    },
    "meta": {
      "type": "object",
      "properties": {
        "query_id": {"type": "string"},
        "executed_at": {"type": "string", "format": "date-time"},
        "result_count": {"type": "integer", "minimum": 0},
        "search_time_ms": {"type": "integer", "minimum": 0}
      },
      "required": ["query_id", "executed_at", "result_count", "search_time_ms"]
    }
  },
  "required": ["data", "meta"]
}
```

**Constraints**:
- Only `approval_status = APPROVED` documents returned
- Max results: 20
- Timeout: 10 seconds
- Retrieved text treated as untrusted - citation only

---

## MCP Router Contract

### Request Format
```json
{
  "request_id": "uuid",
  "user_id": "string",
  "role": "ADMIN|SUPERVISOR|ANALYST|STAFF",
  "scopes": ["region:3201", "tax_type:PBB", "own"],
  "tool": "get_tax_revenue",
  "parameters": {},
  "timeout_ms": 30000
}
```

### Response Format (Success)
```json
{
  "request_id": "uuid",
  "status": "success",
  "tool": "get_tax_revenue",
  "result": {},
  "meta": {
    "executed_at": "ISO8601",
    "latency_ms": 123,
    "rows_returned": 42
  }
}
```

### Response Format (Error)
```json
{
  "request_id": "uuid",
  "status": "error",
  "tool": "get_tax_revenue",
  "error": {
    "code": "PERMISSION_DENIED|INVALID_PARAMETER|TIMEOUT|INTERNAL_ERROR",
    "message": "Human-readable message",
    "details": {}
  },
  "meta": {
    "executed_at": "ISO8601",
    "latency_ms": 123
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| PERMISSION_DENIED | 403 | User lacks required permission/scope |
| INVALID_PARAMETER | 400 | Input schema validation failed |
| SCOPE_VIOLATION | 403 | Requested scope exceeds user assignment |
| TIMEOUT | 504 | Tool execution exceeded timeout |
| RATE_LIMITED | 429 | User exceeded rate limit |
| INTERNAL_ERROR | 500 | Unexpected system error |
| TOOL_NOT_FOUND | 404 | Tool not registered |
| RESULT_TOO_LARGE | 413 | Result exceeds row limit |

---

## Tool Execution Flow

```
LLM Request
    │
    ▼
┌─────────────────────┐
│ Validate Tool Exists│
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Validate Input      │──▶ JSON Schema validation
│ Schema              │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Check Permission    │──▶ RBAC: role + scope match tool requirement
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Apply Scope Filters │──▶ Inject region/tax_type/department/own filters
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Execute Tool        │──▶ Call database adapter / Qdrant
│ (with timeout)      │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Validate Output     │──▶ JSON Schema validation
│ Schema              │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Enforce Row Limit   │──▶ Truncate if > max_rows
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Audit Log           │──▶ Record execution
└─────────┬───────────┘
          │
          ▼
      Return Result
```

---

## Versioning

- Tool versions in URL: `/mcp/v1/tools/get_tax_revenue`
- Schema changes = new version
- Backward compatibility: 12 months
- Deprecation notice: 6 months

---

## Rate Limits

| Role | Requests/min | Requests/hour | Concurrent |
|------|--------------|---------------|------------|
| ADMIN | 120 | 2000 | 10 |
| SUPERVISOR | 60 | 1000 | 5 |
| ANALYST | 60 | 1000 | 5 |
| STAFF | 30 | 500 | 3 |

Per-tool limits also apply (e.g., search_regulation: 10/min)