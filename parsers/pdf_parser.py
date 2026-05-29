"""PDF parsing using LlamaParse."""
import asyncio
import logging
import time
from typing import List, Dict
from dataclasses import dataclass

from llama_parse import LlamaParse
import tiktoken

from config import settings
from retry_utils import call_with_exponential_backoff

logger = logging.getLogger(__name__)


@dataclass
class ParsedChunkData:
    """Data for a parsed chunk."""
    chunk_index: int
    chunk_type: str  # text, code, table, heading
    content: str
    metadata: Dict
    token_count: int


class PDFParser:
    """Parse PDFs using LlamaParse."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.llama_cloud_api_key

        self.parser = LlamaParse(
            api_key=self.api_key,
            result_type="markdown",  # Get markdown for better structure
            verbose=False,
            language="de",  # German course materials
            num_workers=4,
            invalidate_cache=False,  # Use cache for faster repeated parses
            do_not_cache=False
        )

        # Tokenizer for counting tokens
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        except:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        try:
            return len(self.tokenizer.encode(text))
        except:
            # Fallback: rough estimate
            return len(text) // 4

    async def parse_pdf(self, file_path: str, doc_id: str) -> List[ParsedChunkData]:
        """
        Parse PDF file and return chunks.

        Args:
            file_path: Path to PDF file
            doc_id: Document ID for logging

        Returns:
            List of ParsedChunkData objects
        """
        start_time = time.time()
        logger.info(f"Parsing PDF: {file_path}")

        try:
            # Parse with LlamaParse (handles its own retries internally)
            # Create async wrapper function for retry logic
            async def _parse():
                return await self.parser.aload_data(file_path)

            documents = await call_with_exponential_backoff(
                _parse,
                max_attempts=3,
                base_delay=5.0
            )

            parsing_duration = int((time.time() - start_time) * 1000)
            logger.info(f"PDF parsed in {parsing_duration}ms: {file_path}")

            # Extract text from documents
            if not documents:
                logger.warning(f"No content extracted from PDF: {file_path}")
                return []

            # Combine all pages
            full_text = "\n\n".join([doc.text for doc in documents if doc.text])

            if not full_text.strip():
                logger.warning(f"Empty content after parsing: {file_path}")
                return []

            # Split into semantic chunks
            chunks = self._split_into_chunks(full_text, file_path)

            logger.info(f"Created {len(chunks)} chunks from PDF: {file_path}")
            return chunks

        except Exception as e:
            logger.error(f"Error parsing PDF {file_path}: {e}")
            raise

    def _split_into_chunks(
        self,
        text: str,
        file_path: str,
        target_chunk_size: int = 512,
        overlap: int = 50
    ) -> List[ParsedChunkData]:
        """
        Split text into semantic chunks.

        Strategy:
        1. Split on markdown headers (##, ###) to preserve semantic boundaries
        2. Further split large sections to meet target chunk size
        3. Add overlap between consecutive chunks
        """
        chunks = []

        # Split on markdown headers
        sections = self._split_on_headers(text)

        chunk_index = 0
        for section in sections:
            section_text = section['content'].strip()
            if not section_text:
                continue

            # Check if section needs further splitting
            section_tokens = self.count_tokens(section_text)

            if section_tokens <= target_chunk_size:
                # Section fits in one chunk
                chunks.append(ParsedChunkData(
                    chunk_index=chunk_index,
                    chunk_type=section['type'],
                    content=section_text,
                    metadata={
                        'heading': section.get('heading'),
                        'level': section.get('level'),
                        'source_file': file_path
                    },
                    token_count=section_tokens
                ))
                chunk_index += 1
            else:
                # Split large section into smaller chunks
                sub_chunks = self._split_large_section(
                    section_text,
                    target_chunk_size,
                    overlap,
                    section
                )

                for sub_chunk_text in sub_chunks:
                    chunks.append(ParsedChunkData(
                        chunk_index=chunk_index,
                        chunk_type=section['type'],
                        content=sub_chunk_text,
                        metadata={
                            'heading': section.get('heading'),
                            'level': section.get('level'),
                            'source_file': file_path,
                            'is_split': True
                        },
                        token_count=self.count_tokens(sub_chunk_text)
                    ))
                    chunk_index += 1

        return chunks

    def _split_on_headers(self, text: str) -> List[Dict]:
        """Split text on markdown headers."""
        lines = text.split('\n')
        sections = []
        current_section = {'heading': None, 'level': 0, 'type': 'text', 'content': []}

        for line in lines:
            # Check for markdown headers
            if line.startswith('###'):
                if current_section['content']:
                    sections.append({
                        **current_section,
                        'content': '\n'.join(current_section['content'])
                    })
                current_section = {
                    'heading': line.strip('# ').strip(),
                    'level': 3,
                    'type': 'heading',
                    'content': [line]
                }
            elif line.startswith('##'):
                if current_section['content']:
                    sections.append({
                        **current_section,
                        'content': '\n'.join(current_section['content'])
                    })
                current_section = {
                    'heading': line.strip('# ').strip(),
                    'level': 2,
                    'type': 'heading',
                    'content': [line]
                }
            elif line.startswith('#'):
                if current_section['content']:
                    sections.append({
                        **current_section,
                        'content': '\n'.join(current_section['content'])
                    })
                current_section = {
                    'heading': line.strip('# ').strip(),
                    'level': 1,
                    'type': 'heading',
                    'content': [line]
                }
            else:
                current_section['content'].append(line)

                # Detect code blocks
                if line.strip().startswith('```'):
                    current_section['type'] = 'code'

        # Add final section
        if current_section['content']:
            sections.append({
                **current_section,
                'content': '\n'.join(current_section['content'])
            })

        return sections

    def _split_large_section(
        self,
        text: str,
        target_size: int,
        overlap: int,
        section_meta: Dict
    ) -> List[str]:
        """Split large section into smaller chunks with overlap."""
        # Simple sentence-based splitting
        sentences = text.split('. ')
        chunks = []
        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_tokens = self.count_tokens(sentence)

            if current_tokens + sentence_tokens > target_size and current_chunk:
                # Save current chunk
                chunks.append('. '.join(current_chunk) + '.')

                # Start new chunk with overlap
                overlap_sentences = current_chunk[-2:] if len(current_chunk) >= 2 else current_chunk
                current_chunk = overlap_sentences + [sentence]
                current_tokens = sum(self.count_tokens(s) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens

        # Add final chunk
        if current_chunk:
            chunks.append('. '.join(current_chunk) + '.')

        return chunks


async def test_pdf_parser():
    """Test PDF parser."""
    parser = PDFParser()

    # Find a small PDF to test
    import glob
    pdfs = glob.glob("/home/cedrik/AI-Tutor/modules/**/materials/*.pdf", recursive=True)

    if pdfs:
        test_pdf = min(pdfs, key=lambda p: __import__('os').path.getsize(p))
        print(f"\nTesting PDF parser with: {test_pdf}")
        print(f"Size: {__import__('os').path.getsize(test_pdf) / 1024:.1f} KB")

        chunks = await parser.parse_pdf(test_pdf, "test-doc-id")
        print(f"\nExtracted {len(chunks)} chunks")

        if chunks:
            print(f"\nFirst chunk:")
            print(f"  Type: {chunks[0].chunk_type}")
            print(f"  Tokens: {chunks[0].token_count}")
            print(f"  Content preview: {chunks[0].content[:200]}...")
    else:
        print("No PDFs found to test")


if __name__ == "__main__":
    asyncio.run(test_pdf_parser())
