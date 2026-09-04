# Semantic Domain Model

## Overview

This document defines the canonical data model for the BAPENDA Local AI Platform. All MCP tools, database views, and RAG documents conform to these semantic definitions.

## Core Entities

### Taxpayer (Wajib Pajak)

```yaml
entity: Taxpayer
table: oracle.TAXPAYER_MASTER (view: V_TAXPAYER_SCOPE)
primary_key: taxpayer_id
fields:
  taxpayer_id:
    type: VARCHAR2(20)
    format: "TP_\\d+"
    description: "Unique taxpayer identifier"
    pii: false
  npwpd:
    type: VARCHAR2(30)
    description: "Nomor Pokok Wajib Pajak Daerah"
    pii: true
    masking: "partial"  # Show first 4, last 4
  taxpayer_name:
    type: VARCHAR2(200)
    description: "Nama Wajib Pajak"
    pii: true
    masking: "partial"
  address:
    type: VARCHAR2(500)
    description: "Alamat lengkap"
    pii: true
    masking: "full"  # Only for authorized roles
  region_code:
    type: VARCHAR2(4)
    pattern: "^\\d{4}$"
    description: "Kode wilayah administratif"
    fk: Region.region_code
  tax_types:
    type: VARCHAR2(100)
    description: "Comma-separated tax types (PBB,BPHTB,...)"
  status:
    type: VARCHAR2(20)
    enum: [ACTIVE, INACTIVE, BLOCKED, MERGED]
  created_at:
    type: TIMESTAMP
  updated_at:
    type: TIMESTAMP
relationships:
  - has_many: TaxRevenue
  - has_many: TaxArrears
  - belongs_to: Region
scope_fields: [region_code, taxpayer_id]
```

### Region (Wilayah)

```yaml
entity: Region
table: mysql.REGION_MASTER (view: V_REGION_HIERARCHY)
primary_key: region_code
fields:
  region_code:
    type: CHAR(4)
    pattern: "^\\d{4}$"
    description: "Kode wilayah (Kemendagri standard)"
  region_name:
    type: VARCHAR2(100)
    description: "Nama wilayah"
  parent_code:
    type: CHAR(4)
    nullable: true
    description: "Kode wilayah induk"
    fk: Region.region_code
  level:
    type: VARCHAR2(20)
    enum: [PROVINCE, CITY, DISTRICT, VILLAGE]
  province_code:
    type: CHAR(2)
    description: "Kode provinsi (2 digit)"
  city_code:
    type: CHAR(2)
    description: "Kode kota/kabupaten (2 digit)"
  district_code:
    type: CHAR(2)
    description: "Kode kecamatan (2 digit)"
  village_code:
    type: CHAR(2)
    description: "Kode kelurahan/desa (2 digit)"
  geometry:
    type: JSON
    description: "GeoJSON polygon for mapping"
  is_active:
    type: BOOLEAN
    default: true
relationships:
  - has_many: Region (children)
  - belongs_to: Region (parent)
  - has_many: Taxpayer
  - has_many: TaxRevenue
  - has_many: TaxArrears
  - has_many: GrowthStatistics
scope_fields: [region_code]
```

### Tax Revenue (Realisasi Penerimaan)

```yaml
entity: TaxRevenue
table: oracle.TAX_REVENUE_FACT (view: V_TAX_REVENUE_SCOPE)
primary_key: revenue_id
fields:
  revenue_id:
    type: VARCHAR2(36)
    format: UUID
  taxpayer_id:
    type: VARCHAR2(20)
    fk: Taxpayer.taxpayer_id
  region_code:
    type: CHAR(4)
    fk: Region.region_code
  tax_type:
    type: VARCHAR2(10)
    enum: [PBB, BPHTB, PPh, PDAM, OTHER]
  tax_period:
    type: DATE
    description: "Period pajak (YYYY-MM-01)"
  target_amount:
    type: NUMBER(18,2)
    description: "Target penerimaan"
    constraint: ">= 0"
  realization_amount:
    type: NUMBER(18,2)
    description: "Realisasi penerimaan"
    constraint: ">= 0"
  percentage:
    type: NUMBER(5,2)
    description: "Persentase realisasi vs target"
    derived: "(realization_amount / target_amount) * 100"
  payment_date:
    type: DATE
    nullable: true
  payment_channel:
    type: VARCHAR2(50)
    enum: [BANK, ONLINE, COUNTER, MOBILE, OTHER]
  status:
    type: VARCHAR2(20)
    enum: [PAID, PARTIAL, PENDING, OVERDUE]
  created_at:
    type: TIMESTAMP
relationships:
  - belongs_to: Taxpayer
  - belongs_to: Region
scope_fields: [region_code, tax_type, taxpayer_id]
aggregations:
  - by_region_month: SUM(realization_amount) GROUP BY region_code, tax_period
  - by_tax_type: SUM(realization_amount) GROUP BY tax_type
  - yoy_growth: (current_year - prior_year) / prior_year * 100
```

### Tax Arrears (Tunggakan Pajak)

```yaml
entity: TaxArrears
table: oracle.TAX_ARREARS_FACT (view: V_TAX_ARREARS_SCOPE)
primary_key: arrears_id
fields:
  arrears_id:
    type: VARCHAR2(36)
    format: UUID
  taxpayer_id:
    type: VARCHAR2(20)
    fk: Taxpayer.taxpayer_id
  region_code:
    type: CHAR(4)
    fk: Region.region_code
  tax_type:
    type: VARCHAR2(10)
    enum: [PBB, BPHTB, PPh, PDAM, OTHER]
  tax_period:
    type: DATE
    description: "Period pajak yang tertunggak"
  principal_amount:
    type: NUMBER(18,2)
    description: "Pokok tunggakan"
    constraint: ">= 0"
  penalty_amount:
    type: NUMBER(18,2)
    description: "Denda/ administratif"
    constraint: ">= 0"
  interest_amount:
    type: NUMBER(18,2)
    description: "Bunga tunggakan"
    constraint: ">= 0"
  total_amount:
    type: NUMBER(18,2)
    description: "Total tunggakan (pokok + denda + bunga)"
    derived: "principal_amount + penalty_amount + interest_amount"
  aging_days:
    type: INTEGER
    description: "Hari terhitung dari jatuh tempo"
    constraint: ">= 0"
  aging_bucket:
    type: VARCHAR2(20)
    enum: [0-30, 31-90, 91-180, 181-365, 1-2_YEARS, 2-5_YEARS, 5+_YEARS]
    derived: "CASE aging_days ..."
  status:
    type: VARCHAR2(30)
    enum: [OPEN, PAYMENT_PLAN, LEGAL_ACTION, WRITE_OFF, CLOSED]
  last_payment_date:
    type: DATE
    nullable: true
  last_payment_amount:
    type: NUMBER(18,2)
    nullable: true
  collector_id:
    type: VARCHAR2(20)
    nullable: true
    description: "Petugas pemungut penanggung jawab"
  created_at:
    type: TIMESTAMP
  updated_at:
    type: TIMESTAMP
relationships:
  - belongs_to: Taxpayer
  - belongs_to: Region
scope_fields: [region_code, tax_type, taxpayer_id]
aggregations:
  - by_region: SUM(total_amount) GROUP BY region_code
  - by_aging: SUM(total_amount) GROUP BY aging_bucket
  - by_status: COUNT(*) GROUP BY status
```

### Growth Statistics (Statistik Pertumbuhan)

```yaml
entity: GrowthStatistics
table: postgresql.growth_statistics (view: v_growth_statistics_scope)
primary_key: stat_id
fields:
  stat_id:
    type: UUID
  region_code:
    type: CHAR(4)
    fk: Region.region_code
  tax_type:
    type: VARCHAR2(10)
    enum: [PBB, BPHTB, PPh, PDAM, ALL]
  period_start:
    type: DATE
  period_end:
    type: DATE
  period_type:
    type: VARCHAR2(10)
    enum: [MONTHLY, QUARTERLY, YEARLY]
  revenue_current:
    type: NUMERIC(18,2)
    description: "Pendapatan periode berjalan"
  revenue_prior:
    type: NUMERIC(18,2)
    description: "Pendapatan periode komparasi"
  yoy_growth:
    type: NUMERIC(10,4)
    description: "Year-over-year growth (%)"
    derived: "(revenue_current - revenue_prior) / NULLIF(revenue_prior, 0) * 100"
  qoq_growth:
    type: NUMERIC(10,4)
    description: "Quarter-over-quarter growth (%)"
  cagr:
    type: NUMERIC(10,4)
    description: "Compound Annual Growth Rate (%)"
  volatility:
    type: NUMERIC(10,4)
    description: "Coefficient of variation"
  target_amount:
    type: NUMERIC(18,2)
  target_achievement:
    type: NUMERIC(5,2)
    derived: "(revenue_current / NULLIF(target_amount, 0)) * 100"
  taxpayer_count:
    type: INTEGER
    description: "Jumlah WP aktif"
  new_taxpayer_count:
    type: INTEGER
  created_at:
    type: TIMESTAMPTZ
relationships:
  - belongs_to: Region
scope_fields: [region_code, tax_type]
```

## RAG Document Entity

### Regulation Document

```yaml
entity: RegulationDocument
index: qdrant.regulation_documents
primary_key: document_id
fields:
  document_id:
    type: string
    format: "REG_\\d{8}_\\d{4}"
  title:
    type: string
    description: "Judul dokumen"
  document_type:
    type: string
    enum: [PERDA, PERGUB, SOP, SURAT_EDARAN, PERMEN, PERDIR]
  document_number:
    type: string
    description: "Nomor dokumen resmi"
  issuing_authority:
    type: string
    description: "Penerbit (DPRD, Gubernur, Kepala Dinas, dll)"
  effective_date:
    type: date
    description: "Tanggal mulai berlaku"
  expiry_date:
    type: date
    nullable: true
  classification:
    type: string
    enum: [PUBLIC, INTERNAL, RESTRICTED]
  approval_status:
    type: string
    enum: [DRAFT, REVIEW, APPROVED, REJECTED, SUPERSEDED]
  version:
    type: string
    pattern: "^v\\d+(\\.\\d+)?$"
  tax_types:
    type: array
    items: string
    enum: [PBB, BPHTB, PPh, PDAM, GENERAL]
  regions:
    type: array
    items: string
    pattern: "^\\d{4}$"
  keywords:
    type: array
    items: string
  content_hash:
    type: string
    pattern: "^[a-f0-9]{64}$"
    description: "SHA-256 of full content"
  content_text:
    type: string
    description: "Full text content (chunked for embedding)"
  chunk_index:
    type: integer
  chunk_count:
    type: integer
  embedding_vector:
    type: vector
    dimensions: 1024
    model: "bge-m3"
  source_url:
    type: string
    nullable: true
  created_at:
    type: datetime
  approved_at:
    type: datetime
    nullable: true
  approved_by:
    type: string
    nullable: true
searchable_fields: [title, document_number, content_text, keywords]
filterable_fields: [document_type, classification, approval_status, tax_types, regions, effective_date]
constraints:
  - approval_status must be APPROVED for search
  - content_hash verified at retrieval
  - version immutable once APPROVED
```

## Enumerations (Controlled Vocabularies)

### Tax Type (Jenis Pajak)
| Code | Name | Description |
|------|------|-------------|
| PBB | Pajak Bumi dan Bangunan | Annual property tax |
| BPHTB | Bea Perolehan Hak Atas Tanah dan Bangunan | Transfer tax |
| PPh | Pajak Penghasilan | Income tax (local portion) |
| PDAM | Air Tanah / PDAM | Water utility charges |
| OTHER | Lain-lain | Other local taxes |

### Arrears Status (Status Tunggakan)
| Code | Name | Description |
|------|------|-------------|
| OPEN | Belum Ditindaklanjuti | New arrears, no action |
| PAYMENT_PLAN | Cicilan | Approved installment plan |
| LEGAL_ACTION | Proses Hukum | Legal proceedings initiated |
| WRITE_OFF | Dihapuskan | Written off per regulation |
| CLOSED | Tertutup | Fully paid |

### Document Classification
| Level | Description | Access |
|-------|-------------|--------|
| PUBLIC | Publik | All roles |
| INTERNAL | Internal | All authenticated |
| RESTRICTED | Terbatas | ADMIN, SUPERVISOR only |

### Approval Status
| Status | Description |
|--------|-------------|
| DRAFT | Disusun |
| REVIEW | Dalam review |
| APPROVED | Disetujui - searchable |
| REJECTED | Ditolak |
| SUPERSEDED | Diganti versi baru |

## Derived Metrics

### Revenue Metrics
- **Realization Rate**: `SUM(realization) / SUM(target) * 100`
- **YoY Growth**: `(Current Period - Same Period Prior Year) / Prior Year * 100`
- **Collection Efficiency**: `Collected / (Collected + Outstanding) * 100`

### Arrears Metrics
- **Arrears Ratio**: `Total Arrears / Total Revenue * 100`
- **Aging Profile**: Distribution across aging buckets
- **Recovery Rate**: `Collected from Arrears / Beginning Arrears * 100`

### Growth Metrics
- **CAGR**: `(End Value / Start Value)^(1/Years) - 1`
- **Volatility**: `StdDev(Monthly Growth) / Mean(Monthly Growth)`

## Data Quality Rules

| Rule | Entity | Severity |
|------|--------|----------|
| taxpayer_id must exist in master | TaxRevenue, TaxArrears | Error |
| region_code must exist in Region | All | Error |
| tax_period first day of month | TaxRevenue, TaxArrears | Error |
| realization_amount <= target_amount * 2 | TaxRevenue | Warning |
| aging_days >= 0 | TaxArrears | Error |
| total_amount = principal + penalty + interest | TaxArrears | Error |
| approval_status = APPROVED for search | RegulationDocument | Error |
| content_hash matches stored content | RegulationDocument | Error |

## View Definitions (Logical)

### V_TAXPAYER_SCOPE
```sql
SELECT t.* 
FROM TAXPAYER_MASTER t
WHERE t.region_code IN (:user_regions)
  AND (t.taxpayer_id IN (:user_taxpayers) OR :has_region_scope = 1)
```

### V_TAX_REVENUE_SCOPE
```sql
SELECT r.*
FROM TAX_REVENUE_FACT r
JOIN V_TAXPAYER_SCOPE t ON r.taxpayer_id = t.taxpayer_id
WHERE r.region_code IN (:user_regions)
  AND r.tax_type IN (:user_tax_types)
```

### V_TAX_ARREARS_SCOPE
```sql
SELECT a.*
FROM TAX_ARREARS_FACT a
JOIN V_TAXPAYER_SCOPE t ON a.taxpayer_id = t.taxpayer_id
WHERE a.region_code IN (:user_regions)
  AND a.tax_type IN (:user_tax_types)
```

### V_GROWTH_STATISTICS_SCOPE
```sql
SELECT g.*
FROM growth_statistics g
WHERE g.region_code IN (:user_regions)
  AND g.tax_type IN (:user_tax_types)
```

## API Response Envelope

All MCP tool responses wrap data in standard envelope:

```json
{
  "data": [...],
  "meta": {
    "query_id": "uuid",
    "executed_at": "2026-01-15T10:30:00Z",
    "row_count": 42,
    "scope_applied": {
      "regions": ["3201"],
      "tax_types": ["PBB"],
      "departments": ["PEMUNGUTAN"]
    },
    "filters": {
      "period_start": "2025-01-01",
      "period_end": "2025-12-31"
    }
  }
}
```

## Versioning

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-15 | Initial domain model |