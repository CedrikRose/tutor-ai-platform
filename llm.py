"""LLM inference module for AWS Bedrock Kimi K2.5."""
import json
import asyncio
import logging
import os
from pathlib import Path
from typing import List, Dict, Optional, AsyncIterator

import boto3
from botocore.exceptions import ClientError

from config import Settings
from retry_utils import BedrockCircuitBreaker, call_with_exponential_backoff

logger = logging.getLogger(__name__)

# System prompt file path
SYSTEM_PROMPT_FILE = Path(__file__).parent / "config" / "system_prompt.txt"


def load_system_prompt() -> str:
    """Load system prompt from file."""
    try:
        if SYSTEM_PROMPT_FILE.exists():
            with open(SYSTEM_PROMPT_FILE, 'r', encoding='utf-8') as f:
                prompt = f.read().strip()
                logger.info(f"Loaded system prompt from {SYSTEM_PROMPT_FILE}")
                return prompt
        else:
            logger.warning(f"System prompt file not found: {SYSTEM_PROMPT_FILE}")
            return get_default_system_prompt()
    except Exception as e:
        logger.error(f"Error loading system prompt: {e}")
        return get_default_system_prompt()


def save_system_prompt(prompt: str) -> bool:
    """Save system prompt to file."""
    try:
        SYSTEM_PROMPT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SYSTEM_PROMPT_FILE, 'w', encoding='utf-8') as f:
            f.write(prompt)
        logger.info(f"Saved system prompt to {SYSTEM_PROMPT_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error saving system prompt: {e}")
        return False


def get_default_system_prompt() -> str:
    """Get default system prompt."""
    return """Du bist ein pädagogischer KI-Tutor für Programmierkurse. Dein Ziel ist es, Studenten beim Lernen zu unterstützen durch Hilfe zur Selbsthilfe (Scaffolding).

**Wichtige Regeln:**
1. Gib NIEMALS direkte Lösungen zu Hausaufgaben
2. Stelle Gegenfragen, um das Verständnis zu überprüfen
3. Gib Hints und Denkanstöße statt fertiger Antworten
4. Erkläre Konzepte mit Analogien und Beispielen
5. Ermutige zum eigenständigen Ausprobieren
6. Wenn der Student wirklich feststeckt: Zeige einen ähnlichen, aber ANDEREN Ansatz

Du hast Zugriff auf Kursmaterialien und Musterlösungen. Nutze diese als Referenz für deine Hilfestellung, aber gib KEINE direkten Code-Auszüge aus Musterlösungen weiter.

**Wenn ein Student fragt "Was ist die Lösung?":**
Antworte: "Lass uns gemeinsam darauf hinarbeiten. Was hast du bereits versucht? Wo bist du unsicher?"

**Dein Ton:** Freundlich, ermutigend, geduldig, aber fordernd."""


# Load system prompt at module initialization (fallback only)
SCAFFOLDING_SYSTEM_PROMPT = load_system_prompt()


def get_chatbot_system_prompt() -> str:
    """
    Get current chatbot system prompt from prompt manager.

    Falls back to file-based prompt if prompt manager is not available.
    """
    try:
        from prompt_manager import prompt_manager
        from database import SessionLocal

        prompt = prompt_manager.get_prompt("chatbot_system")
        if prompt:
            logger.info(f"✓ Using chatbot prompt from cache (last 50 chars: ...{prompt[-50:]})")
            return prompt

        # Fallback to DB lookup if not in cache
        logger.warning("Chatbot prompt not in cache, loading from DB")
        db = SessionLocal()
        try:
            prompt = prompt_manager.get_prompt("chatbot_system", db)
            if prompt:
                logger.info(f"✓ Loaded chatbot prompt from DB (last 50 chars: ...{prompt[-50:]})")
                return prompt
        finally:
            db.close()

    except Exception as e:
        logger.warning(f"Could not load prompt from manager, using fallback: {e}")

    # Final fallback: use file-based prompt
    logger.warning("⚠️ Using fallback chatbot prompt from file")
    return SCAFFOLDING_SYSTEM_PROMPT


class BedrockLLM:
    """AWS Bedrock LLM client for Kimi K2.5 with streaming support."""

    def __init__(self, config: Settings, circuit_breaker: BedrockCircuitBreaker):
        """
        Initialize Bedrock LLM client.

        Args:
            config: Application settings
            circuit_breaker: Circuit breaker for resilient API calls
        """
        self.config = config
        self.circuit_breaker = circuit_breaker
        self.model_id = config.bedrock_llm_model_primary
        self.context_window_size = 32000  # Kimi K2.5 context window

        # Initialize Bedrock client with extended timeout for streaming
        from botocore.config import Config as BotocoreConfig

        boto_config = BotocoreConfig(
            read_timeout=300,  # 5 minutes - allow for longer generation times
            connect_timeout=10,  # 10 seconds to establish connection
            retries={'max_attempts': 0}  # Don't retry, we handle retries with exponential backoff
        )

        self.bedrock_client = boto3.client(
            service_name='bedrock-runtime',
            region_name=config.aws_region,
            config=boto_config
        )

        logger.info(f"BedrockLLM initialized with model: {self.model_id}")

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        rag_context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> AsyncIterator[str]:
        """
        Stream chat completion from Bedrock.

        Args:
            messages: Conversation history [{"role": "user|assistant", "content": "..."}]
            system_prompt: System prompt for scaffolding behavior
            rag_context: Retrieved context from RAG (prepended to first user message)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate

        Yields:
            Token strings as they arrive from the LLM
        """
        try:
            # Format messages for Bedrock Converse API
            # Content must be a list of content blocks, not a string
            formatted_messages = []
            for msg in messages:
                formatted_msg = {
                    "role": msg["role"],
                    "content": [{"text": msg["content"]}]
                }
                formatted_messages.append(formatted_msg)

            # Prepend RAG context to the last user message if provided
            if rag_context and formatted_messages:
                # Find last user message
                for i in range(len(formatted_messages) - 1, -1, -1):
                    if formatted_messages[i]["role"] == "user":
                        original_text = formatted_messages[i]["content"][0]["text"]
                        formatted_messages[i]["content"][0]["text"] = (
                            f"**Relevanter Kontext aus den Kursmaterialien:**\n\n"
                            f"{rag_context}\n\n"
                            f"---\n\n"
                            f"**Frage des Studenten:**\n{original_text}"
                        )
                        break

            # Use prompt from manager if not provided
            if system_prompt is None:
                system_prompt = get_chatbot_system_prompt()

            # Build request body for Bedrock Converse API
            request_body = {
                "modelId": self.model_id,
                "messages": formatted_messages,
                "system": [{"text": system_prompt}],
                "inferenceConfig": {
                    "temperature": temperature,
                    "maxTokens": max_tokens
                }
            }

            # Call with circuit breaker
            async def _stream():
                response = await asyncio.to_thread(
                    self.bedrock_client.converse_stream,
                    **request_body
                )
                return response

            response = await call_with_exponential_backoff(
                _stream,
                max_attempts=self.config.retry_max_attempts,
                base_delay=self.config.retry_base_delay,
                circuit_breaker=self.circuit_breaker
            )

            # Stream tokens from response
            stream = response.get('stream')
            if stream:
                for event in stream:
                    if 'contentBlockDelta' in event:
                        delta = event['contentBlockDelta'].get('delta', {})
                        if 'text' in delta:
                            yield delta['text']

                    elif 'messageStop' in event:
                        # Stream completed
                        logger.debug("Stream completed successfully")
                        break

                    elif 'metadata' in event:
                        # Log metadata (token usage, etc.)
                        metadata = event['metadata']
                        logger.debug(f"Stream metadata: {metadata}")

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Bedrock API error ({error_code}): {error_message}")

            # Yield error message to user
            yield f"\n\n⚠️ Fehler beim Generieren der Antwort: {error_message}"

        except Exception as e:
            logger.error(f"Unexpected error during streaming: {e}", exc_info=True)
            yield f"\n\n⚠️ Unerwarteter Fehler: {str(e)}"

    async def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Args:
            text: Input text

        Returns:
            Estimated token count

        Note:
            This is a simple estimation. For accurate counts, use Bedrock's
            token counting API if available.
        """
        # Simple estimation: ~0.75 tokens per word for English/German mix
        # This is a rough approximation
        words = text.split()
        estimated_tokens = int(len(words) * 0.75)

        # Add tokens for punctuation and special characters
        estimated_tokens += len([c for c in text if c in '.,!?;:()[]{}'])

        return estimated_tokens

    async def count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Count total tokens in a list of messages.

        Args:
            messages: List of message dicts

        Returns:
            Total estimated token count
        """
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            total += await self.count_tokens(content)
            # Add overhead for role and formatting
            total += 4

        return total

    async def summarize_conversation(
        self,
        messages: List[Dict[str, str]],
        max_summary_tokens: int = 500
    ) -> str:
        """
        Summarize a conversation to reduce context window usage.

        Args:
            messages: List of messages to summarize
            max_summary_tokens: Maximum tokens for summary

        Returns:
            Condensed summary of the conversation
        """
        # Build summarization prompt
        conversation_text = "\n\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in messages
        ])

        summarization_prompt = f"""Fasse diese Konversation prägnant zusammen. Behalte wichtige technische Details, Konzepte und den Lernfortschritt des Studenten bei.

Konversation:
{conversation_text}

Zusammenfassung (max {max_summary_tokens} Tokens):"""

        summary_messages = [
            {"role": "user", "content": summarization_prompt}
        ]

        # Get conversation summary prompt from manager
        try:
            from prompt_manager import prompt_manager
            summary_system_prompt = prompt_manager.get_prompt("conversation_summary")
        except:
            summary_system_prompt = "Du bist ein präziser Zusammenfasser. Erstelle kurze, informative Zusammenfassungen."

        # Generate summary (non-streaming for simplicity)
        summary = ""
        async for token in self.stream_chat(
            messages=summary_messages,
            system_prompt=summary_system_prompt,
            rag_context=None,
            temperature=0.3,  # Lower temperature for more focused summaries
            max_tokens=max_summary_tokens
        ):
            summary += token

        logger.info(f"Conversation summarized: {len(conversation_text)} chars -> {len(summary)} chars")
        return summary.strip()

    def calculate_context_usage(self, total_tokens: int) -> float:
        """
        Calculate context window usage as percentage.

        Args:
            total_tokens: Current token count

        Returns:
            Usage percentage (0-100)
        """
        return min(100.0, (total_tokens / self.context_window_size) * 100)

    async def should_summarize(self, total_tokens: int, threshold: float = 0.8) -> bool:
        """
        Check if conversation should be summarized.

        Args:
            total_tokens: Current token count
            threshold: Trigger threshold (0-1)

        Returns:
            True if summarization should be triggered
        """
        usage = self.calculate_context_usage(total_tokens)
        return usage >= (threshold * 100)

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """
        Non-streaming completion for simple use cases.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate

        Returns:
            Complete response text
        """
        messages = [{"role": "user", "content": prompt}]

        response_text = ""
        async for token in self.stream_chat(
            messages=messages,
            system_prompt=system_prompt or "You are a helpful assistant.",
            rag_context=None,
            temperature=temperature,
            max_tokens=max_tokens
        ):
            response_text += token

        return response_text.strip()
