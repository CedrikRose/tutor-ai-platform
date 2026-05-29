-- ============================================================
-- Migration: New Chat Structure (Frage+Antwort Paare)
-- ============================================================
-- This migration creates the new chat structure where:
-- 1. Conversations are only created when first message is sent
-- 2. Question + Answer are stored together as atomic exchanges
-- 3. Each exchange tracks which course/material was used
-- 4. Each exchange has an analyzed flag for daily analysis tracking

-- ============================================================
-- NEW TABLES
-- ============================================================

-- Conversations (replaces chat_sessions)
CREATE TABLE chat_conversations (
    conversation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cookie_id VARCHAR(255) NOT NULL,

    -- Auto-generated title from first question
    title VARCHAR(255) NOT NULL,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_active TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Totals
    exchange_count INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,

    -- Indexes
    CONSTRAINT chat_conversations_cookie_id_idx UNIQUE (cookie_id, conversation_id)
);

CREATE INDEX idx_chat_conversations_cookie ON chat_conversations(cookie_id);
CREATE INDEX idx_chat_conversations_last_active ON chat_conversations(last_active DESC);


-- Chat Exchanges (Frage + Antwort als atomare Einheit)
CREATE TABLE chat_exchanges (
    exchange_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES chat_conversations(conversation_id) ON DELETE CASCADE,

    -- Position in conversation
    exchange_number INTEGER NOT NULL,

    -- Content
    user_question TEXT NOT NULL,
    assistant_answer TEXT NOT NULL,

    -- Course context (was active when this question was asked)
    course_id UUID REFERENCES courses(course_id) ON DELETE SET NULL,

    -- Material filters (what was selected when asking)
    max_lecture_sequence INTEGER,  -- Max lecture to include (NULL = all)
    material_types JSONB,  -- ["homework", "tutorium", "other"] (NULL = all, lecture_slide always included)
    selected_material_id UUID REFERENCES course_materials(material_id) ON DELETE SET NULL,  -- Specific material loaded

    -- RAG context (references to chunks used, NOT the content itself!)
    rag_chunk_ids UUID[],  -- Array of chunk IDs from material_chunks
    rag_metadata JSONB,  -- [{chunk_id, file_name, distance, material_name}]

    -- Tokens
    tokens_used INTEGER,

    -- Analysis tracking
    analyzed BOOLEAN NOT NULL DEFAULT FALSE,  -- Has this exchange been analyzed?
    analyzed_at TIMESTAMP,

    -- Timestamp
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chat_exchanges_unique_number UNIQUE (conversation_id, exchange_number)
);

CREATE INDEX idx_chat_exchanges_conversation ON chat_exchanges(conversation_id, exchange_number);
CREATE INDEX idx_chat_exchanges_course ON chat_exchanges(course_id);
CREATE INDEX idx_chat_exchanges_analyzed ON chat_exchanges(analyzed) WHERE analyzed = FALSE;
CREATE INDEX idx_chat_exchanges_timestamp ON chat_exchanges(timestamp);


-- Conversation Snapshots (updated to reference exchanges instead of messages)
CREATE TABLE chat_snapshots_v2 (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES chat_conversations(conversation_id) ON DELETE CASCADE,

    -- Date of snapshot (created at 4 AM)
    snapshot_date DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Range of exchanges included
    from_exchange_number INTEGER NOT NULL,
    to_exchange_number INTEGER NOT NULL,
    exchange_count INTEGER NOT NULL,

    -- Formatted content for analysis
    chat_content TEXT NOT NULL,

    -- Metadata
    course_id UUID REFERENCES courses(course_id) ON DELETE SET NULL,
    cookie_id VARCHAR(255) NOT NULL,

    -- Analysis status
    analysis_status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, analyzing, completed, error
    analyzed_at TIMESTAMP,

    CONSTRAINT chat_snapshots_v2_unique UNIQUE (conversation_id, snapshot_date)
);

CREATE INDEX idx_chat_snapshots_v2_conversation ON chat_snapshots_v2(conversation_id);
CREATE INDEX idx_chat_snapshots_v2_date ON chat_snapshots_v2(snapshot_date);
CREATE INDEX idx_chat_snapshots_v2_status ON chat_snapshots_v2(analysis_status);
CREATE INDEX idx_chat_snapshots_v2_course ON chat_snapshots_v2(course_id);


-- Conversation Analyses (updated to reference chat_snapshots_v2)
CREATE TABLE conversation_analyses_v2 (
    analysis_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_id UUID NOT NULL REFERENCES chat_snapshots_v2(snapshot_id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES chat_conversations(conversation_id) ON DELETE CASCADE,
    analyzed_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Analysis metadata
    primary_model VARCHAR(100) NOT NULL,
    secondary_model VARCHAR(100),
    required_secondary BOOLEAN NOT NULL DEFAULT FALSE,

    -- Analysis results (full text from LLM)
    analysis_text TEXT NOT NULL,

    -- Metadata
    exchange_count INTEGER,
    course_id UUID REFERENCES courses(course_id),
    tokens_used INTEGER,

    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'completed'  -- completed, error, skipped
);

CREATE INDEX idx_analyses_v2_snapshot ON conversation_analyses_v2(snapshot_id);
CREATE INDEX idx_analyses_v2_conversation ON conversation_analyses_v2(conversation_id);
CREATE INDEX idx_analyses_v2_date ON conversation_analyses_v2(analyzed_at);
CREATE INDEX idx_analyses_v2_course ON conversation_analyses_v2(course_id);


-- Student Knowledge (updated to reference exchanges instead of messages)
CREATE TABLE student_knowledge_v2 (
    knowledge_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES conversation_analyses_v2(analysis_id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES chat_conversations(conversation_id) ON DELETE CASCADE,
    cookie_id VARCHAR(255) NOT NULL,

    -- What student could do
    understood_concepts TEXT[],

    -- What student struggled with
    struggled_concept VARCHAR(255) NOT NULL,
    error_description TEXT NOT NULL,
    solution_description TEXT NOT NULL,

    -- Reference to exchanges (not individual messages!)
    reference_exchange_numbers INTEGER[],  -- e.g., [3, 5] means exchanges 3 and 5

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_student_knowledge_v2_analysis ON student_knowledge_v2(analysis_id);
CREATE INDEX idx_student_knowledge_v2_cookie ON student_knowledge_v2(cookie_id);
CREATE INDEX idx_student_knowledge_v2_concept ON student_knowledge_v2(struggled_concept);


-- General Feedback (updated to reference exchanges)
CREATE TABLE general_feedback_v2 (
    feedback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES conversation_analyses_v2(analysis_id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES chat_conversations(conversation_id) ON DELETE CASCADE,

    -- Feedback type and content
    feedback_type VARCHAR(50) NOT NULL,  -- 'professor_explanation', 'tutor_behavior', 'material_quality', 'other'
    feedback_text TEXT NOT NULL,
    sentiment VARCHAR(20),  -- positive, negative, neutral

    -- Reference to exchanges
    reference_exchange_numbers INTEGER[],

    -- Metadata
    course_id UUID REFERENCES courses(course_id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_general_feedback_v2_analysis ON general_feedback_v2(analysis_id);
CREATE INDEX idx_general_feedback_v2_type ON general_feedback_v2(feedback_type);
CREATE INDEX idx_general_feedback_v2_course ON general_feedback_v2(course_id);


-- ============================================================
-- MIGRATION SCRIPT (OLD → NEW)
-- ============================================================

-- Function to migrate existing chat_sessions to chat_conversations
CREATE OR REPLACE FUNCTION migrate_chat_sessions_to_conversations()
RETURNS TABLE (
    old_session_id UUID,
    new_conversation_id UUID,
    exchanges_migrated INTEGER
) AS $$
DECLARE
    session_record RECORD;
    conv_id UUID;
    exchange_num INTEGER;
    user_msg RECORD;
    assistant_msg RECORD;
    exchanges_count INTEGER;
BEGIN
    -- Loop through all chat_sessions with at least 1 message
    FOR session_record IN
        SELECT cs.*, COUNT(cm.message_id) as msg_count
        FROM chat_sessions cs
        JOIN chat_messages cm ON cm.session_id = cs.session_id
        GROUP BY cs.session_id
        HAVING COUNT(cm.message_id) > 0
    LOOP
        -- Create new conversation
        INSERT INTO chat_conversations (
            cookie_id,
            title,
            created_at,
            last_active,
            exchange_count,
            total_tokens
        ) VALUES (
            session_record.cookie_id,
            COALESCE(session_record.title, 'Migrated Chat'),
            session_record.created_at,
            session_record.last_active,
            0,  -- Will be updated
            session_record.total_tokens
        ) RETURNING conversation_id INTO conv_id;

        -- Pair up user + assistant messages into exchanges
        exchange_num := 1;
        exchanges_count := 0;

        -- Get all user messages ordered by timestamp
        FOR user_msg IN
            SELECT * FROM chat_messages
            WHERE session_id = session_record.session_id
              AND role = 'user'
            ORDER BY timestamp ASC
        LOOP
            -- Find corresponding assistant message (next one after this user message)
            SELECT * INTO assistant_msg
            FROM chat_messages
            WHERE session_id = session_record.session_id
              AND role = 'assistant'
              AND timestamp > user_msg.timestamp
            ORDER BY timestamp ASC
            LIMIT 1;

            -- Only create exchange if we have both user and assistant
            IF FOUND THEN
                -- Extract chunk IDs from rag_chunks JSONB
                INSERT INTO chat_exchanges (
                    conversation_id,
                    exchange_number,
                    user_question,
                    assistant_answer,
                    course_id,
                    max_lecture_sequence,
                    material_types,
                    selected_material_id,
                    rag_chunk_ids,
                    rag_metadata,
                    tokens_used,
                    analyzed,
                    timestamp
                ) VALUES (
                    conv_id,
                    exchange_num,
                    user_msg.content,
                    assistant_msg.content,
                    session_record.course_id,
                    session_record.max_lecture_sequence,
                    session_record.material_types,
                    session_record.selected_material_id,
                    -- Extract chunk_id from JSONB array
                    (SELECT ARRAY_AGG((elem->>'chunk_id')::UUID)
                     FROM jsonb_array_elements(COALESCE(assistant_msg.rag_chunks, '[]'::jsonb)) elem),
                    assistant_msg.rag_chunks,
                    assistant_msg.tokens_used,
                    FALSE,  -- Not yet analyzed in new system
                    user_msg.timestamp
                );

                exchange_num := exchange_num + 1;
                exchanges_count := exchanges_count + 1;
            END IF;
        END LOOP;

        -- Update exchange_count
        UPDATE chat_conversations
        SET exchange_count = exchanges_count
        WHERE conversation_id = conv_id;

        -- Return migration info
        old_session_id := session_record.session_id;
        new_conversation_id := conv_id;
        exchanges_migrated := exchanges_count;
        RETURN NEXT;
    END LOOP;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- HELPER VIEWS
-- ============================================================

-- View to get all unanalyzed exchanges
CREATE VIEW unanalyzed_exchanges AS
SELECT
    ce.*,
    cc.cookie_id,
    cc.title as conversation_title
FROM chat_exchanges ce
JOIN chat_conversations cc ON ce.conversation_id = cc.conversation_id
WHERE ce.analyzed = FALSE
ORDER BY ce.timestamp ASC;


-- View to get conversation summary with exchange count per course
CREATE VIEW conversation_summary AS
SELECT
    cc.conversation_id,
    cc.cookie_id,
    cc.title,
    cc.exchange_count,
    cc.total_tokens,
    cc.created_at,
    cc.last_active,
    COUNT(DISTINCT ce.course_id) as courses_used,
    ARRAY_AGG(DISTINCT ce.course_id) FILTER (WHERE ce.course_id IS NOT NULL) as course_ids
FROM chat_conversations cc
LEFT JOIN chat_exchanges ce ON ce.conversation_id = cc.conversation_id
GROUP BY cc.conversation_id;


-- ============================================================
-- COMMENTS
-- ============================================================

COMMENT ON TABLE chat_conversations IS 'Chat conversations - created only when first message is sent';
COMMENT ON TABLE chat_exchanges IS 'Question + Answer pairs with course context and analysis tracking';
COMMENT ON COLUMN chat_exchanges.exchange_number IS 'Sequential number starting at 1 for each conversation';
COMMENT ON COLUMN chat_exchanges.analyzed IS 'FALSE until daily analysis processes this exchange';
COMMENT ON COLUMN chat_exchanges.rag_chunk_ids IS 'Array of UUIDs referencing material_chunks - NO content duplication!';
COMMENT ON COLUMN chat_exchanges.course_id IS 'Which course was selected when this question was asked - can change per exchange!';
