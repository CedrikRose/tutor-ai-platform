"""Embedding generation using AWS Bedrock."""
import asyncio
import json
import logging
from typing import List
import base64

import boto3
from botocore.exceptions import ClientError

from config import settings
from retry_utils import BedrockCircuitBreaker, call_with_exponential_backoff, is_throttling_error
from parsers.pdf_parser import ParsedChunkData

logger = logging.getLogger(__name__)


class BedrockEmbedder:
    """Generate embeddings using AWS Bedrock Titan model."""

    def __init__(self, circuit_breaker: BedrockCircuitBreaker = None):
        # Initialize Bedrock client using long-term API key
        # Set the long-term API key as environment variable for boto3
        import os
        os.environ['AWS_BEDROCK_API_KEY'] = settings.bedrock_api_key

        self.region = settings.aws_region

        # Create bedrock client - it will pick up the API key from environment
        self.bedrock_client = boto3.client(
            service_name='bedrock-runtime',
            region_name=self.region
        )

        self.model_id = settings.bedrock_embedding_model
        self.circuit_breaker = circuit_breaker or BedrockCircuitBreaker(name="embedding")
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_embeddings)

        # Track statistics
        self.total_embedded = 0
        self.total_tokens = 0

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed (max 8192 tokens for Titan)

        Returns:
            Embedding vector (1024 dimensions)
        """
        # Truncate if too long (rough estimate: 1 token ≈ 4 chars)
        max_chars = 8192 * 4
        if len(text) > max_chars:
            text = text[:max_chars]
            logger.warning(f"Text truncated to {max_chars} chars for embedding")

        async def _embed():
            request_body = json.dumps({
                "inputText": text
            })

            try:
                response = self.bedrock_client.invoke_model(
                    modelId=self.model_id,
                    body=request_body,
                    contentType="application/json",
                    accept="application/json"
                )

                response_body = json.loads(response['body'].read())
                embedding = response_body.get('embedding')

                if not embedding:
                    raise ValueError("No embedding in response")

                self.total_embedded += 1
                self.total_tokens += response_body.get('inputTextTokenCount', 0)

                return embedding

            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                error_message = e.response.get('Error', {}).get('Message', '')

                if is_throttling_error(e):
                    logger.warning(f"Bedrock throttling: {error_message}")
                    raise

                logger.error(f"Bedrock error [{error_code}]: {error_message}")
                raise

        # Use semaphore to limit concurrent requests
        async with self.semaphore:
            return await call_with_exponential_backoff(
                _embed,
                max_attempts=settings.retry_max_attempts,
                base_delay=settings.retry_base_delay,
                max_delay=settings.retry_max_delay,
                exceptions=(ClientError, ValueError),
                circuit_breaker=self.circuit_breaker
            )

    async def embed_chunks_batch(
        self,
        chunks: List[ParsedChunkData],
        batch_size: int = None
    ) -> List[tuple[ParsedChunkData, List[float]]]:
        """
        Generate embeddings for multiple chunks in batches.

        Args:
            chunks: List of parsed chunks
            batch_size: Batch size (default from settings)

        Returns:
            List of (chunk, embedding) tuples
        """
        if batch_size is None:
            batch_size = settings.embedding_batch_size

        results = []
        total_chunks = len(chunks)

        logger.info(f"Embedding {total_chunks} chunks in batches of {batch_size}")

        # Process in batches
        for i in range(0, total_chunks, batch_size):
            batch = chunks[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_chunks + batch_size - 1) // batch_size

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)")

            # Create embedding tasks for this batch
            tasks = []
            for chunk in batch:
                tasks.append(self._embed_chunk(chunk))

            # Execute batch concurrently
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for chunk, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to embed chunk {chunk.chunk_index}: {result}")
                    # Skip failed chunks
                    continue

                results.append((chunk, result))

            logger.info(f"Batch {batch_num}/{total_batches} complete: {len(batch_results)} embeddings")

        logger.info(f"Embedding complete: {len(results)}/{total_chunks} successful")
        return results

    async def _embed_chunk(self, chunk: ParsedChunkData) -> List[float]:
        """Embed a single chunk."""
        return await self.embed_text(chunk.content)

    def get_stats(self) -> dict:
        """Get embedding statistics."""
        return {
            "total_embedded": self.total_embedded,
            "total_tokens": self.total_tokens,
            "avg_tokens_per_embedding": self.total_tokens / self.total_embedded if self.total_embedded > 0 else 0
        }


async def test_embedder():
    """Test embedder with sample text."""
    embedder = BedrockEmbedder()

    test_texts = [
        "Was ist ein Bubblesort Algorithmus?",
        "Erklären Sie den Quicksort Algorithmus.",
        "Wie funktioniert eine verkettete Liste?"
    ]

    print("\nTesting Bedrock embedder...")

    for text in test_texts:
        try:
            embedding = await embedder.embed_text(text)
            print(f"✓ Embedded: '{text[:50]}...'")
            print(f"  Dimension: {len(embedding)}")
            print(f"  Sample values: {embedding[:5]}")
        except Exception as e:
            print(f"✗ Failed: {e}")

    stats = embedder.get_stats()
    print(f"\nStats: {stats}")


if __name__ == "__main__":
    asyncio.run(test_embedder())
