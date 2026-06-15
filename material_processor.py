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
from config import settings
from reducto_client import get_reducto_client
from lecture_synthesizer import LectureSynthesizer

logger = logging.getLogger(__name__)


class MaterialProcessor:
    """Process course materials through LLM analysis, parsing, and embedding."""

    def __init__(self):
        self.storage = get_storage()
        self.embedder = None  # Lazy init
        self.llm = None  # Lazy init

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

    def read_file_preview(self, file_path: str, max_chars: int = 500) -> str:
        """
        Read first N characters of a file for preview.

        Args:
            file_path: Path to file
            max_chars: Maximum characters to read

        Returns:
            Preview content (first max_chars characters)
        """
        try:
            content = self.read_code_file(file_path)
            return content[:max_chars]
        except Exception as e:
            logger.error(f"Failed to read preview for {file_path}: {e}")
            return "[Error reading file]"

    @staticmethod
    def is_text_file(filename: str) -> bool:
        """
        Check if file is text-based (not binary).

        Args:
            filename: File name with extension

        Returns:
            True if file is text-based
        """
        text_extensions = [
            '.java', '.scala', '.py', '.js', '.ts', '.cpp', '.c', '.h',
            '.txt', '.md', '.gradle', '.xml', '.json', '.yaml', '.yml',
            '.sh', '.bat', '.sql', '.html', '.css', '.properties', '.rs',
            '.go', '.rb', '.php', '.swift', '.kt', '.cs', '.r', '.m'
        ]
        return any(filename.lower().endswith(ext) for ext in text_extensions)


    async def analyze_files_two_stage(
        self,
        files: List,
        parsed_pdfs: Dict[str, str] = None,
        material_type: str = None,
        display_name: str = None
    ) -> Dict[str, Tuple[bool, str]]:
        """
        Two-stage LLM analysis for file importance.

        Stage 1: Fast categorization (filenames only + PDF context)
        Stage 2: Detailed analysis (only for "unsure" files with content preview)

        Args:
            files: List of MaterialFile objects
            parsed_pdfs: Dict mapping PDF filename to parsed content
            material_type: Type of material (homework, tutorium, other)
            display_name: Display name of material

        Returns:
            Dict mapping filename to (is_important: bool, reason: str)
        """
        llm = await self._get_llm()

        # Prepare PDF context
        pdf_context = ""
        if parsed_pdfs:
            pdf_parts = []
            for pdf_name, pdf_content in parsed_pdfs.items():
                pdf_parts.append(f"### PDF: {pdf_name}\n{pdf_content}")
            pdf_context = "\n\n".join(pdf_parts)

        # Prepare filenames list
        filenames = "\n".join([f"- {f.filename}" for f in files])

        # ===== STAGE 1: Fast Categorization =====
        logger.info(f"[STAGE 1] Analyzing {len(files)} files (filenames only)")

        try:
            from prompt_manager import prompt_manager
            from database import SessionLocal

            # Ensure prompt manager has DB access
            if not hasattr(prompt_manager, 'db') or prompt_manager.db is None:
                temp_db = SessionLocal()
                prompt_manager.initialize(temp_db)
                temp_db.close()

            stage1_prompt_template = prompt_manager.get_prompt("material_file_analysis_stage1_fast")

            if not stage1_prompt_template:
                logger.error("Stage 1 prompt not found in cache")
                raise Exception("Stage 1 prompt 'material_file_analysis_stage1_fast' not found")

        except Exception as e:
            logger.error(f"Could not load stage 1 prompt: {e}")
            raise Exception(f"Failed to load stage 1 prompt: {e}")

        # Build Stage 1 prompt
        stage1_prompt = stage1_prompt_template
        stage1_prompt = stage1_prompt.replace("{material_type}", material_type or "unknown")
        stage1_prompt = stage1_prompt.replace("{display_name}", display_name or "unknown")
        stage1_prompt = stage1_prompt.replace("{pdf_context}", pdf_context if pdf_context else "(Kein PDF vorhanden)")
        stage1_prompt = stage1_prompt.replace("{filenames}", filenames)

        try:
            # Call LLM for Stage 1
            stage1_response = await llm.complete(
                prompt=stage1_prompt,
                system_prompt="Du bist ein Datei-Analyzer. Antworte NUR mit dem strukturierten JSON.",
                temperature=0.2,
                max_tokens=2000
            )

            # Parse JSON response (handle markdown code blocks)
            stage1_response_clean = stage1_response.strip()

            # Remove markdown code blocks if present
            if stage1_response_clean.startswith('```'):
                # Extract JSON from ```json ... ``` or ``` ... ```
                lines = stage1_response_clean.split('\n')
                # Remove first line (```json or ```)
                lines = lines[1:]
                # Remove last line (```)
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                stage1_response_clean = '\n'.join(lines)

            stage1_result = json.loads(stage1_response_clean)

            definitely_important = stage1_result.get("definitely_important", [])
            definitely_unimportant = stage1_result.get("definitely_unimportant", [])
            unsure = stage1_result.get("unsure", [])

            logger.info(f"[STAGE 1] Results: {len(definitely_important)} important, {len(definitely_unimportant)} unimportant, {len(unsure)} unsure")

        except json.JSONDecodeError as e:
            logger.error(f"[STAGE 1] JSON parse failed: {e}")
            logger.error(f"Response: {stage1_response[:500]}")
            raise Exception(f"Stage 1 JSON parsing failed: {e}")
        except Exception as e:
            logger.error(f"[STAGE 1] Error: {e}")
            raise Exception(f"Stage 1 analysis failed: {e}")

        # Early return if no unsure files
        if not unsure:
            logger.info("[STAGE 2] Skipped (no unsure files)")
            results = {}
            for item in definitely_important:
                results[item["filename"]] = (True, f"[Stage 1] {item['reason']}")
            for item in definitely_unimportant:
                results[item["filename"]] = (False, f"[Stage 1] {item['reason']}")
            return results

        # ===== STAGE 2: Detailed Analysis =====
        logger.info(f"[STAGE 2] Analyzing {len(unsure)} unsure files (with previews)")

        try:
            from prompt_manager import prompt_manager

            stage2_prompt_template = prompt_manager.get_prompt("material_file_analysis_stage2_detailed")

            if not stage2_prompt_template:
                logger.error("Stage 2 prompt not found in cache")
                # Include all unsure files by default
                results = {}
                for item in definitely_important:
                    results[item["filename"]] = (True, f"[Stage 1] {item['reason']}")
                for item in unsure:
                    results[item["filename"]] = (True, f"[Stage 1 unsure, Stage 2 failed] {item['reason']}")
                for item in definitely_unimportant:
                    results[item["filename"]] = (False, f"[Stage 1] {item['reason']}")
                return results

        except Exception as e:
            logger.error(f"Could not load stage 2 prompt: {e}")
            # Include all unsure files by default
            results = {}
            for item in definitely_important:
                results[item["filename"]] = (True, f"[Stage 1] {item['reason']}")
            for item in unsure:
                results[item["filename"]] = (True, f"[Stage 1 unsure, Stage 2 failed] {item['reason']}")
            for item in definitely_unimportant:
                results[item["filename"]] = (False, f"[Stage 1] {item['reason']}")
            return results

        # Build list of important files for context
        important_files_list = "\n".join([f"- {item['filename']}" for item in definitely_important])

        # Load content previews for unsure files
        unsure_with_preview = []
        for unsure_item in unsure:
            filename = unsure_item["filename"]
            file_obj = next((f for f in files if f.filename == filename), None)

            if file_obj and self.is_text_file(file_obj.filename):
                preview = self.read_file_preview(file_obj.file_path, max_chars=500)
                unsure_with_preview.append(f"### {filename}\n```\n{preview}\n```")
            else:
                # Binary file or not found
                unsure_with_preview.append(f"### {filename}\n[Binary file or not readable]")

        unsure_files_text = "\n\n".join(unsure_with_preview)

        # Build Stage 2 prompt
        stage2_prompt = stage2_prompt_template
        stage2_prompt = stage2_prompt.replace("{pdf_context}", pdf_context if pdf_context else "(Kein PDF vorhanden)")
        stage2_prompt = stage2_prompt.replace("{important_files}", important_files_list if important_files_list else "(Keine)")
        stage2_prompt = stage2_prompt.replace("{unsure_files_with_preview}", unsure_files_text)

        try:
            # Call LLM for Stage 2
            stage2_response = await llm.complete(
                prompt=stage2_prompt,
                system_prompt="Du bist ein Datei-Analyzer. Antworte NUR mit dem strukturierten JSON.",
                temperature=0.3,
                max_tokens=1500
            )

            # Parse JSON response (handle markdown code blocks)
            stage2_response_clean = stage2_response.strip()

            # Remove markdown code blocks if present
            if stage2_response_clean.startswith('```'):
                # Extract JSON from ```json ... ``` or ``` ... ```
                lines = stage2_response_clean.split('\n')
                # Remove first line (```json or ```)
                lines = lines[1:]
                # Remove last line (```)
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                stage2_response_clean = '\n'.join(lines)

            stage2_result = json.loads(stage2_response_clean)

            essential = stage2_result.get("essential", [])
            not_essential = stage2_result.get("not_essential", [])

            logger.info(f"[STAGE 2] Results: {len(essential)} essential, {len(not_essential)} not essential")

        except json.JSONDecodeError as e:
            logger.error(f"[STAGE 2] JSON parse failed: {e}")
            logger.error(f"Response: {stage2_response[:500]}")
            # Include all unsure files by default (conservative)
            essential = unsure
            not_essential = []
        except Exception as e:
            logger.error(f"[STAGE 2] Error: {e}")
            # Include all unsure files by default (conservative)
            essential = unsure
            not_essential = []

        # ===== COMBINE RESULTS =====
        results = {}

        # Definitely important from Stage 1
        for item in definitely_important:
            results[item["filename"]] = (True, f"[Stage 1] {item['reason']}")

        # Essential from Stage 2
        for item in essential:
            results[item["filename"]] = (True, f"[Stage 2] {item['reason']}")

        # Definitely unimportant from Stage 1
        for item in definitely_unimportant:
            results[item["filename"]] = (False, f"[Stage 1] {item['reason']}")

        # Not essential from Stage 2
        for item in not_essential:
            results[item["filename"]] = (False, f"[Stage 2] {item['reason']}")

        logger.info(f"[2-STAGE] Final: {sum(1 for v in results.values() if v[0])} important, {sum(1 for v in results.values() if not v[0])} unimportant")

        return results

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

    async def parse_pdf_with_reducto(self, file_path: str) -> str:
        """
        Parse PDF using Reducto and combine all chunk content.

        Args:
            file_path: Path to PDF file

        Returns:
            Combined content from all Reducto chunks
        """
        logger.info(f"Parsing PDF with Reducto: {file_path}")

        try:
            reducto_client = get_reducto_client()

            # Parse with Reducto
            reducto_response = await reducto_client.parse_pdf(file_path)
            result_data = reducto_response.get("result", {})

            if isinstance(result_data, dict):
                reducto_chunks = result_data.get("chunks", [])
            else:
                reducto_chunks = []

            if not reducto_chunks:
                logger.warning(f"Reducto returned no chunks for {file_path}")
                return f"[Empty PDF or parsing failed: {Path(file_path).name}]"

            # Extract content from all chunks
            content_parts = []
            for chunk in reducto_chunks:
                chunk_content = chunk.get("content", "")
                if chunk_content.strip():
                    content_parts.append(chunk_content)

            # Combine with double newline separator
            combined_content = "\n\n".join(content_parts)

            logger.info(f"Reducto parsed {len(reducto_chunks)} chunks → {len(combined_content)} chars")
            return combined_content

        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path} with Reducto: {e}")
            # Return error placeholder instead of failing completely
            return f"[PDF Parsing Error for {Path(file_path).name}: {str(e)}]"

    def read_code_file(self, file_path: str) -> str:
        """
        Read code file directly.
        For CSV files, only reads the first 5 lines to save tokens.
        For large TXT files (>50KB), only reads first 100 lines.

        Args:
            file_path: Path to code file

        Returns:
            File content as string
        """
        try:
            file_content = self.storage.get_file(file_path)
            # Decode as UTF-8
            content = file_content.decode('utf-8', errors='ignore')

            # Special handling for CSV files: only keep first 5 lines
            if file_path.lower().endswith('.csv'):
                lines = content.split('\n')
                if len(lines) > 5:
                    content = '\n'.join(lines[:5])
                    content += f"\n... (truncated: {len(lines) - 5} more lines)"
                    logger.info(f"CSV file truncated: kept 5/{len(lines)} lines from {Path(file_path).name}")

            # Special handling for large TXT files: only keep first 100 lines
            elif file_path.lower().endswith('.txt') and len(content) > 50000:
                lines = content.split('\n')
                if len(lines) > 100:
                    content = '\n'.join(lines[:100])
                    content += f"\n... (truncated: {len(lines) - 100} more lines, file size: {len(file_content):,} bytes)"
                    logger.info(f"Large TXT file truncated: kept 100/{len(lines)} lines from {Path(file_path).name}")

            return content
        except Exception as e:
            logger.error(f"Failed to read code file {file_path}: {e}")
            raise

    async def smart_truncate_with_llm(self, content: str, file_name: str) -> Optional[str]:
        """
        Use LLM to intelligently shorten large files (>10KB).

        Args:
            content: File content to potentially shorten
            file_name: Name of the file (for logging and prompt context)

        Returns:
            Shortened content if LLM decided to truncate, None otherwise
        """
        from prompt_manager import prompt_manager

        llm = await self._get_llm()

        # Prepare content with truncation info
        if len(content) > 30000:
            content_to_send = content[:30000]
            content_info = f"Original-Datei (erste 30.000 Zeichen, Datei geht danach noch weiter mit {len(content) - 30000} Zeichen):\n{content_to_send}"
        else:
            content_info = f"Original-Datei:\n{content}"

        # Get prompt from database
        prompt_template = prompt_manager.get_prompt("file_intelligent_truncation")

        if not prompt_template:
            logger.error("Truncation prompt not found in database!")
            return None

        # Replace placeholders
        prompt = prompt_template.replace("{file_name}", file_name)
        prompt = prompt.replace("{content_info}", content_info)

        try:
            response = await llm.complete(prompt, temperature=0.3, max_tokens=16384)

            # Try to extract JSON from response (handle cases where LLM adds text around JSON)
            response_stripped = response.strip()

            # Try direct parsing first
            try:
                result = json.loads(response_stripped)
            except json.JSONDecodeError:
                # Try to find JSON object in response
                import re
                json_match = re.search(r'\{.*"shortened_content".*\}', response_stripped, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(0))
                else:
                    raise ValueError("No valid JSON found in response")

            if result.get("shortened_content"):
                logger.info(f"LLM truncated {file_name}: {result.get('reason', 'no reason')}")
                return result["shortened_content"]
            else:
                logger.info(f"LLM decided not to truncate {file_name}")
                return None

        except Exception as e:
            logger.error(f"LLM truncation failed for {file_name}: {e}")
            return None  # Fallback: keep original

    async def read_code_file_smart(self, file_path: str) -> str:
        """
        Read code file with intelligent LLM-based truncation for large files.

        - Files >10KB: Pass through LLM for intelligent shortening
        - Files >30KB: LLM only sees first 30KB with note that file continues
        - Files ≤10KB: Return as-is

        Args:
            file_path: Path to code file

        Returns:
            File content (potentially shortened)
        """
        try:
            file_content = self.storage.get_file(file_path)
            content = file_content.decode('utf-8', errors='ignore')
            file_name = Path(file_path).name

            # Skip workspace files - not relevant
            if 'workspace.xml' in file_path or '.idea/workspace' in file_path:
                logger.info(f"Skipping IDE workspace file: {file_name}")
                return "[IDE workspace file - not relevant for course content]"

            # Files ≤10KB: return as-is
            if len(content) <= 10000:
                return content

            # Files >10KB: LLM-based intelligent truncation
            logger.info(f"File {file_name} is {len(content):,} chars, using LLM truncation")
            truncated = await self.smart_truncate_with_llm(content, file_name)

            if truncated:
                return truncated
            else:
                # LLM decided not to truncate
                return content

        except Exception as e:
            logger.error(f"Failed to read code file smart {file_path}: {e}")
            raise

    async def process_lecture_with_synthesis(self, material_id: str, files: List, db: Session):
        """Process lecture slides with Reducto + Kimi K2.5 synthesis."""
        from prompt_manager import prompt_manager

        # Get material name for context
        material = db.query(CourseMaterial).filter(CourseMaterial.material_id == material_id).first()
        material_name = material.display_name if material else "Unknown Lecture"

        reducto_client = get_reducto_client()
        llm = await self._get_llm()
        synthesizer = LectureSynthesizer(llm, prompt_manager)

        all_synthesized_chunks = []
        
        for file in files:
            try:
                self.log_processing(db, str(material_id), 'parsing', 'started',
                                  f"Parsing with Reducto: {file.filename}", file_id=str(file.file_id))
                
                reducto_response = await reducto_client.parse_pdf(file.file_path)
                result_data = reducto_response.get("result", {})
                
                if isinstance(result_data, dict):
                    reducto_chunks = result_data.get("chunks", [])
                else:
                    reducto_chunks = []
                
                logger.info(f"[LECTURE] Reducto returned {len(reducto_chunks)} chunks for {file.filename}")
                
                if reducto_chunks:
                    self.log_processing(db, str(material_id), 'synthesis', 'started',
                                      f"Synthesizing with Kimi K2.5: {len(reducto_chunks)} chunks")

                    # Pass material_name for context
                    synthesis_result = await synthesizer.process_lecture(reducto_chunks, material_name=material_name)
                    
                    self.log_processing(db, str(material_id), 'synthesis', 'completed',
                                      f"Synthesized {len(synthesis_result['synthesized_chunks'])} chunks",
                                      details=synthesis_result)
                    
                    all_synthesized_chunks.extend(synthesis_result['synthesized_chunks'])
                else:
                    logger.error(f"[LECTURE] No chunks returned from Reducto for {file.filename}")
                    raise Exception("No chunks from Reducto")
                
            except Exception as e:
                logger.error(f"[LECTURE] Reducto + Synthesis failed for {file.filename}: {e}")
                self.log_processing(db, str(material_id), 'parsing', 'failed',
                                  f"Reducto processing failed: {str(e)}", file_id=str(file.file_id))
                # Abort processing - do not continue with this material
                raise Exception(f"Lecture processing failed for {file.filename}: {e}")
        
        if not all_synthesized_chunks:
            logger.error(f"[LECTURE] No chunks processed")
            return

        # NEW: Store synthesized chunks DIRECTLY without re-chunking
        self.log_processing(db, str(material_id), 'storage', 'started',
                           f"Storing {len(all_synthesized_chunks)} synthesized chunks")

        embedder = await self._get_embedder()
        stored_count = 0

        for chunk in all_synthesized_chunks:
            try:
                # Get the synthesized explanation
                content = chunk.get("erklaerung", chunk.get("content", ""))
                sanitized_content = self.sanitize_content(content)

                # Generate embedding
                embedding = await embedder.embed_text(sanitized_content)

                # Prepare metadata
                chunk_metadata = {
                    "pages": chunk.get("pages", [chunk.get("page", 0)]),
                    "source": "reducto+kimi",
                    "synthesized_at": datetime.now(timezone.utc).isoformat(),
                    "batch_index": chunk.get("batch_index", 0),
                    "original_chunk_id": chunk.get("chunk_id"),
                    "original_content_preview": chunk.get("original_content", "")[:200],
                    "attempt_count": chunk.get("attempt_count", 1)
                }

                # Create MaterialChunk record
                chunk_record = MaterialChunk(
                    material_id=material_id,
                    file_id=None,  # Synthesis spans multiple files potentially
                    content=sanitized_content,
                    chunk_index=chunk.get("chunk_id", 0),
                    source_type='reducto_synthesis',  # New source type
                    file_name=material_name,  # Store material name for context
                    start_char=None,  # Not applicable for synthesized chunks
                    end_char=None,
                    embedding=embedding,
                    chunk_metadata=chunk_metadata  # NEW: Store structured metadata
                )
                db.add(chunk_record)
                stored_count += 1

                # Commit in batches of 10 to avoid memory issues
                if stored_count % 10 == 0:
                    db.commit()
                    logger.info(f"[LECTURE] Stored {stored_count}/{len(all_synthesized_chunks)} chunks")

            except Exception as e:
                logger.error(f"[LECTURE] Failed to store chunk {chunk.get('chunk_id')}: {e}")
                # Continue with next chunk rather than failing entirely

        # Final commit
        db.commit()

        logger.info(f"[LECTURE] Stored {stored_count}/{len(all_synthesized_chunks)} synthesized chunks")
        self.log_processing(db, str(material_id), 'storage', 'completed',
                           f"Stored {stored_count} chunks with embeddings and metadata")


    async def process_material(
        self,
        material_id: str,
        db: Session,
        skip_llm_filter: bool = False,
        important_file_ids: List[str] = None
    ):
        """
        Process a single material through all stages.

        Strategy depends on material type:
        - lecture_slide: Parse PDFs → Chunk → Embed → Store in MaterialChunk (for RAG)
        - homework/tutorium/other: Parse PDFs → Store full content in MaterialContent (no chunking)

        Args:
            material_id: Material UUID
            db: Database session
            skip_llm_filter: If True, skip LLM-based file analysis (manual selection)
            important_file_ids: List of file IDs to process (if None, process all when skip_llm_filter=True)
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

            # Stage 1: Filter files based on material type and skip_llm_filter flag
            if skip_llm_filter:
                # Manual file selection mode - process only specified files
                if important_file_ids:
                    important_file_id_set = set(str(fid) for fid in important_file_ids)
                    important_files = [
                        (f, "Manually selected by professor")
                        for f in files
                        if str(f.file_id) in important_file_id_set
                    ]
                    logger.info(f"Manual selection: Processing {len(important_files)} of {len(files)} files")
                else:
                    # No files specified and skip_llm_filter=True → empty material
                    important_files = []
                    logger.info(f"No important files specified - creating placeholder content")

                # Log all files
                for file in files:
                    if str(file.file_id) in (important_file_ids or []):
                        self.log_processing(
                            db, str(material_id), 'file_analysis', 'completed',
                            f"Manually selected: {file.filename}",
                            {'important': True, 'reason': 'Manually selected by professor'},
                            file_id=str(file.file_id)
                        )
                    else:
                        self.log_processing(
                            db, str(material_id), 'file_analysis', 'skipped',
                            f"Not selected: {file.filename}",
                            {'important': False, 'reason': 'Not marked as important by professor'},
                            file_id=str(file.file_id)
                        )

            elif is_lecture:
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
                            pdf_content = await self.parse_pdf_with_reducto(file.file_path)
                            parsed_pdfs[file.filename] = pdf_content
                            logger.info(f"Successfully parsed {file.filename} ({len(pdf_content)} chars)")
                        except Exception as e:
                            logger.error(f"Failed to parse PDF {file.filename}: {e}")
                            parsed_pdfs[file.filename] = f"[Error parsing PDF: {e}]"

                    # Two-stage analysis: Fast categorization + detailed analysis
                    analysis_results = await self.analyze_files_two_stage(
                        files, parsed_pdfs,
                        material_type=material.material_type,
                        display_name=material.display_name
                    )

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

            # Handle empty materials (no important files)
            if len(important_files) == 0:
                logger.warning(f"No important files for material {material_id} - creating placeholder")

                if is_lecture:
                    # Create placeholder chunk for lecture
                    placeholder_chunk = MaterialChunk(
                        material_id=material_id,
                        file_id=None,
                        content="Material ist aktuell nicht verfügbar.",
                        chunk_index=0,
                        source_type='placeholder',
                        file_name='placeholder.txt',
                        start_char=0,
                        end_char=0,
                        embedding=None  # No embedding for placeholder
                    )
                    db.add(placeholder_chunk)
                else:
                    # Create placeholder content for homework/tutorium/other
                    placeholder_content = MaterialContent(
                        material_id=material_id,
                        file_id=None,
                        content="Material ist aktuell nicht verfügbar.",
                        source_type='placeholder',
                        file_name='placeholder.txt',
                        file_size=len("Material ist aktuell nicht verfügbar."),
                        importance_reason='No important files selected'
                    )
                    db.add(placeholder_content)

                db.commit()
                self.log_processing(
                    db, str(material_id), 'placeholder', 'completed',
                    "Created placeholder content (no important files)"
                )

                # Mark material as processed
                material.processed_at = datetime.now(timezone.utc)
                db.commit()

                logger.info(f"Material {material_id} processed with placeholder content")
                return

            # Stage 2 & 3: Process based on material type
            if is_lecture:
                # NEW: Use Reducto + Kimi K2.5 synthesis
                await self.process_lecture_with_synthesis(material_id, important_files, db)

            else:
                # HOMEWORK/TUTORIUM/OTHER: Parse all → Store full content (NO chunking)
                stored_count = 0
                failed_count = 0

                for file, importance_reason in important_files:
                    try:
                        filename_lower = file.filename.lower()

                        if filename_lower.endswith('.pdf'):
                            # Parse PDF with Reducto
                            self.log_processing(
                                db, str(material_id), 'parsing', 'started',
                                f"Parsing PDF with Reducto: {file.filename}",
                                file_id=str(file.file_id)
                            )
                            content = await self.parse_pdf_with_reducto(file.file_path)
                            source_type = 'pdf_markdown'

                        else:
                            # Read code/text file directly
                            self.log_processing(
                                db, str(material_id), 'parsing', 'started',
                                f"Reading file: {file.filename}",
                                file_id=str(file.file_id)
                            )
                            content = await self.read_code_file_smart(file.file_path)

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
