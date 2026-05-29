-- Migration: Add conversation_analyses table
-- Run this to create the table for storing daily analysis results

CREATE TABLE IF NOT EXISTS conversation_analyses (
    analysis_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    analyzed_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Analysis results (JSON format)
    analysis_json JSONB NOT NULL,

    -- Metadata
    message_count INTEGER,
    course_module VARCHAR(50),
    homework_id VARCHAR(50),

    -- Status
    status VARCHAR(50) DEFAULT 'completed'
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_analyses_session ON conversation_analyses(session_id);
CREATE INDEX IF NOT EXISTS idx_analyses_date ON conversation_analyses(analyzed_at);
CREATE INDEX IF NOT EXISTS idx_analyses_module ON conversation_analyses(course_module);

-- Query examples:

-- Get all analyses for a session
-- SELECT * FROM conversation_analyses WHERE session_id = 'xxx' ORDER BY analyzed_at DESC;

-- Get analyses from last week
-- SELECT * FROM conversation_analyses WHERE analyzed_at >= NOW() - INTERVAL '7 days';

-- Get analyses by module
-- SELECT * FROM conversation_analyses WHERE course_module = 'prog2';
