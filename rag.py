"""RAG (Retrieval-Augmented Generation) module for semantic search using material_chunks."""
import logging
from typing import List, Dict, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from embeddings import BedrockEmbedder

logger = logging.getLogger(__name__)


class RAGRetriever:
    """Semantic search over pgvector with material_chunks."""

    def __init__(self, db: Session, embedder: BedrockEmbedder):
        """
        Initialize RAG retriever.

        Args:
            db: Database session
            embedder: Bedrock embedder for query embedding
        """
        self.db = db
        self.embedder = embedder
        logger.info("RAGRetriever initialized (using material_chunks)")

    async def retrieve(
        self,
        query: str,
        course_id: Optional[str] = None,
        material_type: Optional[str] = None,
        max_lecture_sequence: Optional[int] = None,
        material_types: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Retrieve relevant chunks from vector database.

        Args:
            query: User query text
            course_id: Filter by course UUID
            material_type: Filter by single material type (DEPRECATED - use material_types)
            max_lecture_sequence: Max lecture sequence_number to include (NULL = all lectures)
            material_types: List of allowed material types (NULL = all, lecture_slide always included)
            top_k: Number of chunks to retrieve

        Returns:
            List of dicts with:
              - chunk_id: UUID
              - content: Text content
              - distance: Similarity score
              - file_name: Source file
              - material_name: Display name of material
              - material_type: Type of material
              - source_type: Type of source ('pdf', 'code', 'text')
        """
        try:
            # 1. Generate query embedding
            logger.info(f"RAG RETRIEVE: course_id={course_id}, material_type={material_type}, max_lecture_seq={max_lecture_sequence}, material_types={material_types}, top_k={top_k}")
            logger.debug(f"Query: {query[:100]}...")
            query_embedding = await self.embedder.embed_text(query)

            # 2. Build SQL filters
            filters = ["mc.embedding IS NOT NULL"]  # Only chunks with embeddings

            if course_id:
                filters.append(f"cm.course_id = '{course_id}'")
                logger.info(f"✓ Filter: course_id = {course_id}")

            # Max lecture sequence filter (only for lecture_slide materials)
            if max_lecture_sequence is not None:
                filters.append(f"(cm.material_type != 'lecture_slide' OR cm.sequence_number IS NULL OR cm.sequence_number <= {max_lecture_sequence})")
                logger.info(f"✓ Filter: max_lecture_sequence = {max_lecture_sequence}")

            # Material types filter
            # lecture_slide is always included, material_types filters OTHER types
            if material_types is not None and len(material_types) > 0:
                # Build list: lecture_slide + selected types
                allowed_types = ['lecture_slide'] + material_types
                types_str = "'" + "','".join(allowed_types) + "'"
                filters.append(f"cm.material_type IN ({types_str})")
                logger.info(f"✓ Filter: material_types IN ({types_str})")

            # Backward compatibility: old material_type parameter (DEPRECATED)
            if material_type:
                filters.append(f"cm.material_type = '{material_type}'")
                logger.info(f"✓ Filter: material_type = {material_type} (DEPRECATED)")

            # Exclude deleted materials
            filters.append("cm.deleted_at IS NULL")

            where_clause = " AND ".join(filters)
            logger.info(f"SQL WHERE: {where_clause}")

            # 3. Execute pgvector similarity search
            query_sql = text(f"""
                SELECT
                    mc.chunk_id,
                    mc.content,
                    mc.file_name,
                    mc.source_type,
                    mc.chunk_index,
                    cm.display_name as material_name,
                    cm.material_type,
                    cm.sequence_number,
                    mc.embedding <=> :query_vec AS distance
                FROM material_chunks mc
                JOIN course_materials cm ON mc.material_id = cm.material_id
                WHERE {where_clause}
                ORDER BY distance ASC
                LIMIT :top_k
            """)

            # Format embedding as PostgreSQL vector string
            embedding_str = f"[{','.join(map(str, query_embedding))}]"

            results = self.db.execute(query_sql, {
                "query_vec": embedding_str,
                "top_k": top_k
            }).fetchall()

            # Convert to list of dicts
            chunks = []
            for row in results:
                chunk = {
                    "chunk_id": str(row.chunk_id),
                    "content": row.content,
                    "file_name": row.file_name,
                    "source_type": row.source_type,
                    "chunk_index": row.chunk_index,
                    "material_name": row.material_name,
                    "material_type": row.material_type,
                    "sequence_number": row.sequence_number,
                    "distance": float(row.distance)
                }
                chunks.append(chunk)

            logger.info(f"Retrieved {len(chunks)} chunks")
            if chunks:
                logger.debug(f"Best match: {chunks[0]['material_name']} / {chunks[0]['file_name']} (distance={chunks[0]['distance']:.4f})")

            return chunks

        except Exception as e:
            logger.error(f"Error during RAG retrieval: {e}", exc_info=True)
            return []

    async def retrieve_all_from_material(self, material_id: str) -> List[Dict]:
        """
        Retrieve ALL content from a specific material (no similarity search).
        Used when student selects a specific homework/tutorium to work on.

        For lectures: Returns chunks (legacy behavior)
        For homework/tutorium/other: Returns full contents from MaterialContent

        Args:
            material_id: UUID of the material

        Returns:
            List of all content from this material
        """
        try:
            logger.info(f"🎯 RETRIEVE ALL from material_id={material_id}")

            from database import MaterialChunk, MaterialContent, CourseMaterial

            # First, check the material type
            material = self.db.query(CourseMaterial).filter(
                CourseMaterial.material_id == material_id
            ).first()

            if not material:
                logger.error(f"Material {material_id} not found")
                return []

            logger.info(f"Material type: {material.material_type}")

            if material.material_type == 'lecture_slide':
                # LECTURE: Load chunks (old behavior)
                results = self.db.query(
                    MaterialChunk.chunk_id,
                    MaterialChunk.content,
                    MaterialChunk.file_name,
                    MaterialChunk.source_type,
                    MaterialChunk.chunk_index,
                    CourseMaterial.display_name.label('material_name'),
                    CourseMaterial.material_type,
                    CourseMaterial.sequence_number
                ).join(
                    CourseMaterial,
                    MaterialChunk.material_id == CourseMaterial.material_id
                ).filter(
                    MaterialChunk.material_id == material_id,
                    CourseMaterial.deleted_at == None
                ).order_by(
                    MaterialChunk.file_name,
                    MaterialChunk.chunk_index
                ).all()

                # Convert to list of dicts
                chunks = []
                for row in results:
                    chunk = {
                        "chunk_id": str(row.chunk_id),
                        "content": row.content,
                        "file_name": row.file_name,
                        "source_type": row.source_type,
                        "chunk_index": row.chunk_index,
                        "material_name": row.material_name,
                        "material_type": row.material_type,
                        "sequence_number": row.sequence_number,
                        "distance": 0.0
                    }
                    chunks.append(chunk)

                logger.info(f"✅ Loaded {len(chunks)} chunks from lecture material")
                return chunks

            else:
                # HOMEWORK/TUTORIUM/OTHER: Load full contents
                results = self.db.query(
                    MaterialContent.content_id,
                    MaterialContent.content,
                    MaterialContent.file_name,
                    MaterialContent.source_type,
                    MaterialContent.importance_reason,
                    CourseMaterial.display_name.label('material_name'),
                    CourseMaterial.material_type,
                    CourseMaterial.sequence_number
                ).join(
                    CourseMaterial,
                    MaterialContent.material_id == CourseMaterial.material_id
                ).filter(
                    MaterialContent.material_id == material_id,
                    CourseMaterial.deleted_at == None
                ).order_by(
                    MaterialContent.file_name
                ).all()

                # Convert to list of dicts (same format as chunks for compatibility)
                contents = []
                for idx, row in enumerate(results):
                    content_item = {
                        "chunk_id": str(row.content_id),  # Use content_id as chunk_id for compatibility
                        "content": row.content,
                        "file_name": row.file_name,
                        "source_type": row.source_type,
                        "chunk_index": idx,  # Sequential index
                        "material_name": row.material_name,
                        "material_type": row.material_type,
                        "sequence_number": row.sequence_number,
                        "distance": 0.0,
                        "importance_reason": row.importance_reason
                    }
                    contents.append(content_item)

                logger.info(f"✅ Loaded {len(contents)} full content items from non-lecture material")
                return contents

        except Exception as e:
            logger.error(f"Error loading content from material: {e}", exc_info=True)
            return []

    def format_context_for_llm(self, chunks: List[Dict]) -> str:
        """
        Format retrieved chunks/contents into a context string for LLM.

        Args:
            chunks: List of chunk/content dicts from retrieve() or retrieve_all_from_material()

        Returns:
            Formatted context string

        Note:
            This context is NOT shown to the student, only passed to the LLM!
        """
        if not chunks:
            return "Keine relevanten Kursmaterialien gefunden."

        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            # Check if this is a solution file (heuristic)
            is_solution = any(marker in chunk['file_name'].lower()
                            for marker in ['lsg', 'lösung', 'solution', 'musterlösung'])
            solution_marker = " [MUSTERLÖSUNG]" if is_solution else ""

            # Build context block
            context_block = f"[Kontext {i}{solution_marker}]\n"
            context_block += f"Material: {chunk['material_name']} ({chunk['material_type']})\n"
            context_block += f"Datei: {chunk['file_name']}\n"
            context_block += f"Typ: {chunk['source_type']}\n"

            # Add importance reason if available (for non-lecture materials)
            if 'importance_reason' in chunk and chunk['importance_reason']:
                context_block += f"Relevanz: {chunk['importance_reason']}\n"

            context_block += f"\n{chunk['content']}\n"
            context_parts.append(context_block)

        # Join with separator
        full_context = "\n---\n".join(context_parts)

        logger.debug(f"Formatted context: {len(full_context)} characters")
        return full_context
