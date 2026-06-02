"""Admin API for system prompt management."""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from prompt_manager import prompt_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prompts", tags=["prompts-admin"])

# Admin password (TODO: Move to .env in production)
ADMIN_PASSWORD = "zp63hC!dmov*XyYgt%%j"

# In-memory token storage (expires after 1 hour)
# Key: token, Value: expiry datetime
active_tokens: Dict[str, datetime] = {}


# ============================================================================
# Request/Response Models
# ============================================================================

class PasswordAuth(BaseModel):
    password: str


class AuthResponse(BaseModel):
    token: str
    expires_in: int  # seconds


class PromptListItem(BaseModel):
    prompt_key: str
    prompt_name: str
    prompt_content: str
    description: Optional[str]
    category: Optional[str]
    temperature: Optional[float]
    max_tokens: Optional[int]
    updated_at: Optional[str]
    updated_by: Optional[str]
    version: Optional[int]


class PromptUpdate(BaseModel):
    prompt_key: str
    prompt_content: str


class PromptUpdateResponse(BaseModel):
    status: str
    prompt_key: str
    version: int


class ReloadResponse(BaseModel):
    status: str
    count: int


# ============================================================================
# Helper Functions
# ============================================================================

def _verify_token(token: str) -> bool:
    """Verify if token is valid and not expired."""
    if token not in active_tokens:
        return False

    expiry = active_tokens[token]
    if datetime.utcnow() > expiry:
        # Token expired, remove it
        del active_tokens[token]
        return False

    return True


def _clean_expired_tokens():
    """Remove expired tokens from memory."""
    now = datetime.utcnow()
    expired = [token for token, expiry in active_tokens.items() if now > expiry]
    for token in expired:
        del active_tokens[token]


def verify_auth_token(token: str = Header(..., alias="Authorization")) -> str:
    """Dependency to verify auth token."""
    # Remove "Bearer " prefix if present
    if token.startswith("Bearer "):
        token = token[7:]

    if not _verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return token


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/authenticate", response_model=AuthResponse)
async def authenticate(auth: PasswordAuth):
    """
    Authenticate with admin password and receive a session token.

    Token is valid for 1 hour.
    """
    if auth.password != ADMIN_PASSWORD:
        logger.warning("Failed authentication attempt")
        raise HTTPException(status_code=401, detail="Invalid password")

    # Clean expired tokens before creating new one
    _clean_expired_tokens()

    # Generate new token
    token = str(uuid.uuid4())
    expiry = datetime.utcnow() + timedelta(hours=1)
    active_tokens[token] = expiry

    logger.info(f"New admin session created (expires: {expiry})")

    return AuthResponse(
        token=token,
        expires_in=3600  # 1 hour in seconds
    )


@router.get("/list", response_model=List[PromptListItem])
async def list_prompts(
    token: str = Depends(verify_auth_token)
):
    """
    List all system prompts with metadata.

    Requires valid authentication token.
    """
    try:
        prompts = prompt_manager.list_all()

        # Convert to response model
        response = [
            PromptListItem(
                prompt_key=p["prompt_key"],
                prompt_name=p.get("prompt_name", ""),
                prompt_content=p["prompt_content"],
                description=p.get("description"),
                category=p.get("category"),
                temperature=p.get("temperature"),
                max_tokens=p.get("max_tokens"),
                updated_at=p.get("updated_at"),
                updated_by=p.get("updated_by"),
                version=p.get("version")
            )
            for p in prompts
        ]

        logger.info(f"Listed {len(response)} prompts")
        return response

    except Exception as e:
        logger.error(f"Error listing prompts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list prompts")


@router.post("/update", response_model=PromptUpdateResponse)
async def update_prompt(
    update: PromptUpdate,
    token: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    """
    Update a system prompt.

    Changes are applied immediately (no server restart needed).
    Requires valid authentication token.
    """
    try:
        success = prompt_manager.update_prompt(
            prompt_key=update.prompt_key,
            content=update.prompt_content,
            updated_by="admin",
            db=db
        )

        if not success:
            raise HTTPException(status_code=404, detail=f"Prompt '{update.prompt_key}' not found")

        # Get updated metadata
        metadata = prompt_manager.get_metadata(update.prompt_key)
        version = metadata.get("version", 1) if metadata else 1

        logger.info(f"✅ Prompt '{update.prompt_key}' updated to version {version}")

        return PromptUpdateResponse(
            status="success",
            prompt_key=update.prompt_key,
            version=version
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prompt '{update.prompt_key}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update prompt")


@router.post("/reload", response_model=ReloadResponse)
async def reload_prompts(
    token: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    """
    Force reload all prompts from database.

    Useful after manual database changes.
    Requires valid authentication token.
    """
    try:
        prompt_manager.reload_all(db)
        count = prompt_manager.cache_size

        logger.info(f"✅ Reloaded {count} prompts from database")

        return ReloadResponse(
            status="reloaded",
            count=count
        )

    except Exception as e:
        logger.error(f"Error reloading prompts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to reload prompts")


@router.get("/health")
async def health_check():
    """
    Health check endpoint (no auth required).

    Returns cache status and statistics.
    """
    return {
        "status": "ok",
        "cache_size": prompt_manager.cache_size,
        "last_reload": prompt_manager.last_reload_time.isoformat() if prompt_manager.last_reload_time else None,
        "active_sessions": len(active_tokens)
    }
