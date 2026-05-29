"""
Professor Analysis API

Endpoints for accessing analysis results, summaries, and automations.
"""
import uuid
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from database import (
    get_db,
    ConversationAnalysis,
    StudentKnowledge,
    GeneralFeedback,
    ChatSnapshot,
    ChatSession,
    ChatMessage,
    CourseSummary,
    EmailAutomation,
    EmailLog,
    Course,
    ConversationFinding,
    ChatConversation,
    ChatExchange,
    CourseReport,
    User
)
from auth import get_current_user as get_current_professor
from course_summary_generator import generate_and_store_summary
from report_generator import create_report_generator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/professor", tags=["professor-analysis"])


# ============================================================================
# Pydantic Models
# ============================================================================

class TopicCount(BaseModel):
    topic: str
    count: int


class AnalysisListItem(BaseModel):
    analysis_id: str
    session_id: str
    analyzed_at: datetime
    message_count: int
    course_id: Optional[str]
    primary_model: str
    required_secondary: bool
    tokens_used: Optional[int]


class AnalysisDetail(BaseModel):
    analysis_id: str
    session_id: str
    snapshot_id: str
    analyzed_at: datetime
    analysis_text: str
    message_count: int
    course_id: Optional[str]
    primary_model: str
    secondary_model: Optional[str]
    required_secondary: bool
    tokens_used: Optional[int]


class StudentKnowledgeItem(BaseModel):
    knowledge_id: str
    session_id: str
    cookie_id: str
    understood_concepts: List[str]
    struggled_concept: str
    error_description: str
    solution_description: str
    reference_message_ids: List[str]
    created_at: datetime


class FeedbackItem(BaseModel):
    feedback_id: str
    session_id: str
    feedback_type: str
    feedback_text: str
    sentiment: Optional[str]
    reference_message_ids: List[str]
    created_at: datetime


class ChatMessageItem(BaseModel):
    message_id: str
    role: str
    content: str
    timestamp: datetime
    rag_chunks: Optional[dict]


class ChatSessionDetail(BaseModel):
    session_id: str
    cookie_id: str
    course_id: Optional[str]
    title: Optional[str]
    created_at: datetime
    last_active: datetime
    message_count: int
    messages: List[ChatMessageItem]


class SummaryStatistics(BaseModel):
    total_analyses: int
    unique_students: int
    total_knowledge_entries: int
    total_feedback_entries: int
    top_topics: List[TopicCount]
    feedback_by_type: dict


class CourseSummaryItem(BaseModel):
    summary_id: str
    course_id: str
    start_date: date
    end_date: date
    days_back: int
    summary_text: str
    statistics: Optional[SummaryStatistics]
    generated_at: datetime
    generated_by: str


class GenerateSummaryRequest(BaseModel):
    course_id: str
    days_back: int = 7


class EmailAutomationConfig(BaseModel):
    course_id: str
    days_back: int  # Every X days → summary of last X days (1-7)
    recipient_emails: List[EmailStr]


class EmailAutomationItem(BaseModel):
    automation_id: str
    course_id: str
    enabled: bool
    days_back: int
    send_time_hour: int
    recipient_emails: List[str]
    created_at: datetime
    last_sent_at: Optional[datetime]
    next_send_date: Optional[date] = None  # Calculated field


# ============================================================================
# Analyses Endpoints
# ============================================================================

@router.get("/analyses", response_model=List[AnalysisListItem])
def get_analyses(
    course_id: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """
    Get list of analyses with optional filters.
    """
    query = db.query(ConversationAnalysis)

    # Filter by course
    if course_id:
        query = query.filter(ConversationAnalysis.course_id == uuid.UUID(course_id))

    # Filter by date range
    if date_from:
        query = query.filter(ConversationAnalysis.analyzed_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(ConversationAnalysis.analyzed_at <= datetime.combine(date_to, datetime.max.time()))

    # Order and paginate
    query = query.order_by(ConversationAnalysis.analyzed_at.desc())
    analyses = query.offset(offset).limit(limit).all()

    return [
        AnalysisListItem(
            analysis_id=str(a.analysis_id),
            session_id=str(a.session_id),
            analyzed_at=a.analyzed_at,
            message_count=a.message_count,
            course_id=str(a.course_id) if a.course_id else None,
            primary_model=a.primary_model,
            required_secondary=a.required_secondary,
            tokens_used=a.tokens_used
        )
        for a in analyses
    ]


@router.get("/analyses/{analysis_id}", response_model=AnalysisDetail)
def get_analysis_detail(
    analysis_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """
    Get detailed analysis by ID.
    """
    analysis = db.query(ConversationAnalysis).filter(
        ConversationAnalysis.analysis_id == uuid.UUID(analysis_id)
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return AnalysisDetail(
        analysis_id=str(analysis.analysis_id),
        session_id=str(analysis.session_id),
        snapshot_id=str(analysis.snapshot_id),
        analyzed_at=analysis.analyzed_at,
        analysis_text=analysis.analysis_text,
        message_count=analysis.message_count,
        course_id=str(analysis.course_id) if analysis.course_id else None,
        primary_model=analysis.primary_model,
        secondary_model=analysis.secondary_model,
        required_secondary=analysis.required_secondary,
        tokens_used=analysis.tokens_used
    )


# ============================================================================
# Student Knowledge Endpoints
# ============================================================================

@router.get("/student-knowledge", response_model=List[StudentKnowledgeItem])
def get_student_knowledge(
    course_id: Optional[str] = None,
    cookie_id: Optional[str] = None,
    topic: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """
    Get student knowledge entries with optional filters.

    This shows which students had questions or needed help on which topics.
    Each entry links to the original chat via session_id.
    """
    query = db.query(StudentKnowledge).join(ConversationAnalysis)

    # Filter by course
    if course_id:
        query = query.filter(ConversationAnalysis.course_id == uuid.UUID(course_id))

    # Filter by student
    if cookie_id:
        query = query.filter(StudentKnowledge.cookie_id == cookie_id)

    # Filter by topic (search in struggled_concept)
    if topic:
        query = query.filter(StudentKnowledge.struggled_concept.ilike(f"%{topic}%"))

    # Order and paginate
    query = query.order_by(StudentKnowledge.created_at.desc())
    entries = query.offset(offset).limit(limit).all()

    return [
        StudentKnowledgeItem(
            knowledge_id=str(e.knowledge_id),
            session_id=str(e.session_id),
            cookie_id=e.cookie_id,
            understood_concepts=e.understood_concepts or [],
            struggled_concept=e.struggled_concept,
            error_description=e.error_description,
            solution_description=e.solution_description,
            reference_message_ids=[str(mid) for mid in (e.reference_message_ids or [])],
            created_at=e.created_at
        )
        for e in entries
    ]


@router.get("/topics-overview")
def get_topics_overview(
    course_id: str,
    days_back: int = 7,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """
    Get overview of topics students asked about or needed help with.

    Returns:
    - List of topics with count of students who asked about them
    - Links to sessions where topic was discussed
    """
    # Calculate date range
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)

    # Get knowledge entries in date range
    entries = db.query(StudentKnowledge).join(ConversationAnalysis).filter(
        ConversationAnalysis.course_id == uuid.UUID(course_id),
        ConversationAnalysis.analyzed_at >= datetime.combine(start_date, datetime.min.time()),
        ConversationAnalysis.analyzed_at <= datetime.combine(end_date, datetime.max.time())
    ).all()

    # Group by topic
    topics = {}
    for entry in entries:
        topic = entry.struggled_concept
        if topic not in topics:
            topics[topic] = {
                "topic": topic,
                "count": 0,
                "students": set(),
                "sessions": set()
            }
        topics[topic]["count"] += 1
        topics[topic]["students"].add(entry.cookie_id)
        topics[topic]["sessions"].add(str(entry.session_id))

    # Format response
    result = []
    for topic, data in topics.items():
        result.append({
            "topic": topic,
            "student_count": len(data["students"]),
            "occurrence_count": data["count"],
            "session_ids": list(data["sessions"])
        })

    # Sort by student count
    result.sort(key=lambda x: x["student_count"], reverse=True)

    return {
        "course_id": course_id,
        "date_range": {"start": start_date, "end": end_date},
        "topics": result
    }


# ============================================================================
# Feedback Endpoints
# ============================================================================

@router.get("/feedback", response_model=List[FeedbackItem])
def get_feedback(
    course_id: Optional[str] = None,
    feedback_type: Optional[str] = None,
    sentiment: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """
    Get feedback entries with optional filters.
    """
    query = db.query(GeneralFeedback)

    # Filter by course
    if course_id:
        query = query.filter(GeneralFeedback.course_id == uuid.UUID(course_id))

    # Filter by type
    if feedback_type:
        query = query.filter(GeneralFeedback.feedback_type == feedback_type)

    # Filter by sentiment
    if sentiment:
        query = query.filter(GeneralFeedback.sentiment == sentiment)

    # Order and paginate
    query = query.order_by(GeneralFeedback.created_at.desc())
    entries = query.offset(offset).limit(limit).all()

    return [
        FeedbackItem(
            feedback_id=str(e.feedback_id),
            session_id=str(e.session_id),
            feedback_type=e.feedback_type,
            feedback_text=e.feedback_text,
            sentiment=e.sentiment,
            reference_message_ids=[str(mid) for mid in (e.reference_message_ids or [])],
            created_at=e.created_at
        )
        for e in entries
    ]


# ============================================================================
# Chat Viewer Endpoint
# ============================================================================

@router.get("/chat/{session_id}", response_model=ChatSessionDetail)
def get_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """
    Get original chat session with all messages.
    Used when professor wants to read the full context.
    """
    session = db.query(ChatSession).filter(
        ChatSession.session_id == uuid.UUID(session_id)
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get all messages
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session.session_id
    ).order_by(ChatMessage.timestamp.asc()).all()

    return ChatSessionDetail(
        session_id=str(session.session_id),
        cookie_id=session.cookie_id,
        course_id=str(session.course_id) if session.course_id else None,
        title=session.title,
        created_at=session.created_at,
        last_active=session.last_active,
        message_count=session.message_count,
        messages=[
            ChatMessageItem(
                message_id=str(m.message_id),
                role=m.role,
                content=m.content,
                timestamp=m.timestamp,
                rag_chunks=m.rag_chunks
            )
            for m in messages
        ]
    )


# ============================================================================
# Summary Endpoints
# ============================================================================

@router.post("/summaries/generate", response_model=CourseSummaryItem)
async def generate_summary(
    request: GenerateSummaryRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """
    Generate a course summary for the last N days.
    """
    try:
        summary_data = await generate_and_store_summary(
            course_id=uuid.UUID(request.course_id),
            days_back=request.days_back
        )

        return CourseSummaryItem(
            summary_id=summary_data["summary_id"],
            course_id=summary_data["course_id"],
            start_date=datetime.fromisoformat(summary_data["start_date"]).date(),
            end_date=datetime.fromisoformat(summary_data["end_date"]).date(),
            days_back=summary_data["days_back"],
            summary_text=summary_data["summary"],
            statistics=SummaryStatistics(**summary_data["statistics"]) if summary_data.get("statistics") else None,
            generated_at=datetime.fromisoformat(summary_data["generated_at"]),
            generated_by="professor_manual"
        )
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summaries", response_model=List[CourseSummaryItem])
def get_summaries(
    course_id: str,
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """
    Get historical summaries for a course.
    """
    summaries = db.query(CourseSummary).filter(
        CourseSummary.course_id == uuid.UUID(course_id)
    ).order_by(CourseSummary.generated_at.desc()).limit(limit).all()

    return [
        CourseSummaryItem(
            summary_id=str(s.summary_id),
            course_id=str(s.course_id),
            start_date=s.start_date,
            end_date=s.end_date,
            days_back=s.days_back,
            summary_text=s.summary_text,
            statistics=s.statistics,
            generated_at=s.generated_at,
            generated_by=s.generated_by
        )
        for s in summaries
    ]


# ============================================================================
# Email Automation Endpoints
# ============================================================================

@router.post("/email-automation", response_model=EmailAutomationItem)
def create_email_automation(
    config: EmailAutomationConfig,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """
    Create a new email automation.

    Logic: Every X days at 8 AM → summary of last X days
    Example: days_back=7 → Every 7 days, get summary of last 7 days
    """
    # Validate days_back
    if config.days_back < 1 or config.days_back > 7:
        raise HTTPException(status_code=400, detail="days_back must be between 1 and 7")

    automation = EmailAutomation(
        course_id=uuid.UUID(config.course_id),
        owner_user_id=current_user.user_id,
        days_back=config.days_back,
        send_time_hour=8,  # Always 8 AM
        recipient_emails=config.recipient_emails
    )

    db.add(automation)
    db.commit()
    db.refresh(automation)

    # Calculate next send date
    next_send = None
    if automation.last_sent_at:
        next_send = automation.last_sent_at.date() + timedelta(days=automation.days_back)
    else:
        next_send = date.today()  # First send today if possible

    return EmailAutomationItem(
        automation_id=str(automation.automation_id),
        course_id=str(automation.course_id),
        enabled=automation.enabled,
        days_back=automation.days_back,
        send_time_hour=automation.send_time_hour,
        recipient_emails=automation.recipient_emails,
        created_at=automation.created_at,
        last_sent_at=automation.last_sent_at,
        next_send_date=next_send
    )


@router.get("/email-automation", response_model=List[EmailAutomationItem])
def get_email_automations(
    course_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """
    Get all email automations for current professor.
    """
    query = db.query(EmailAutomation).filter(
        EmailAutomation.owner_user_id == current_user.user_id
    )

    if course_id:
        query = query.filter(EmailAutomation.course_id == uuid.UUID(course_id))

    automations = query.order_by(EmailAutomation.created_at.desc()).all()

    result = []
    for a in automations:
        # Calculate next send date
        next_send = None
        if a.last_sent_at:
            next_send = a.last_sent_at.date() + timedelta(days=a.days_back)
        else:
            next_send = date.today()

        result.append(EmailAutomationItem(
            automation_id=str(a.automation_id),
            course_id=str(a.course_id),
            enabled=a.enabled,
            days_back=a.days_back,
            send_time_hour=a.send_time_hour,
            recipient_emails=a.recipient_emails,
            created_at=a.created_at,
            last_sent_at=a.last_sent_at,
            next_send_date=next_send
        ))

    return result


@router.patch("/email-automation/{automation_id}/toggle")
def toggle_email_automation(
    automation_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """
    Enable/disable an email automation.
    """
    automation = db.query(EmailAutomation).filter(
        EmailAutomation.automation_id == uuid.UUID(automation_id),
        EmailAutomation.owner_user_id == current_user.user_id
    ).first()

    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")

    automation.enabled = not automation.enabled
    db.commit()

    return {"automation_id": str(automation.automation_id), "enabled": automation.enabled}


@router.delete("/email-automation/{automation_id}")
def delete_email_automation(
    automation_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """
    Delete an email automation.
    """
    automation = db.query(EmailAutomation).filter(
        EmailAutomation.automation_id == uuid.UUID(automation_id),
        EmailAutomation.owner_user_id == current_user.user_id
    ).first()

    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")

    db.delete(automation)
    db.commit()

    return {"message": "Automation deleted"}


# ============================================================================
# V2 Findings API (New Analysis System)
# ============================================================================

class FindingItem(BaseModel):
    finding_id: str
    conversation_id: str
    category: str
    title: str
    description: str
    reasoning: str
    reference_exchange_numbers: List[int]
    related_material_id: Optional[str]
    related_topic: Optional[str]
    created_at: datetime
    analysis_model: Optional[str]

    # Populated fields
    conversation_title: Optional[str] = None
    exchange_count: int = 0


class FindingWithExchanges(BaseModel):
    finding: FindingItem
    exchanges: List[dict]  # The actual exchange texts


@router.get("/findings")
def get_findings(
    course_id: str,
    category: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """
    Get findings for a course with optional filters.
    """
    # Verify course belongs to professor
    course = db.query(Course).filter(
        Course.course_id == uuid.UUID(course_id),
        Course.owner_user_id == current_user.user_id
    ).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Build query
    query = db.query(ConversationFinding).filter(
        ConversationFinding.course_id == uuid.UUID(course_id)
    )

    if category:
        query = query.filter(ConversationFinding.category == category)

    if from_date:
        query = query.filter(ConversationFinding.created_at >= datetime.combine(from_date, datetime.min.time()))

    if to_date:
        query = query.filter(ConversationFinding.created_at <= datetime.combine(to_date, datetime.max.time()))

    # Get total count
    total_count = query.count()

    # Get findings
    findings = query.order_by(ConversationFinding.created_at.desc()).limit(limit).offset(offset).all()

    # Populate conversation titles
    result = []
    for finding in findings:
        conversation = db.query(ChatConversation).filter(
            ChatConversation.conversation_id == finding.conversation_id
        ).first()

        result.append(FindingItem(
            finding_id=str(finding.finding_id),
            conversation_id=str(finding.conversation_id),
            category=finding.category,
            title=finding.title,
            description=finding.description,
            reasoning=finding.reasoning,
            reference_exchange_numbers=finding.reference_exchange_numbers,
            related_material_id=str(finding.related_material_id) if finding.related_material_id else None,
            related_topic=finding.related_topic,
            created_at=finding.created_at,
            analysis_model=finding.analysis_model,
            conversation_title=conversation.title if conversation else "Unknown",
            exchange_count=len(finding.reference_exchange_numbers)
        ))

    return {
        "findings": result,
        "total_count": total_count,
        "limit": limit,
        "offset": offset
    }


@router.get("/findings/{finding_id}")
def get_finding_detail(
    finding_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """
    Get a specific finding with its referenced exchanges.
    """
    finding = db.query(ConversationFinding).filter(
        ConversationFinding.finding_id == uuid.UUID(finding_id)
    ).first()

    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    # Verify course belongs to professor
    course = db.query(Course).filter(
        Course.course_id == finding.course_id,
        Course.owner_user_id == current_user.user_id
    ).first()

    if not course:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get conversation
    conversation = db.query(ChatConversation).filter(
        ChatConversation.conversation_id == finding.conversation_id
    ).first()

    # Get referenced exchanges
    exchanges = db.query(ChatExchange).filter(
        ChatExchange.conversation_id == finding.conversation_id,
        ChatExchange.exchange_number.in_(finding.reference_exchange_numbers)
    ).order_by(ChatExchange.exchange_number).all()

    # Format exchanges
    exchanges_data = []
    for exchange in exchanges:
        exchanges_data.append({
            "exchange_number": exchange.exchange_number,
            "user_question": exchange.user_question,
            "assistant_answer": exchange.assistant_answer,
            "timestamp": exchange.timestamp
        })

    finding_item = FindingItem(
        finding_id=str(finding.finding_id),
        conversation_id=str(finding.conversation_id),
        category=finding.category,
        title=finding.title,
        description=finding.description,
        reasoning=finding.reasoning,
        reference_exchange_numbers=finding.reference_exchange_numbers,
        related_material_id=str(finding.related_material_id) if finding.related_material_id else None,
        related_topic=finding.related_topic,
        created_at=finding.created_at,
        analysis_model=finding.analysis_model,
        conversation_title=conversation.title if conversation else "Unknown",
        exchange_count=len(finding.reference_exchange_numbers)
    )

    return FindingWithExchanges(
        finding=finding_item,
        exchanges=exchanges_data
    )


@router.get("/findings/stats/by-category")
def get_findings_stats(
    course_id: str,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """
    Get findings statistics grouped by category.
    """
    # Verify course belongs to professor
    course = db.query(Course).filter(
        Course.course_id == uuid.UUID(course_id),
        Course.owner_user_id == current_user.user_id
    ).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Build query
    query = db.query(ConversationFinding).filter(
        ConversationFinding.course_id == uuid.UUID(course_id)
    )

    if from_date:
        query = query.filter(ConversationFinding.created_at >= datetime.combine(from_date, datetime.min.time()))

    if to_date:
        query = query.filter(ConversationFinding.created_at <= datetime.combine(to_date, datetime.max.time()))

    findings = query.all()

    # Group by category
    stats = {}
    for finding in findings:
        if finding.category not in stats:
            stats[finding.category] = 0
        stats[finding.category] += 1

    return {
        "total_findings": len(findings),
        "by_category": [{"category": k, "count": v} for k, v in stats.items()]
    }


# ============================================================================
# REPORTS ENDPOINTS
# ============================================================================

class GenerateReportRequest(BaseModel):
    course_id: str
    end_date: Optional[date] = None
    days_back: Optional[int] = None


class ReportSettingsUpdate(BaseModel):
    report_days_back: Optional[int] = None
    report_recipient_emails: Optional[List[EmailStr]] = None
    report_emails_enabled: Optional[bool] = None

    class Config:
        from_attributes = True


class ReportStatistics(BaseModel):
    total_findings: int
    by_category: dict
    unique_conversations: int
    topics_mentioned: List[dict]


class ReportListItem(BaseModel):
    report_id: str
    course_id: str
    start_date: date
    end_date: date
    days_back: int
    generated_at: datetime
    statistics: Optional[ReportStatistics] = None

    class Config:
        from_attributes = True


class ReportDetail(ReportListItem):
    report_text: str
    finding_ids: List[str]

    class Config:
        from_attributes = True


@router.post("/reports/generate", response_model=ReportDetail)
async def generate_report(
    request: GenerateReportRequest,
    current_user: User = Depends(get_current_professor),
    db: Session = Depends(get_db)
):
    """
    Generate a new report for a course based on findings in a date range.

    Args:
        request: Report generation request with course_id, end_date, days_back
        current_user: Authenticated user
        db: Database session

    Returns:
        Generated report with full text
    """
    try:
        course_id = uuid.UUID(request.course_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid course_id format")

    # Check course exists and user has access
    course = db.query(Course).filter(Course.course_id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if course.owner_user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="You don't have access to this course")

    # Determine days_back (request > course setting > default 7)
    days_back = request.days_back or course.report_days_back or 7

    # Validate days_back
    if days_back < 1 or days_back > 50:
        raise HTTPException(status_code=400, detail="days_back must be between 1 and 50")

    # Generate report
    try:
        generator = create_report_generator(db)
        report = await generator.generate_report(
            course_id=course_id,
            days_back=days_back,
            end_date=request.end_date,
            generated_by=current_user.user_id
        )

        logger.info(f"Report {report.report_id} generated for course {course_id} by user {current_user.user_id}")

        return ReportDetail(
            report_id=str(report.report_id),
            course_id=str(report.course_id),
            start_date=report.start_date,
            end_date=report.end_date,
            days_back=report.days_back,
            generated_at=report.generated_at,
            report_text=report.report_text,
            finding_ids=[str(fid) for fid in report.finding_ids],
            statistics=report.statistics
        )

    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.get("/reports", response_model=List[ReportListItem])
async def get_reports(
    course_id: str,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_professor),
    db: Session = Depends(get_db)
):
    """
    Get list of reports for a course (newest first).

    Args:
        course_id: Course UUID
        limit: Max number of reports to return
        offset: Pagination offset
        current_user: Authenticated user
        db: Database session

    Returns:
        List of report summaries (without full text)
    """
    try:
        course_uuid = uuid.UUID(course_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid course_id format")

    # Check course access
    course = db.query(Course).filter(Course.course_id == course_uuid).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if course.owner_user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="You don't have access to this course")

    # Fetch reports
    reports = db.query(CourseReport).filter(
        CourseReport.course_id == course_uuid
    ).order_by(
        CourseReport.generated_at.desc()
    ).limit(limit).offset(offset).all()

    return [
        ReportListItem(
            report_id=str(r.report_id),
            course_id=str(r.course_id),
            start_date=r.start_date,
            end_date=r.end_date,
            days_back=r.days_back,
            generated_at=r.generated_at,
            statistics=r.statistics
        )
        for r in reports
    ]


@router.get("/reports/{report_id}", response_model=ReportDetail)
async def get_report_detail(
    report_id: str,
    current_user: User = Depends(get_current_professor),
    db: Session = Depends(get_db)
):
    """
    Get full report including text.

    Args:
        report_id: Report UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Complete report with text
    """
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report_id format")

    # Fetch report
    report = db.query(CourseReport).filter(
        CourseReport.report_id == report_uuid
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Check course access
    course = db.query(Course).filter(Course.course_id == report.course_id).first()
    if not course or course.owner_user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="You don't have access to this report")

    return ReportDetail(
        report_id=str(report.report_id),
        course_id=str(report.course_id),
        start_date=report.start_date,
        end_date=report.end_date,
        days_back=report.days_back,
        generated_at=report.generated_at,
        report_text=report.report_text,
        finding_ids=[str(fid) for fid in report.finding_ids],
        statistics=report.statistics
    )


@router.patch("/courses/{course_id}/report-settings")
async def update_report_settings(
    course_id: str,
    settings: ReportSettingsUpdate,
    current_user: User = Depends(get_current_professor),
    db: Session = Depends(get_db)
):
    """
    Update report settings for a course.

    Args:
        course_id: Course UUID
        settings: Report settings to update
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message
    """
    try:
        course_uuid = uuid.UUID(course_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid course_id format")

    # Fetch course
    course = db.query(Course).filter(Course.course_id == course_uuid).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if course.owner_user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="You don't have access to this course")

    # Validate days_back
    if settings.report_days_back is not None:
        if settings.report_days_back < 1 or settings.report_days_back > 50:
            raise HTTPException(status_code=400, detail="report_days_back must be between 1 and 50")
        course.report_days_back = settings.report_days_back

    # Validate email list
    if settings.report_recipient_emails is not None:
        if len(settings.report_recipient_emails) > 3:
            raise HTTPException(status_code=400, detail="Maximum 3 email addresses allowed")
        course.report_recipient_emails = settings.report_recipient_emails

    # Update email enabled flag
    if settings.report_emails_enabled is not None:
        course.report_emails_enabled = settings.report_emails_enabled

    # Save changes
    db.commit()

    logger.info(f"Report settings updated for course {course_id} by user {current_user.user_id}")

    return {
        "message": "Report settings updated successfully",
        "report_days_back": course.report_days_back,
        "report_recipient_emails": course.report_recipient_emails,
        "report_emails_enabled": course.report_emails_enabled
    }
