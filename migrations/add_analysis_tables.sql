-- Migration: Add chat analysis tables
-- Created: 2026-05-18
-- Description: Adds tables for daily chat analysis at 4 AM

-- Chat Snapshots (content captured at 4 AM for analysis)
CREATE TABLE IF NOT EXISTS chat_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Message range
    from_message_id UUID NOT NULL,
    to_message_id UUID NOT NULL,
    message_count INTEGER NOT NULL,

    -- Content
    chat_content TEXT NOT NULL,

    -- Metadata
    course_id UUID REFERENCES courses(course_id),
    cookie_id VARCHAR(255) NOT NULL,

    -- Analysis status
    analysis_status VARCHAR(50) DEFAULT 'pending',
    analyzed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_snapshots_session ON chat_snapshots(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_snapshots_date ON chat_snapshots(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_chat_snapshots_status ON chat_snapshots(analysis_status);
CREATE INDEX IF NOT EXISTS idx_chat_snapshots_course ON chat_snapshots(course_id);

-- Student Knowledge (what student understood/struggled with)
CREATE TABLE IF NOT EXISTS student_knowledge (
    knowledge_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES conversation_analyses(analysis_id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    cookie_id VARCHAR(255) NOT NULL,

    -- Knowledge state
    understood_concepts TEXT[],
    struggled_concept VARCHAR(255) NOT NULL,
    error_description TEXT NOT NULL,
    solution_description TEXT NOT NULL,

    -- Message references
    reference_message_ids UUID[],

    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_student_knowledge_analysis ON student_knowledge(analysis_id);
CREATE INDEX IF NOT EXISTS idx_student_knowledge_cookie ON student_knowledge(cookie_id);
CREATE INDEX IF NOT EXISTS idx_student_knowledge_concept ON student_knowledge(struggled_concept);

-- General Feedback (about professor, tutor, materials)
CREATE TABLE IF NOT EXISTS general_feedback (
    feedback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES conversation_analyses(analysis_id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,

    -- Feedback
    feedback_type VARCHAR(50) NOT NULL,
    feedback_text TEXT NOT NULL,
    sentiment VARCHAR(20),

    -- Message references
    reference_message_ids UUID[],

    -- Metadata
    course_id UUID REFERENCES courses(course_id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_general_feedback_analysis ON general_feedback(analysis_id);
CREATE INDEX IF NOT EXISTS idx_general_feedback_type ON general_feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_general_feedback_course ON general_feedback(course_id);

-- Update conversation_analyses table to use snapshots
-- Drop old indexes if they exist
DROP INDEX IF EXISTS idx_analyses_session;
DROP INDEX IF EXISTS idx_analyses_date;
DROP INDEX IF EXISTS idx_analyses_module;

-- Add new columns if not exists
DO $$
BEGIN
    -- Add snapshot_id
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversation_analyses' AND column_name = 'snapshot_id'
    ) THEN
        ALTER TABLE conversation_analyses
        ADD COLUMN snapshot_id UUID REFERENCES chat_snapshots(snapshot_id) ON DELETE CASCADE;
    END IF;

    -- Add primary_model
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversation_analyses' AND column_name = 'primary_model'
    ) THEN
        ALTER TABLE conversation_analyses
        ADD COLUMN primary_model VARCHAR(100);
    END IF;

    -- Add secondary_model
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversation_analyses' AND column_name = 'secondary_model'
    ) THEN
        ALTER TABLE conversation_analyses
        ADD COLUMN secondary_model VARCHAR(100);
    END IF;

    -- Add required_secondary
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversation_analyses' AND column_name = 'required_secondary'
    ) THEN
        ALTER TABLE conversation_analyses
        ADD COLUMN required_secondary BOOLEAN DEFAULT FALSE;
    END IF;

    -- Rename analysis_json to analysis_text if it's JSONB
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversation_analyses'
        AND column_name = 'analysis_json'
    ) THEN
        ALTER TABLE conversation_analyses
        RENAME COLUMN analysis_json TO analysis_text;

        -- Change type to TEXT if needed
        ALTER TABLE conversation_analyses
        ALTER COLUMN analysis_text TYPE TEXT;
    END IF;

    -- Add analysis_text if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversation_analyses' AND column_name = 'analysis_text'
    ) THEN
        ALTER TABLE conversation_analyses
        ADD COLUMN analysis_text TEXT;
    END IF;

    -- Add course_id
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversation_analyses' AND column_name = 'course_id'
    ) THEN
        ALTER TABLE conversation_analyses
        ADD COLUMN course_id UUID REFERENCES courses(course_id);
    END IF;

    -- Add tokens_used
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversation_analyses' AND column_name = 'tokens_used'
    ) THEN
        ALTER TABLE conversation_analyses
        ADD COLUMN tokens_used INTEGER;
    END IF;
END $$;

-- Create new indexes
CREATE INDEX IF NOT EXISTS idx_analyses_snapshot ON conversation_analyses(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_analyses_session ON conversation_analyses(session_id);
CREATE INDEX IF NOT EXISTS idx_analyses_date ON conversation_analyses(analyzed_at);
CREATE INDEX IF NOT EXISTS idx_analyses_course ON conversation_analyses(course_id);

-- Drop old columns if they exist (backward compatibility)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversation_analyses' AND column_name = 'course_module'
    ) THEN
        ALTER TABLE conversation_analyses DROP COLUMN IF EXISTS course_module;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversation_analyses' AND column_name = 'homework_id'
    ) THEN
        ALTER TABLE conversation_analyses DROP COLUMN IF EXISTS homework_id;
    END IF;
END $$;
