-- Add course materials table for file upload with review period
-- Created: 2026-05-06

CREATE TABLE IF NOT EXISTS course_materials (
    material_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    uploaded_by UUID NOT NULL REFERENCES users(user_id),

    -- Material info
    material_type VARCHAR(50) NOT NULL CHECK (material_type IN ('lecture_slide', 'homework', 'tutorium', 'other')),
    display_name VARCHAR(255) NOT NULL,
    original_filename TEXT NOT NULL,
    sequence_number INTEGER,

    -- File storage
    file_path TEXT NOT NULL,
    file_size BIGINT,

    -- Review period (1 hour)
    pending_review BOOLEAN DEFAULT TRUE,
    review_deadline TIMESTAMP NOT NULL,
    processed_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

-- Indexes
CREATE INDEX idx_course_materials_course ON course_materials(course_id);
CREATE INDEX idx_course_materials_type ON course_materials(material_type);
CREATE INDEX idx_course_materials_review ON course_materials(pending_review, review_deadline);

-- Function to automatically process materials after review period
CREATE OR REPLACE FUNCTION process_pending_materials()
RETURNS void AS $$
BEGIN
    UPDATE course_materials
    SET
        pending_review = FALSE,
        processed_at = CURRENT_TIMESTAMP
    WHERE
        pending_review = TRUE
        AND review_deadline <= CURRENT_TIMESTAMP
        AND deleted_at IS NULL;
END;
$$ LANGUAGE plpgsql;

-- You can schedule this with pg_cron or call it manually:
-- SELECT process_pending_materials();
