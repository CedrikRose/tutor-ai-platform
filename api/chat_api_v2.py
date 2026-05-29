"""
New Chat API (v2) - Frage+Antwort Paare
- Conversations are created only when first message is sent
- Question + Answer are stored together atomically
- Each exchange tracks course/material context
- Analysis tracking per exchange
"""
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Cookie, Response, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from database import (
    get_db, SessionLocal, ChatConversation, ChatExchange, CourseMaterial
)
from embeddings import BedrockEmbedder
from retry_utils import BedrockCircuitBreaker
from llm import BedrockLLM, load_system_prompt
from rag import RAGRetriever

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2", tags=["chat-v2"])

# Global instances (will be initialized)
circuit_breaker = None
embedder = None
llm = None


def init_chat_v2_globals(cb, emb, llm_instance):
    """Initialize global instances from main app."""
    global circuit_breaker, embedder, llm
    circuit_breaker = cb
    embedder = emb
    llm = llm_instance


# ============================================================================
# Pydantic Models
# ============================================================================

class ConversationListResponse(BaseModel):
    """Conversation in list view."""
    conversation_id: str
    title: str
    exchange_count: int
    total_tokens: int
    created_at: datetime
    last_active: datetime


class ExchangeResponse(BaseModel):
    """Single exchange (question + answer)."""
    exchange_id: str
    exchange_number: int
    user_question: str
    assistant_answer: str
    course_id: Optional[str]
    max_lecture_sequence: Optional[int]
    material_types: Optional[List[str]]
    selected_material_id: Optional[str]
    timestamp: datetime
    tokens_used: Optional[int]
    analyzed: bool


class ConversationDetailResponse(BaseModel):
    """Full conversation with exchanges."""
    conversation_id: str
    title: str
    exchange_count: int
    total_tokens: int
    created_at: datetime
    last_active: datetime
    exchanges: List[ExchangeResponse]


class CourseContextUpdate(BaseModel):
    """Update course/material context for current chat."""
    course_id: Optional[str] = None
    max_lecture_sequence: Optional[int] = None
    material_types: Optional[List[str]] = None
    selected_material_id: Optional[str] = None


# ============================================================================
# Helper Functions
# ============================================================================

def get_or_create_cookie_id(response: Response, cookie_id: Optional[str] = None) -> str:
    """Get or create cookie ID for session tracking."""
    if not cookie_id:
        cookie_id = str(uuid.uuid4())
        response.set_cookie(
            key="ai_tutor_user_id",
            value=cookie_id,
            max_age=31536000,  # 1 year
            httponly=False,
            samesite="lax"
        )
        logger.info(f"Created new cookie ID: {cookie_id}")
    return cookie_id


def generate_title_from_question(question: str) -> str:
    """Generate conversation title from first question."""
    title = question[:60]
    if len(question) > 60:
        title += "..."
    return title


def get_conversation(db: Session, conversation_id: str, cookie_id: str) -> ChatConversation:
    """Get conversation and verify ownership via cookie."""
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")

    conversation = db.query(ChatConversation).filter(
        ChatConversation.conversation_id == conv_uuid,
        ChatConversation.cookie_id == cookie_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation


# ============================================================================
# REST Endpoints
# ============================================================================

@router.get("/conversations", response_model=List[ConversationListResponse])
async def list_conversations(
    cookie_id: str = Cookie(..., alias="ai_tutor_user_id"),
    db: Session = Depends(get_db)
):
    """List all conversations for this user (cookie-based)."""
    conversations = db.query(ChatConversation).filter(
        ChatConversation.cookie_id == cookie_id
    ).order_by(ChatConversation.last_active.desc()).all()

    return [
        ConversationListResponse(
            conversation_id=str(c.conversation_id),
            title=c.title,
            exchange_count=c.exchange_count,
            total_tokens=c.total_tokens,
            created_at=c.created_at,
            last_active=c.last_active
        )
        for c in conversations
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation_detail(
    conversation_id: str,
    cookie_id: str = Cookie(..., alias="ai_tutor_user_id"),
    db: Session = Depends(get_db)
):
    """Get full conversation with all exchanges."""
    conversation = get_conversation(db, conversation_id, cookie_id)

    exchanges = db.query(ChatExchange).filter(
        ChatExchange.conversation_id == conversation.conversation_id
    ).order_by(ChatExchange.exchange_number.asc()).all()

    return ConversationDetailResponse(
        conversation_id=str(conversation.conversation_id),
        title=conversation.title,
        exchange_count=conversation.exchange_count,
        total_tokens=conversation.total_tokens,
        created_at=conversation.created_at,
        last_active=conversation.last_active,
        exchanges=[
            ExchangeResponse(
                exchange_id=str(e.exchange_id),
                exchange_number=e.exchange_number,
                user_question=e.user_question,
                assistant_answer=e.assistant_answer,
                course_id=str(e.course_id) if e.course_id else None,
                max_lecture_sequence=e.max_lecture_sequence,
                material_types=e.material_types,
                selected_material_id=str(e.selected_material_id) if e.selected_material_id else None,
                timestamp=e.timestamp,
                tokens_used=e.tokens_used,
                analyzed=e.analyzed
            )
            for e in exchanges
        ]
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    cookie_id: str = Cookie(..., alias="ai_tutor_user_id"),
    db: Session = Depends(get_db)
):
    """Delete a conversation and all its exchanges."""
    conversation = get_conversation(db, conversation_id, cookie_id)

    db.delete(conversation)
    db.commit()

    logger.info(f"Deleted conversation {conversation_id}")
    return {"status": "deleted"}


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@router.websocket("/ws/chat")
async def chat_websocket_v2(
    websocket: WebSocket
):
    """
    WebSocket endpoint for new chat structure.

    Client sends:
    {
        "conversation_id": "uuid" or null (to create new),
        "message": "user question",
        "course_context": {
            "course_id": "uuid",
            "max_lecture_sequence": 5,
            "material_types": ["homework", "tutorium"],
            "selected_material_id": "uuid" or null
        }
    }

    Server streams:
        {"type": "token", "content": "..."}
        {"type": "done", "exchange_id": "uuid", "tokens": 123}
        {"type": "error", "message": "..."}
    """
    await websocket.accept()

    # Extract cookie from WebSocket headers
    cookie_id = None
    if "cookie" in websocket.headers:
        cookies = websocket.headers["cookie"]
        for cookie in cookies.split(";"):
            if "ai_tutor_user_id=" in cookie:
                cookie_id = cookie.split("ai_tutor_user_id=")[1].strip()
                break

    if not cookie_id:
        # Generate new cookie ID if not present
        cookie_id = str(uuid.uuid4())

    logger.info(f"WebSocket v2 connected for cookie {cookie_id}")

    db = Session(bind=SessionLocal.kw['bind'])

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            user_message = data.get("message", "").strip()
            conversation_id_str = data.get("conversation_id")
            course_context = data.get("course_context", {})

            if not user_message:
                await websocket.send_json({"type": "error", "message": "Empty message"})
                continue

            logger.info(f"Received message: {user_message[:100]}")

            # Get or create conversation
            conversation = None
            exchange_number = 1

            if conversation_id_str:
                # Existing conversation
                try:
                    conv_uuid = uuid.UUID(conversation_id_str)
                    conversation = db.query(ChatConversation).filter(
                        ChatConversation.conversation_id == conv_uuid,
                        ChatConversation.cookie_id == cookie_id
                    ).first()

                    if not conversation:
                        await websocket.send_json({"type": "error", "message": "Conversation not found"})
                        continue

                    exchange_number = conversation.exchange_count + 1

                except ValueError:
                    await websocket.send_json({"type": "error", "message": "Invalid conversation ID"})
                    continue
            else:
                # NEW CONVERSATION - create only now when first message arrives!
                conversation = ChatConversation(
                    cookie_id=cookie_id,
                    title=generate_title_from_question(user_message)
                )
                db.add(conversation)
                db.flush()  # Get conversation_id without committing yet

                logger.info(f"Created new conversation {conversation.conversation_id}")

            # Extract course context
            course_id = None
            if course_context.get("course_id"):
                try:
                    course_id = uuid.UUID(course_context["course_id"])
                except ValueError:
                    pass

            max_lecture_seq = course_context.get("max_lecture_sequence")
            material_types = course_context.get("material_types")
            selected_material_id = None
            if course_context.get("selected_material_id"):
                try:
                    selected_material_id = uuid.UUID(course_context["selected_material_id"])
                except ValueError:
                    pass

            # RAG retrieval
            retriever = RAGRetriever(db, embedder)
            chunks = []

            if selected_material_id:
                # Load ALL chunks from specific material
                logger.info(f"Loading ALL chunks from material {selected_material_id}")
                material_chunks = await retriever.retrieve_all_from_material(str(selected_material_id))

                # Additionally retrieve relevant lecture chunks via semantic search
                logger.info(f"Additionally retrieving relevant lecture chunks for context")
                lecture_chunks = await retriever.retrieve(
                    query=user_message,
                    course_id=str(course_id) if course_id else None,
                    max_lecture_sequence=max_lecture_seq,
                    material_types=["lecture_slide"],  # Only lectures
                    top_k=5  # Fewer since we already have the full material
                )

                # Combine: material first (priority), then relevant lectures
                chunks = material_chunks + lecture_chunks
                logger.info(f"RAG retrieved {len(material_chunks)} chunks from material + {len(lecture_chunks)} lecture chunks")
            else:
                # Semantic search
                top_k = 10
                chunks = await retriever.retrieve(
                    query=user_message,
                    course_id=str(course_id) if course_id else None,
                    max_lecture_sequence=max_lecture_seq,
                    material_types=material_types,
                    top_k=top_k
                )
                logger.info(f"RAG retrieved {len(chunks)} chunks")

            rag_context = retriever.format_context_for_llm(chunks) if chunks else None

            # Get conversation history for context
            previous_exchanges = db.query(ChatExchange).filter(
                ChatExchange.conversation_id == conversation.conversation_id
            ).order_by(ChatExchange.exchange_number.asc()).all()

            # Build message history
            message_history = []
            for ex in previous_exchanges:
                message_history.append({"role": "user", "content": ex.user_question})
                message_history.append({"role": "assistant", "content": ex.assistant_answer})

            # Add current question
            message_history.append({"role": "user", "content": user_message})

            # Stream LLM response
            assistant_response = ""
            system_prompt = load_system_prompt()

            try:
                async for token in llm.stream_chat(
                    messages=message_history,
                    system_prompt=system_prompt,
                    rag_context=rag_context,
                    temperature=0.7,
                    max_tokens=2048
                ):
                    assistant_response += token
                    await websocket.send_json({
                        "type": "token",
                        "content": token
                    })

                # Count tokens
                response_tokens = await llm.count_tokens(assistant_response)

                # Save exchange ATOMICALLY (question + answer together!)
                exchange = ChatExchange(
                    conversation_id=conversation.conversation_id,
                    exchange_number=exchange_number,
                    user_question=user_message,
                    assistant_answer=assistant_response,
                    course_id=course_id,
                    max_lecture_sequence=max_lecture_seq,
                    material_types=material_types,
                    selected_material_id=selected_material_id,
                    rag_chunk_ids=[uuid.UUID(c["chunk_id"]) for c in chunks] if chunks else None,
                    rag_metadata=chunks,
                    tokens_used=response_tokens,
                    analyzed=False  # Will be analyzed at 4 AM
                )
                db.add(exchange)

                # Update conversation totals
                conversation.exchange_count = exchange_number
                conversation.total_tokens += response_tokens
                conversation.last_active = datetime.utcnow()

                db.commit()

                # Send completion
                await websocket.send_json({
                    "type": "done",
                    "exchange_id": str(exchange.exchange_id),
                    "conversation_id": str(conversation.conversation_id),
                    "tokens": response_tokens
                })

                logger.info(f"Saved exchange {exchange_number} in conversation {conversation.conversation_id}")

            except Exception as e:
                logger.error(f"Error during LLM streaming: {e}", exc_info=True)
                db.rollback()
                await websocket.send_json({
                    "type": "error",
                    "message": f"Fehler beim Generieren der Antwort: {str(e)}"
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket v2 disconnected for cookie {cookie_id}")

    except Exception as e:
        logger.error(f"WebSocket v2 error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass

    finally:
        db.close()
