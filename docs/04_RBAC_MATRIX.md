# RBAC Matrix

## Role Definitions

| Role | Description | Typical User | Data Scope Default |
|------|-------------|--------------|-------------------|
| ADMIN | Full system administration, user management, audit access | IT Security, System Admin | All regions, all tax types, all departments |
| SUPERVISOR | Department/region oversight, team management, escalations | Section Head, Division Chief | Assigned region(s), all tax types, assigned department |
| ANALYST | Deep analysis, cross-region reports, trend detection | Tax Analyst, Data Scientist | Assigned region(s), assigned tax types, read-only |
| STAFF | Operational queries, daily tasks, taxpayer assistance | Front-line Staff, Counter Officer | Assigned region, assigned tax type, own taxpayers |

## Permission Model

Permissions are composed of: `resource:action:scope`

### Resources
- `tax_revenue` - Revenue collection data
- `tax_arrears` - Outstanding tax debts
- `growth_statistics` - Regional growth metrics
- `region_master` - Administrative boundaries
- `taxpayer_summary` - Individual taxpayer profile
- `regulation` - Legal documents (Perda, Pergub, SOP, SE)
- `audit_log` - System audit trail
- `user_management` - User/role administration
- `system_config` - System configuration

### Actions
- `read` - View data
- `export` - Download data (CSV/Excel)
- `analyze` - Run analytical queries
- `manage` - CRUD on resource (admin only)

### Scopes
- `all` - No restriction
- `region:{code}` - Specific region code (e.g., `region:3201`)
- `tax_type:{code}` - Specific tax type (e.g., `tax_type:PBB`)
- `department:{code}` - Specific department
- `own` - Only own records (taxpayer assigned to user)

## RBAC Matrix

| Permission | ADMIN | SUPERVISOR | ANALYST | STAFF |
|------------|-------|------------|---------|-------|
| **tax_revenue** | | | | |
| tax_revenue:read:all | ✅ | ❌ | ❌ | ❌ |
| tax_revenue:read:region | ✅ | ✅ | ✅ | ✅ |
| tax_revenue:read:tax_type | ✅ | ✅ | ✅ | ✅ |
| tax_revenue:export:region | ✅ | ✅ | ✅ | ❌ |
| tax_revenue:analyze:all | ✅ | ❌ | ❌ | ❌ |
| tax_revenue:analyze:region | ✅ | ✅ | ✅ | ❌ |
| **tax_arrears** | | | | |
| tax_arrears:read:all | ✅ | ❌ | ❌ | ❌ |
| tax_arrears:read:region | ✅ | ✅ | ✅ | ✅ |
| tax_arrears:read:tax_type | ✅ | ✅ | ✅ | ✅ |
| tax_arrears:read:own | ✅ | ✅ | ✅ | ✅ |
| tax_arrears:export:region | ✅ | ✅ | ✅ | ❌ |
| tax_arrears:analyze:all | ✅ | ❌ | ❌ | ❌ |
| tax_arrears:analyze:region | ✅ | ✅ | ✅ | ❌ |
| **growth_statistics** | | | | |
| growth_statistics:read:all | ✅ | ❌ | ❌ | ❌ |
| growth_statistics:read:region | ✅ | ✅ | ✅ | ✅ |
| growth_statistics:export:region | ✅ | ✅ | ✅ | ❌ |
| growth_statistics:analyze:all | ✅ | ❌ | ✅ | ❌ |
| growth_statistics:analyze:region | ✅ | ✅ | ✅ | ❌ |
| **region_master** | | | | |
| region_master:read:all | ✅ | ✅ | ✅ | ✅ |
| region_master:manage:all | ✅ | ❌ | ❌ | ❌ |
| **taxpayer_summary** | | | | |
| taxpayer_summary:read:region | ✅ | ✅ | ✅ | ✅ |
| taxpayer_summary:read:own | ✅ | ✅ | ✅ | ✅ |
| taxpayer_summary:read:all | ✅ | ❌ | ❌ | ❌ |
| taxpayer_summary:export:region | ✅ | ✅ | ❌ | ❌ |
| **regulation** | | | | |
| regulation:read:approved | ✅ | ✅ | ✅ | ✅ |
| regulation:read:all_status | ✅ | ✅ | ❌ | ❌ |
| regulation:manage:all | ✅ | ❌ | ❌ | ❌ |
| **audit_log** | | | | |
| audit_log:read:all | ✅ | ❌ | ❌ | ❌ |
| audit_log:read:own | ✅ | ✅ | ✅ | ✅ |
| audit_log:read:region | ✅ | ✅ | ❌ | ❌ |
| audit_log:export:all | ✅ | ❌ | ❌ | ❌ |
| **user_management** | | | | |
| user_management:read:all | ✅ | ❌ | ❌ | ❌ |
| user_management:manage:all | ✅ | ❌ | ❌ | ❌ |
| **system_config** | | | | |
| system_config:read:all | ✅ | ❌ | ❌ | ❌ |
| system_config:manage:all | ✅ | ❌ | ❌ | ❌ |

## MCP Tool Permissions

| MCP Tool | Required Permission | ADMIN | SUPERVISOR | ANALYST | STAFF |
|----------|---------------------|-------|------------|---------|-------|
| get_tax_revenue | tax_revenue:read:{scope} | ✅ | ✅ | ✅ | ✅ |
| get_tax_arrears | tax_arrears:read:{scope} | ✅ | ✅ | ✅ | ✅ |
| get_growth_statistics | growth_statistics:read:{scope} | ✅ | ✅ | ✅ | ✅ |
| get_region | region_master:read:all | ✅ | ✅ | ✅ | ✅ |
| get_taxpayer_summary | taxpayer_summary:read:{scope} | ✅ | ✅ | ✅ | ✅ |
| search_regulation | regulation:read:approved | ✅ | ✅ | ✅ | ✅ |

## Scope Resolution

Scope is resolved at runtime based on user assignment:

```
User Assignment (from IdP/HR System):
{
  "user_id": "STAFF_001",
  "role": "STAFF",
  "region": "3201",
  "tax_types": ["PBB", "BPHTB"],
  "department": "PEMUNGUTAN",
  "taxpayer_ids": ["TP_001", "TP_002", ...]
}

Effective Scopes for STAFF_001:
- region:3201
- tax_type:PBB
- tax_type:BPHTB
- department:PEMUNGUTAN
- own (taxpayer_ids)
```

### Scope Inheritance Rules

1. **Region**: Explicit assignment only, no inheritance
2. **Tax Type**: Explicit assignment only
3. **Department**: Explicit assignment only
4. **Own**: Derived from taxpayer assignment table
5. **All**: Only for ADMIN role

### Scope Combination Logic

For a query requiring multiple scopes (e.g., revenue by region AND tax_type):
- User must have ALL required scopes
- Result is intersection of all scopes
- If any scope missing → 403 Forbidden

## API Endpoint Permissions

| Endpoint | Method | Required Permission | Roles |
|----------|--------|---------------------|-------|
| /api/v1/auth/login | POST | public | All |
| /api/v1/auth/refresh | POST | valid refresh token | All |
| /api/v1/auth/me | GET | authenticated | All |
| /api/v1/query | POST | any read permission | All |
| /api/v1/tools/execute | POST | tool-specific permission | All |
| /api/v1/regulations/search | GET | regulation:read:approved | All |
| /api/v1/audit/logs | GET | audit_log:read:{scope} | ADMIN, SUPERVISOR |
| /api/v1/admin/users | GET | user_management:read:all | ADMIN |
| /api/v1/admin/users | POST | user_management:manage:all | ADMIN |
| /api/v1/admin/config | GET | system_config:read:all | ADMIN |
| /api/v1/admin/config | PUT | system_config:manage:all | ADMIN |

## Role Assignment Rules

1. **Assignment Authority**: Only ADMIN can assign/modify roles
2. **Scope Assignment**: ADMIN or SUPERVISOR (for their region/department)
3. **Default Role**: New users → STAFF with minimal scope
4. **Role Changes**: Require approval workflow, audit logged
5. **Temporary Elevation**: Max 4 hours, requires SUPERVISOR approval, auto-revoke

## Separation of Duties

| Conflict | Enforcement |
|----------|-------------|
| ADMIN cannot be SUPERVISOR | Single role per user |
| User management + Audit read | ADMIN only, logged |
| Config change + Data access | ADMIN only, dual approval for prod |
| Scope assignment + Data query | Separate roles |

## Emergency Access

| Scenario | Process | Duration | Audit |
|----------|---------|----------|-------|
| Break-glass admin | Pre-approved key, 2-person auth | 1 hour | Full session recording |
| Disaster recovery | Offline procedure, physical access | Until restored | Manual log |
| Audit investigation | Court order / legal request | Case-specific | Legal hold |

## Testing Matrix

| Test Case | Expected Result |
|-----------|-----------------|
| STAFF queries other region revenue | 403 Forbidden |
| ANALYST exports arrears data | 403 Forbidden |
| SUPERVISOR manages users | 403 Forbidden |
| ADMIN reads audit logs all | 200 OK |
| STAFF searches regulations | 200 OK (approved only) |
| SUPERVISOR views other dept arrears | 403 Forbidden |
| Expired token access | 401 Unauthorized |
| Revoked role immediate effect | 403 on next request |