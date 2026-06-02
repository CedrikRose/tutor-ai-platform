"""Centralized system prompt management with caching."""
import logging
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class PromptManager:
    """Manages system prompts with in-memory caching for performance."""

    def __init__(self):
        """Initialize prompt manager with empty cache."""
        self._cache: Dict[str, str] = {}
        self._metadata_cache: Dict[str, Dict] = {}
        self._last_reload = None
        logger.info("PromptManager initialized")

    def initialize(self, db: Session):
        """Load all prompts from database into cache."""
        try:
            from database import SystemPrompt

            prompts = db.query(SystemPrompt).all()

            for prompt in prompts:
                self._cache[prompt.prompt_key] = prompt.prompt_content
                self._metadata_cache[prompt.prompt_key] = {
                    "prompt_id": str(prompt.prompt_id),
                    "prompt_name": prompt.prompt_name,
                    "description": prompt.description,
                    "category": prompt.category,
                    "temperature": float(prompt.temperature) if prompt.temperature else None,
                    "max_tokens": prompt.max_tokens,
                    "updated_at": prompt.updated_at.isoformat() if prompt.updated_at else None,
                    "updated_by": prompt.updated_by,
                    "version": prompt.version
                }

            self._last_reload = datetime.utcnow()
            logger.info(f"✓ Loaded {len(self._cache)} prompts into cache")

        except Exception as e:
            logger.error(f"Error initializing prompts: {e}", exc_info=True)

    def get_prompt(self, prompt_key: str, db: Optional[Session] = None) -> Optional[str]:
        """
        Get prompt content by key.

        Args:
            prompt_key: Unique key for the prompt
            db: Optional database session for fallback if not in cache

        Returns:
            Prompt content or None if not found
        """
        # Try cache first
        if prompt_key in self._cache:
            return self._cache[prompt_key]

        # Fallback: load from DB if session provided
        if db:
            logger.warning(f"Prompt '{prompt_key}' not in cache, loading from DB")
            self._reload_prompt(prompt_key, db)
            return self._cache.get(prompt_key)

        logger.error(f"Prompt '{prompt_key}' not found in cache and no DB session provided")
        return None

    def _reload_prompt(self, prompt_key: str, db: Session):
        """Reload a single prompt from database."""
        try:
            from database import SystemPrompt

            prompt = db.query(SystemPrompt).filter(
                SystemPrompt.prompt_key == prompt_key
            ).first()

            if prompt:
                self._cache[prompt_key] = prompt.prompt_content
                self._metadata_cache[prompt_key] = {
                    "prompt_id": str(prompt.prompt_id),
                    "prompt_name": prompt.prompt_name,
                    "description": prompt.description,
                    "category": prompt.category,
                    "temperature": float(prompt.temperature) if prompt.temperature else None,
                    "max_tokens": prompt.max_tokens,
                    "updated_at": prompt.updated_at.isoformat() if prompt.updated_at else None,
                    "updated_by": prompt.updated_by,
                    "version": prompt.version
                }
                logger.info(f"✓ Reloaded prompt: {prompt_key}")
            else:
                logger.error(f"Prompt not found in DB: {prompt_key}")

        except Exception as e:
            logger.error(f"Error reloading prompt '{prompt_key}': {e}", exc_info=True)

    def update_prompt(self, prompt_key: str, content: str, updated_by: str, db: Session) -> bool:
        """
        Update prompt in database and cache.

        Args:
            prompt_key: Unique key for the prompt
            content: New prompt content
            updated_by: Who made the update (e.g., "admin")
            db: Database session

        Returns:
            True if successful, False otherwise
        """
        try:
            from database import SystemPrompt

            prompt = db.query(SystemPrompt).filter(
                SystemPrompt.prompt_key == prompt_key
            ).first()

            if not prompt:
                logger.error(f"Cannot update: Prompt '{prompt_key}' not found")
                return False

            # Update in DB
            prompt.prompt_content = content
            prompt.updated_by = updated_by
            prompt.updated_at = datetime.utcnow()
            prompt.version += 1

            db.commit()

            # Update cache
            self._cache[prompt_key] = content
            if prompt_key in self._metadata_cache:
                self._metadata_cache[prompt_key]["updated_at"] = prompt.updated_at.isoformat()
                self._metadata_cache[prompt_key]["updated_by"] = updated_by
                self._metadata_cache[prompt_key]["version"] = prompt.version

            logger.info(f"✓ Updated prompt: {prompt_key} (v{prompt.version}) by {updated_by}")
            return True

        except Exception as e:
            logger.error(f"Error updating prompt '{prompt_key}': {e}", exc_info=True)
            db.rollback()
            return False

    def reload_all(self, db: Session):
        """Reload all prompts from database."""
        logger.info("Reloading all prompts from database...")
        self._cache.clear()
        self._metadata_cache.clear()
        self.initialize(db)

    def list_all(self) -> List[Dict]:
        """
        List all prompts with metadata.

        Returns:
            List of prompts with full metadata
        """
        prompts = []

        for prompt_key, content in self._cache.items():
            metadata = self._metadata_cache.get(prompt_key, {})
            prompts.append({
                "prompt_key": prompt_key,
                "prompt_content": content,
                **metadata
            })

        # Sort by category, then by name
        prompts.sort(key=lambda p: (p.get("category", ""), p.get("prompt_name", "")))

        return prompts

    def get_metadata(self, prompt_key: str) -> Optional[Dict]:
        """Get metadata for a specific prompt."""
        return self._metadata_cache.get(prompt_key)

    @property
    def cache_size(self) -> int:
        """Return number of prompts in cache."""
        return len(self._cache)

    @property
    def last_reload_time(self) -> Optional[datetime]:
        """Return timestamp of last reload."""
        return self._last_reload


# Global instance
prompt_manager = PromptManager()
