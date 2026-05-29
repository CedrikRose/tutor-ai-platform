"""
Llama Parse Client

Wrapper for LlamaParse API to parse PDFs with high accuracy,
preserving layout, tables, formulas, and diagrams.
"""
import logging
import tempfile
import os
from typing import Optional
from pathlib import Path

from llama_parse import LlamaParse
from config import settings

logger = logging.getLogger(__name__)


class LlamaParseClient:
    """Client for parsing PDFs with LlamaParse."""

    def __init__(self):
        """Initialize LlamaParse client."""
        self.parser = LlamaParse(
            api_key=settings.llama_cloud_api_key,
            result_type="markdown",  # Get markdown output
            verbose=True,
            language="de",  # German language support
            parsing_instruction="""
This is a programming course document (lecture slides, homework, or exercises).
Please preserve:
- Code blocks and syntax highlighting
- Tables and their structure
- Mathematical formulas
- Diagrams and figure captions
- Section headings and structure
""",
            num_workers=4,  # Parallel processing
            invalidate_cache=True,  # Always get fresh parse
        )
        logger.info("LlamaParse client initialized")

    def _get_cache_path(self, file_path: str) -> str:
        """
        Get cache file path for parsed PDF result.

        Args:
            file_path: Original PDF file path

        Returns:
            Path to cache file (markdown)
        """
        # Generate cache filename based on original file path
        # Use the file path as unique identifier
        import hashlib
        cache_key = hashlib.md5(file_path.encode()).hexdigest()
        cache_dir = Path("uploads/.llama_parse_cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        return str(cache_dir / f"{cache_key}.md")

    async def parse_pdf(self, file_path: str) -> str:
        """
        Parse PDF file using LlamaParse with caching.

        Args:
            file_path: Path to PDF file (can be local path or S3 path)

        Returns:
            Parsed content as markdown text

        Raises:
            Exception if parsing fails
        """
        from file_storage import get_storage

        # Check cache first
        cache_path = self._get_cache_path(file_path)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cached_content = f.read()
                logger.info(f"LlamaParse cache HIT for: {file_path} (loaded from {cache_path})")
                return cached_content
            except Exception as e:
                logger.warning(f"Failed to read cache file {cache_path}: {e}")

        logger.info(f"LlamaParse cache MISS for: {file_path}, parsing...")

        try:
            # If it's a storage path, we need to download to temp file
            storage = get_storage()

            if file_path.startswith('s3://') or not os.path.exists(file_path):
                # Download from storage to temp file
                file_content = storage.get_file(file_path)

                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(file_content)
                    tmp_path = tmp_file.name

                logger.info(f"Downloaded to temp file: {tmp_path}")
                cleanup_temp = True
            else:
                # Use local file directly
                tmp_path = file_path
                cleanup_temp = False

            # Parse with LlamaParse
            logger.info(f"Calling LlamaParse API...")
            documents = await self.parser.aload_data(tmp_path)

            # Clean up temp file if needed
            if cleanup_temp:
                try:
                    os.remove(tmp_path)
                    logger.info("Cleaned up temp file")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file: {e}")

            # Extract text from all pages
            if not documents:
                logger.warning(f"No content extracted from {file_path}")
                return ""

            # Combine all document pages
            full_text = "\n\n".join([doc.text for doc in documents])

            logger.info(f"Successfully parsed PDF: {len(full_text)} characters, {len(documents)} pages")

            # Save to cache
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    f.write(full_text)
                logger.info(f"Cached LlamaParse result to: {cache_path}")
            except Exception as e:
                logger.warning(f"Failed to save cache file {cache_path}: {e}")

            return full_text

        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path}: {e}", exc_info=True)
            raise

    def parse_pdf_sync(self, file_path: str) -> str:
        """
        Synchronous version of parse_pdf with caching.

        Args:
            file_path: Path to PDF file

        Returns:
            Parsed content as markdown text
        """
        from file_storage import get_storage

        # Check cache first
        cache_path = self._get_cache_path(file_path)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cached_content = f.read()
                logger.info(f"LlamaParse cache HIT (sync) for: {file_path}")
                return cached_content
            except Exception as e:
                logger.warning(f"Failed to read cache file {cache_path}: {e}")

        logger.info(f"LlamaParse cache MISS (sync) for: {file_path}, parsing...")

        try:
            storage = get_storage()

            if file_path.startswith('s3://') or not os.path.exists(file_path):
                file_content = storage.get_file(file_path)

                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(file_content)
                    tmp_path = tmp_file.name

                cleanup_temp = True
            else:
                tmp_path = file_path
                cleanup_temp = False

            # Parse with LlamaParse (sync)
            documents = self.parser.load_data(tmp_path)

            if cleanup_temp:
                try:
                    os.remove(tmp_path)
                except:
                    pass

            if not documents:
                return ""

            full_text = "\n\n".join([doc.text for doc in documents])

            logger.info(f"Successfully parsed PDF: {len(full_text)} characters, {len(documents)} pages")

            # Save to cache
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    f.write(full_text)
                logger.info(f"Cached LlamaParse result to: {cache_path}")
            except Exception as e:
                logger.warning(f"Failed to save cache file {cache_path}: {e}")

            return full_text

        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path}: {e}", exc_info=True)
            raise


# Global client instance
_llama_parse_client = None


def get_llama_parse_client() -> LlamaParseClient:
    """Get global LlamaParse client instance."""
    global _llama_parse_client
    if _llama_parse_client is None:
        _llama_parse_client = LlamaParseClient()
    return _llama_parse_client


if __name__ == "__main__":
    # Test parsing
    import asyncio

    async def test_parse():
        client = get_llama_parse_client()

        # Test with a sample PDF
        test_pdf = "uploads/courses/d4d55441-ad4b-472b-93e5-fe59b1846a2f/20260506_113118_0a98db2c.pdf"

        if os.path.exists(test_pdf):
            result = await client.parse_pdf(test_pdf)
            print(f"Parsed content length: {len(result)}")
            print(f"First 500 chars:\n{result[:500]}")
        else:
            print(f"Test PDF not found: {test_pdf}")

    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_parse())
