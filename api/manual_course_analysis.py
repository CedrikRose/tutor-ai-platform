"""
Manual Course Analysis Trigger

Endpoint to trigger analysis for all unanalyzed exchanges in a course.
"""
import uuid
import logging
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import (
    get_db,
    Course,
    ChatConversation,
    ChatExchange,
    ChatSnapshotV2,
    ConversationAnalysisV2,
    ConversationFinding
)
from auth import get_current_user as get_current_professor

# Import the analysis components
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from daily_chat_analysis_v2 import SnapshotCreator, ChatAnalyzer, FindingExtractor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/professor", tags=["professor-analysis"])


class TriggerAnalysisRequest(BaseModel):
    course_id: str


class TriggerAnalysisResponse(BaseModel):
    success: bool
    message: str
    snapshots_created: int
    analyses_completed: int
    findings_created: int


@router.post("/trigger-analysis", response_model=TriggerAnalysisResponse)
def trigger_course_analysis(
    request: TriggerAnalysisRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """
    Manually trigger analysis for all unanalyzed exchanges in a course.

    This will:
    1. Create snapshots for conversations with unanalyzed exchanges (max 10 exchanges per snapshot)
    2. Analyze snapshots using LLM
    3. Extract findings
    4. Mark exchanges as analyzed
    """
    course_id = uuid.UUID(request.course_id)

    # Verify course belongs to professor
    course = db.query(Course).filter(
        Course.course_id == course_id,
        Course.owner_user_id == current_user.user_id
    ).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found or access denied")

    logger.info(f"Manual analysis triggered for course {course_id} by professor {current_user.user_id}")

    try:
        # Step 1: Create snapshots for unanalyzed exchanges
        snapshot_creator = SnapshotCreator(db)

        # Get conversations with unanalyzed exchanges for this course
        conversations_to_analyze = (
            db.query(ChatConversation)
            .join(ChatExchange, ChatConversation.conversation_id == ChatExchange.conversation_id)
            .filter(
                ChatExchange.analyzed == False,
                ChatExchange.course_id == course_id
            )
            .distinct()
            .all()
        )

        logger.info(f"Found {len(conversations_to_analyze)} conversations with unanalyzed exchanges")

        snapshots = []
        for conversation in conversations_to_analyze:
            # Create snapshot (will use max 10 exchanges as per updated limit)
            snapshot = snapshot_creator._create_snapshot_for_conversation(
                conversation,
                date.today()
            )
            if snapshot:
                snapshots.append(snapshot)

        db.commit()
        logger.info(f"Created {len(snapshots)} snapshots")

        # Step 2: Analyze snapshots
        analyzer = ChatAnalyzer(db)
        analyses_with_responses = []

        for snapshot in snapshots:
            try:
                snapshot.analysis_status = "analyzing"
                db.commit()

                analysis, llm_response = analyzer._analyze_snapshot(snapshot)
                analyses_with_responses.append((analysis, llm_response))

                snapshot.analysis_status = "completed"
                snapshot.analyzed_at = datetime.utcnow()

            except Exception as e:
                logger.error(f"Error analyzing snapshot {snapshot.snapshot_id}: {e}", exc_info=True)
                snapshot.analysis_status = "error"

            db.commit()

        logger.info(f"Completed {len(analyses_with_responses)} analyses")

        # Step 3: Extract findings
        extractor = FindingExtractor(db)
        total_findings = 0

        for analysis, llm_response in analyses_with_responses:
            findings = extractor.extract_findings_from_analysis(analysis, llm_response)
            total_findings += len(findings)

        db.commit()
        logger.info(f"Extracted {total_findings} findings")

        return TriggerAnalysisResponse(
            success=True,
            message=f"Analysis completed successfully",
            snapshots_created=len(snapshots),
            analyses_completed=len(analyses_with_responses),
            findings_created=total_findings
        )

    except Exception as e:
        logger.error(f"Error during manual analysis: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
