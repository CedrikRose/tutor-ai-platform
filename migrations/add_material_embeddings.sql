-- Migration: Add material embeddings and processing tables
-- Date: 2026-05-06

-- ============================================================
-- 1. MATERIAL CHUNKS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS material_chunks (
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_id UUID NOT NULL REFERENCES course_materials(material_id) ON DELETE CASCADE,
    file_id UUID REFERENCES material_files(file_id) ON DELETE CASCADE,

    -- Chunk content
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,

    -- Metadata
    source_type VARCHAR(50),  -- 'pdf', 'code', 'text'
    file_name TEXT,
    start_char INTEGER,
    end_char INTEGER,

    -- Embedding
    embedding vector(1536),  -- Amazon Titan embedding dimension

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),

    -- Index for efficient retrieval
    CONSTRAINT unique_chunk UNIQUE(material_id, file_id, chunk_index)
);

-- Indexes for fast vector search
CREATE INDEX IF NOT EXISTS idx_material_chunks_material ON material_chunks(material_id);
CREATE INDEX IF NOT EXISTS idx_material_chunks_file ON material_chunks(file_id);
CREATE INDEX IF NOT EXISTS idx_material_chunks_embedding ON material_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================================
-- 2. MATERIAL PROCESSING LOG
-- ============================================================

CREATE TABLE IF NOT EXISTS material_processing_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_id UUID NOT NULL REFERENCES course_materials(material_id) ON DELETE CASCADE,
    file_id UUID REFERENCES material_files(file_id) ON DELETE SET NULL,

    -- Processing details
    stage VARCHAR(50) NOT NULL,  -- 'file_analysis', 'parsing', 'chunking', 'embedding'
    status VARCHAR(50) NOT NULL,  -- 'started', 'completed', 'failed', 'skipped'

    -- Results
    message TEXT,
    details JSONB,

    -- Timestamps
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_processing_log_material ON material_processing_log(material_id);
CREATE INDEX IF NOT EXISTS idx_processing_log_status ON material_processing_log(status, stage);

-- ============================================================
-- MIGRATION COMPLETE
-- ============================================================

SELECT 'Material embeddings tables created!' as status;
