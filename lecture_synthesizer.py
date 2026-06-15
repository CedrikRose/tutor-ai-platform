"""
Lecture Synthesizer

Orchestrates dynamic batching and LLM synthesis of lecture materials.
"""
import asyncio
import json
import logging
import re
import time
from typing import List, Dict, Optional
from datetime import datetime

from llm import BedrockLLM
from prompt_manager import PromptManager

logger = logging.getLogger(__name__)


class LectureSynthesizer:
    """Synthesize lecture content with Kimi K2.5."""

    def __init__(self, llm: BedrockLLM, prompt_manager: PromptManager):
        self.llm = llm
        self.prompt_manager = prompt_manager

    def _extract_pages(self, chunk: Dict) -> List[int]:
        """Extract all unique page numbers from all blocks in a chunk."""
        pages = set()

        # Check top-level bbox first
        bbox = chunk.get("bbox", {})
        if isinstance(bbox, dict) and "page" in bbox:
            pages.add(bbox["page"])

        # Check all blocks for additional pages
        for block in chunk.get("blocks", []):
            block_bbox = block.get("bbox", {})
            if isinstance(block_bbox, dict) and "page" in block_bbox:
                pages.add(block_bbox["page"])

        return sorted(list(pages)) if pages else [0]

    def batch_chunks(self, reducto_chunks: List[Dict], max_chars: int = 10000) -> List[List[Dict]]:
        """Group Reducto chunks into batches by character count."""
        batches = []
        current_batch = []
        current_length = 0

        for idx, chunk in enumerate(reducto_chunks):
            chunk_content = chunk.get("content", "")
            chunk_data = {
                "chunk_id": idx,
                "content": chunk_content,
                "pages": self._extract_pages(chunk),
                "original_content": chunk_content[:200]  # Store preview for debugging
            }

            chunk_len = len(chunk_content)

            if current_length + chunk_len > max_chars and current_batch:
                batches.append(current_batch)
                logger.info(f"[SYNTHESIS] Created batch with {len(current_batch)} chunks, {current_length} chars")
                current_batch = [chunk_data]
                current_length = chunk_len
            else:
                current_batch.append(chunk_data)
                current_length += chunk_len

        if current_batch:
            batches.append(current_batch)
            logger.info(f"[SYNTHESIS] Created final batch with {len(current_batch)} chunks, {current_length} chars")

        logger.info(f"[SYNTHESIS] Total: {len(reducto_chunks)} chunks to {len(batches)} batches")
        return batches

    def _parse_json_response(self, response_text: str) -> Optional[List[Dict]]:
        """Parse JSON from LLM response with multiple fallback strategies."""

        # Strategy 1: Direct parse (clean JSON)
        try:
            data = json.loads(response_text)
            if isinstance(data, list):
                logger.info("[SYNTHESIS] Strategy 1 (direct) succeeded")
                return data
            elif isinstance(data, dict) and "results" in data:
                logger.info("[SYNTHESIS] Strategy 1 (direct with results key) succeeded")
                return data["results"]
            elif isinstance(data, dict) and "chunks" in data:
                logger.info("[SYNTHESIS] Strategy 1 (direct with chunks key) succeeded")
                return data["chunks"]
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract from markdown code block (```json ... ```)
        try:
            match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response_text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                if isinstance(data, list):
                    logger.info("[SYNTHESIS] Strategy 2 (markdown block) succeeded")
                    return data
        except (json.JSONDecodeError, AttributeError):
            pass

        # Strategy 3: Find JSON array containing "chunk_id" or "erklaerung"
        try:
            match = re.search(r'\[[\s\S]*?(?:"chunk_id"|"erklaerung")[\s\S]*?\]', response_text)
            if match:
                data = json.loads(match.group(0))
                if isinstance(data, list):
                    logger.info("[SYNTHESIS] Strategy 3 (pattern match) succeeded")
                    return data
        except (json.JSONDecodeError, AttributeError):
            pass

        # Strategy 4: Cut everything outside first [ and last ]
        try:
            start = response_text.find('[')
            end = response_text.rfind(']')
            if start != -1 and end != -1 and end > start:
                json_str = response_text[start:end+1]
                data = json.loads(json_str)
                if isinstance(data, list):
                    logger.info("[SYNTHESIS] Strategy 4 (bracket extraction) succeeded")
                    return data
        except (json.JSONDecodeError, ValueError):
            pass

        # Strategy 5: Line-by-line extraction (for malformed multiline JSON)
        try:
            lines = response_text.split('\n')
            json_lines = []
            in_json = False
            bracket_depth = 0

            for line in lines:
                if '[' in line and not in_json:
                    in_json = True
                    bracket_depth += line.count('[') - line.count(']')
                    json_lines.append(line)
                elif in_json:
                    bracket_depth += line.count('[') - line.count(']')
                    json_lines.append(line)
                    if bracket_depth <= 0:
                        break

            if json_lines:
                json_str = '\n'.join(json_lines)
                data = json.loads(json_str)
                if isinstance(data, list):
                    logger.info("[SYNTHESIS] Strategy 5 (line-by-line) succeeded")
                    return data
        except (json.JSONDecodeError, ValueError):
            pass

        # All strategies failed - log for debugging
        logger.error("[SYNTHESIS] All 5 parsing strategies failed!")
        logger.error(f"[SYNTHESIS] Response length: {len(response_text)} chars")
        logger.error(f"[SYNTHESIS] Response preview (first 500 chars):\n{response_text[:500]}")
        logger.error(f"[SYNTHESIS] Response preview (last 300 chars):\n{response_text[-300:]}")

        return None

    async def synthesize_batch(
        self,
        batch: List[Dict],
        historical_context: str = "",
        attempt: int = 1
    ) -> Dict:
        """Synthesize a single batch with LLM. Retries up to 3 times on JSON parse failure."""
        system_prompt = self.prompt_manager.get_prompt("lecture_synthesis_universal")

        if not system_prompt:
            logger.error("[SYNTHESIS] System prompt not found!")
            raise Exception("System prompt 'lecture_synthesis_universal' not found")

        # NEW: Send only content as simple string array (not full JSON with metadata)
        # But include chunk_ids separately so LLM knows the correct IDs
        first_chunk_id = batch[0].get("chunk_id", 0) if batch else 0
        last_chunk_id = batch[-1].get("chunk_id", 0) if batch else 0

        content_array = [chunk.get("content", "") for chunk in batch]
        batch_json = json.dumps(content_array, ensure_ascii=False, indent=2)

        user_prompt = f"""**Historischer Kontext (letzte verarbeitete Folien):**
{historical_context if historical_context else '(Beginn der Vorlesung)'}

**Zu analysierende Abschnitte (Array von {len(batch)} Folien-Texten):**
{batch_json}

**WICHTIG:**
- Du erhältst ein Array mit {len(batch)} Folien-Texten
- Array-Index 0 entspricht chunk_id "{first_chunk_id}"
- Array-Index {len(batch)-1} entspricht chunk_id "{last_chunk_id}"
- Gib für JEDEN Text GENAU EINE Erklärung zurück mit der korrekten chunk_id ("{first_chunk_id}" bis "{last_chunk_id}")!
"""

        formatted_system_prompt = system_prompt.replace("{historical_context}", historical_context or "(Beginn der Vorlesung)")
        formatted_system_prompt = formatted_system_prompt.replace("{batch_content}", batch_json)

        logger.info(f"[SYNTHESIS] Batch attempt {attempt}: {len(batch)} chunks")

        try:
            response = await self.llm.complete(
                prompt=user_prompt,
                system_prompt=formatted_system_prompt,
                temperature=0.4,
                max_tokens=16384  # Increased for larger batches (up to 40 chunks)
            )

            parsed_result = self._parse_json_response(response)

            if parsed_result is None:
                logger.warning(f"[SYNTHESIS] JSON parse FAILED (attempt {attempt}/3)")

                if attempt < 3:
                    await asyncio.sleep(2)
                    return await self.synthesize_batch(batch, historical_context, attempt + 1)
                else:
                    # NEW: Split batch if it has more than 1 chunk
                    if len(batch) > 1:
                        logger.warning(f"[SYNTHESIS] JSON parse failed after 3 attempts. Splitting batch of {len(batch)} chunks...")
                        mid = len(batch) // 2
                        batch1 = batch[:mid]
                        batch2 = batch[mid:]
                        logger.info(f"[SYNTHESIS] Split: Batch 1 = {len(batch1)} chunks, Batch 2 = {len(batch2)} chunks")

                        # Process both halves with fresh 3 attempts each
                        result1 = await self.synthesize_batch(batch1, historical_context, attempt=1)
                        result2 = await self.synthesize_batch(batch2, historical_context, attempt=1)

                        # Combine results
                        combined_chunks = result1["synthesized_chunks"] + result2["synthesized_chunks"]
                        logger.info(f"[SYNTHESIS] Split successful: Combined {len(combined_chunks)} chunks")
                        return {
                            "synthesized_chunks": combined_chunks,
                            "attempt_count": max(result1["attempt_count"], result2["attempt_count"])
                        }
                    else:
                        logger.error("[SYNTHESIS] JSON parse failed after 3 attempts and batch has only 1 chunk, aborting")
                        raise Exception("JSON parse failed after 3 attempts - material processing aborted")

            # NEW: Validate count matches
            if len(parsed_result) != len(batch):
                logger.error(f"[SYNTHESIS] COUNT MISMATCH!")
                logger.error(f"[SYNTHESIS] Expected {len(batch)} chunks, got {len(parsed_result)}")
                logger.error(f"[SYNTHESIS] Input chunk_ids: {[c['chunk_id'] for c in batch]}")
                logger.error(f"[SYNTHESIS] Output chunk_ids: {[r.get('chunk_id') for r in parsed_result]}")

                if attempt < 1:
                    logger.warning(f"[SYNTHESIS] Retrying (attempt {attempt + 1}/1)...")
                    await asyncio.sleep(2)
                    return await self.synthesize_batch(batch, historical_context, attempt + 1)
                else:
                    # NEW: Split batch if it has more than 1 chunk
                    if len(batch) > 1:
                        logger.warning(f"[SYNTHESIS] Splitting batch of {len(batch)} chunks into 2 smaller batches...")
                        mid = len(batch) // 2
                        batch1 = batch[:mid]
                        batch2 = batch[mid:]
                        logger.info(f"[SYNTHESIS] Split: Batch 1 = {len(batch1)} chunks, Batch 2 = {len(batch2)} chunks")

                        # Process both halves with fresh 3 attempts each
                        result1 = await self.synthesize_batch(batch1, historical_context, attempt=1)
                        result2 = await self.synthesize_batch(batch2, historical_context, attempt=1)

                        # Combine results
                        combined_chunks = result1["synthesized_chunks"] + result2["synthesized_chunks"]
                        logger.info(f"[SYNTHESIS] Split successful: Combined {len(combined_chunks)} chunks")
                        return {
                            "synthesized_chunks": combined_chunks,
                            "attempt_count": max(result1["attempt_count"], result2["attempt_count"])
                        }
                    else:
                        raise Exception(f"Synthesis count mismatch after 3 attempts: expected {len(batch)}, got {len(parsed_result)}")

            # NEW: Validate all chunk_ids present
            input_ids = {str(c["chunk_id"]) for c in batch}
            output_ids = {str(r.get("chunk_id", "")) for r in parsed_result}

            if input_ids != output_ids:
                missing = input_ids - output_ids
                extra = output_ids - input_ids
                logger.error(f"[SYNTHESIS] CHUNK_ID MISMATCH!")
                logger.error(f"[SYNTHESIS] Missing chunk_ids: {missing}")
                logger.error(f"[SYNTHESIS] Extra chunk_ids: {extra}")

                if attempt < 1:
                    logger.warning(f"[SYNTHESIS] Retrying (attempt {attempt + 1}/1)...")
                    await asyncio.sleep(2)
                    return await self.synthesize_batch(batch, historical_context, attempt + 1)
                else:
                    # NEW: Split batch if it has more than 1 chunk
                    if len(batch) > 1:
                        logger.warning(f"[SYNTHESIS] Splitting batch of {len(batch)} chunks into 2 smaller batches...")
                        mid = len(batch) // 2
                        batch1 = batch[:mid]
                        batch2 = batch[mid:]
                        logger.info(f"[SYNTHESIS] Split: Batch 1 = {len(batch1)} chunks, Batch 2 = {len(batch2)} chunks")

                        # Process both halves with fresh 3 attempts each
                        result1 = await self.synthesize_batch(batch1, historical_context, attempt=1)
                        result2 = await self.synthesize_batch(batch2, historical_context, attempt=1)

                        # Combine results
                        combined_chunks = result1["synthesized_chunks"] + result2["synthesized_chunks"]
                        logger.info(f"[SYNTHESIS] Split successful: Combined {len(combined_chunks)} chunks")
                        return {
                            "synthesized_chunks": combined_chunks,
                            "attempt_count": max(result1["attempt_count"], result2["attempt_count"])
                        }
                    else:
                        raise Exception(f"Synthesis chunk_id mismatch after 3 attempts")

            # Merge page info and original content
            for item in parsed_result:
                chunk_id = item.get("chunk_id")
                for c in batch:
                    if str(c["chunk_id"]) == str(chunk_id):  # String comparison for safety
                        item["pages"] = c.get("pages", [c.get("page", 0)])  # NEW: use pages list
                        item["original_content"] = c.get("original_content", c["content"][:200])
                        break

            logger.info(f"[SYNTHESIS] Batch successful: {len(parsed_result)} chunks")

            return {
                "synthesized_chunks": parsed_result,
                "attempt_count": attempt
            }

        except Exception as e:
            logger.error(f"[SYNTHESIS] Error: {e}")
            raise

    async def process_lecture(self, reducto_chunks: List[Dict], material_name: str = "Unknown") -> Dict:
        """Main processing loop: batch to synthesize to combine."""
        start_time = time.time()

        logger.info(f"[SYNTHESIS] Processing {len(reducto_chunks)} chunks for '{material_name}'")

        batches = self.batch_chunks(reducto_chunks, max_chars=15000)

        if not batches:
            return {
                "metadata": {"batch_count": 0, "total_chunks": 0, "synthesis_duration_sec": 0, "retry_count": 0},
                "synthesized_chunks": []
            }

        all_synthesized = []
        total_retries = 0
        historical_context = ""

        for batch_index, batch in enumerate(batches):
            logger.info(f"[SYNTHESIS] Processing batch {batch_index + 1}/{len(batches)}...")

            result = await self.synthesize_batch(batch, historical_context)

            synthesized_chunks = result.get("synthesized_chunks", [])

            for chunk in synthesized_chunks:
                chunk["batch_index"] = batch_index

            all_synthesized.extend(synthesized_chunks)

            if "attempt_count" in result:
                total_retries += (result["attempt_count"] - 1)

            # NEW: Use last 3 synthesized chunks as context for next batch
            if synthesized_chunks:
                # Take last 3 chunks (or all if less than 3)
                last_chunks = synthesized_chunks[-3:] if len(synthesized_chunks) > 3 else synthesized_chunks
                # Extract just the explanations (no JSON structure)
                context_texts = [c.get("erklaerung", "") for c in last_chunks]
                historical_context = "\n\n".join(context_texts)
                logger.info(f"[SYNTHESIS] Context updated with last {len(last_chunks)} chunks ({len(historical_context)} chars)")

        duration = time.time() - start_time

        final_result = {
            "metadata": {
                "batch_count": len(batches),
                "total_chunks": len(all_synthesized),
                "synthesis_duration_sec": round(duration, 2),
                "retry_count": total_retries,
                "timestamp": datetime.utcnow().isoformat()
            },
            "synthesized_chunks": all_synthesized
        }

        logger.info(f"[SYNTHESIS] Complete: {len(all_synthesized)} chunks in {duration:.1f}s")

        return final_result
