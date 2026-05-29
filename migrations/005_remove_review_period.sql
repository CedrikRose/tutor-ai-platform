-- Migration: Remove review period functionality from course_materials
-- Date: 2026-05-20
-- Reason: Review period feature was deprecated, materials are now processed on-demand

-- Step 1: Make review_deadline nullable (for existing data)
ALTER TABLE course_materials
    ALTER COLUMN review_deadline DROP NOT NULL;

-- Step 2: Set all existing review_deadlines to NULL (cleanup)
UPDATE course_materials
    SET review_deadline = NULL,
        pending_review = false
    WHERE review_deadline IS NOT NULL;

-- Step 3: Drop the review_deadline column (no longer needed)
ALTER TABLE course_materials
    DROP COLUMN review_deadline;

-- Step 4: Update pending_review to always be false for all materials
--         (keep column for now in case we want to use it differently later)
UPDATE course_materials
    SET pending_review = false
    WHERE pending_review = true;

-- Note: pending_review column is kept but no longer used for review period
--       It could be repurposed in the future for other pending states

-- Verification queries:
-- SELECT COUNT(*) FROM course_materials WHERE review_deadline IS NOT NULL;  -- Should error (column doesn't exist)
-- SELECT COUNT(*) FROM course_materials WHERE pending_review = true;  -- Should be 0
