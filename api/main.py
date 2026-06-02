"""FastAPI application for AI-Tutor chat interface."""
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Cookie, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config import settings
from database import (
    SessionLocal, ChatSession, ChatMessage, Document, ParsedChunk,
    get_db
)
from embeddings import BedrockEmbedder
from retry_utils import BedrockCircuitBreaker
from llm import BedrockLLM, load_system_prompt, save_system_prompt
from rag import RAGRetriever

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances (initialized at startup)
circuit_breaker = None
embedder = None
llm = None
scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    global circuit_breaker, embedder, llm, scheduler
    logger.info("🚀 Starting AI-Tutor API...")

    circuit_breaker = BedrockCircuitBreaker()
    embedder = BedrockEmbedder(circuit_breaker)
    llm = BedrockLLM(settings, circuit_breaker)

    # Initialize prompt manager
    try:
        from prompt_manager import prompt_manager
        from database import SessionLocal
        db = SessionLocal()
        prompt_manager.initialize(db)
        db.close()
        logger.info(f"✓ Prompt manager initialized ({prompt_manager.cache_size} prompts loaded)")
    except Exception as e:
        logger.warning(f"Could not initialize prompt manager: {e}")

    # Initialize chat API v2 globals
    try:
        from api.chat_api_v2 import init_chat_v2_globals
        init_chat_v2_globals(circuit_breaker, embedder, llm)
        logger.info("✓ Chat API v2 globals initialized")
    except Exception as e:
        logger.warning(f"Could not initialize chat_api_v2 globals: {e}")

    # Start automated analysis scheduler
    try:
        from api.scheduler import start_scheduler
        scheduler = start_scheduler()
        logger.info("✓ Automated analysis scheduler started (runs daily at 3:00 AM)")
    except Exception as e:
        logger.warning(f"Could not start scheduler: {e}")

    logger.info("✅ AI-Tutor API started successfully")

    yield

    # Shutdown
    logger.info("👋 Shutting down AI-Tutor API...")

    # Stop scheduler
    if scheduler:
        try:
            from api.scheduler import stop_scheduler
            stop_scheduler(scheduler)
        except Exception as e:
            logger.warning(f"Error stopping scheduler: {e}")


# Create FastAPI app
app = FastAPI(
    title="AI-Tutor API",
    description="Chat API for AI-powered programming tutor",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
cors_origins = settings.cors_origins.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Pydantic Models
# ============================================================================

class SessionCreate(BaseModel):
    """Request to create a new chat session."""
    title: Optional[str] = None


class SessionResponse(BaseModel):
    """Chat session response."""
    session_id: str
    title: Optional[str]
    created_at: datetime
    last_active: datetime
    message_count: int
    total_tokens: int
    course_module: Optional[str]
    homework_id: Optional[str]
    lecture_number: Optional[int]


class SessionUpdate(BaseModel):
    """Update session context."""
    course_module: Optional[str] = None
    homework_id: Optional[str] = None
    lecture_number: Optional[int] = None
    course_id: Optional[str] = None  # For real course selection
    max_lecture_sequence: Optional[int] = None  # Max lecture to include (NULL = all)
    material_types: Optional[List[str]] = None  # List of allowed material types (NULL = all)
    selected_material_id: Optional[str] = None  # Specific material - loads ALL chunks


class MessageResponse(BaseModel):
    """Chat message response."""
    message_id: str
    role: str
    content: str
    timestamp: datetime
    tokens_used: Optional[int]


class ModuleResponse(BaseModel):
    """Course module response."""
    id: str
    name: str
    lecture_count: int


class HomeworkResponse(BaseModel):
    """Homework response."""
    id: str
    name: str
    sequence: int


class LectureResponse(BaseModel):
    """Lecture response."""
    number: int
    name: str


class MaterialResponse(BaseModel):
    """Material response for student chat."""
    material_id: str
    display_name: str
    material_type: str  # 'homework', 'tutorium', 'other'
    sequence_number: Optional[int]


class MaterialsListResponse(BaseModel):
    """List of materials grouped by type."""
    homeworks: List[MaterialResponse]
    tutorien: List[MaterialResponse]
    other: List[MaterialResponse]


class SystemPromptUpdate(BaseModel):
    """Update system prompt."""
    system_prompt: str


class AdminDataResponse(BaseModel):
    """Admin data response."""
    system_prompt: str
    last_rag_context: Optional[str]
    rag_chunks: List[Dict[str, Any]]
    session_context: Optional[Dict[str, Any]]


class CourseListResponse(BaseModel):
    """Course list response for student UI."""
    course_id: str
    course_code: str
    course_name: str
    semester: str
    material_count: int


class CourseMaterialResponse(BaseModel):
    """Material in a course."""
    material_id: str
    display_name: str
    material_type: str
    sequence_number: Optional[int]
    chunk_count: int


class LectureListItem(BaseModel):
    """Single lecture in dropdown."""
    sequence_number: int
    display_name: str
    chunk_count: int


class MaterialTypeOption(BaseModel):
    """Material type with count."""
    material_type: str
    display_name: str
    count: int


class CourseFiltersResponse(BaseModel):
    """Available filters for a course."""
    lectures: List[LectureListItem]
    material_types: List[MaterialTypeOption]


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
            httponly=False,  # Allow client-side access
            samesite="lax"
        )
        logger.info(f"Created new cookie ID: {cookie_id}")
    return cookie_id


def get_session(db: Session, session_id: str, cookie_id: str) -> ChatSession:
    """Get session and verify ownership."""
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    session = db.query(ChatSession).filter(
        ChatSession.session_id == session_uuid,
        ChatSession.cookie_id == cookie_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session


async def calculate_total_tokens(db: Session, session_id: uuid.UUID) -> int:
    """Calculate total tokens used in session."""
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).all()

    total = 0
    for msg in messages:
        if msg.tokens_used:
            total += msg.tokens_used
        else:
            # Estimate if not recorded
            estimated = await llm.count_tokens(msg.content)
            total += estimated

    return total


def generate_session_title(first_message: str) -> str:
    """Generate session title from first message."""
    # Take first 50 chars of user's first message
    title = first_message[:50]
    if len(first_message) > 50:
        title += "..."
    return title


# ============================================================================
# REST Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "AI-Tutor API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/courses", response_model=List[CourseListResponse])
async def list_all_courses(db: Session = Depends(get_db)):
    """List all active courses for students."""
    from sqlalchemy import func
    from database import Course, CourseMaterial

    courses = db.query(
        Course.course_id,
        Course.course_code,
        Course.course_name,
        Course.semester,
        func.count(CourseMaterial.material_id).label('material_count')
    ).outerjoin(
        CourseMaterial,
        (CourseMaterial.course_id == Course.course_id) &
        (CourseMaterial.deleted_at == None) &
        (CourseMaterial.processed_at != None)
    ).filter(
        Course.is_active == True,
        Course.student_access == True
    ).group_by(
        Course.course_id,
        Course.course_code,
        Course.course_name,
        Course.semester
    ).all()

    return [
        CourseListResponse(
            course_id=str(c.course_id),
            course_code=c.course_code,
            course_name=c.course_name,
            semester=c.semester or "N/A",
            material_count=c.material_count
        )
        for c in courses
    ]


@app.get("/api/courses/{course_id}/materials-list", response_model=List[CourseMaterialResponse])
async def list_course_materials_new(course_id: str, db: Session = Depends(get_db)):
    """List materials for a specific course."""
    from sqlalchemy import func
    from database import CourseMaterial, MaterialChunk

    materials = db.query(
        CourseMaterial.material_id,
        CourseMaterial.display_name,
        CourseMaterial.material_type,
        CourseMaterial.sequence_number,
        func.count(MaterialChunk.chunk_id).label('chunk_count')
    ).outerjoin(
        MaterialChunk,
        MaterialChunk.material_id == CourseMaterial.material_id
    ).filter(
        CourseMaterial.course_id == course_id,
        CourseMaterial.deleted_at == None,
        CourseMaterial.processed_at != None
    ).group_by(
        CourseMaterial.material_id,
        CourseMaterial.display_name,
        CourseMaterial.material_type,
        CourseMaterial.sequence_number
    ).order_by(
        CourseMaterial.sequence_number.nullslast()
    ).all()

    return [
        CourseMaterialResponse(
            material_id=str(m.material_id),
            display_name=m.display_name,
            material_type=m.material_type,
            sequence_number=m.sequence_number,
            chunk_count=m.chunk_count
        )
        for m in materials
    ]


@app.get("/api/courses/{course_id}/filters", response_model=CourseFiltersResponse)
async def get_course_filters(course_id: str, db: Session = Depends(get_db)):
    """Get available filters (lectures + material types) for a course."""
    from sqlalchemy import func
    from database import CourseMaterial, MaterialChunk

    # Get all lectures (material_type='lecture_slide' with sequence_number)
    lectures = db.query(
        CourseMaterial.sequence_number,
        CourseMaterial.display_name,
        func.count(MaterialChunk.chunk_id).label('chunk_count')
    ).outerjoin(
        MaterialChunk,
        MaterialChunk.material_id == CourseMaterial.material_id
    ).filter(
        CourseMaterial.course_id == course_id,
        CourseMaterial.material_type == 'lecture_slide',
        CourseMaterial.sequence_number.isnot(None),
        CourseMaterial.deleted_at == None,
        CourseMaterial.processed_at != None
    ).group_by(
        CourseMaterial.sequence_number,
        CourseMaterial.display_name
    ).order_by(
        CourseMaterial.sequence_number
    ).all()

    # Get material type counts (exclude lecture_slide)
    material_type_counts = db.query(
        CourseMaterial.material_type,
        func.count(CourseMaterial.material_id).label('count')
    ).filter(
        CourseMaterial.course_id == course_id,
        CourseMaterial.material_type != 'lecture_slide',
        CourseMaterial.deleted_at == None,
        CourseMaterial.processed_at != None
    ).group_by(
        CourseMaterial.material_type
    ).all()

    # Map material types to display names
    type_display_map = {
        'homework': 'Hausaufgaben',
        'tutorium': 'Tutorien/Übungen',
        'other': 'Sonstiges'
    }

    return CourseFiltersResponse(
        lectures=[
            LectureListItem(
                sequence_number=lec.sequence_number,
                display_name=lec.display_name,
                chunk_count=lec.chunk_count
            )
            for lec in lectures
        ],
        material_types=[
            MaterialTypeOption(
                material_type=mat_type,
                display_name=type_display_map.get(mat_type, mat_type.title()),
                count=count
            )
            for mat_type, count in material_type_counts
        ]
    )


@app.post("/api/sessions", response_model=SessionResponse)
async def create_session(
    body: SessionCreate,
    response: Response,
    cookie_id: Optional[str] = Cookie(None, alias="ai_tutor_user_id"),
    db: Session = Depends(get_db)
):
    """Create a new chat session."""
    cookie_id = get_or_create_cookie_id(response, cookie_id)

    session = ChatSession(
        cookie_id=cookie_id,
        title=body.title or "New Chat"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    logger.info(f"Created session {session.session_id} for cookie {cookie_id}")

    return SessionResponse(
        session_id=str(session.session_id),
        title=session.title,
        created_at=session.created_at,
        last_active=session.last_active,
        message_count=0,
        total_tokens=0,
        course_module=session.course_module,
        homework_id=session.homework_id,
        lecture_number=session.lecture_number
    )


@app.get("/api/sessions", response_model=List[SessionResponse])
async def list_sessions(
    cookie_id: str = Cookie(..., alias="ai_tutor_user_id"),
    db: Session = Depends(get_db)
):
    """List all sessions for this user."""
    sessions = db.query(ChatSession).filter(
        ChatSession.cookie_id == cookie_id
    ).order_by(ChatSession.last_active.desc()).all()

    return [
        SessionResponse(
            session_id=str(s.session_id),
            title=s.title,
            created_at=s.created_at,
            last_active=s.last_active,
            message_count=s.message_count,
            total_tokens=s.total_tokens,
            course_module=s.course_module,
            homework_id=s.homework_id,
            lecture_number=s.lecture_number
        )
        for s in sessions
    ]


@app.get("/api/sessions/{session_id}", response_model=Dict[str, Any])
async def get_session_details(
    session_id: str,
    cookie_id: str = Cookie(..., alias="ai_tutor_user_id"),
    db: Session = Depends(get_db)
):
    """Get session details with message history."""
    session = get_session(db, session_id, cookie_id)

    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session.session_id
    ).order_by(ChatMessage.timestamp.asc()).all()

    return {
        "session_id": str(session.session_id),
        "title": session.title,
        "created_at": session.created_at,
        "last_active": session.last_active,
        "total_tokens": session.total_tokens,
        "message_count": session.message_count,
        "course_module": session.course_module,
        "homework_id": session.homework_id,
        "lecture_number": session.lecture_number,
        "messages": [
            {
                "message_id": str(m.message_id),
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp,
                "tokens_used": m.tokens_used
            }
            for m in messages
        ]
    }


@app.delete("/api/sessions/{session_id}")
async def delete_session(
    session_id: str,
    cookie_id: str = Cookie(..., alias="ai_tutor_user_id"),
    db: Session = Depends(get_db)
):
    """Delete a session."""
    session = get_session(db, session_id, cookie_id)

    db.delete(session)
    db.commit()

    logger.info(f"Deleted session {session_id}")
    return {"status": "deleted"}


@app.patch("/api/sessions/{session_id}/context")
async def update_session_context(
    session_id: str,
    body: SessionUpdate,
    cookie_id: str = Cookie(..., alias="ai_tutor_user_id"),
    db: Session = Depends(get_db)
):
    """Update session context (course/module/homework/lecture selection)."""
    session = get_session(db, session_id, cookie_id)

    # Handle course_id
    if body.course_id is not None:
        import uuid as uuid_module
        try:
            session.course_id = uuid_module.UUID(body.course_id) if body.course_id else None
            logger.info(f"Updated session {session_id} course_id: {body.course_id}")
        except ValueError:
            session.course_id = None

    # Handle max_lecture_sequence
    if body.max_lecture_sequence is not None:
        session.max_lecture_sequence = body.max_lecture_sequence
        logger.info(f"Updated session {session_id} max_lecture_sequence: {body.max_lecture_sequence}")

    # Handle material_types
    if body.material_types is not None:
        session.material_types = body.material_types if body.material_types else None
        logger.info(f"Updated session {session_id} material_types: {body.material_types}")

    # Handle selected_material_id (specific material - loads ALL chunks)
    if body.selected_material_id is not None:
        import uuid as uuid_module
        try:
            session.selected_material_id = uuid_module.UUID(body.selected_material_id) if body.selected_material_id else None
            logger.info(f"Updated session {session_id} selected_material_id: {body.selected_material_id}")
        except ValueError:
            session.selected_material_id = None

    # OLD: Handle course_module (deprecated but still supported)
    if body.course_module is not None:
        session.course_module = body.course_module
    if body.homework_id is not None:
        session.homework_id = body.homework_id
    if body.lecture_number is not None:
        session.lecture_number = body.lecture_number

    session.last_active = datetime.utcnow()
    db.commit()

    logger.info(f"Updated session {session_id} context: course_id={body.course_id}, module={body.course_module}, hw={body.homework_id}, lecture={body.lecture_number}")

    return {"status": "updated"}


@app.get("/api/modules", response_model=List[ModuleResponse])
async def list_modules(db: Session = Depends(get_db)):
    """List available course modules."""
    # Query distinct course modules from documents
    from sqlalchemy import func, distinct

    modules = db.query(
        Document.course_module,
        func.count(distinct(Document.sequence_number)).label('lecture_count')
    ).filter(
        Document.content_type == 'lecture_slides'
    ).group_by(
        Document.course_module
    ).all()

    module_names = {
        "introprog": "Introduction to Programming",
        "prog2": "Programming II"
    }

    return [
        ModuleResponse(
            id=mod.course_module,
            name=module_names.get(mod.course_module, mod.course_module),
            lecture_count=mod.lecture_count
        )
        for mod in modules if mod.course_module
    ]


@app.get("/api/modules/{module_id}/homework", response_model=List[HomeworkResponse])
async def list_homework(module_id: str, db: Session = Depends(get_db)):
    """List homework for a module."""
    homework = db.query(
        Document.sequence_number
    ).filter(
        Document.course_module == module_id,
        Document.content_type.in_(['homework', 'code_impl']),
        Document.sequence_number.isnot(None)
    ).distinct().order_by(Document.sequence_number).all()

    # Generate homework IDs based on module
    hw_prefix = "ha" if module_id == "prog2" else "aufgabe_"

    return [
        HomeworkResponse(
            id=f"{hw_prefix}{seq:02d}",
            name=f"Homework {seq}",
            sequence=seq
        )
        for (seq,) in homework
    ]


@app.get("/api/modules/{module_id}/lectures", response_model=List[LectureResponse])
async def list_lectures(module_id: str, db: Session = Depends(get_db)):
    """List lectures for a module."""
    lectures = db.query(
        Document.sequence_number
    ).filter(
        Document.course_module == module_id,
        Document.content_type == 'lecture_slides',
        Document.sequence_number.isnot(None)
    ).distinct().order_by(Document.sequence_number).all()

    return [
        LectureResponse(
            number=seq,
            name=f"Lecture {seq}"
        )
        for (seq,) in lectures
    ]


@app.get("/api/courses/{course_id}/materials", response_model=MaterialsListResponse)
async def list_course_materials(course_id: str, db: Session = Depends(get_db)):
    """
    List all processed materials for a course, grouped by type.
    Returns homeworks, tutorien, and other materials separately.
    """
    from database import CourseMaterial

    # Get all processed materials (not deleted)
    materials = db.query(CourseMaterial).filter(
        CourseMaterial.course_id == uuid.UUID(course_id),
        CourseMaterial.processed_at.isnot(None),
        CourseMaterial.deleted_at.is_(None)
    ).order_by(
        CourseMaterial.material_type,
        CourseMaterial.sequence_number
    ).all()

    # Group by type
    homeworks = []
    tutorien = []
    other = []

    for material in materials:
        mat_response = MaterialResponse(
            material_id=str(material.material_id),
            display_name=material.display_name,
            material_type=material.material_type,
            sequence_number=material.sequence_number
        )

        if material.material_type == 'homework':
            homeworks.append(mat_response)
        elif material.material_type == 'tutorium':
            tutorien.append(mat_response)
        else:  # 'other' or 'lecture_slide'
            other.append(mat_response)

    return MaterialsListResponse(
        homeworks=homeworks,
        tutorien=tutorien,
        other=other
    )


# ============================================================================
# Admin Endpoints
# ============================================================================

@app.get("/api/admin/session/{session_id}", response_model=AdminDataResponse)
async def get_admin_data(
    session_id: str,
    cookie_id: str = Cookie(..., alias="ai_tutor_user_id"),
    db: Session = Depends(get_db)
):
    """Get admin data for a session (system prompt, RAG context, etc.)."""
    session = get_session(db, session_id, cookie_id)

    # Get last assistant message with RAG chunks
    last_message = db.query(ChatMessage).filter(
        ChatMessage.session_id == session.session_id,
        ChatMessage.role == 'assistant',
        ChatMessage.rag_chunks.isnot(None)
    ).order_by(ChatMessage.timestamp.desc()).first()

    rag_context = None
    rag_chunks = []

    if last_message and last_message.rag_chunks:
        # Retrieve full chunk data with JOIN to get material info
        chunk_ids = [c['chunk_id'] for c in last_message.rag_chunks]

        # Query with JOIN to get course material info
        results = db.query(MaterialChunk, CourseMaterial).join(
            CourseMaterial, MaterialChunk.material_id == CourseMaterial.material_id
        ).filter(
            MaterialChunk.chunk_id.in_(chunk_ids)
        ).all()

        # Create mapping for distances
        distance_map = {c['chunk_id']: c['distance'] for c in last_message.rag_chunks}

        rag_chunks = [
            {
                'chunk_id': str(chunk.chunk_id),
                'file_name': chunk.file_name or material.display_name,
                'content': chunk.content,
                'distance': distance_map.get(str(chunk.chunk_id), 0.0),
                'course_module': None,  # No longer used
                'content_type': material.material_type,
                'is_solution': material.is_solution
            }
            for chunk, material in results
        ]

        # Reconstruct RAG context
        retriever = RAGRetriever(db, embedder)
        rag_context = retriever.format_context_for_llm(rag_chunks)

    return AdminDataResponse(
        system_prompt=load_system_prompt(),
        last_rag_context=rag_context,
        rag_chunks=rag_chunks,
        session_context={
            'course_module': session.course_module,
            'homework_id': session.homework_id,
            'lecture_number': session.lecture_number
        }
    )


@app.put("/api/admin/system-prompt")
async def update_system_prompt(
    body: SystemPromptUpdate,
    cookie_id: str = Cookie(..., alias="ai_tutor_user_id")
):
    """Update the system prompt globally (persists to file)."""
    # Save to file
    success = save_system_prompt(body.system_prompt)

    if success:
        # Reload in the LLM module
        import llm
        llm.SCAFFOLDING_SYSTEM_PROMPT = body.system_prompt

        logger.info(f"System prompt updated and saved by {cookie_id}")

        return {
            "status": "updated",
            "message": "System prompt wurde global gespeichert und wird für alle neuen Chats verwendet"
        }
    else:
        raise HTTPException(status_code=500, detail="Fehler beim Speichern des System Prompts")


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@app.websocket("/ws/chat/{session_id}")
async def chat_websocket(
    websocket: WebSocket,
    session_id: str
):
    """
    WebSocket endpoint for real-time chat with streaming responses.

    Client sends: {"message": "user query"}
    Server streams:
        {"type": "token", "content": "..."} for each token
        {"type": "done", "tokens": 123} when complete
        {"type": "error", "message": "..."} on error
        {"type": "context_update", "usage": 75.5} for context window updates
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for session {session_id}")

    db = SessionLocal()

    try:
        # Verify session exists
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError:
            await websocket.send_json({"type": "error", "message": "Invalid session ID"})
            await websocket.close()
            return

        session = db.query(ChatSession).filter(
            ChatSession.session_id == session_uuid
        ).first()

        if not session:
            await websocket.send_json({"type": "error", "message": "Session not found"})
            await websocket.close()
            return

        # Initialize RAG retriever
        retriever = RAGRetriever(db, embedder)

        while True:
            # Receive user message
            data = await websocket.receive_json()
            user_message = data.get("message", "").strip()

            if not user_message:
                await websocket.send_json({"type": "error", "message": "Empty message"})
                continue

            logger.info(f"Received message in session {session_id}: {user_message[:100]}")

            # Save user message
            user_msg = ChatMessage(
                session_id=session.session_id,
                role="user",
                content=user_message
            )
            db.add(user_msg)
            db.commit()

            # Update session title if first message
            if session.message_count == 0:
                session.title = generate_session_title(user_message)

            session.message_count += 1
            session.last_active = datetime.utcnow()
            db.commit()

            # Check context window
            total_tokens = await calculate_total_tokens(db, session.session_id)
            context_usage = llm.calculate_context_usage(total_tokens)

            await websocket.send_json({
                "type": "context_update",
                "usage": round(context_usage, 2)
            })

            # Auto-summarize if needed
            if await llm.should_summarize(total_tokens, threshold=settings.context_warning_threshold):
                logger.info(f"Context window at {context_usage:.1f}%, triggering summarization")
                await websocket.send_json({
                    "type": "info",
                    "message": "📝 Zusammenfassung älterer Nachrichten..."
                })

                # Get older messages (all except last 5)
                all_messages = db.query(ChatMessage).filter(
                    ChatMessage.session_id == session.session_id
                ).order_by(ChatMessage.timestamp.asc()).all()

                if len(all_messages) > 5:
                    messages_to_summarize = all_messages[:-5]
                    msg_dicts = [{"role": m.role, "content": m.content} for m in messages_to_summarize]

                    summary = await llm.summarize_conversation(msg_dicts)

                    # Delete old messages and replace with summary
                    for msg in messages_to_summarize:
                        db.delete(msg)

                    summary_msg = ChatMessage(
                        session_id=session.session_id,
                        role="assistant",
                        content=f"[Zusammenfassung der vorherigen Konversation]\n\n{summary}"
                    )
                    db.add(summary_msg)
                    db.commit()

                    logger.info(f"Summarized {len(messages_to_summarize)} messages")

            # RAG retrieval
            # Check if specific material is selected (load ALL chunks)
            if session.selected_material_id:
                selected_material_id = str(session.selected_material_id)
                logger.info(f"🎯 Loading ALL chunks from selected material: {selected_material_id}")
                chunks = await retriever.retrieve_all_from_material(selected_material_id)
            else:
                # Normal semantic search
                top_k = 25 if session.homework_id else 10

                # Get filters from session
                course_id = str(session.course_id) if session.course_id else None
                max_lecture_sequence = session.max_lecture_sequence
                material_types = session.material_types

                # Map material type if available (DEPRECATED - use material_types)
                material_type = None
                if session.homework_id:
                    material_type = "homework"

                chunks = await retriever.retrieve(
                    query=user_message,
                    course_id=course_id,
                    material_type=material_type,
                    max_lecture_sequence=max_lecture_sequence,
                    material_types=material_types,
                    top_k=top_k
                )

            logger.info(f"RAG retrieved {len(chunks)} chunks for session {session_id}")
            if chunks:
                for i, chunk in enumerate(chunks[:3], 1):
                    logger.info(f"  Top {i}: {chunk['material_name']}/{chunk['file_name']} (distance={chunk['distance']:.4f}, type={chunk.get('material_type', 'N/A')})")

            rag_context = retriever.format_context_for_llm(chunks) if chunks else None

            # Get conversation history
            messages = db.query(ChatMessage).filter(
                ChatMessage.session_id == session.session_id
            ).order_by(ChatMessage.timestamp.asc()).all()

            message_history = [
                {"role": m.role, "content": m.content}
                for m in messages
            ]

            # Stream LLM response
            assistant_response = ""

            try:
                # Load current system prompt from file
                current_system_prompt = load_system_prompt()

                async for token in llm.stream_chat(
                    messages=message_history,
                    system_prompt=current_system_prompt,
                    rag_context=rag_context,
                    temperature=0.7,
                    max_tokens=2048
                ):
                    assistant_response += token
                    await websocket.send_json({
                        "type": "token",
                        "content": token
                    })

                # Save assistant message
                response_tokens = await llm.count_tokens(assistant_response)

                assistant_msg = ChatMessage(
                    session_id=session.session_id,
                    role="assistant",
                    content=assistant_response,
                    tokens_used=response_tokens,
                    rag_chunks=[
                        {
                            "chunk_id": c["chunk_id"],
                            "file_name": c["file_name"],
                            "distance": c["distance"]
                        }
                        for c in chunks
                    ] if chunks else None
                )
                db.add(assistant_msg)

                session.message_count += 1
                session.total_tokens = await calculate_total_tokens(db, session.session_id)
                session.last_active = datetime.utcnow()
                db.commit()

                # Send completion
                await websocket.send_json({
                    "type": "done",
                    "tokens": response_tokens
                })

                logger.info(f"Completed response in session {session_id} ({response_tokens} tokens)")

            except Exception as e:
                logger.error(f"Error during LLM streaming: {e}", exc_info=True)
                await websocket.send_json({
                    "type": "error",
                    "message": f"Fehler beim Generieren der Antwort: {str(e)}"
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass

    finally:
        db.close()


# ============================================================================
# Include API Routers
# ============================================================================

# Include auth router
try:
    from api.auth_api import router as auth_router
    app.include_router(auth_router)
    logger.info("✓ Auth API included")
except ImportError as e:
    logger.warning(f"Could not import auth_api: {e}")

# Include professor course router
try:
    from api.professor_course_api import router as course_router
    app.include_router(course_router)
    logger.info("✓ Professor Course API included")
except ImportError as e:
    logger.warning(f"Could not import professor_course_api: {e}")

# Include professor material router
try:
    from api.professor_material_api import router as material_router
    app.include_router(material_router)
    logger.info("✓ Professor Material API included")
except ImportError as e:
    logger.warning(f"Could not import professor_material_api: {e}")

# Include professor analysis router
try:
    from api.professor_analysis_api import router as analysis_router
    app.include_router(analysis_router)
    logger.info("✓ Professor Analysis API included")
except ImportError as e:
    logger.warning(f"Could not import professor_analysis_api: {e}")

# Include manual analysis trigger
try:
    from api.manual_course_analysis import router as trigger_router
    app.include_router(trigger_router)
    logger.info("✓ Manual Analysis Trigger API included")
except ImportError as e:
    logger.warning(f"Could not import manual_course_analysis: {e}")

# Include scheduler status API
try:
    from api.scheduler_api import router as scheduler_router
    app.include_router(scheduler_router)
    logger.info("✓ Scheduler Status API included")
except ImportError as e:
    logger.warning(f"Could not import scheduler_api: {e}")

# Include chat API v2 (MUST be after lifespan where globals are created!)
try:
    from api.chat_api_v2 import router as chat_v2_router, init_chat_v2_globals
    app.include_router(chat_v2_router)
    logger.info("✓ Chat API v2 router included")
    # Note: globals will be initialized in lifespan startup
except ImportError as e:
    logger.warning(f"Could not import chat_api_v2: {e}")

# Include prompts admin API
try:
    from api.prompts_api import router as prompts_router
    app.include_router(prompts_router)
    logger.info("✓ Prompts Admin API router included")
except ImportError as e:
    logger.warning(f"Could not import prompts_api: {e}")


# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )
