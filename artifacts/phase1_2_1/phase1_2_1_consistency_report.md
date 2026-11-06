# PHASE 1.2.1 – AUTOMATED CONSISTENCY VALIDATION REPORT

- **Generated At:** `2026-11-05T13:45:27.833392+00:00`
- **Database Catalog Verified Against:** `PostgreSQL 18.6 on x86_64-windows` (`artifacts/database-discovery/schema_inventory.json`)
- **Validation Script:** `scripts/phase1_2_1/validate_phase1_2_1.py`
- **Overall Consistency Status:** **`PASS`** (`13/13` checks passed, `0` contradictions remaining)

## 1. Summary Verification Matrix (`Check 01` – `Check 13`)

| Check ID | Validation Dimension | Status | Verified Metrics | Issues Found |
|---|---|---|---|---:|
| `check_01_node_id_consistency` | Check 01 Node Id Consistency | **`PASS`** | `evaluated_nodes=27`, `approved_mvp_nodes=24`, `blocked_nodes=1`, `future_nodes=2` | `0` |
| `check_02_relationship_id_consistency` | Check 02 Relationship Id Consistency | **`PASS`** | `evaluated_relationships=45`, `approved_mvp_relationships=42`, `blocked_relationships=1`, `future_relationships=2` | `0` |
| `check_03_source_table_existence` | Check 03 Source Table Existence | **`PASS`** | `verified_public_tables_count=40` | `0` |
| `check_04_source_column_existence` | Check 04 Source Column Existence | **`PASS`** | `verified_node_source_column_mappings=271` | `0` |
| `check_05_node_property_consistency` | Check 05 Node Property Consistency | **`PASS`** | `mvp_source_column_properties=271`, `mvp_derived_properties=2`, `mvp_business_and_derived_properties=273`, `mvp_audit_last_synced_at_properties=24`, `mvp_total_runtime_node_properties=297`, `blocked_and_future_node_properties=13` | `0` |
| `check_06_relationship_property_consistency` | Check 06 Relationship Property Consistency | **`PASS`** | `mvp_relationship_properties_total=108` | `0` |
| `check_07_tenant_ownership_consistency` | Check 07 Tenant Ownership Consistency | **`PASS`** | `global_or_pooled_labels=['User', 'Permission', 'ScheduleRoom', 'AssetCategory']`, `dual_scope_labels=['Audience']` | `0` |
| `check_08_attendance_resolution_consistency` | Check 08 Attendance Resolution Consistency | **`PASS`** | `required_status_codes_verified=['RESOLVED_BY_USER_ID', 'RESOLVED_BY_EMPLOYEE_NUMBER', 'UNRESOLVED', 'AMBIGUOUS', 'INVALID_TENANT', 'INVALID_SOURCE_REFERENCE']`, `unlinked_attendance_nodes_prohibited=True` | `0` |
| `check_09_approval_participant_consistency` | Check 09 Approval Participant Consistency | **`PASS`** | `canonical_property=sequence_order` | `0` |
| `check_10_audience_security_consistency` | Check 10 Audience Security Consistency | **`PASS`** | `system_audience_rule=is_system = true AND tenant_id IS NULL (0 member edges)`, `custom_audience_rule=is_system = false AND tenant_id = $tenant_id` | `0` |
| `check_11_fulltext_security_consistency` | Check 11 Fulltext Security Consistency | **`PASS`** | `verified_query_scenarios=14`, `verified_security_tests=20` | `0` |
| `check_12_department_membership_lifecycle` | Check 12 Department Membership Lifecycle | **`PASS`** | `active_predicate=dm.is_active = true AND dm.tenant_id = $tenant_id (dm.effective_to IS NULL)` | `0` |
| `check_13_sensitive_column_exclusion` | Check 13 Sensitive Column Exclusion | **`PASS`** | `excluded_sensitive_columns_verified=32` | `0` |

## 2. Reconciled Property Count Breakdown

| Property Category | Count |
|---|---:|
| Mapped PostgreSQL Source Column Properties on 24 Approved MVP Nodes | `271` |
| ETL-Derived Discriminator/Status Properties (`resolution_status`, `tag_scope`) | `2` |
| Subtotal Business & Derived Node Properties (`271 + 2`) | `273` |
| ETL Sync Audit Properties (`last_synced_at` across 24 MVP Node Labels) | `24` |
| **Total Runtime Properties on 24 Approved MVP Nodes (`273 + 24`)** | **`297`** |
| Mapped Relationship Properties Across 42 Approved MVP Relationships | `108` |
| Excluded Sensitive Source Columns Verified Absent from Neo4j | `32` |
