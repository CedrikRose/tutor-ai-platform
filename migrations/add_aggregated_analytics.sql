-- Migration: Add Aggregated Analytics Tables
-- Purpose: Store structured data extracted from conversation analyses
-- Part of Phase 3: Hybrid Storage & Aggregation

-- ============================================================
-- 1. TOPICS TABLE (PostgreSQL - Quantitative)
-- ============================================================
-- Tracks which topics/concepts were covered in sessions

CREATE TABLE IF NOT EXISTS topics (
    topic_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_name VARCHAR(255) NOT NULL UNIQUE, -- e.g., "Bubblesort", "for-yield Syntax"
    category VARCHAR(100), -- e.g., "Algorithmen", "Scala-Syntax", "Datenstrukturen"
    occurrences INT DEFAULT 1, -- How many times this topic appeared
    first_seen TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP DEFAULT NOW(),

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_topics_name ON topics(topic_name);
CREATE INDEX idx_topics_category ON topics(category);


-- ============================================================
-- 2. DIFFICULTY_TYPES TABLE (PostgreSQL - Quantitative)
-- ============================================================
-- Master list of difficulty/error types

CREATE TABLE IF NOT EXISTS difficulty_types (
    difficulty_type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type_name VARCHAR(255) NOT NULL UNIQUE, -- e.g., "Syntax Error", "Logical Error"
    description TEXT,
    occurrences INT DEFAULT 1,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_difficulty_types_name ON difficulty_types(type_name);


-- ============================================================
-- 3. SESSION_DIFFICULTIES TABLE (PostgreSQL - Links)
-- ============================================================
-- Links conversation analyses to specific difficulties

CREATE TABLE IF NOT EXISTS session_difficulties (
    session_difficulty_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES conversation_analyses(analysis_id) ON DELETE CASCADE,
    difficulty_type_id UUID REFERENCES difficulty_types(difficulty_type_id),

    -- Extracted from analysis JSON
    topic VARCHAR(255), -- What topic caused difficulty
    description TEXT, -- Human-readable description
    tutor_response TEXT, -- How tutor helped

    -- Metadata
    severity VARCHAR(50), -- "low", "medium", "high" (if LLM provides it)
    resolved BOOLEAN DEFAULT FALSE, -- Did student overcome it?

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_session_difficulties_analysis ON session_difficulties(analysis_id);
CREATE INDEX idx_session_difficulties_type ON session_difficulties(difficulty_type_id);
CREATE INDEX idx_session_difficulties_topic ON session_difficulties(topic);


-- ============================================================
-- 4. FEEDBACK_ENTRIES TABLE (PostgreSQL - Structured)
-- ============================================================
-- Explicit feedback about course, prof, or tutor

CREATE TABLE IF NOT EXISTS feedback_entries (
    feedback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES conversation_analyses(analysis_id) ON DELETE CASCADE,
    session_id UUID REFERENCES chat_sessions(session_id) ON DELETE CASCADE,

    -- Feedback classification
    feedback_type VARCHAR(50) NOT NULL, -- "course", "professor", "tutor", "materials", "other"
    sentiment VARCHAR(20), -- "positive", "negative", "neutral"

    -- Content
    feedback_text TEXT NOT NULL, -- Original student quote or extracted feedback
    context TEXT, -- Additional context if needed

    -- Metadata
    course_module VARCHAR(50),
    homework_id VARCHAR(50),
    extracted_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_feedback_type ON feedback_entries(feedback_type);
CREATE INDEX idx_feedback_sentiment ON feedback_entries(sentiment);
CREATE INDEX idx_feedback_module ON feedback_entries(course_module);


-- ============================================================
-- 5. LEARNING_PROGRESS TABLE (PostgreSQL - Metrics)
-- ============================================================
-- Aggregated learning progress per student (cookie_id)

CREATE TABLE IF NOT EXISTS learning_progress (
    progress_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cookie_id VARCHAR(255) NOT NULL,
    course_module VARCHAR(50),

    -- Metrics
    total_sessions INT DEFAULT 0,
    avg_rating DECIMAL(3,2), -- Average from "gut"=3, "mittel"=2, "schwach"=1
    total_difficulties INT DEFAULT 0,
    resolved_difficulties INT DEFAULT 0,

    -- Topics covered
    topics_covered TEXT[], -- Array of topic names

    -- Time tracking
    first_session TIMESTAMP,
    last_session TIMESTAMP,

    -- Metadata
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(cookie_id, course_module)
);

CREATE INDEX idx_learning_progress_cookie ON learning_progress(cookie_id);
CREATE INDEX idx_learning_progress_module ON learning_progress(course_module);


-- ============================================================
-- 6. ERROR_PATTERNS TABLE (PostgreSQL - Aggregation)
-- ============================================================
-- Tracks recurring error patterns across all students

CREATE TABLE IF NOT EXISTS error_patterns (
    pattern_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_name VARCHAR(255) NOT NULL,
    pattern_type VARCHAR(100), -- e.g., "syntax", "logic", "conceptual"

    -- Aggregated stats
    total_occurrences INT DEFAULT 1,
    affected_students INT DEFAULT 1, -- Unique cookie_ids
    course_module VARCHAR(50),

    -- Common context
    common_topics TEXT[], -- Topics where this pattern appears
    example_description TEXT, -- Representative example

    -- Metadata
    first_seen TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP DEFAULT NOW(),
    severity_avg DECIMAL(3,2), -- Average severity if tracked

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_error_patterns_type ON error_patterns(pattern_type);
CREATE INDEX idx_error_patterns_module ON error_patterns(course_module);
CREATE INDEX idx_error_patterns_occurrences ON error_patterns(total_occurrences DESC);


-- ============================================================
-- 7. DIFFICULTY_EMBEDDINGS TABLE (pgvector - Semantic Search)
-- ============================================================
-- Vector embeddings for semantic similarity search on difficulties

CREATE TABLE IF NOT EXISTS difficulty_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_difficulty_id UUID NOT NULL REFERENCES session_difficulties(session_difficulty_id) ON DELETE CASCADE,

    -- Vector embedding (1024-dim Titan)
    embedding vector(1024) NOT NULL,
    model_id VARCHAR(100) DEFAULT 'amazon.titan-embed-text-v2:0',

    -- Text that was embedded
    embedded_text TEXT NOT NULL,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_difficulty_embeddings_vector ON difficulty_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX idx_difficulty_embeddings_session ON difficulty_embeddings(session_difficulty_id);


-- ============================================================
-- 8. FEEDBACK_EMBEDDINGS TABLE (pgvector - Semantic Search)
-- ============================================================
-- Vector embeddings for semantic similarity search on feedback

CREATE TABLE IF NOT EXISTS feedback_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feedback_id UUID NOT NULL REFERENCES feedback_entries(feedback_id) ON DELETE CASCADE,

    -- Vector embedding (1024-dim Titan)
    embedding vector(1024) NOT NULL,
    model_id VARCHAR(100) DEFAULT 'amazon.titan-embed-text-v2:0',

    -- Text that was embedded
    embedded_text TEXT NOT NULL,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_feedback_embeddings_vector ON feedback_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX idx_feedback_embeddings_feedback ON feedback_embeddings(feedback_id);


-- ============================================================
-- 9. DAILY_STATS TABLE (PostgreSQL - Time Series)
-- ============================================================
-- Daily aggregated statistics for dashboards

CREATE TABLE IF NOT EXISTS daily_stats (
    stat_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stat_date DATE NOT NULL UNIQUE,

    -- Session stats
    total_sessions INT DEFAULT 0,
    total_messages INT DEFAULT 0,
    avg_session_length DECIMAL(5,2), -- Average messages per session

    -- Analysis stats
    total_analyses INT DEFAULT 0,
    avg_rating DECIMAL(3,2),

    -- Difficulty stats
    total_difficulties INT DEFAULT 0,
    unique_difficulty_types INT DEFAULT 0,
    top_difficulty_type VARCHAR(255),

    -- Feedback stats
    total_feedback_entries INT DEFAULT 0,
    positive_feedback INT DEFAULT 0,
    negative_feedback INT DEFAULT 0,

    -- Module breakdown (JSONB for flexibility)
    module_stats JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_daily_stats_date ON daily_stats(stat_date DESC);


-- ============================================================
-- HELPER FUNCTION: Convert rating to numeric
-- ============================================================
CREATE OR REPLACE FUNCTION rating_to_numeric(rating TEXT)
RETURNS DECIMAL(3,2) AS $$
BEGIN
    RETURN CASE LOWER(rating)
        WHEN 'gut' THEN 3.0
        WHEN 'mittel' THEN 2.0
        WHEN 'schwach' THEN 1.0
        ELSE NULL
    END;
END;
$$ LANGUAGE plpgsql IMMUTABLE;


-- ============================================================
-- MATERIALIZED VIEW: Quick Stats Overview
-- ============================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics_overview AS
SELECT
    COUNT(DISTINCT ca.session_id) as total_sessions_analyzed,
    COUNT(DISTINCT cs.cookie_id) as unique_students,
    COUNT(DISTINCT ca.course_module) as active_modules,
    COUNT(sd.session_difficulty_id) as total_difficulties,
    COUNT(fe.feedback_id) as total_feedback_entries,
    AVG(rating_to_numeric(ca.analysis_json->'lernfortschritt'->>'bewertung')) as avg_rating,
    MAX(ca.analyzed_at) as last_analysis_date
FROM conversation_analyses ca
LEFT JOIN chat_sessions cs ON ca.session_id = cs.session_id
LEFT JOIN session_difficulties sd ON ca.analysis_id = sd.analysis_id
LEFT JOIN feedback_entries fe ON ca.analysis_id = fe.analysis_id;

-- Refresh command: REFRESH MATERIALIZED VIEW analytics_overview;


-- ============================================================
-- COMMENTS
-- ============================================================
COMMENT ON TABLE topics IS 'Master list of topics/concepts covered in sessions';
COMMENT ON TABLE difficulty_types IS 'Master list of difficulty/error types';
COMMENT ON TABLE session_difficulties IS 'Links analyses to specific student difficulties';
COMMENT ON TABLE feedback_entries IS 'Explicit feedback about course, prof, or tutor';
COMMENT ON TABLE learning_progress IS 'Aggregated learning progress per student';
COMMENT ON TABLE error_patterns IS 'Recurring error patterns across all students';
COMMENT ON TABLE difficulty_embeddings IS 'Vector embeddings for semantic difficulty search';
COMMENT ON TABLE feedback_embeddings IS 'Vector embeddings for semantic feedback search';
COMMENT ON TABLE daily_stats IS 'Daily aggregated statistics for dashboards';
