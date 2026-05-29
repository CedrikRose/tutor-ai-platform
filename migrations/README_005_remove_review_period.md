# Migration 005: Remove Review Period Feature

**Date:** 2026-05-20  
**Status:** Ready to apply

## Problem

The `course_materials` table had a `review_deadline` column with `NOT NULL` constraint, but the newer API code (`api/professor_material_api.py`) was setting it to `NULL`, causing database constraint violations:

```
sqlalchemy.exc.IntegrityError: (psycopg2.errors.NotNullViolation) 
null value in column "review_deadline" of relation "course_materials" violates not-null constraint
```

## Root Cause

There were **two different upload endpoints** with conflicting logic:

1. **Old endpoint** (`api/professor.py`): Set review period with `review_deadline = now() + 10 minutes`
2. **New endpoint** (`api/professor_material_api.py`): No review period, `review_deadline = NULL`

The review period feature was deprecated but not cleanly removed from:
- Database schema (column still `NOT NULL`)
- Background processor (`material_processor.py` still checking for expired deadlines)

## Solution

Completely remove the review period feature:

1. **Database**: Drop `review_deadline` column entirely
2. **API**: Remove `review_deadline` from response models
3. **Processor**: Disable automatic processing (materials now processed on-demand)
4. **Frontend**: Already handles nullable review_deadline, no changes needed

## Changes Made

### 1. Database Schema (`database.py`)
```python
# BEFORE
review_deadline = Column(TIMESTAMP, nullable=False)

# AFTER
# Column removed entirely
```

### 2. API Endpoints
- `/api/courses/{course_id}/materials/upload` (both files)
  - Removed `review_deadline` from response
  - Set `pending_review = False` (no automatic processing)

### 3. Material Processor (`material_processor.py`)
- `process_pending_materials()` now does nothing (deprecated)
- Materials processed on-demand via `/api/materials/{material_id}/process`

## Migration Steps

### On Server (AWS)

1. **Backup database:**
   ```bash
   ssh your-server
   docker exec ai-tutor-backend-1 pg_dump -U ai_tutor ai_tutor > backup_before_migration_005.sql
   ```

2. **Apply migration:**
   ```bash
   # Copy migration file to server
   scp migrations/005_remove_review_period.sql your-server:~/

   # Apply it
   ssh your-server
   docker exec -i ai-tutor-backend-1 psql -U ai_tutor -d ai_tutor < ~/005_remove_review_period.sql
   ```

3. **Verify:**
   ```bash
   docker exec ai-tutor-backend-1 psql -U ai_tutor -d ai_tutor -c "\d course_materials"
   # Should NOT show review_deadline column
   ```

4. **Deploy updated code:**
   ```bash
   cd /path/to/AI-Tutor
   git pull
   docker-compose down
   docker-compose up -d --build
   ```

### Locally

1. **If you have local DB with data:**
   ```bash
   psql -U ai_tutor -d ai_tutor_dev -f migrations/005_remove_review_period.sql
   ```

2. **If starting fresh:**
   - Delete old DB
   - Run `python -c "from database import init_db; init_db()"`
   - New schema already has review_deadline removed

## Verification

After migration, check:

```sql
-- Should error (column doesn't exist)
SELECT review_deadline FROM course_materials LIMIT 1;

-- Should return 0
SELECT COUNT(*) FROM course_materials WHERE pending_review = true;

-- Should work
SELECT material_id, display_name, processed_at FROM course_materials;
```

## Rollback (if needed)

If you need to rollback:

```sql
-- Add column back (but DON'T use it!)
ALTER TABLE course_materials 
    ADD COLUMN review_deadline TIMESTAMP NULL;

-- Restore from backup
-- psql -U ai_tutor -d ai_tutor < backup_before_migration_005.sql
```

## Notes

- `pending_review` column kept for future use (always false for now)
- Frontend already handles nullable review_deadline, no frontend changes needed
- Cron jobs that called `process_pending_materials()` will do nothing now (safe)
