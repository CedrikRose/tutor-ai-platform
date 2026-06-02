"""
Material Processor

Handles automatic processing of course materials after review period:
1. LLM file analysis (filter unimportant files)
2. PDF parsing via Llama Parse
3. Code file reading
4. Chunking
5. Embedding generation
6. Vector storage
"""
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import and_

from database import (
    SessionLocal, CourseMaterial, MaterialFile, MaterialChunk,
    MaterialProcessingLog, ProcessingStatus
)
from file_storage import get_storage
from embeddings import BedrockEmbedder
from llm import BedrockLLM
from llama_parse_client import get_llama_parse_client
from config import settings

logger = logging.getLogger(__name__)


class MaterialProcessor:
    """Process course materials through LLM analysis, parsing, and embedding."""

    def __init__(self):
        self.storage = get_storage()
        self.embedder = None  # Lazy init
        self.llm = None  # Lazy init
        self.llama_parse = None  # Lazy init

    async def _get_embedder(self) -> BedrockEmbedder:
        """Lazy initialize embedder."""
        if self.embedder is None:
            self.embedder = BedrockEmbedder()
        return self.embedder

    async def _get_llm(self) -> BedrockLLM:
        """Lazy initialize LLM."""
        if self.llm is None:
            from retry_utils import BedrockCircuitBreaker
            from config import settings

            circuit_breaker = BedrockCircuitBreaker(name="material_llm")
            self.llm = BedrockLLM(config=settings, circuit_breaker=circuit_breaker)
        return self.llm

    def log_processing(
        self,
        db: Session,
        material_id: str,
        stage: str,
        status: str,
        message: str = None,
        details: Dict = None,
        file_id: str = None
    ):
        """Log processing step."""
        log = MaterialProcessingLog(
            material_id=material_id,
            file_id=file_id,
            stage=stage,
            status=status,
            message=message,
            details=details,
            started_at=datetime.now(timezone.utc)
        )
        if status in ['completed', 'failed', 'skipped']:
            log.completed_at = datetime.now(timezone.utc)

        db.add(log)
        db.commit()
        logger.info(f"[{material_id}] {stage}: {status} - {message}")

    @staticmethod
    def sanitize_content(content: str) -> str:
        """
        Remove NULL bytes and other problematic characters from content.
        PostgreSQL TEXT columns cannot contain NULL bytes (0x00).

        Args:
            content: Raw content string

        Returns:
            Sanitized content safe for PostgreSQL
        """
        if not content:
            return content
        # Remove NULL bytes
        return content.replace('\x00', '')

    async def analyze_files_batch(
        self,
        files: List,
        parsed_pdfs: Dict[str, str] = None
    ) -> Dict[str, Tuple[bool, str]]:
        """
        Analyze multiple files at once for efficiency.

        Args:
            files: List of MaterialFile objects
            parsed_pdfs: Dict mapping PDF filename to parsed content

        Returns:
            Dict mapping filename to (is_important, reason)
        """
        llm = await self._get_llm()

        # Common patterns to skip immediately
        skip_patterns = [
            '.gitignore', '.git/', '.DS_Store', '__MACOSX',
            'node_modules/', '.vscode/', '.idea/',
            '.class', '.pyc', '.o', '.so', '.dll',
            'package-lock.json', 'yarn.lock', '.jar'
        ]

        results = {}
        files_to_analyze = []

        # First pass: auto-skip obvious files
        for file in files:
            skip = False
            for pattern in skip_patterns:
                if pattern in file.filename:
                    results[file.filename] = (False, f"Automatically skipped: {pattern}")
                    skip = True
                    break
            if not skip:
                files_to_analyze.append(file)

        if not files_to_analyze:
            return results

        # Build detailed file list with previews
        file_info_list = []

        # First add PDF assignment content if available
        if parsed_pdfs:
            for pdf_name, pdf_content in parsed_pdfs.items():
                file_info_list.append(f"\n### PDF Assignment: {pdf_name}")
                file_info_list.append(f"Full content:\n{pdf_content}\n")

        # Then add other files with previews
        for file in files_to_analyze:
            file_info_list.append(f"\n### File: {file.filename}")

            # Get preview for text-based files
            try:
                if file.filename.lower().endswith(('.java', '.scala', '.py', '.js', '.ts', '.cpp', '.c', '.h', '.txt', '.md', '.gradle', '.xml', '.json', '.csv', '.sh')):
                    content = self.read_code_file(file.file_path)
                    lines = content.split('\n')[:10]  # First 10 lines
                    preview = '\n'.join(lines)
                    file_info_list.append(f"First 10 lines:\n{preview}")
            except Exception as e:
                logger.debug(f"Could not read preview for {file.filename}: {e}")

        files_info = '\n'.join(file_info_list)

        # Get batch analysis prompt from manager
        try:
            from prompt_manager import prompt_manager
            batch_prompt_template = prompt_manager.get_prompt("material_file_analysis_batch")
        except Exception as e:
            logger.warning(f"Could not load material batch analysis prompt: {e}")
            # Fallback
            batch_prompt_template = """You are analyzing course material files to determine which are important for student learning.

**Task:**
Analyze the following files and determine if each is important for students:

{file_list}

**Criteria for "important":**
✅ **Include:**
- Lecture slides (PDF)
- Homework assignments
- Exercise sheets
- Solution files
- Code examples
- Study guides
- Relevant documentation

❌ **Exclude:**
- Build artifacts (.class, .o, .pyc)
- Dependencies (node_modules, .venv)
- Temporary files (.tmp, .bak)
- System files (.DS_Store, Thumbs.db)
- Large binary files (unless explicitly educational)

**Output Format:**
JSON array: [{"filename": "...", "important": true/false, "reason": "..."}]

Analyze ALL files and respond ONLY with the JSON array."""

        prompt = batch_prompt_template.replace("{file_list}", files_info)

        try:
            response = await llm.complete(prompt)
            import json
            analysis = json.loads(response)

            for item in analysis:
                filename = item.get('filename')
                # Match filename from any file in files_to_analyze
                for file in files_to_analyze:
                    if file.filename == filename:
                        results[file.filename] = (item.get('important', False), item.get('reason', 'No reason provided'))
                        break

            # Mark any files not in response as unimportant
            for file in files_to_analyze:
                if file.filename not in results:
                    results[file.filename] = (False, "Not analyzed by LLM")

        except Exception as e:
            logger.error(f"Batch file analysis failed: {e}", exc_info=True)
            # Fallback: mark all as important to be safe
            for file in files_to_analyze:
                results[file.filename] = (True, f"Batch analysis failed, included by default")

        return results

    async def analyze_file_importance(
        self,
        filename: str,
        file_content: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Use LLM to determine if file is important for learning.

        Args:
            filename: Name of the file
            file_content: Optional content preview (first 500 chars)

        Returns:
            Tuple of (is_important, reason)
        """
        llm = await self._get_llm()

        # Common patterns to skip immediately
        skip_patterns = [
            '.gitignore', '.git/', '.DS_Store', '__MACOSX',
            'node_modules/', '.vscode/', '.idea/',
            '.class', '.pyc', '.o', '.so', '.dll',
            'package-lock.json', 'yarn.lock'
        ]

        for pattern in skip_patterns:
            if pattern in filename:
                return False, f"Automatically skipped: {pattern}"

        # Get single file analysis prompt from manager
        try:
            from prompt_manager import prompt_manager
            single_prompt_template = prompt_manager.get_prompt("material_file_analysis_single")
        except Exception as e:
            logger.warning(f"Could not load material single analysis prompt: {e}")
            # Fallback
            single_prompt_template = """You are analyzing a course material file to determine if it is important for student learning.

**File:** {filename}
**Material Type:** {material_type}

**Criteria for "important":**
✅ Include: Lecture slides, homework, exercises, solutions, code examples, study materials
❌ Exclude: Build artifacts, dependencies, temp files, system files

**Respond in JSON:**
{"important": true/false, "reason": "brief explanation"}"""

        # Build prompt for LLM
        prompt = single_prompt_template.replace("{filename}", filename).replace("{material_type}", material_type or "unknown")

        if file_content:
            prompt += f"\n\nFile preview (first 500 chars):\n{file_content[:500]}"

        try:
            response = await llm.complete(
                prompt,
                system_prompt="You are a file analyzer. Return ONLY valid JSON.",
                temperature=0.3,
                max_tokens=150
            )

            # Try to parse JSON directly
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{[^}]+\}', response)
                if json_match:
                    result = json.loads(json_match.group(0))
                else:
                    raise ValueError(f"No JSON found in response: {response}")

            return result.get('important', True), result.get('reason', 'No reason provided')
        except Exception as e:
            logger.warning(f"LLM file analysis failed for {filename}: {e}, defaulting to IMPORTANT")
            # Default to important if analysis fails
            return True, "Analysis failed, keeping file"

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200, max_chunks: int = 100) -> List[Dict]:
        """
        Split text into overlapping chunks.

        Args:
            text: Text to chunk
            chunk_size: Maximum chunk size in characters
            overlap: Overlap between chunks
            max_chunks: Maximum number of chunks to create (safety limit)

        Returns:
            List of chunk dictionaries with content and metadata
        """
        if not text or len(text.strip()) == 0:
            logger.warning("Empty text provided to chunk_text")
            return []

        chunks = []
        start = 0
        chunk_index = 0

        try:
            while start < len(text) and chunk_index < max_chunks:
                end = start + chunk_size

                # Try to break at sentence boundary
                if end < len(text):
                    # Look for period, newline, or other break
                    for break_char in ['. ', '\n\n', '\n', '. ']:
                        break_pos = text.rfind(break_char, start, end)
                        if break_pos != -1:
                            end = break_pos + len(break_char)
                            break

                chunk_text = text[start:end].strip()

                if chunk_text:
                    chunks.append({
                        'content': chunk_text,
                        'chunk_index': chunk_index,
                        'start_char': start,
                        'end_char': end
                    })
                    chunk_index += 1

                # Move start position with overlap
                start = end - overlap if end < len(text) else end

            if chunk_index >= max_chunks:
                logger.warning(f"Reached max_chunks limit ({max_chunks}), text may be truncated")

        except Exception as e:
            logger.error(f"Error during chunking: {e}")
            # Return what we have so far
            pass

        return chunks

    async def parse_pdf(self, file_path: str) -> str:
        """
        Parse PDF using Llama Parse.

        Args:
            file_path: Path to PDF file

        Returns:
            Parsed text content
        """
        logger.info(f"Parsing PDF with LlamaParse: {file_path}")

        try:
            # Lazy init LlamaParse client
            if self.llama_parse is None:
                self.llama_parse = get_llama_parse_client()

            # Parse with LlamaParse
            content = await self.llama_parse.parse_pdf(file_path)

            if not content or len(content.strip()) == 0:
                logger.warning(f"LlamaParse returned empty content for {file_path}")
                return f"[Empty PDF or parsing failed: {Path(file_path).name}]"

            logger.info(f"LlamaParse successful: {len(content)} characters")
            return content

        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path} with LlamaParse: {e}")
            # Return error placeholder instead of failing completely
            return f"[PDF Parsing Error for {Path(file_path).name}: {str(e)}]"

    def read_code_file(self, file_path: str) -> str:
        """
        Read code file directly.

        Args:
            file_path: Path to code file

        Returns:
            File content as string
        """
        try:
            file_content = self.storage.get_file(file_path)
            # Decode as UTF-8
            return file_content.decode('utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Failed to read code file {file_path}: {e}")
            raise

    async def process_material(self, material_id: str, db: Session):
        """
        Process a single material through all stages.

        Strategy depends on material type:
        - lecture_slide: Parse PDFs → Chunk → Embed → Store in MaterialChunk (for RAG)
        - homework/tutorium/other: Parse PDFs → Store full content in MaterialContent (no chunking)

        Args:
            material_id: Material UUID
            db: Database session
        """
        from database import CourseMaterial, MaterialFile, MaterialChunk, MaterialContent

        material = db.query(CourseMaterial).filter(
            CourseMaterial.material_id == material_id
        ).first()

        if not material:
            logger.error(f"Material {material_id} not found")
            return

        logger.info(f"Processing material: {material.display_name} ({material_id}) - Type: {material.material_type}")

        self.log_processing(
            db, str(material_id), 'processing', 'started',
            f"Starting processing of {material.display_name} (Type: {material.material_type})"
        )

        # Determine processing strategy based on material type
        is_lecture = material.material_type == 'lecture_slide'

        try:
            # Get all files for this material
            files = db.query(MaterialFile).filter(
                MaterialFile.material_id == material_id
            ).all()

            logger.info(f"Found {len(files)} files to process (lecture={is_lecture})")

            # Stage 1: Filter files based on material type
            if is_lecture:
                # For lectures: Only PDFs are relevant (will be chunked and embedded)
                pdf_files = [f for f in files if f.filename.lower().endswith('.pdf')]
                important_files = pdf_files
                logger.info(f"Lecture material: Processing {len(pdf_files)} PDF files")

                for file in files:
                    if file in pdf_files:
                        self.log_processing(
                            db, str(material_id), 'file_analysis', 'completed',
                            f"PDF file for lecture: {file.filename}",
                            {'important': True, 'reason': 'PDF in lecture material'},
                            file_id=str(file.file_id)
                        )
                    else:
                        self.log_processing(
                            db, str(material_id), 'file_analysis', 'skipped',
                            f"Non-PDF file in lecture: {file.filename}",
                            {'important': False, 'reason': 'Only PDFs are processed for lectures'},
                            file_id=str(file.file_id)
                        )
            else:
                # For homework/tutorium/other: Check if we only have PDFs
                pdf_files = [f for f in files if f.filename.lower().endswith('.pdf')]
                non_pdf_files = [f for f in files if not f.filename.lower().endswith('.pdf')]

                if len(non_pdf_files) == 0:
                    # Only PDFs - no need for LLM analysis, all are important
                    logger.info(f"Non-lecture material: Only {len(pdf_files)} PDF(s), skipping LLM analysis")
                    important_files = [(f, "PDF file (auto-included)") for f in pdf_files]

                    for file in pdf_files:
                        self.log_processing(
                            db, str(material_id), 'file_analysis', 'completed',
                            f"PDF file (auto-included): {file.filename}",
                            {'important': True, 'reason': 'PDF file (auto-included)'},
                            file_id=str(file.file_id)
                        )
                else:
                    # Mixed files - need LLM analysis to filter
                    logger.info(f"Non-lecture material: Batch analyzing {len(files)} files with LLM")
                    important_files = []

                    # First, parse all PDFs to get assignment content
                    logger.info("Parsing PDFs first to extract assignment content...")
                    parsed_pdfs = {}
                    for file in pdf_files:
                        try:
                            logger.info(f"Parsing PDF for batch analysis: {file.filename}")
                            pdf_content = await self.parse_pdf(file.file_path)
                            parsed_pdfs[file.filename] = pdf_content
                            logger.info(f"Successfully parsed {file.filename} ({len(pdf_content)} chars)")
                        except Exception as e:
                            logger.error(f"Failed to parse PDF {file.filename}: {e}")
                            parsed_pdfs[file.filename] = f"[Error parsing PDF: {e}]"

                    # Batch analyze all files with rich context (filenames + file previews + PDF content)
                    analysis_results = await self.analyze_files_batch(files, parsed_pdfs)

                    for file in files:
                        is_important, reason = analysis_results.get(file.filename, (False, "Not analyzed"))

                        if is_important:
                            important_files.append((file, reason))
                            self.log_processing(
                                db, str(material_id), 'file_analysis', 'completed',
                                f"File is IMPORTANT: {reason}",
                                {'important': True, 'reason': reason},
                                file_id=str(file.file_id)
                            )
                        else:
                            self.log_processing(
                                db, str(material_id), 'file_analysis', 'skipped',
                                f"File skipped: {reason}",
                                {'important': False, 'reason': reason},
                                file_id=str(file.file_id)
                            )

            logger.info(f"Filtered to {len(important_files)} important files")

            # Stage 2 & 3: Process based on material type
            if is_lecture:
                # LECTURE: Parse PDFs → Chunk → Embed → Store in MaterialChunk
                all_chunks = []
                for file in important_files:
                    try:
                        self.log_processing(
                            db, str(material_id), 'parsing', 'started',
                            f"Parsing lecture PDF: {file.filename}",
                            file_id=str(file.file_id)
                        )
                        content = await self.parse_pdf(file.file_path)

                        # Chunk the content
                        content_len = len(content)
                        logger.info(f"Chunking lecture PDF {file.filename} ({content_len} chars)...")

                        if content_len > 100000:
                            logger.warning(f"Large lecture PDF ({content_len} chars), limiting to 100k")
                            content = content[:100000]

                        chunks = self.chunk_text(content, chunk_size=2000, overlap=300, max_chunks=50)
                        logger.info(f"Created {len(chunks)} chunks from {file.filename}")

                        # Add metadata
                        for chunk in chunks:
                            chunk['file_id'] = file.file_id
                            chunk['file_name'] = file.filename
                            chunk['source_type'] = 'pdf'

                        all_chunks.extend(chunks)

                        self.log_processing(
                            db, str(material_id), 'parsing', 'completed',
                            f"Parsed and chunked: {len(chunks)} chunks",
                            {'chunk_count': len(chunks)},
                            file_id=str(file.file_id)
                        )

                    except Exception as e:
                        logger.error(f"Error processing lecture PDF {file.filename}: {e}")
                        self.log_processing(
                            db, str(material_id), 'parsing', 'failed',
                            f"Failed to parse: {str(e)}",
                            file_id=str(file.file_id)
                        )

                logger.info(f"Total chunks to embed: {len(all_chunks)}")

                # Generate embeddings and store chunks
                if all_chunks:
                    self.log_processing(
                        db, str(material_id), 'embedding', 'started',
                        f"Generating embeddings for {len(all_chunks)} chunks"
                    )

                    embedder = await self._get_embedder()
                    stored_count = 0
                    failed_count = 0
                    batch_size = 10

                    for batch_start in range(0, len(all_chunks), batch_size):
                        batch_end = min(batch_start + batch_size, len(all_chunks))
                        batch_chunks = all_chunks[batch_start:batch_end]

                        logger.info(f"Embedding batch {batch_start//batch_size + 1} (chunks {batch_start}-{batch_end})")

                        for chunk in batch_chunks:
                            try:
                                # Sanitize content to remove NULL bytes
                                sanitized_chunk_content = self.sanitize_content(chunk['content'])
                                embedding = await embedder.embed_text(sanitized_chunk_content)

                                chunk_record = MaterialChunk(
                                    material_id=material_id,
                                    file_id=chunk['file_id'],
                                    content=sanitized_chunk_content,
                                    chunk_index=chunk['chunk_index'],
                                    source_type=chunk['source_type'],
                                    file_name=chunk['file_name'],
                                    start_char=chunk['start_char'],
                                    end_char=chunk['end_char'],
                                    embedding=embedding
                                )
                                db.add(chunk_record)
                                stored_count += 1

                            except Exception as e:
                                logger.error(f"Failed to embed chunk {chunk.get('chunk_index', '?')}: {e}")
                                failed_count += 1

                        try:
                            db.commit()
                            logger.info(f"✓ Batch committed: {stored_count} chunks stored")
                        except Exception as e:
                            logger.error(f"Failed to commit batch: {e}")
                            db.rollback()

                    logger.info(f"Embedding complete: {stored_count} successful, {failed_count} failed")

                    self.log_processing(
                        db, str(material_id), 'embedding', 'completed',
                        f"Stored {stored_count}/{len(all_chunks)} chunks with embeddings"
                    )

            else:
                # HOMEWORK/TUTORIUM/OTHER: Parse all → Store full content (NO chunking)
                stored_count = 0
                failed_count = 0

                for file, importance_reason in important_files:
                    try:
                        filename_lower = file.filename.lower()

                        if filename_lower.endswith('.pdf'):
                            # Parse PDF to markdown
                            self.log_processing(
                                db, str(material_id), 'parsing', 'started',
                                f"Parsing PDF to markdown: {file.filename}",
                                file_id=str(file.file_id)
                            )
                            content = await self.parse_pdf(file.file_path)
                            source_type = 'pdf_markdown'

                        else:
                            # Read code/text file directly
                            self.log_processing(
                                db, str(material_id), 'parsing', 'started',
                                f"Reading file: {file.filename}",
                                file_id=str(file.file_id)
                            )
                            content = self.read_code_file(file.file_path)

                            # Determine source type
                            if filename_lower.endswith(('.java', '.scala', '.py', '.js', '.ts', '.cpp', '.c', '.h')):
                                source_type = 'code'
                            elif filename_lower.endswith(('.txt', '.md', '.json', '.yaml', '.yml')):
                                source_type = 'text'
                            else:
                                source_type = 'data'

                        # Sanitize content to remove NULL bytes
                        sanitized_content = self.sanitize_content(content)

                        # Store full content (no chunking!)
                        content_record = MaterialContent(
                            material_id=material_id,
                            file_id=file.file_id,
                            content=sanitized_content,
                            source_type=source_type,
                            file_name=file.filename,
                            file_size=len(sanitized_content.encode('utf-8')),
                            importance_reason=importance_reason
                        )
                        db.add(content_record)
                        stored_count += 1

                        self.log_processing(
                            db, str(material_id), 'parsing', 'completed',
                            f"Stored full content ({len(content)} chars)",
                            {'content_size': len(content), 'source_type': source_type},
                            file_id=str(file.file_id)
                        )

                    except Exception as e:
                        logger.error(f"Error processing {file.filename}: {e}")
                        failed_count += 1
                        self.log_processing(
                            db, str(material_id), 'parsing', 'failed',
                            f"Failed to parse: {str(e)}",
                            file_id=str(file.file_id)
                        )

                try:
                    db.commit()
                    logger.info(f"Stored {stored_count} full content records")
                except Exception as e:
                    logger.error(f"Failed to commit content: {e}")
                    db.rollback()

                self.log_processing(
                    db, str(material_id), 'storage', 'completed',
                    f"Stored {stored_count} full content records (no chunking)"
                )

            # Mark material as processed
            material.processed_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(f"Successfully processed material: {material.display_name}")

        except Exception as e:
            logger.error(f"Failed to process material {material_id}: {e}")

            # Update status to failed
            try:
                material.processing_status = ProcessingStatus.FAILED
                material.processing_error = str(e)[:1000]  # Limit to 1000 chars
                db.commit()
            except Exception as update_error:
                logger.error(f"Failed to update failure status: {update_error}")
                db.rollback()

            self.log_processing(
                db, str(material_id), 'processing', 'failed',
                f"Processing failed: {str(e)}"
            )
            raise

    async def process_pending_materials(self):
        """
        DEPRECATED: Review period feature was removed.
        Materials are now processed on-demand via API call.
        This function is kept for backward compatibility but does nothing.
        """
        logger.info("process_pending_materials called but review period feature is disabled")
        logger.info("Materials are now processed on-demand via /api/materials/{material_id}/process")
        return


async def run_material_processor():
    """Run material processor once."""
    processor = MaterialProcessor()
    await processor.process_pending_materials()


if __name__ == "__main__":
    # Run processor
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_material_processor())
