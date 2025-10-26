

# Supabase Database Schema Documentation

**Last Updated**: 2025-10-19
**Database**: PostgreSQL 15 (Supabase-managed)
**Schema Version**: 1.0.0

---

## Overview

This document describes the database schema for lift-sys session storage, implemented on Supabase with Row-Level Security (RLS) for user isolation.

**Design Principles**:
- **User Isolation**: RLS policies prevent cross-user data access
- **Denormalization**: Counters cached in `sessions` table for performance
- **JSONB Flexibility**: IR and metadata stored as JSONB for schema evolution
- **Audit Trail**: Full history via revisions and drafts tables
- **Performance**: GIN indexes on JSONB columns, B-tree on foreign keys

---

## Tables

### 1. `sessions`

**Purpose**: Core table storing prompt sessions and current state

**Columns**:
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Unique session identifier |
| `user_id` | UUID | NOT NULL | Owner (for RLS isolation) |
| `status` | TEXT | NOT NULL, CHECK IN (...), DEFAULT 'active' | Current state: active, paused, finalized, error |
| `source` | TEXT | NOT NULL, CHECK IN (...), DEFAULT 'prompt' | How created: prompt (forward) or code (reverse) |
| `original_input` | TEXT | NOT NULL, CHECK length > 0 | Original prompt text or code |
| `current_ir` | JSONB | | Latest IR snapshot |
| `current_code` | TEXT | | Latest generated code |
| `revision_count` | INTEGER | NOT NULL, DEFAULT 0 | Denormalized count (auto-updated by trigger) |
| `draft_count` | INTEGER | NOT NULL, DEFAULT 0 | Denormalized count (auto-updated by trigger) |
| `hole_count` | INTEGER | NOT NULL, DEFAULT 0 | Denormalized count (auto-updated by trigger) |
| `metadata` | JSONB | DEFAULT '{}' | Additional metadata (tags, performance, etc.) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Session creation time |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Last modification (auto-updated by trigger) |
| `finalized_at` | TIMESTAMPTZ | | When session finalized (null if active) |

**Indexes**:
- `idx_sessions_user_id`: B-tree on `user_id`
- `idx_sessions_status`: B-tree on `status`
- `idx_sessions_created_at`: B-tree DESC on `created_at`
- `idx_sessions_user_status`: Composite on `(user_id, status)`
- `idx_sessions_current_ir`: GIN on `current_ir`
- `idx_sessions_metadata`: GIN on `metadata`

**RLS Policies**:
- SELECT: User can view own sessions (`auth.uid() = user_id`)
- INSERT: User can create own sessions (`auth.uid() = user_id`)
- UPDATE: User can modify own sessions
- DELETE: User can delete own sessions

---

### 2. `session_revisions`

**Purpose**: Tracks IR revision history with change tracking

**Columns**:
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique revision identifier |
| `session_id` | UUID | NOT NULL, REFERENCES sessions(id) ON DELETE CASCADE | Parent session |
| `revision_number` | INTEGER | NOT NULL, CHECK > 0 | Sequential number within session |
| `source` | TEXT | NOT NULL, CHECK IN (...) | How created: initial, refinement, repair, user_edit |
| `ir_content` | JSONB | NOT NULL | IR snapshot for this revision |
| `validation_result` | JSONB | | IR interpreter validation result |
| `changed_fields` | TEXT[] | DEFAULT ARRAY[]::TEXT[] | Which IR fields changed from previous revision |
| `change_summary` | TEXT | | Human-readable description of changes |
| `metadata` | JSONB | DEFAULT '{}' | Additional revision metadata |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Revision creation time |

**Indexes**:
- `idx_revisions_session_id`: B-tree on `session_id`
- `idx_revisions_session_revision`: Composite DESC on `(session_id, revision_number)`
- `idx_revisions_created_at`: B-tree DESC on `created_at`
- `idx_revisions_source`: B-tree on `source`
- `idx_revisions_ir_content`: GIN on `ir_content`
- `idx_revisions_metadata`: GIN on `metadata`

**Constraints**:
- UNIQUE: `(session_id, revision_number)`

**RLS Policies**:
- All operations allowed for users who own the parent session

**Triggers**:
- `trigger_revisions_count_insert`: Increment `sessions.revision_count` on INSERT
- `trigger_revisions_count_delete`: Decrement `sessions.revision_count` on DELETE

---

### 3. `session_drafts`

**Purpose**: Tracks code generation attempts with validation and performance metrics

**Columns**:
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique draft identifier |
| `session_id` | UUID | NOT NULL, REFERENCES sessions(id) ON DELETE CASCADE | Parent session |
| `ir_revision_id` | UUID | REFERENCES session_revisions(id) ON DELETE SET NULL | IR revision used to generate this draft |
| `draft_number` | INTEGER | NOT NULL, CHECK > 0 | Sequential number within session |
| `source` | TEXT | NOT NULL, CHECK IN (...) | How created: initial_generation, ast_repair, llm_regeneration, user_edit |
| `code_content` | TEXT | NOT NULL, CHECK length > 0 | Generated code |
| `language` | TEXT | NOT NULL, DEFAULT 'python' | Programming language |
| `syntax_valid` | BOOLEAN | NOT NULL, DEFAULT false | Valid syntax? |
| `ast_valid` | BOOLEAN | NOT NULL, DEFAULT false | Valid AST? |
| `validation_errors` | JSONB | DEFAULT '[]' | Syntax/AST errors |
| `generation_time_ms` | INTEGER | | Time to generate (milliseconds) |
| `validation_time_ms` | INTEGER | | Time to validate (milliseconds) |
| `llm_tokens_used` | INTEGER | | Total tokens (input + output) |
| `llm_cost_usd` | NUMERIC(10, 6) | | LLM API cost in USD |
| `metadata` | JSONB | DEFAULT '{}' | Additional draft metadata |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Draft creation time |

**Indexes**:
- `idx_drafts_session_id`: B-tree on `session_id`
- `idx_drafts_session_draft`: Composite DESC on `(session_id, draft_number)`
- `idx_drafts_ir_revision_id`: B-tree on `ir_revision_id`
- `idx_drafts_created_at`: B-tree DESC on `created_at`
- `idx_drafts_source`: B-tree on `source`
- `idx_drafts_valid`: Composite on `(syntax_valid, ast_valid)`
- `idx_drafts_validation_errors`: GIN on `validation_errors`
- `idx_drafts_metadata`: GIN on `metadata`

**Constraints**:
- UNIQUE: `(session_id, draft_number)`

**RLS Policies**:
- All operations allowed for users who own the parent session

**Triggers**:
- `trigger_drafts_count_insert`: Increment `sessions.draft_count` on INSERT
- `trigger_drafts_count_delete`: Decrement `sessions.draft_count` on DELETE

---

### 4. `hole_resolutions`

**Purpose**: Tracks typed hole resolutions during interactive refinement

**Columns**:
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique resolution identifier |
| `session_id` | UUID | NOT NULL, REFERENCES sessions(id) ON DELETE CASCADE | Parent session |
| `ir_revision_id` | UUID | REFERENCES session_revisions(id) ON DELETE SET NULL | IR revision where hole resolved |
| `hole_id` | TEXT | NOT NULL | Identifier of the hole |
| `hole_type` | TEXT | NOT NULL, CHECK IN (...) | Category: type, parameter, return_value, validation, entity, constraint, other |
| `resolution_method` | TEXT | NOT NULL, CHECK IN (...) | How resolved: user_selection, ai_suggestion, inference, default |
| `resolved_value` | JSONB | NOT NULL | Final value/type for this hole |
| `confidence_score` | NUMERIC(3, 2) | CHECK BETWEEN 0 AND 1 | Confidence in resolution (0-1) |
| `original_hole_data` | JSONB | | Snapshot of hole before resolution |
| `suggestions_provided` | JSONB | DEFAULT '[]' | AI suggestions shown to user |
| `user_feedback` | TEXT | | User comments about this resolution |
| `metadata` | JSONB | DEFAULT '{}' | Additional resolution metadata |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Resolution time |

**Indexes**:
- `idx_resolutions_session_id`: B-tree on `session_id`
- `idx_resolutions_ir_revision_id`: B-tree on `ir_revision_id`
- `idx_resolutions_hole_type`: B-tree on `hole_type`
- `idx_resolutions_resolution_method`: B-tree on `resolution_method`
- `idx_resolutions_created_at`: B-tree DESC on `created_at`
- `idx_resolutions_resolved_value`: GIN on `resolved_value`
- `idx_resolutions_original_data`: GIN on `original_hole_data`
- `idx_resolutions_suggestions`: GIN on `suggestions_provided`
- `idx_resolutions_metadata`: GIN on `metadata`

**Constraints**:
- UNIQUE: `(session_id, ir_revision_id, hole_id)`

**RLS Policies**:
- All operations allowed for users who own the parent session

**Triggers**:
- `trigger_resolutions_count_insert`: Update `sessions.hole_count` on INSERT
- `trigger_resolutions_count_delete`: Update `sessions.hole_count` on DELETE

---

## Views

### 1. `session_summary`

**Purpose**: Aggregated session metrics for dashboards

**Columns**: Session fields + computed aggregates:
- `latest_revision_number`: Latest revision number
- `latest_draft_number`: Latest draft number
- `latest_draft_valid`: Whether latest draft passed validation
- `total_generation_time_ms`: Sum of all draft generation times
- `total_llm_cost_usd`: Total LLM API cost for session
- `total_llm_tokens_used`: Total tokens consumed
- `session_duration_seconds`: updated_at - created_at
- `time_to_finalization_seconds`: finalized_at - created_at

**Usage**:
```sql
SELECT * FROM session_summary WHERE user_id = <uuid> ORDER BY created_at DESC;
```

---

### 2. `user_analytics`

**Purpose**: Per-user aggregate metrics for usage tracking

**Columns**:
- `user_id`: User identifier
- `total_sessions`: Count of all sessions
- `finalized_sessions`: Count of finalized sessions
- `active_sessions`: Count of active sessions
- `error_sessions`: Count of error sessions
- `total_revisions`: Sum across all sessions
- `total_drafts`: Sum across all sessions
- `avg_revisions_per_session`: Average revisions
- `avg_drafts_per_session`: Average drafts
- `first_session_at`: First session timestamp
- `last_session_at`: Latest session timestamp
- `total_llm_cost_usd`: Total LLM cost
- `total_llm_tokens_used`: Total tokens
- `avg_time_to_finalization_seconds`: Average time to finalize

**Usage**:
```sql
SELECT * FROM user_analytics WHERE user_id = <uuid>;
```

---

### 3. `recent_activity`

**Purpose**: Unified activity feed for timeline views

**Columns**:
- `event_type`: 'session_created' | 'revision_created' | 'draft_created' | 'hole_resolved'
- `session_id`: Session identifier
- `user_id`: User identifier
- `revision_id`: Revision ID (if applicable)
- `draft_id`: Draft ID (if applicable)
- `resolution_id`: Resolution ID (if applicable)
- `event_time`: Event timestamp
- `event_data`: JSONB with event-specific fields

**Usage**:
```sql
SELECT * FROM recent_activity WHERE user_id = <uuid> ORDER BY event_time DESC LIMIT 50;
```

---

### 4. `draft_validation_stats`

**Purpose**: Code generation success rates and performance

**Columns**:
- `session_id`: Session identifier
- `user_id`: User identifier
- `total_drafts`: Count of drafts
- `syntax_valid_count`: Count with valid syntax
- `ast_valid_count`: Count with valid AST
- `fully_valid_count`: Count with both valid
- `syntax_valid_percent`: Percentage
- `ast_valid_percent`: Percentage
- `fully_valid_percent`: Percentage
- `avg_generation_time_ms`: Average generation time
- `avg_validation_time_ms`: Average validation time
- `total_llm_cost_usd`: Total LLM cost

**Usage**:
```sql
SELECT * FROM draft_validation_stats WHERE user_id = <uuid>;
```

---

## Triggers

### 1. `trigger_sessions_updated_at`

**Table**: `sessions`
**Event**: BEFORE UPDATE
**Function**: `update_updated_at_column()`
**Purpose**: Automatically set `updated_at = NOW()` on modification

---

### 2. `trigger_revisions_count_insert/delete`

**Table**: `session_revisions`
**Events**: AFTER INSERT, AFTER DELETE
**Function**: `update_session_revision_count()`
**Purpose**: Maintain denormalized `sessions.revision_count`

---

### 3. `trigger_drafts_count_insert/delete`

**Table**: `session_drafts`
**Events**: AFTER INSERT, AFTER DELETE
**Function**: `update_session_draft_count()`
**Purpose**: Maintain denormalized `sessions.draft_count`

---

### 4. `trigger_resolutions_count_insert/delete`

**Table**: `hole_resolutions`
**Events**: AFTER INSERT, AFTER DELETE
**Function**: `update_session_hole_count()`
**Purpose**: Maintain denormalized `sessions.hole_count`

---

## Row-Level Security (RLS)

**All tables** have RLS enabled with policies enforcing user isolation via `auth.uid()`.

**Policy Pattern**:
```sql
-- SELECT: User can view own data
CREATE POLICY "Users can view their own <table>"
    ON <table>
    FOR SELECT
    USING (auth.uid() = user_id);  -- Or via session_id JOIN

-- INSERT: User can create own data
CREATE POLICY "Users can insert their own <table>"
    ON <table>
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- UPDATE: User can modify own data
CREATE POLICY "Users can update their own <table>"
    ON <table>
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- DELETE: User can delete own data
CREATE POLICY "Users can delete their own <table>"
    ON <table>
    FOR DELETE
    USING (auth.uid() = user_id);
```

**Service Role Bypass**:
- The `service_role` key bypasses RLS entirely
- Use for backend operations, analytics, admin tasks
- Modal API uses `service_role` when operating on user data with auth context

---

## Indexes

**B-tree indexes** for:
- Primary keys (automatic)
- Foreign keys (`session_id`, `ir_revision_id`)
- Timestamp columns (`created_at`, `updated_at`)
- Enum-like columns (`status`, `source`, `hole_type`)
- Composite indexes for common query patterns

**GIN indexes** for:
- JSONB columns (`current_ir`, `ir_content`, `metadata`)
- Array columns (`changed_fields`)

**Performance Considerations**:
- GIN indexes increase write overhead but dramatically speed up JSONB queries
- Composite indexes on `(user_id, status)` optimize dashboard queries
- Descending indexes on timestamps optimize `ORDER BY created_at DESC LIMIT N`

---

## Common Queries

### Get user's active sessions
```sql
SELECT * FROM sessions
WHERE user_id = <uuid>
AND status = 'active'
ORDER BY updated_at DESC;
```

### Get session with latest revision and draft
```sql
SELECT
    s.*,
    (SELECT ir_content FROM session_revisions WHERE session_id = s.id ORDER BY revision_number DESC LIMIT 1) AS latest_ir,
    (SELECT code_content FROM session_drafts WHERE session_id = s.id ORDER BY draft_number DESC LIMIT 1) AS latest_code
FROM sessions s
WHERE id = <session_id>;
```

### Get session activity timeline
```sql
SELECT * FROM recent_activity
WHERE session_id = <session_id>
ORDER BY event_time ASC;
```

### Get user's cost and token usage
```sql
SELECT
    total_llm_cost_usd,
    total_llm_tokens_used,
    total_sessions
FROM user_analytics
WHERE user_id = <uuid>;
```

### Get validation success rate for user
```sql
SELECT
    AVG(fully_valid_percent) AS avg_success_rate,
    SUM(total_drafts) AS total_attempts
FROM draft_validation_stats
WHERE user_id = <uuid>;
```

---

## Migration Files

1. **001_create_sessions_table.sql**: Core sessions table
2. **002_create_revisions_table.sql**: IR revision history
3. **003_create_drafts_table.sql**: Code draft tracking
4. **004_create_resolutions_table.sql**: Hole resolution tracking
5. **005_create_rls_policies.sql**: Row-Level Security policies
6. **006_create_triggers.sql**: Auto-update triggers
7. **007_create_views.sql**: Aggregated views

**Run all migrations**:
```bash
./migrations/run_all_migrations.sh "postgresql://postgres:PASSWORD@db.xxxxx.supabase.co:5432/postgres"
```

---

## Maintenance

### Backup Strategy
- Supabase provides automated daily backups (7-day retention on free tier)
- Point-in-time recovery available on Pro tier
- Export critical data to R2/S3 for long-term retention

### Monitoring
- Watch table sizes with `pg_total_relation_size()`
- Monitor slow queries with `pg_stat_statements`
- Track RLS policy hits with Supabase dashboard

### Performance Tuning
- Vacuum analyze weekly: `VACUUM ANALYZE sessions;`
- Reindex JSONB columns if fragmented
- Consider partitioning `session_drafts` by date if >1M rows

---

## Security Considerations

1. **RLS Enforcement**: Always use `anon` key for client-side queries
2. **Service Role**: Only use `service_role` in secure backend environments
3. **SQL Injection**: Use parameterized queries, never string concatenation
4. **Data Exposure**: JSONB columns may contain sensitive data - apply encryption if needed
5. **Audit Logging**: Enable Supabase audit logs for compliance

---

## References

- Supabase RLS Guide: https://supabase.com/docs/guides/auth/row-level-security
- PostgreSQL JSONB: https://www.postgresql.org/docs/current/datatype-json.html
- GIN Indexes: https://www.postgresql.org/docs/current/gin-intro.html
- Trigger Functions: https://www.postgresql.org/docs/current/plpgsql-trigger.html

---

**Schema Version**: 1.0.0
**Last Updated**: 2025-10-19
**Maintainer**: lift-sys engineering team
