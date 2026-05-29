-- Migration: Add Authentication and Multi-Tenancy
-- Purpose: Professor Dashboard mit Course Management
-- Date: 2026-05-06

-- ============================================================
-- 1. USERS TABLE (Professoren)
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Authentication
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,

    -- Profile
    full_name VARCHAR(255),
    institution VARCHAR(255),

    -- Role & Status
    role VARCHAR(50) DEFAULT 'professor',  -- 'professor', 'admin'
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Email Verification (optional)
    email_verified BOOLEAN DEFAULT FALSE,
    verification_token TEXT,
    verification_token_expires TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

COMMENT ON TABLE users IS 'Professor accounts for dashboard access';
COMMENT ON COLUMN users.password_hash IS 'bcrypt hash with 12 rounds';
COMMENT ON COLUMN users.role IS 'professor=normal user, admin=full access';


-- ============================================================
-- 2. COURSES TABLE (Multi-Tenancy)
-- ============================================================

CREATE TABLE IF NOT EXISTS courses (
    course_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Course Identification
    course_code VARCHAR(100) NOT NULL,      -- e.g., "prog2", "introprog"
    course_name VARCHAR(255) NOT NULL,      -- e.g., "Programmieren 2"
    semester VARCHAR(50),                   -- e.g., "WS 2025/26"
    academic_year INT,                      -- e.g., 2025

    -- Ownership
    owner_user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- Settings
    is_active BOOLEAN DEFAULT TRUE,
    student_access BOOLEAN DEFAULT TRUE,    -- Can students use this course in chat?
    max_lecture_number INT,                 -- For content gating

    -- Metadata
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Ensure unique course per owner per semester
    UNIQUE(owner_user_id, course_code, semester)
);

CREATE INDEX IF NOT EXISTS idx_courses_owner ON courses(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_courses_code ON courses(course_code);
CREATE INDEX IF NOT EXISTS idx_courses_active ON courses(is_active);

COMMENT ON TABLE courses IS 'Courses managed by professors (multi-tenancy)';
COMMENT ON COLUMN courses.owner_user_id IS 'Professor who created the course';
COMMENT ON COLUMN courses.student_access IS 'Allow students to select this course in chat';


-- ============================================================
-- 3. COURSE PERMISSIONS (Multi-Professor Access)
-- ============================================================

CREATE TABLE IF NOT EXISTS course_permissions (
    permission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- Permission Level
    permission_level VARCHAR(50) NOT NULL,  -- 'owner', 'editor', 'viewer'

    -- Timestamps
    granted_at TIMESTAMP DEFAULT NOW(),
    granted_by UUID REFERENCES users(user_id),

    UNIQUE(course_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_course_permissions_course ON course_permissions(course_id);
CREATE INDEX IF NOT EXISTS idx_course_permissions_user ON course_permissions(user_id);

COMMENT ON TABLE course_permissions IS 'Shared access to courses (multiple professors per course)';
COMMENT ON COLUMN course_permissions.permission_level IS 'owner=full, editor=edit files/homework, viewer=read-only';


-- ============================================================
-- 4. HOMEWORKS TABLE (Structured Homework Management)
-- ============================================================

CREATE TABLE IF NOT EXISTS homeworks (
    homework_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,

    -- Homework Info
    homework_code VARCHAR(100) NOT NULL,    -- e.g., "ha01", "aufgabe_05"
    title VARCHAR(255),
    description TEXT,
    sequence_number INT,                    -- For ordering (1, 2, 3, ...)

    -- Dates
    start_date TIMESTAMP,
    due_date TIMESTAMP,

    -- Points/Grading (optional)
    max_points DECIMAL(5,2),

    -- Status
    is_published BOOLEAN DEFAULT FALSE,     -- Visible to students?

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by UUID REFERENCES users(user_id),

    UNIQUE(course_id, homework_code)
);

CREATE INDEX IF NOT EXISTS idx_homeworks_course ON homeworks(course_id);
CREATE INDEX IF NOT EXISTS idx_homeworks_sequence ON homeworks(course_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_homeworks_published ON homeworks(is_published);

COMMENT ON TABLE homeworks IS 'Homework assignments per course';
COMMENT ON COLUMN homeworks.is_published IS 'Only published homework visible to students';


-- ============================================================
-- 5. UPDATE EXISTING TABLES FOR MULTI-TENANCY
-- ============================================================

-- Add course_id to documents table
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS course_id UUID REFERENCES courses(course_id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_documents_course ON documents(course_id);

COMMENT ON COLUMN documents.course_id IS 'Link document to course (multi-tenancy)';


-- Add course_id to chat_sessions (optional, for analytics filtering)
ALTER TABLE chat_sessions
ADD COLUMN IF NOT EXISTS course_id UUID REFERENCES courses(course_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_chat_sessions_course ON chat_sessions(course_id);

COMMENT ON COLUMN chat_sessions.course_id IS 'Link session to course for professor analytics';


-- Add course_id to conversation_analyses
ALTER TABLE conversation_analyses
ADD COLUMN IF NOT EXISTS course_id UUID REFERENCES courses(course_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_conversation_analyses_course ON conversation_analyses(course_id);


-- Link homeworks to documents (many-to-many)
CREATE TABLE IF NOT EXISTS homework_documents (
    homework_document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    homework_id UUID NOT NULL REFERENCES homeworks(homework_id) ON DELETE CASCADE,
    doc_id UUID NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,

    -- Order within homework
    display_order INT DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(homework_id, doc_id)
);

CREATE INDEX IF NOT EXISTS idx_homework_documents_homework ON homework_documents(homework_id);
CREATE INDEX IF NOT EXISTS idx_homework_documents_doc ON homework_documents(doc_id);

COMMENT ON TABLE homework_documents IS 'Link documents to homework assignments';


-- ============================================================
-- 6. FILE UPLOAD PRE-ANALYSIS RESULTS
-- ============================================================

CREATE TABLE IF NOT EXISTS file_upload_sessions (
    upload_session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,

    -- Upload metadata
    total_files INT DEFAULT 0,
    analyzed_files INT DEFAULT 0,
    confirmed_files INT DEFAULT 0,

    -- Status
    status VARCHAR(50) DEFAULT 'analyzing',  -- 'analyzing', 'ready', 'processing', 'completed', 'failed'

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_upload_sessions_user ON file_upload_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_upload_sessions_course ON file_upload_sessions(course_id);

COMMENT ON TABLE file_upload_sessions IS 'Track file upload sessions with LLM pre-analysis';


CREATE TABLE IF NOT EXISTS file_pre_analysis (
    pre_analysis_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_session_id UUID NOT NULL REFERENCES file_upload_sessions(upload_session_id) ON DELETE CASCADE,

    -- File info
    original_filename VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT,
    file_path TEXT,                         -- Temporary S3 path before processing

    -- LLM Analysis Results
    content_type VARCHAR(50),               -- 'lecture_slides', 'homework', 'solution', 'code_impl', 'test', 'setup'
    importance VARCHAR(50),                 -- 'hoch', 'mittel', 'niedrig'
    sequence_number INT,
    analysis_reason TEXT,                   -- LLM's reasoning

    -- User Decision
    user_decision VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'keep', 'skip'

    -- If kept, link to created document
    doc_id UUID REFERENCES documents(doc_id) ON DELETE SET NULL,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_file_pre_analysis_session ON file_pre_analysis(upload_session_id);
CREATE INDEX IF NOT EXISTS idx_file_pre_analysis_decision ON file_pre_analysis(user_decision);

COMMENT ON TABLE file_pre_analysis IS 'LLM pre-analysis results for uploaded files';


-- ============================================================
-- 7. REFRESH TOKENS (for JWT)
-- ============================================================

CREATE TABLE IF NOT EXISTS refresh_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    token_hash TEXT NOT NULL,               -- SHA256 hash of token

    -- Metadata
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP,

    -- Device info (optional)
    user_agent TEXT,
    ip_address INET,

    -- Revocation
    is_revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON refresh_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires ON refresh_tokens(expires_at);

COMMENT ON TABLE refresh_tokens IS 'JWT refresh tokens for session management';


-- ============================================================
-- 8. AUDIT LOG (Optional, für Sicherheit)
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Who & When
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    timestamp TIMESTAMP DEFAULT NOW(),

    -- What
    action VARCHAR(100) NOT NULL,           -- 'login', 'create_course', 'upload_file', 'delete_document'
    resource_type VARCHAR(50),              -- 'user', 'course', 'document', 'homework'
    resource_id UUID,

    -- Details
    details JSONB,

    -- Request Info
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);

COMMENT ON TABLE audit_log IS 'Security audit log for all user actions';


-- ============================================================
-- 9. HELPER FUNCTIONS
-- ============================================================

-- Function to check if user has permission for course
CREATE OR REPLACE FUNCTION user_has_course_permission(
    p_user_id UUID,
    p_course_id UUID,
    p_required_level VARCHAR DEFAULT 'viewer'
) RETURNS BOOLEAN AS $$
DECLARE
    v_permission_level VARCHAR;
BEGIN
    -- Check if user is owner
    IF EXISTS (
        SELECT 1 FROM courses
        WHERE course_id = p_course_id
        AND owner_user_id = p_user_id
    ) THEN
        RETURN TRUE;
    END IF;

    -- Check explicit permissions
    SELECT permission_level INTO v_permission_level
    FROM course_permissions
    WHERE course_id = p_course_id
    AND user_id = p_user_id;

    IF v_permission_level IS NULL THEN
        RETURN FALSE;
    END IF;

    -- Check permission level hierarchy: owner > editor > viewer
    IF p_required_level = 'viewer' THEN
        RETURN TRUE;
    ELSIF p_required_level = 'editor' THEN
        RETURN v_permission_level IN ('owner', 'editor');
    ELSIF p_required_level = 'owner' THEN
        RETURN v_permission_level = 'owner';
    END IF;

    RETURN FALSE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION user_has_course_permission IS 'Check if user has required permission level for course';


-- ============================================================
-- 10. MATERIALIZED VIEW: Course Statistics
-- ============================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS course_statistics AS
SELECT
    c.course_id,
    c.course_code,
    c.course_name,
    c.owner_user_id,

    -- Document counts
    COUNT(DISTINCT d.doc_id) as total_documents,
    COUNT(DISTINCT CASE WHEN d.content_type = 'homework' THEN d.doc_id END) as homework_documents,
    COUNT(DISTINCT CASE WHEN d.is_solution THEN d.doc_id END) as solution_documents,

    -- Homework counts
    COUNT(DISTINCT h.homework_id) as total_homeworks,
    COUNT(DISTINCT CASE WHEN h.is_published THEN h.homework_id END) as published_homeworks,

    -- Session counts
    COUNT(DISTINCT cs.session_id) as total_sessions,
    COUNT(DISTINCT cs.cookie_id) as unique_students,

    -- Analysis counts
    COUNT(DISTINCT ca.analysis_id) as total_analyses,

    -- Last activity
    MAX(cs.last_active) as last_activity,

    -- Created
    c.created_at
FROM courses c
LEFT JOIN documents d ON c.course_id = d.course_id
LEFT JOIN homeworks h ON c.course_id = h.course_id
LEFT JOIN chat_sessions cs ON c.course_id = cs.course_id
LEFT JOIN conversation_analyses ca ON c.course_id = ca.course_id
GROUP BY c.course_id, c.course_code, c.course_name, c.owner_user_id, c.created_at;

CREATE UNIQUE INDEX IF NOT EXISTS idx_course_statistics_id ON course_statistics(course_id);

COMMENT ON MATERIALIZED VIEW course_statistics IS 'Aggregated statistics per course';

-- Refresh command: REFRESH MATERIALIZED VIEW CONCURRENTLY course_statistics;


-- ============================================================
-- 11. DEFAULT ADMIN USER (Optional)
-- ============================================================

-- Create default admin user (password: 'changeme123')
-- Password hash: bcrypt of 'changeme123' with 12 rounds
-- IMPORTANT: Change this password immediately after first login!

INSERT INTO users (email, password_hash, full_name, role, is_active, email_verified)
VALUES (
    'admin@ai-tutor.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5ztC.4YqW3yIG',  -- 'changeme123'
    'Default Admin',
    'admin',
    TRUE,
    TRUE
)
ON CONFLICT (email) DO NOTHING;

COMMENT ON TABLE users IS 'Default admin user created with email: admin@ai-tutor.local, password: changeme123 (CHANGE THIS!)';


-- ============================================================
-- MIGRATION COMPLETE
-- ============================================================

-- Summary of changes:
-- ✅ users table (professors)
-- ✅ courses table (multi-tenancy)
-- ✅ course_permissions (shared access)
-- ✅ homeworks table (structured homework)
-- ✅ homework_documents (link files to homework)
-- ✅ file_upload_sessions (upload tracking)
-- ✅ file_pre_analysis (LLM analysis results)
-- ✅ refresh_tokens (JWT session management)
-- ✅ audit_log (security tracking)
-- ✅ Updated documents, chat_sessions, conversation_analyses with course_id
-- ✅ Helper function for permission checks
-- ✅ Materialized view for course statistics
-- ✅ Default admin user

SELECT 'Migration completed successfully!' as status;
