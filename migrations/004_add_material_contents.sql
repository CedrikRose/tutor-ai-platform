-- Migration: Add MaterialContent table for non-chunked materials
-- This table stores full content for homework, tutorium, and other materials
-- that are included entirely in context (not chunked like lectures)

-- Create material_contents table
CREATE TABLE IF NOT EXISTS material_contents (
    content_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_id UUID NOT NULL REFERENCES course_materials(material_id) ON DELETE CASCADE,
    file_id UUID REFERENCES material_files(file_id) ON DELETE CASCADE,

    -- Full content (markdown for PDFs, raw content for code/text files)
    content TEXT NOT NULL,

    -- Metadata
    source_type VARCHAR(50) NOT NULL,  -- 'pdf_markdown', 'code', 'text', 'data'
    file_name TEXT NOT NULL,
    file_size BIGINT,  -- Size of content in bytes

    -- LLM importance assessment
    importance_reason TEXT,  -- Why this file was deemed important

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient querying
CREATE INDEX idx_material_contents_material ON material_contents(material_id);
CREATE INDEX idx_material_contents_file ON material_contents(file_id);
CREATE INDEX idx_material_contents_source_type ON material_contents(source_type);

-- Add vector index to material_chunks if not exists (for lecture materials)
-- This improves semantic search performance
CREATE INDEX IF NOT EXISTS idx_material_chunks_embedding
ON material_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Update comment on material_chunks to clarify usage
COMMENT ON TABLE material_chunks IS 'Chunked content with embeddings for LECTURE materials only (lecture_slide type). Used for semantic search via RAG.';

COMMENT ON TABLE material_contents IS 'Full content storage for non-lecture materials (homework, tutorium, other). These are NOT chunked and are included entirely in context when selected.';
