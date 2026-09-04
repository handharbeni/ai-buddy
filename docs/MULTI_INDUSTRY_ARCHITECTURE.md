# Multi-Industry Platform Architecture

> This document describes how the BAPENDA Local AI Platform can be adapted for any industry with a database.

## Core Insight

The platform is **industry-agnostic**. The same architecture works for any domain by swapping two things:

1. **MCP tool definitions** — what DB queries are available
2. **Domain knowledge base** — what documents/rules are in RAG

Everything else — auth, RBAC, LLM orchestration, output formatting, security — stays the same.

---

## Platform Layers

```
┌─────────────────────────────────────────────────┐
│                 User Interface                    │
│        (Dashboard / Chat / API / Docs)          │
├─────────────────────────────────────────────────┤
│          Output Formatter (7 formats)            │
│      XLSX · DOCX · PDF · CSV · JSON · MD       │
├─────────────────────────────────────────────────┤
│           Prompt Injection Detector              │
│     Regex (50+ patterns) + LLM fallback        │
├─────────────────────────────────────────────────┤
│              Orchestrator Pipeline               │
│  Intent Detection → MCP / RAG / LLM synthesis │
├─────────────────────────────────────────────────┤
│                 LLM Layer                       │
│   Local Ollama (dev) / vLLM (prod)             │
│   bapenda-ai:latest or any HuggingFace model  │
├─────────────────────────────────────────────────┤
│     MCP Router (tool registry + scope)          │
│   get_tax_revenue  ←→  Oracle/PostgreSQL/MySQL│
│   get_tax_arrears                               │
│   get_growth_statistics                         │
│   get_region                                    │
│   get_taxpayer_summary                          │
│   search_regulation                             │
├─────────────────────────────────────────────────┤
│    Vector DB (Qdrant) — RAG for documents      │
│   Perda · Pergub · SOP · Surat Edaran          │
├─────────────────────────────────────────────────┤
│              Database Adapters                   │
│  Oracle  ·  PostgreSQL  ·  MySQL  ·  Mock    │
└─────────────────────────────────────────────────┘
```

---

## Industry Adaptation Guide

### Step 1: Define MCP Tools

Each tool maps to one DB query. The LLM uses tools to answer structured questions.

**Current (Bapenda — tax domain)**

| Tool | DB Table | Purpose |
|------|---------|---------|
| `get_tax_revenue` | `TAX_REVENUE` | Revenue by period/region/type |
| `get_tax_arrears` | `TAX_ARREARS` | Outstanding tax payments |
| `get_growth_statistics` | `GROWTH_STATS` | Period-over-period growth |
| `get_region` | `REGION_MASTER` | Geographic hierarchy |
| `get_taxpayer_summary` | `TAXPAYER` | Wajib pajak profiles |
| `search_regulation` | RAG/Qdrant | Perda, Pergub, SOP |

**Template (any industry)**

```python
TOOL_REGISTRY = {
    "get_revenue": {
        "description": "Get revenue data by period, region, and category",
        "parameters": ["period_start", "period_end", "region_code", "category"],
        "db_adapter": "oracle",
        "query_template": "SELECT ... FROM revenue WHERE ...",
        "permissions": ["ANALYST", "SUPERVISOR", "ADMIN"],
    },
    "get_inventory": {
        "description": "Get current inventory levels by warehouse and product",
        "parameters": ["warehouse_code", "product_category", "stock_status"],
        "db_adapter": "postgresql",
        "query_template": "SELECT ... FROM inventory WHERE ...",
        "permissions": ["STAFF", "ANALYST", "SUPERVISOR", "ADMIN"],
    },
    # ... add any number of domain-specific tools
}
```

**Rule: One tool = One read-only SQL query. No write operations.**

---

### Step 2: Configure Database Adapters

```python
# config.py
DATABASES = {
    "oracle": {
        "type": "oracle",
        "host": os.getenv("DB_ORACLE_HOST", "localhost"),
        "port": int(os.getenv("DB_ORACLE_PORT", "1521")),
        "service": os.getenv("DB_ORACLE_SERVICE", "XEPDB1"),
        "user_env": "DB_ORACLE_USER",
        "password_env": "DB_ORACLE_PASSWORD",
        "read_only": True,
    },
    # Add any number of databases
}
```

**Rule: All adapters are read-only. No INSERT, UPDATE, DELETE, DROP, TRUNCATE, ALTER.**

---

### Step 3: Upload Domain Documents (RAG)

Documents go into Qdrant vector database. Each document needs metadata:

```python
DocumentMetadata(
    title="Perda No. 12 Tahun 2024 tentang Pajak Restoran",
    version="1.0",
    effective_date=date(2024, 7, 1),
    classification="REGULATION",  # REGULATION | SOP | MANUAL | POLICY
    approval_status="APPROVED",  # APPROVED | DRAFT | ARCHIVED
    issuer="DPRD Jawa Barat",
    tags=["pajak_restoran", "insentif", "daerah"],
)
```

**Document types supported:**
- Perda (local regulation)
- Pergub (governor regulation)
- SOP (Standard Operating Procedure)
- Surat Edaran (Circular Letter)
- Manual / Policy
- Any structured text document

**Rule: Only APPROVED documents are indexed. Draft/Archived are excluded.**

---

### Step 4: Customize LLM System Prompt

```python
SYSTEM_PROMPT = """You are an AI assistant for {INDUSTRY_NAME}.

You help {USER_ROLE} answer questions using data from the available database.
When a question asks for structured data (numbers, tables, trends):
  1. Use the available MCP tools to query the database
  2. Synthesize the results into a clear answer
  3. Always cite the data source

Available data domains: {DOMAIN_LIST}
Available output formats: XLSX, DOCX, PDF, CSV, JSON, HTML, Markdown

Always respond in Indonesian (Bahasa Indonesia).
Never make up data. Only report what is in the database.
"""
```

---

## Example Industry Adaptations

### Healthcare (RSUD / Hospital)
```
MCP tools: get_patient_summary, get_bed_occupancy, get_revenue_ipdn,
           get_drug_inventory, get_medical_records
RAG docs:  SOP Pelayanan, Tarif INA-CBGs, JKN Guidelines,
           Standar Kemenkes
DB:        MySQL (patient data), PostgreSQL (INACBGs), Oracle (finance)
```

### Education (Disdik / School)
```
MCP tools: get_student_enrollment, get_teacher_allocation,
           get_budget_realization, get_facility_inventory
RAG docs:  Kurikulum, Standar Nasional Pendidikan,
           Anggaran Sekolah
DB:        PostgreSQL (student info), MySQL (finance)
```

### Logistics (Dinas Perhubungan)
```
MCP tools: get_vehicle_permit, get_route_statistics,
           get_fine_revenue, get_public_transport_stats
RAG docs:  Perda Transportasi, Standar Keamanan,
           SOP Perizinan
DB:        Oracle (vehicles), PostgreSQL (routes), MySQL (fines)
```

### Agriculture (Dinas Pertanian)
```
MCP tools: get_crop_production, get_land_use, get_subsidy_distribution,
           get_farmer_registry
RAG docs:  Kebijakan Pertanian, Subsidi Benih, Standar Panen
DB:        PostgreSQL (production), MySQL (registry)
```

### Finance (BPKD / Regional Treasury)
```
MCP tools: get_budget_allocation, get_expenditure_realization,
           get_cash_position, get_bilateral_receivables
RAG docs:  PP No. XX/2024, Permendagri, SOP Pelaporan,
           Standar Akuntansi
DB:        Oracle (treasury), PostgreSQL (budget), MySQL (AP)
```

---

## What Stays the Same Across All Industries

| Component | Industry-agnostic? | Notes |
|-----------|---------------------|-------|
| Auth (JWT, RBAC) | ✅ Yes | Add/remove roles as needed |
| Rate limiting | ✅ Yes | Configurable per-endpoint |
| Prompt injection detector | ✅ Yes | 50+ regex patterns + LLM fallback |
| Output formatter (7 formats) | ✅ Yes | Works with any tabular data |
| Intent detection | ✅ Yes | Keyword-based, add industry terms |
| Conversation storage | ✅ Yes | localStorage or DB-backed |
| LLM orchestration | ✅ Yes | Any Ollama/vLLM model |
| Zero Trust RBAC | ✅ Yes | Enforced at every layer |
| Audit logging | ✅ Yes | Append-only, immutable |
| CORS + Security headers | ✅ Yes | Config per deployment |

---

## Minimum Changes Per Industry

| Change | Effort | Description |
|--------|--------|-------------|
| MCP tool definitions | 1-2 days | Define tools + mock data |
| DB adapter config | 1 day | Add connection strings |
| LLM system prompt | 2 hours | Customize domain context |
| RAG documents | Ongoing | Upload Perda/docs per approval |
| RBAC roles | 1 day | Define permissions matrix |
| UI rebrand | 1 day | Logo + color scheme |

**Estimated time to deploy in a new industry: 3-5 working days**

---

## Deployment Options

### Single-industry (current: BAPENDA)
```
docker-compose.local.yml
├── backend (FastAPI)
├── frontend (Next.js)
├── ollama (Local LLM)
└── qdrant (Vector DB)
```

### Multi-industry (shared infrastructure)
```
├── Shared: Ollama, Qdrant, Auth, RBAC, Security, Audit
├── Per-industry: MCP tools, DB adapters, RAG corpus, LLM fine-tune
└── Tenant isolation via RBAC scope (regions, departments, data types)
```

---

## Compliance Notes

- **PDPO / UU PDP**: PII redactor is included and active
- **Audit trail**: Every query logged with user, role, scope, intent, latency
- **Read-only DB**: No write operations in any adapter
- **Data residency**: All processing is local (no cloud call-out)
- **RBAC scope**: Users only see data within their authorized scope

---

*Document version: 1.0 | Last updated: 2026-09-02*
