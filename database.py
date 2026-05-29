"""Database models and session management."""
import uuid
from datetime import datetime, date
from typing import List, Optional
from enum import Enum
from sqlalchemy import (
    create_engine, Column, String, Integer, BigInteger, Boolean,
    Text, TIMESTAMP, Date, ForeignKey, Index, text, ARRAY, DECIMAL,
    Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from pgvector.sqlalchemy import Vector

from config import settings

Base = declarative_base()


class ProcessingStatus(str, Enum):
    """Material processing status enum."""
    UNPROCESSED = "unprocessed"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class ParsingJob(Base):
    """Tracks overall parsing job status."""
    __tablename__ = "parsing_jobs"

    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    total_documents = Column(Integer)
    completed_documents = Column(Integer, default=0)
    failed_documents = Column(Integer, default=0)
    status = Column(String(50), default="pending")  # pending, in_progress, completed, failed
    config_json = Column(JSONB)

    documents = relationship("Document", back_populates="job", cascade="all, delete-orphan")


class Document(Base):
    """Individual document metadata."""
    __tablename__ = "documents"

    doc_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("parsing_jobs.job_id", ondelete="CASCADE"))
    file_path = Column(Text, nullable=False, unique=True)
    file_name = Column(String(255))
    file_size_bytes = Column(BigInteger)
    file_type = Column(String(20))  # pdf, c, java, scala
    course_module = Column(String(100))  # prog2, introprog
    content_type = Column(String(50))  # lecture_slides, homework, solution, code_impl, test
    is_solution = Column(Boolean, default=False)
    sequence_number = Column(Integer)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    metadata_json = Column(JSONB)

    job = relationship("ParsingJob", back_populates="documents")
    parsing_state = relationship("ParsingState", back_populates="document", uselist=False, cascade="all, delete-orphan")
    chunks = relationship("ParsedChunk", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_documents_job_id", "job_id"),
        Index("idx_documents_course_type", "course_module", "content_type"),
    )


class ParsingState(Base):
    """Per-document parsing state for resume capability."""
    __tablename__ = "parsing_state"

    state_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_id = Column(UUID(as_uuid=True), ForeignKey("documents.doc_id", ondelete="CASCADE"), unique=True)
    status = Column(String(50), default="pending")  # pending, in_progress, completed, failed, skipped
    attempt_count = Column(Integer, default=0)
    max_attempts = Column(Integer, default=5)
    last_error = Column(Text)
    last_error_type = Column(String(100))
    last_attempt_at = Column(TIMESTAMP)
    llama_parse_job_id = Column(String(255))
    chunk_count = Column(Integer, default=0)
    parsing_duration_ms = Column(Integer)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    document = relationship("Document", back_populates="parsing_state")

    __table_args__ = (
        Index("idx_parsing_state_status", "status"),
    )


class ParsedChunk(Base):
    """Parsed content chunks for RAG retrieval."""
    __tablename__ = "parsed_chunks"

    chunk_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_id = Column(UUID(as_uuid=True), ForeignKey("documents.doc_id", ondelete="CASCADE"))
    chunk_index = Column(Integer)
    chunk_type = Column(String(50))  # text, code, table, heading
    content = Column(Text, nullable=False)
    metadata_json = Column(JSONB)
    token_count = Column(Integer)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")
    embedding = relationship("ChunkEmbedding", back_populates="chunk", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_parsed_chunks_doc_id", "doc_id"),
    )


class ChunkEmbedding(Base):
    """Vector embeddings for semantic search."""
    __tablename__ = "chunk_embeddings"

    embedding_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("parsed_chunks.chunk_id", ondelete="CASCADE"), unique=True)
    embedding = Column(Vector(1024))  # amazon.titan-embed-text-v2:0 dimension
    model_id = Column(String(100), default="amazon.titan-embed-text-v2:0")
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    chunk = relationship("ParsedChunk", back_populates="embedding")

    __table_args__ = (
        Index(
            "idx_chunk_embeddings_vector",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"}
        ),
    )


# ============================================================
# NEW CHAT STRUCTURE (Frage + Antwort Paare)
# ============================================================

class ChatConversation(Base):
    """Chat conversations - created only when first message is sent."""
    __tablename__ = "chat_conversations"

    conversation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cookie_id = Column(String(255), nullable=False, index=True)

    # Auto-generated title from first question
    title = Column(String(255), nullable=False)

    # Timestamps
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    last_active = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Totals
    exchange_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    # Relationships
    exchanges = relationship("ChatExchange", back_populates="conversation", cascade="all, delete-orphan", order_by="ChatExchange.exchange_number")

    __table_args__ = (
        Index("idx_chat_conversations_cookie", "cookie_id"),
        Index("idx_chat_conversations_last_active", "last_active"),
    )


class ChatExchange(Base):
    """Question + Answer pair with course context and analysis tracking."""
    __tablename__ = "chat_exchanges"

    exchange_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("chat_conversations.conversation_id", ondelete="CASCADE"), nullable=False)

    # Position in conversation
    exchange_number = Column(Integer, nullable=False)

    # Content
    user_question = Column(Text, nullable=False)
    assistant_answer = Column(Text, nullable=False)

    # Course context (what was active when this question was asked)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.course_id", ondelete="SET NULL"), nullable=True)

    # Material filters (what was selected when asking)
    max_lecture_sequence = Column(Integer, nullable=True)
    material_types = Column(JSONB, nullable=True)
    selected_material_id = Column(UUID(as_uuid=True), ForeignKey("course_materials.material_id", ondelete="SET NULL"), nullable=True)

    # RAG context (references to chunks used, NOT the content itself!)
    rag_chunk_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    rag_metadata = Column(JSONB, nullable=True)  # [{chunk_id, file_name, distance, material_name}]

    # Tokens
    tokens_used = Column(Integer, nullable=True)

    # Analysis tracking
    analyzed = Column(Boolean, default=False, nullable=False)
    analyzed_at = Column(TIMESTAMP, nullable=True)

    # Timestamp
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    conversation = relationship("ChatConversation", back_populates="exchanges")

    __table_args__ = (
        Index("idx_chat_exchanges_conversation", "conversation_id", "exchange_number"),
        Index("idx_chat_exchanges_course", "course_id"),
        Index("idx_chat_exchanges_analyzed", "analyzed"),
        Index("idx_chat_exchanges_timestamp", "timestamp"),
    )


# ============================================================
# OLD CHAT STRUCTURE (DEPRECATED - kept for migration)
# ============================================================

class ChatSession(Base):
    """DEPRECATED: Old chat sessions - use ChatConversation instead."""
    __tablename__ = "chat_sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cookie_id = Column(String(255), nullable=False, index=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    last_active = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Optional context selection (DEPRECATED)
    course_module = Column(String(50), nullable=True)
    homework_id = Column(String(50), nullable=True)
    lecture_number = Column(Integer, nullable=True)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.course_id"), nullable=True)
    max_lecture_sequence = Column(Integer, nullable=True)
    material_types = Column(JSONB, nullable=True)
    selected_material_id = Column(UUID(as_uuid=True), ForeignKey("course_materials.material_id"), nullable=True)

    # Metadata
    title = Column(String(255), nullable=True)
    total_tokens = Column(Integer, default=0)
    message_count = Column(Integer, default=0)

    # Export tracking
    exported_at = Column(TIMESTAMP, nullable=True)
    analytics_status = Column(String(50), default="pending")

    # Relationships
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_chat_sessions_cookie", "cookie_id"),
        Index("idx_chat_sessions_module", "course_module"),
        Index("idx_chat_sessions_export", "exported_at", "analytics_status"),
    )


class ChatSnapshotV2(Base):
    """Snapshot of chat exchanges for daily analysis at 4 AM."""
    __tablename__ = "chat_snapshots_v2"

    snapshot_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("chat_conversations.conversation_id", ondelete="CASCADE"), nullable=False)

    # Date when snapshot was created (at 4 AM)
    snapshot_date = Column(Date, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)

    # Range of exchanges included (not message IDs anymore!)
    from_exchange_number = Column(Integer, nullable=False)
    to_exchange_number = Column(Integer, nullable=False)
    exchange_count = Column(Integer, nullable=False)

    # Formatted content for analysis
    chat_content = Column(Text, nullable=False)

    # Metadata
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.course_id"), nullable=True)
    cookie_id = Column(String(255), nullable=False)

    # Analysis status
    analysis_status = Column(String(50), default="pending")  # pending, analyzing, completed, error
    analyzed_at = Column(TIMESTAMP, nullable=True)

    __table_args__ = (
        Index("idx_chat_snapshots_v2_conversation", "conversation_id"),
        Index("idx_chat_snapshots_v2_date", "snapshot_date"),
        Index("idx_chat_snapshots_v2_status", "analysis_status"),
        Index("idx_chat_snapshots_v2_course", "course_id"),
    )


# OLD: Keep for migration
class ChatSnapshot(Base):
    """DEPRECATED: Old snapshot structure - use ChatSnapshotV2 instead."""
    __tablename__ = "chat_snapshots"

    snapshot_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.session_id", ondelete="CASCADE"), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)

    # Snapshot range (which messages are included)
    from_message_id = Column(UUID(as_uuid=True), nullable=False)
    to_message_id = Column(UUID(as_uuid=True), nullable=False)
    message_count = Column(Integer, nullable=False)

    # Chat content (includes RAG context, excludes LLM thinking)
    chat_content = Column(Text, nullable=False)

    # Metadata
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.course_id"), nullable=True)
    cookie_id = Column(String(255), nullable=False)

    # Analysis status
    analysis_status = Column(String(50), default="pending")
    analyzed_at = Column(TIMESTAMP, nullable=True)

    __table_args__ = (
        Index("idx_chat_snapshots_session", "session_id"),
        Index("idx_chat_snapshots_date", "snapshot_date"),
        Index("idx_chat_snapshots_status", "analysis_status"),
        Index("idx_chat_snapshots_course", "course_id"),
    )


class ConversationAnalysisV2(Base):
    """Analysis results from daily conversation processing (new structure)."""
    __tablename__ = "conversation_analyses_v2"

    analysis_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id = Column(UUID(as_uuid=True), ForeignKey("chat_snapshots_v2.snapshot_id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("chat_conversations.conversation_id", ondelete="CASCADE"), nullable=False)
    analyzed_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)

    # Analysis metadata
    primary_model = Column(String(100), nullable=False)
    secondary_model = Column(String(100), nullable=True)
    required_secondary = Column(Boolean, default=False)

    # Analysis results (full text from LLM)
    analysis_text = Column(Text, nullable=False)

    # Metadata
    exchange_count = Column(Integer)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.course_id"), nullable=True)
    tokens_used = Column(Integer, nullable=True)

    # Status
    status = Column(String(50), default="completed")  # completed, error, skipped

    __table_args__ = (
        Index("idx_analyses_v2_snapshot", "snapshot_id"),
        Index("idx_analyses_v2_conversation", "conversation_id"),
        Index("idx_analyses_v2_date", "analyzed_at"),
        Index("idx_analyses_v2_course", "course_id"),
    )




class ConversationFinding(Base):
    """Individual insights from chat analysis (Stage 1)."""
    __tablename__ = "conversation_findings"

    finding_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Links
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("chat_conversations.conversation_id", ondelete="CASCADE"), nullable=False)
    snapshot_id = Column(UUID(as_uuid=True), ForeignKey("chat_snapshots_v2.snapshot_id", ondelete="CASCADE"), nullable=True)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.course_id", ondelete="SET NULL"), nullable=True)

    # Category and content
    category = Column(String(50), nullable=False)  # 'difficulty', 'feedback_professor', 'feedback_chatbot', 'question_pattern'
    title = Column(String(255), nullable=False)  # Short summary
    description = Column(Text, nullable=False)  # Detailed description

    # Reasoning and context
    reasoning = Column(Text, nullable=False)  # Why did the LLM conclude this?
    reference_exchange_numbers = Column(ARRAY(Integer), nullable=False)  # [3, 5, 7] - exchanges that support this

    # Related material (if identifiable)
    related_material_id = Column(UUID(as_uuid=True), ForeignKey("course_materials.material_id", ondelete="SET NULL"), nullable=True)
    related_topic = Column(String(255), nullable=True)  # e.g. "Pointer Arithmetic", "Lecture 5"

    # Metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    analysis_model = Column(String(100), nullable=True)  # Which LLM detected this

    __table_args__ = (
        Index("idx_findings_conversation", "conversation_id"),
        Index("idx_findings_snapshot", "snapshot_id"),
        Index("idx_findings_course", "course_id"),
        Index("idx_findings_category", "category"),
        Index("idx_findings_created", "created_at"),
        Index("idx_findings_material", "related_material_id"),
    )
# OLD: Keep for migration
class ConversationAnalysis(Base):
    """DEPRECATED: Old analysis structure - use ConversationAnalysisV2 instead."""
    __tablename__ = "conversation_analyses"

    analysis_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id = Column(UUID(as_uuid=True), ForeignKey("chat_snapshots.snapshot_id", ondelete="CASCADE"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.session_id", ondelete="CASCADE"), nullable=False)
    analyzed_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)

    # Analysis metadata
    primary_model = Column(String(100), nullable=False)
    secondary_model = Column(String(100), nullable=True)
    required_secondary = Column(Boolean, default=False)

    # Analysis results (full text from LLM)
    analysis_text = Column(Text, nullable=False)

    # Metadata
    message_count = Column(Integer)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.course_id"), nullable=True)
    tokens_used = Column(Integer, nullable=True)

    # Status
    status = Column(String(50), default="completed")

    __table_args__ = (
        Index("idx_analyses_snapshot", "snapshot_id"),
        Index("idx_analyses_session", "session_id"),
        Index("idx_analyses_date", "analyzed_at"),
        Index("idx_analyses_course", "course_id"),
    )


class ChatMessage(Base):
    """Individual messages in chat conversations."""
    __tablename__ = "chat_messages"

    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.session_id", ondelete="CASCADE"), nullable=False)

    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)

    # Token tracking
    tokens_used = Column(Integer, nullable=True)  # From Bedrock response

    # RAG context (stored but NOT shown to user!)
    rag_chunks = Column(JSONB, nullable=True)  # List of retrieved chunk IDs + metadata

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

    __table_args__ = (
        Index("idx_chat_messages_session", "session_id", "timestamp"),
    )


class ConversationExport(Base):
    """Daily conversation export tracking for analytics."""
    __tablename__ = "conversation_exports"

    export_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    export_date = Column(Date, nullable=False, unique=True)  # One export per day
    exported_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Statistics
    sessions_exported = Column(Integer, default=0)
    messages_exported = Column(Integer, default=0)

    # Status
    status = Column(String(50), default="completed")  # completed, failed, in_progress
    error_message = Column(Text, nullable=True)


# ============================================================
# AGGREGATED ANALYTICS MODELS (Phase 3)
# ============================================================


class Topic(Base):
    """Master list of topics/concepts covered in sessions."""
    __tablename__ = "topics"

    topic_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_name = Column(String(255), nullable=False, unique=True)
    category = Column(String(100))
    occurrences = Column(Integer, default=1)
    first_seen = Column(TIMESTAMP, default=datetime.utcnow)
    last_seen = Column(TIMESTAMP, default=datetime.utcnow)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_topics_name", "topic_name"),
        Index("idx_topics_category", "category"),
    )


class DifficultyType(Base):
    """Master list of difficulty/error types."""
    __tablename__ = "difficulty_types"

    difficulty_type_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type_name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    occurrences = Column(Integer, default=1)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_difficulty_types_name", "type_name"),
    )


class StudentKnowledgeV2(Base):
    """Extracted knowledge state from conversation analysis (new structure)."""
    __tablename__ = "student_knowledge_v2"

    knowledge_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("conversation_analyses_v2.analysis_id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("chat_conversations.conversation_id", ondelete="CASCADE"), nullable=False)
    cookie_id = Column(String(255), nullable=False)

    # What student could do
    understood_concepts = Column(ARRAY(Text))

    # What student struggled with
    struggled_concept = Column(String(255), nullable=False)
    error_description = Column(Text, nullable=False)
    solution_description = Column(Text, nullable=False)

    # Reference to exchanges (not messages!)
    reference_exchange_numbers = Column(ARRAY(Integer))  # e.g., [3, 5] means exchanges 3 and 5

    # Metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_student_knowledge_v2_analysis", "analysis_id"),
        Index("idx_student_knowledge_v2_cookie", "cookie_id"),
        Index("idx_student_knowledge_v2_concept", "struggled_concept"),
    )


# OLD: Keep for migration
class StudentKnowledge(Base):
    """DEPRECATED: Old student knowledge structure."""
    __tablename__ = "student_knowledge"

    knowledge_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("conversation_analyses.analysis_id", ondelete="CASCADE"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.session_id", ondelete="CASCADE"), nullable=False)
    cookie_id = Column(String(255), nullable=False)

    # What student could do
    understood_concepts = Column(ARRAY(Text))

    # What student struggled with
    struggled_concept = Column(String(255), nullable=False)
    error_description = Column(Text, nullable=False)
    solution_description = Column(Text, nullable=False)

    # Reference to messages
    reference_message_ids = Column(ARRAY(UUID(as_uuid=True)))

    # Metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_student_knowledge_analysis", "analysis_id"),
        Index("idx_student_knowledge_cookie", "cookie_id"),
        Index("idx_student_knowledge_concept", "struggled_concept"),
    )


class GeneralFeedbackV2(Base):
    """General feedback about professor explanations or tutor behavior (new structure)."""
    __tablename__ = "general_feedback_v2"

    feedback_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("conversation_analyses_v2.analysis_id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("chat_conversations.conversation_id", ondelete="CASCADE"), nullable=False)

    # Feedback type and content
    feedback_type = Column(String(50), nullable=False)  # 'professor_explanation', 'tutor_behavior', 'material_quality', 'other'
    feedback_text = Column(Text, nullable=False)
    sentiment = Column(String(20))  # positive, negative, neutral

    # Reference to exchanges (not messages!)
    reference_exchange_numbers = Column(ARRAY(Integer))

    # Metadata
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.course_id"), nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_general_feedback_v2_analysis", "analysis_id"),
        Index("idx_general_feedback_v2_type", "feedback_type"),
        Index("idx_general_feedback_v2_course", "course_id"),
    )


# OLD: Keep for migration
class GeneralFeedback(Base):
    """DEPRECATED: Old general feedback structure."""
    __tablename__ = "general_feedback"

    feedback_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("conversation_analyses.analysis_id", ondelete="CASCADE"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.session_id", ondelete="CASCADE"), nullable=False)

    # Feedback type and content
    feedback_type = Column(String(50), nullable=False)
    feedback_text = Column(Text, nullable=False)
    sentiment = Column(String(20))

    # Reference to messages
    reference_message_ids = Column(ARRAY(UUID(as_uuid=True)))

    # Metadata
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.course_id"), nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_general_feedback_analysis", "analysis_id"),
        Index("idx_general_feedback_type", "feedback_type"),
        Index("idx_general_feedback_course", "course_id"),
    )


class SessionDifficulty(Base):
    """Links conversation analyses to specific difficulties (DEPRECATED - use StudentKnowledge instead)."""
    __tablename__ = "session_difficulties"

    session_difficulty_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("conversation_analyses.analysis_id", ondelete="CASCADE"), nullable=False)
    difficulty_type_id = Column(UUID(as_uuid=True), ForeignKey("difficulty_types.difficulty_type_id"))

    # Extracted from analysis JSON
    topic = Column(String(255))
    description = Column(Text)
    tutor_response = Column(Text)

    # Metadata
    severity = Column(String(50))
    resolved = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    embedding = relationship("DifficultyEmbedding", back_populates="difficulty", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_session_difficulties_analysis", "analysis_id"),
        Index("idx_session_difficulties_type", "difficulty_type_id"),
        Index("idx_session_difficulties_topic", "topic"),
    )


class FeedbackEntry(Base):
    """Explicit feedback about course, prof, or tutor."""
    __tablename__ = "feedback_entries"

    feedback_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("conversation_analyses.analysis_id", ondelete="CASCADE"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.session_id", ondelete="CASCADE"))

    # Feedback classification
    feedback_type = Column(String(50), nullable=False)  # course, professor, tutor, materials, other
    sentiment = Column(String(20))  # positive, negative, neutral

    # Content
    feedback_text = Column(Text, nullable=False)
    context = Column(Text)

    # Metadata
    course_module = Column(String(50))
    homework_id = Column(String(50))
    extracted_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    embedding = relationship("FeedbackEmbedding", back_populates="feedback", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_feedback_type", "feedback_type"),
        Index("idx_feedback_sentiment", "sentiment"),
        Index("idx_feedback_module", "course_module"),
    )


class LearningProgress(Base):
    """Aggregated learning progress per student (cookie_id)."""
    __tablename__ = "learning_progress"

    progress_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cookie_id = Column(String(255), nullable=False)
    course_module = Column(String(50))

    # Metrics
    total_sessions = Column(Integer, default=0)
    avg_rating = Column(DECIMAL(3, 2))
    total_difficulties = Column(Integer, default=0)
    resolved_difficulties = Column(Integer, default=0)

    # Topics covered
    topics_covered = Column(ARRAY(Text))

    # Time tracking
    first_session = Column(TIMESTAMP)
    last_session = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_learning_progress_cookie", "cookie_id"),
        Index("idx_learning_progress_module", "course_module"),
    )


class ErrorPattern(Base):
    """Recurring error patterns across all students."""
    __tablename__ = "error_patterns"

    pattern_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pattern_name = Column(String(255), nullable=False)
    pattern_type = Column(String(100))

    # Aggregated stats
    total_occurrences = Column(Integer, default=1)
    affected_students = Column(Integer, default=1)
    course_module = Column(String(50))

    # Common context
    common_topics = Column(ARRAY(Text))
    example_description = Column(Text)

    # Metadata
    first_seen = Column(TIMESTAMP, default=datetime.utcnow)
    last_seen = Column(TIMESTAMP, default=datetime.utcnow)
    severity_avg = Column(DECIMAL(3, 2))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_error_patterns_type", "pattern_type"),
        Index("idx_error_patterns_module", "course_module"),
        Index("idx_error_patterns_occurrences", "total_occurrences"),
    )


class DifficultyEmbedding(Base):
    """Vector embeddings for semantic similarity search on difficulties."""
    __tablename__ = "difficulty_embeddings"

    embedding_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_difficulty_id = Column(UUID(as_uuid=True), ForeignKey("session_difficulties.session_difficulty_id", ondelete="CASCADE"), nullable=False)

    # Vector embedding
    embedding = Column(Vector(1024))
    model_id = Column(String(100), default="amazon.titan-embed-text-v2:0")
    embedded_text = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    difficulty = relationship("SessionDifficulty", back_populates="embedding")

    __table_args__ = (
        Index(
            "idx_difficulty_embeddings_vector",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"}
        ),
        Index("idx_difficulty_embeddings_session", "session_difficulty_id"),
    )


class FeedbackEmbedding(Base):
    """Vector embeddings for semantic similarity search on feedback."""
    __tablename__ = "feedback_embeddings"

    embedding_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feedback_id = Column(UUID(as_uuid=True), ForeignKey("feedback_entries.feedback_id", ondelete="CASCADE"), nullable=False)

    # Vector embedding
    embedding = Column(Vector(1024))
    model_id = Column(String(100), default="amazon.titan-embed-text-v2:0")
    embedded_text = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    feedback = relationship("FeedbackEntry", back_populates="embedding")

    __table_args__ = (
        Index(
            "idx_feedback_embeddings_vector",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"}
        ),
        Index("idx_feedback_embeddings_feedback", "feedback_id"),
    )


class CourseReport(Base):
    """Aggregated reports based on conversation findings."""
    __tablename__ = "course_reports"

    report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False)

    # Zeitraum
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days_back = Column(Integer, nullable=False)

    # Bericht-Inhalt
    report_text = Column(Text, nullable=False)

    # Verwendete Erkenntnisse
    finding_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False)

    # Metadaten
    generated_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    generated_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)

    # Statistiken (optional)
    statistics = Column(JSONB, nullable=True)

    __table_args__ = (
        Index("idx_course_reports_course", "course_id"),
        Index("idx_course_reports_date", "end_date"),
        Index("idx_course_reports_generated", "generated_at"),
    )


class CourseSummary(Base):
    """Generated course summaries for professors."""
    __tablename__ = "course_summaries"

    summary_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.course_id"), nullable=False)

    # Date range
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days_back = Column(Integer, nullable=False)

    # Summary content
    summary_text = Column(Text, nullable=False)
    statistics = Column(JSONB, nullable=True)

    # Metadata
    generated_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    generated_by = Column(String(50), default="system")  # system, professor_manual, automation

    __table_args__ = (
        Index("idx_course_summaries_course", "course_id"),
        Index("idx_course_summaries_date", "end_date"),
        Index("idx_course_summaries_generated", "generated_at"),
    )


class EmailAutomation(Base):
    """Email automation configuration for course summaries.

    Logic: Every X days at 8 AM, send summary of last X days.
    Example: days_back=7 → Every 7 days, send summary of last 7 days
    """
    __tablename__ = "email_automations"

    automation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.course_id"), nullable=False)
    professor_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)

    # Configuration
    enabled = Column(Boolean, default=True)
    days_back = Column(Integer, nullable=False)  # Every X days at 8 AM → summary of last X days
    send_time_hour = Column(Integer, default=8)  # Hour to send (always 8 AM)

    # Email recipients
    recipient_emails = Column(ARRAY(String), nullable=False)  # List of email addresses

    # Metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_sent_at = Column(TIMESTAMP, nullable=True)

    __table_args__ = (
        Index("idx_email_automations_course", "course_id"),
        Index("idx_email_automations_professor", "professor_id"),
        Index("idx_email_automations_enabled", "enabled"),
    )


class EmailLog(Base):
    """Log of sent summary emails."""
    __tablename__ = "email_logs"

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    automation_id = Column(UUID(as_uuid=True), ForeignKey("email_automations.automation_id"), nullable=True)
    summary_id = Column(UUID(as_uuid=True), ForeignKey("course_summaries.summary_id"), nullable=True)

    # Email details
    recipient_emails = Column(ARRAY(String), nullable=False)
    subject = Column(String(255), nullable=False)

    # Status
    sent_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    status = Column(String(50), default="sent")  # sent, failed, pending
    error_message = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_email_logs_automation", "automation_id"),
        Index("idx_email_logs_sent", "sent_at"),
        Index("idx_email_logs_status", "status"),
    )


class DailyStats(Base):
    """Daily aggregated statistics for dashboards."""
    __tablename__ = "daily_stats"

    stat_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stat_date = Column(Date, nullable=False, unique=True)

    # Session stats
    total_sessions = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    avg_session_length = Column(DECIMAL(5, 2))

    # Analysis stats
    total_analyses = Column(Integer, default=0)
    avg_rating = Column(DECIMAL(3, 2))

    # Difficulty stats
    total_difficulties = Column(Integer, default=0)
    unique_difficulty_types = Column(Integer, default=0)
    top_difficulty_type = Column(String(255))

    # Feedback stats
    total_feedback_entries = Column(Integer, default=0)
    positive_feedback = Column(Integer, default=0)
    negative_feedback = Column(Integer, default=0)

    # Module breakdown
    module_stats = Column(JSONB)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_daily_stats_date", "stat_date"),
    )


# Database engine and session management
engine = create_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database schema."""
    # Create pgvector extension first
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully")


def get_pending_documents(db: Session, job_id: uuid.UUID) -> List[Document]:
    """Get documents with pending or failed status."""
    return (
        db.query(Document)
        .join(ParsingState)
        .filter(
            Document.job_id == job_id,
            ParsingState.status.in_(["pending", "failed"]),
            ParsingState.attempt_count < ParsingState.max_attempts
        )
        .order_by(Document.file_size_bytes.asc())  # Smallest first
        .all()
    )


def update_job_progress(db: Session, job_id: uuid.UUID):
    """Update job progress counters."""
    job = db.query(ParsingJob).filter(ParsingJob.job_id == job_id).first()
    if not job:
        return

    completed = (
        db.query(ParsingState)
        .join(Document)
        .filter(
            Document.job_id == job_id,
            ParsingState.status == "completed"
        )
        .count()
    )

    failed = (
        db.query(ParsingState)
        .join(Document)
        .filter(
            Document.job_id == job_id,
            ParsingState.status == "failed"
        )
        .count()
    )

    job.completed_documents = completed
    job.failed_documents = failed
    job.updated_at = datetime.utcnow()

    if completed + failed >= job.total_documents:
        job.status = "completed" if failed == 0 else "completed_with_errors"
    elif completed > 0:
        job.status = "in_progress"

    db.commit()


def get_job_status(db: Session, job_id: uuid.UUID) -> dict:
    """Get comprehensive job status."""
    job = db.query(ParsingJob).filter(ParsingJob.job_id == job_id).first()
    if not job:
        return None

    status_counts = (
        db.query(ParsingState.status, text("COUNT(*)"))
        .join(Document)
        .filter(Document.job_id == job_id)
        .group_by(ParsingState.status)
        .all()
    )

    return {
        "job_id": str(job.job_id),
        "name": job.name,
        "status": job.status,
        "total_documents": job.total_documents,
        "completed_documents": job.completed_documents,
        "failed_documents": job.failed_documents,
        "status_breakdown": {status: count for status, count in status_counts},
        "created_at": job.created_at,
        "updated_at": job.updated_at
    }


# ============================================================
# PROFESSOR DASHBOARD MODELS (Authentication & Multi-Tenancy)
# ============================================================


class User(Base):
    """Professor user accounts."""
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)

    # Profile
    full_name = Column(String(255))
    institution = Column(String(255))

    # Role & Status
    role = Column(String(50), default="professor")
    is_active = Column(Boolean, default=False)  # Requires admin approval

    # Timestamps
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    last_login = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Email verification
    email_verified = Column(Boolean, default=False)
    verification_token = Column(Text)
    verification_token_expires = Column(TIMESTAMP)

    # Relationships
    owned_courses = relationship("Course", back_populates="owner", cascade="all, delete-orphan")
    course_permissions = relationship("CoursePermission", foreign_keys="CoursePermission.user_id", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
        Index("idx_users_active", "is_active"),
    )


class Course(Base):
    """Courses (multi-tenancy)."""
    __tablename__ = "courses"

    course_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Course info
    course_code = Column(String(100), nullable=False)
    course_name = Column(String(255), nullable=False)
    semester = Column(String(50))
    academic_year = Column(Integer)

    # Ownership
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    # Settings
    is_active = Column(Boolean, default=True)
    student_access = Column(Boolean, default=True)
    max_lecture_number = Column(Integer)

    # Metadata
    description = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Report settings
    report_days_back = Column(Integer, default=7)
    report_recipient_emails = Column(ARRAY(String), default=[])
    report_emails_enabled = Column(Boolean, default=False)

    # Relationships
    owner = relationship("User", back_populates="owned_courses")
    permissions = relationship("CoursePermission", back_populates="course", cascade="all, delete-orphan")
    homeworks = relationship("Homework", back_populates="course", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_courses_owner", "owner_user_id"),
        Index("idx_courses_code", "course_code"),
        Index("idx_courses_active", "is_active"),
    )


class CoursePermission(Base):
    """Shared course access permissions."""
    __tablename__ = "course_permissions"

    permission_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    # Permission level
    permission_level = Column(String(50), nullable=False)  # owner, editor, viewer

    # Metadata
    granted_at = Column(TIMESTAMP, default=datetime.utcnow)
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))

    # Relationships
    course = relationship("Course", back_populates="permissions")
    user = relationship("User", foreign_keys=[user_id], back_populates="course_permissions")

    __table_args__ = (
        Index("idx_course_permissions_course", "course_id"),
        Index("idx_course_permissions_user", "user_id"),
    )


class Homework(Base):
    """Homework assignments."""
    __tablename__ = "homeworks"

    homework_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False)

    # Homework info
    homework_code = Column(String(100), nullable=False)
    title = Column(String(255))
    description = Column(Text)
    sequence_number = Column(Integer)

    # Dates
    start_date = Column(TIMESTAMP)
    due_date = Column(TIMESTAMP)

    # Points
    max_points = Column(DECIMAL(5, 2))

    # Status
    is_published = Column(Boolean, default=False)

    # Metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))

    # Relationships
    course = relationship("Course", back_populates="homeworks")
    homework_documents = relationship("HomeworkDocument", back_populates="homework", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_homeworks_course", "course_id"),
        Index("idx_homeworks_sequence", "course_id", "sequence_number"),
        Index("idx_homeworks_published", "is_published"),
    )


class HomeworkDocument(Base):
    """Link documents to homework."""
    __tablename__ = "homework_documents"

    homework_document_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    homework_id = Column(UUID(as_uuid=True), ForeignKey("homeworks.homework_id", ondelete="CASCADE"), nullable=False)
    doc_id = Column(UUID(as_uuid=True), ForeignKey("documents.doc_id", ondelete="CASCADE"), nullable=False)

    display_order = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    homework = relationship("Homework", back_populates="homework_documents")
    document = relationship("Document")

    __table_args__ = (
        Index("idx_homework_documents_homework", "homework_id"),
        Index("idx_homework_documents_doc", "doc_id"),
    )


class FileUploadSession(Base):
    """Track file upload sessions with LLM pre-analysis."""
    __tablename__ = "file_upload_sessions"

    upload_session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False)

    # Upload metadata
    total_files = Column(Integer, default=0)
    analyzed_files = Column(Integer, default=0)
    confirmed_files = Column(Integer, default=0)

    # Status
    status = Column(String(50), default="analyzing")

    # Timestamps
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    completed_at = Column(TIMESTAMP)

    # Relationships
    file_analyses = relationship("FilePreAnalysis", back_populates="upload_session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_upload_sessions_user", "user_id"),
        Index("idx_upload_sessions_course", "course_id"),
    )


class FilePreAnalysis(Base):
    """LLM pre-analysis results for uploaded files."""
    __tablename__ = "file_pre_analysis"

    pre_analysis_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_session_id = Column(UUID(as_uuid=True), ForeignKey("file_upload_sessions.upload_session_id", ondelete="CASCADE"), nullable=False)

    # File info
    original_filename = Column(String(500), nullable=False)
    file_size_bytes = Column(BigInteger)
    file_path = Column(Text)  # Temporary path (S3 or local)

    # LLM analysis results
    content_type = Column(String(50))
    importance = Column(String(50))
    sequence_number = Column(Integer)
    analysis_reason = Column(Text)

    # User decision
    user_decision = Column(String(50), default="pending")

    # Linked document
    doc_id = Column(UUID(as_uuid=True), ForeignKey("documents.doc_id", ondelete="SET NULL"))

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    upload_session = relationship("FileUploadSession", back_populates="file_analyses")

    __table_args__ = (
        Index("idx_file_pre_analysis_session", "upload_session_id"),
        Index("idx_file_pre_analysis_decision", "user_decision"),
    )


class CourseMaterial(Base):
    """Course materials with 1-hour review period."""
    __tablename__ = "course_materials"

    material_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)

    # Material info
    material_type = Column(String(50), nullable=False)  # lecture_slide, homework, tutorium, other
    display_name = Column(String(255), nullable=False)
    original_filename = Column(Text, nullable=False)
    sequence_number = Column(Integer)

    # File count (for multiple files per material)
    file_count = Column(Integer, default=1)

    # Processing status (process on demand) - processed_at is the main indicator
    processed_at = Column(TIMESTAMP)

    # Timestamps
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    deleted_at = Column(TIMESTAMP)

    # Relationships
    files = relationship("MaterialFile", back_populates="material", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_course_materials_course", "course_id"),
        Index("idx_course_materials_type", "material_type"),
    )


class MaterialFile(Base):
    """Individual files belonging to a course material."""
    __tablename__ = "material_files"

    file_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id = Column(UUID(as_uuid=True), ForeignKey("course_materials.material_id", ondelete="CASCADE"), nullable=False)

    # File info
    filename = Column(Text, nullable=False)
    file_path = Column(Text, nullable=False)
    file_size = Column(BigInteger)
    file_type = Column(String(50))

    # Timestamps
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    material = relationship("CourseMaterial", back_populates="files")

    __table_args__ = (
        Index("idx_material_files_material", "material_id"),
    )


class MaterialChunk(Base):
    """Chunks from processed LECTURE materials with embeddings (only for lecture_slide type)."""
    __tablename__ = "material_chunks"

    chunk_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id = Column(UUID(as_uuid=True), ForeignKey("course_materials.material_id", ondelete="CASCADE"), nullable=False)
    file_id = Column(UUID(as_uuid=True), ForeignKey("material_files.file_id", ondelete="CASCADE"))

    # Content
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)

    # Metadata
    source_type = Column(String(50))  # 'pdf', 'code', 'text'
    file_name = Column(Text)
    start_char = Column(Integer)
    end_char = Column(Integer)

    # Embedding
    embedding = Column(Vector(1024))  # Amazon Titan v2 uses 1024 dimensions

    # Timestamps
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_material_chunks_material", "material_id"),
        Index("idx_material_chunks_file", "file_id"),
        Index(
            "idx_material_chunks_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"}
        ),
    )


class MaterialContent(Base):
    """Full content storage for non-lecture materials (homework, tutorium, other).

    These materials are NOT chunked because they are included entirely in the context
    when selected by the student. Only important files (as determined by LLM) are stored.
    """
    __tablename__ = "material_contents"

    content_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id = Column(UUID(as_uuid=True), ForeignKey("course_materials.material_id", ondelete="CASCADE"), nullable=False)
    file_id = Column(UUID(as_uuid=True), ForeignKey("material_files.file_id", ondelete="CASCADE"), nullable=True)

    # Content (full markdown for PDFs, or full file content for code/text files)
    content = Column(Text, nullable=False)

    # Metadata
    source_type = Column(String(50), nullable=False)  # 'pdf_markdown', 'code', 'text', 'data'
    file_name = Column(Text, nullable=False)
    file_size = Column(BigInteger)  # Size of the content in bytes

    # LLM importance assessment
    importance_reason = Column(Text)  # Why this file was included

    # Timestamps
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_material_contents_material", "material_id"),
        Index("idx_material_contents_file", "file_id"),
        Index("idx_material_contents_source_type", "source_type"),
    )


class MaterialProcessingLog(Base):
    """Log of material processing stages."""
    __tablename__ = "material_processing_log"

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id = Column(UUID(as_uuid=True), ForeignKey("course_materials.material_id", ondelete="CASCADE"), nullable=False)
    file_id = Column(UUID(as_uuid=True), ForeignKey("material_files.file_id", ondelete="SET NULL"))

    # Processing details
    stage = Column(String(50), nullable=False)  # 'file_analysis', 'parsing', 'chunking', 'embedding'
    status = Column(String(50), nullable=False)  # 'started', 'completed', 'failed', 'skipped'

    # Results
    message = Column(Text)
    details = Column(JSONB)

    # Timestamps
    started_at = Column(TIMESTAMP, default=datetime.utcnow)
    completed_at = Column(TIMESTAMP)

    __table_args__ = (
        Index("idx_processing_log_material", "material_id"),
        Index("idx_processing_log_status", "status", "stage"),
    )


class RefreshToken(Base):
    """JWT refresh tokens."""
    __tablename__ = "refresh_tokens"

    token_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    token_hash = Column(Text, nullable=False)

    # Metadata
    expires_at = Column(TIMESTAMP, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    last_used_at = Column(TIMESTAMP)

    # Device info
    user_agent = Column(Text)
    ip_address = Column(INET)

    # Revocation
    is_revoked = Column(Boolean, default=False)
    revoked_at = Column(TIMESTAMP)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        Index("idx_refresh_tokens_user", "user_id"),
        Index("idx_refresh_tokens_hash", "token_hash"),
        Index("idx_refresh_tokens_expires", "expires_at"),
    )


class AuditLog(Base):
    """Security audit log."""
    __tablename__ = "audit_log"

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Who & When
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"))
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)

    # What
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(UUID(as_uuid=True))

    # Details
    details = Column(JSONB)

    # Request info
    ip_address = Column(INET)
    user_agent = Column(Text)

    __table_args__ = (
        Index("idx_audit_log_user", "user_id"),
        Index("idx_audit_log_timestamp", "timestamp"),
        Index("idx_audit_log_action", "action"),
    )
