-- Migration: Add report settings and course_reports table
-- Created: 2026-05-28
-- Description: Adds report functionality to courses and creates reports table

-- ============================================================
-- 1. Extend courses table with report settings
-- ============================================================

DO $$
BEGIN
    -- Add report_days_back column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'courses' AND column_name = 'report_days_back'
    ) THEN
        ALTER TABLE courses
        ADD COLUMN report_days_back INTEGER DEFAULT 7 CHECK (report_days_back >= 1 AND report_days_back <= 50);
    END IF;

    -- Add report_recipient_emails column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'courses' AND column_name = 'report_recipient_emails'
    ) THEN
        ALTER TABLE courses
        ADD COLUMN report_recipient_emails VARCHAR[] DEFAULT ARRAY[]::VARCHAR[];
    END IF;

    -- Add report_emails_enabled column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'courses' AND column_name = 'report_emails_enabled'
    ) THEN
        ALTER TABLE courses
        ADD COLUMN report_emails_enabled BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- ============================================================
-- 2. Create course_reports table
-- ============================================================

CREATE TABLE IF NOT EXISTS course_reports (
    report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,

    -- Zeitraum
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    days_back INTEGER NOT NULL,

    -- Bericht-Inhalt
    report_text TEXT NOT NULL,

    -- Verwendete Erkenntnisse
    finding_ids UUID[] NOT NULL,

    -- Metadaten
    generated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    generated_by UUID REFERENCES users(user_id),

    -- Statistiken (optional)
    statistics JSONB
);

-- ============================================================
-- 3. Create indexes for performance
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_course_reports_course ON course_reports(course_id);
CREATE INDEX IF NOT EXISTS idx_course_reports_date ON course_reports(end_date DESC);
CREATE INDEX IF NOT EXISTS idx_course_reports_generated ON course_reports(generated_at DESC);

-- ============================================================
-- MIGRATION COMPLETE
-- ============================================================

SELECT 'Report settings migration completed!' as status;
