-- ============================================================
-- FRESH START MIGRATION FOR AI TUTOR
-- Date: 2026-05-06
-- ============================================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 1. USERS TABLE
-- ============================================================

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(255),
    institution VARCHAR(255),
    role VARCHAR(50) DEFAULT 'professor',
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    verification_token TEXT,
    verification_token_expires TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- ============================================================
-- 2. COURSES TABLE
-- ============================================================

CREATE TABLE courses (
    course_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_code VARCHAR(100) NOT NULL,
    course_name VARCHAR(255) NOT NULL,
    semester VARCHAR(50),
    academic_year INT,
    owner_user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT TRUE,
    student_access BOOLEAN DEFAULT TRUE,
    max_lecture_number INT,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(owner_user_id, course_code, semester)
);

CREATE INDEX idx_courses_owner ON courses(owner_user_id);
CREATE INDEX idx_courses_code ON courses(course_code);

-- ============================================================
-- 3. COURSE PERMISSIONS
-- ============================================================

CREATE TABLE course_permissions (
    permission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    permission_level VARCHAR(50) NOT NULL,
    granted_at TIMESTAMP DEFAULT NOW(),
    granted_by UUID REFERENCES users(user_id),
    UNIQUE(course_id, user_id)
);

CREATE INDEX idx_course_permissions_course ON course_permissions(course_id);
CREATE INDEX idx_course_permissions_user ON course_permissions(user_id);

-- ============================================================
-- 4. COURSE MATERIALS (with 1-hour review period)
-- ============================================================

CREATE TABLE course_materials (
    material_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    uploaded_by UUID NOT NULL REFERENCES users(user_id),

    material_type VARCHAR(50) NOT NULL CHECK (material_type IN ('lecture_slide', 'homework', 'tutorium', 'other')),
    display_name VARCHAR(255) NOT NULL,
    original_filename TEXT NOT NULL,
    sequence_number INTEGER,
    file_count INTEGER DEFAULT 1,

    pending_review BOOLEAN DEFAULT TRUE,
    review_deadline TIMESTAMP NOT NULL,
    processed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP
);

CREATE INDEX idx_course_materials_course ON course_materials(course_id);
CREATE INDEX idx_course_materials_type ON course_materials(material_type);
CREATE INDEX idx_course_materials_review ON course_materials(pending_review, review_deadline);

-- ============================================================
-- 5. MATERIAL FILES (individual files within a material)
-- ============================================================

CREATE TABLE material_files (
    file_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_id UUID NOT NULL REFERENCES course_materials(material_id) ON DELETE CASCADE,

    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    file_type VARCHAR(50),

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_material_files_material ON material_files(material_id);

-- ============================================================
-- 6. REFRESH TOKENS
-- ============================================================

CREATE TABLE refresh_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP,
    user_agent TEXT,
    ip_address INET,
    is_revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP
);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash);

-- ============================================================
-- 7. AUDIT LOG
-- ============================================================

CREATE TABLE audit_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_log_action ON audit_log(action);

-- ============================================================
-- 8. CREATE ADMIN USER
-- ============================================================

-- Email: cedrik.rose@tutanota.com
-- Password: QweAsdYxc1.
-- Hash generated with bcrypt rounds=12

INSERT INTO users (email, password_hash, full_name, role, is_active, email_verified)
VALUES (
    'cedrik.rose@tutanota.com',
    '$2b$12$8oDSGNAVJTviY3MxKdl81OdHTOOEr.yamKjdQFdSQXKVd9xN8NcNO',
    'Cedrik Rose',
    'admin',
    TRUE,
    TRUE
);

-- ============================================================
-- MIGRATION COMPLETE
-- ============================================================

SELECT 'Fresh migration completed!' as status;
