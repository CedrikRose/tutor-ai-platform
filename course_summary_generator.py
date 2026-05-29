"""
Course Summary Generator

Generates course summaries from analysis data for the last N days.
Uses Amazon Bedrock Kimi K2.5 with context window management.
"""
import logging
import uuid
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from database import (
    SessionLocal,
    ConversationAnalysis,
    StudentKnowledge,
    GeneralFeedback,
    ChatSnapshot,
    ChatSession
)
from config import settings

logger = logging.getLogger(__name__)


class CourseSummaryGenerator:
    """Generates summaries of course activity and student performance."""

    # Kimi K2.5 context window (approximately, leaving buffer)
    MAX_CONTEXT_TOKENS = 120000  # Kimi has 128k, we use 120k for safety
    AVG_CHARS_PER_TOKEN = 4  # Rough estimate

    def __init__(self, db: Session):
        self.db = db
        # Initialize Bedrock client
        import boto3
        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )

    async def generate_course_summary(
        self,
        course_id: uuid.UUID,
        days_back: int = 7
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive summary for a course over the last N days.

        Args:
            course_id: UUID of the course
            days_back: Number of days to look back (1-7)

        Returns:
            Summary dict with text and metadata
        """
        logger.info(f"Generating summary for course {course_id}, last {days_back} days")

        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)

        # Gather data from database
        data = self._gather_analysis_data(course_id, start_date, end_date)

        if not data["analyses"]:
            logger.info(f"No analyses found for course {course_id} in date range")
            return {
                "course_id": str(course_id),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "summary": "Keine Daten für diesen Zeitraum verfügbar.",
                "statistics": data["statistics"]
            }

        # Build context for LLM with token management
        context_text = self._build_summary_context(data, start_date, end_date)

        # Generate summary with Kimi K2.5
        summary_text = await self._generate_summary_with_llm(
            context_text,
            course_id,
            start_date,
            end_date
        )

        return {
            "course_id": str(course_id),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days_back": days_back,
            "summary": summary_text,
            "statistics": data["statistics"],
            "generated_at": datetime.utcnow().isoformat()
        }

    def _gather_analysis_data(
        self,
        course_id: uuid.UUID,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Gather all analysis data from database."""

        # Get all analyses in date range
        analyses = self.db.query(ConversationAnalysis).join(
            ChatSnapshot
        ).filter(
            ChatSnapshot.course_id == course_id,
            ChatSnapshot.snapshot_date >= start_date,
            ChatSnapshot.snapshot_date <= end_date,
            ConversationAnalysis.status == "completed"
        ).order_by(ConversationAnalysis.analyzed_at.asc()).all()

        # Get student knowledge entries
        knowledge_entries = self.db.query(StudentKnowledge).join(
            ConversationAnalysis
        ).join(
            ChatSnapshot
        ).filter(
            ChatSnapshot.course_id == course_id,
            ChatSnapshot.snapshot_date >= start_date,
            ChatSnapshot.snapshot_date <= end_date
        ).all()

        # Get feedback entries
        feedback_entries = self.db.query(GeneralFeedback).filter(
            GeneralFeedback.course_id == course_id,
            GeneralFeedback.created_at >= datetime.combine(start_date, datetime.min.time()),
            GeneralFeedback.created_at <= datetime.combine(end_date, datetime.max.time())
        ).all()

        # Calculate statistics
        unique_students = len(set([a.cookie_id for s in analyses
                                   for a in [self.db.query(ChatSnapshot).filter(
                                       ChatSnapshot.snapshot_id == s.snapshot_id
                                   ).first()] if a]))

        # Get topics from knowledge entries
        topics = {}
        for entry in knowledge_entries:
            concept = entry.struggled_concept
            if concept:
                topics[concept] = topics.get(concept, 0) + 1

        statistics = {
            "total_analyses": len(analyses),
            "unique_students": unique_students,
            "total_knowledge_entries": len(knowledge_entries),
            "total_feedback_entries": len(feedback_entries),
            "top_topics": sorted(topics.items(), key=lambda x: x[1], reverse=True)[:10],
            "feedback_by_type": self._count_feedback_by_type(feedback_entries)
        }

        return {
            "analyses": analyses,
            "knowledge_entries": knowledge_entries,
            "feedback_entries": feedback_entries,
            "statistics": statistics
        }

    def _count_feedback_by_type(self, feedback_entries: List[GeneralFeedback]) -> Dict[str, int]:
        """Count feedback by type."""
        counts = {}
        for feedback in feedback_entries:
            ftype = feedback.feedback_type
            counts[ftype] = counts.get(ftype, 0) + 1
        return counts

    def _build_summary_context(
        self,
        data: Dict[str, Any],
        start_date: date,
        end_date: date
    ) -> str:
        """
        Build context text for LLM with token management.
        Prioritizes recent and important analyses.
        """
        context_parts = []

        # Add statistics overview
        stats = data["statistics"]
        context_parts.append(f"""# Statistiken ({start_date} bis {end_date})

- Anzahl Studenten: {stats['unique_students']}
- Anzahl Analysen: {stats['total_analyses']}
- Wissenseinträge: {stats['total_knowledge_entries']}
- Feedback-Einträge: {stats['total_feedback_entries']}

## Häufigste Themen:
""")
        for topic, count in stats["top_topics"][:10]:
            context_parts.append(f"- {topic}: {count}x")

        context_parts.append("\n## Feedback-Verteilung:")
        for ftype, count in stats["feedback_by_type"].items():
            context_parts.append(f"- {ftype}: {count}x")

        context_parts.append("\n\n# Detaillierte Analysen\n")

        # Add analyses with token budget management
        current_length = sum(len(p) for p in context_parts)
        max_length = self.MAX_CONTEXT_TOKENS * self.AVG_CHARS_PER_TOKEN

        # Add analysis texts (most recent first, truncate if needed)
        for i, analysis in enumerate(reversed(data["analyses"])):
            analysis_text = f"\n## Analyse {i+1} (Session {analysis.session_id})\n"
            analysis_text += f"Datum: {analysis.analyzed_at.strftime('%Y-%m-%d %H:%M')}\n"
            analysis_text += f"Nachrichten: {analysis.message_count}\n\n"
            analysis_text += analysis.analysis_text
            analysis_text += "\n" + "="*80 + "\n"

            # Check if we have space
            if current_length + len(analysis_text) > max_length * 0.8:  # Leave 20% for summary
                logger.info(f"Context limit reached, truncating at analysis {i+1}/{len(data['analyses'])}")
                context_parts.append("\n\n[... Weitere Analysen aus Platzgründen weggelassen ...]\n")
                break

            context_parts.append(analysis_text)
            current_length += len(analysis_text)

        # Add feedback summary
        if data["feedback_entries"]:
            context_parts.append("\n\n# Allgemeines Feedback\n")
            for i, feedback in enumerate(data["feedback_entries"][:20], 1):  # Max 20 feedback items
                context_parts.append(f"\n{i}. [{feedback.feedback_type}] ({feedback.sentiment})")
                context_parts.append(f"   {feedback.feedback_text}\n")

        return "".join(context_parts)

    async def _generate_summary_with_llm(
        self,
        context_text: str,
        course_id: uuid.UUID,
        start_date: date,
        end_date: date
    ) -> str:
        """Generate summary using Kimi K2.5."""

        import json

        prompt = f"""Du bist ein pädagogischer Analyst für einen Professor.

Erstelle eine FAKTENBASIERTE Zusammenfassung der Kursaktivität für den Zeitraum {start_date} bis {end_date}.

**Verfügbare Daten:**
{context_text}

**Deine Aufgabe:**
Erstelle eine objektive Zusammenfassung die folgendes enthält:

1. **Überblick**
   - Wie viele Studenten haben den KI-Tutor genutzt?
   - Für welche Themen und Aufgaben?

2. **Häufige Fragen & Schwierigkeiten**
   - Welche Konzepte bereiteten Schwierigkeiten?
   - Welche Fehler traten häufig auf?
   - Wie wurden sie gelöst?

3. **Allgemeines Feedback**
   - Feedback zu Professor-Erklärungen
   - Feedback zum Tutor-Verhalten
   - Feedback zu Materialien

**WICHTIG:**
- Nur FAKTEN berichten, keine Interpretationen
- KEINE Empfehlungen oder Ratschläge
- KEINE Belehrungen an den Professor
- Nur zusammenfassen was in den Daten steht

**Format:**
Schreibe klar und prägnant. Verwende Markdown-Formatierung.
Fokussiere auf die wichtigsten Erkenntnisse.
"""

        body = json.dumps({
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4,
            "max_tokens": 4000
        })

        response = self.bedrock_runtime.invoke_model(
            modelId="moonshotai.kimi-k2.5",
            body=body,
            contentType="application/json",
            accept="application/json"
        )

        response_body = json.loads(response["body"].read())

        # Extract text based on response format
        if "choices" in response_body:
            summary = response_body["choices"][0]["message"]["content"]
        elif "content" in response_body:
            summary = response_body["content"][0]["text"]
        else:
            summary = str(response_body)

        return summary.strip()


class CourseSummaryStorage:
    """Stores and retrieves course summaries."""

    def __init__(self, db: Session):
        self.db = db

    def store_summary(
        self,
        course_id: uuid.UUID,
        summary_data: Dict[str, Any]
    ) -> uuid.UUID:
        """Store a generated summary in the database."""
        from database import CourseSummary

        summary = CourseSummary(
            course_id=course_id,
            start_date=datetime.fromisoformat(summary_data["start_date"]).date(),
            end_date=datetime.fromisoformat(summary_data["end_date"]).date(),
            days_back=summary_data["days_back"],
            summary_text=summary_data["summary"],
            statistics=summary_data["statistics"],
            generated_at=datetime.fromisoformat(summary_data["generated_at"])
        )

        self.db.add(summary)
        self.db.commit()
        self.db.refresh(summary)

        logger.info(f"Stored summary {summary.summary_id} for course {course_id}")
        return summary.summary_id

    def get_latest_summary(
        self,
        course_id: uuid.UUID,
        days_back: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get the most recent summary for a course."""
        from database import CourseSummary

        query = self.db.query(CourseSummary).filter(
            CourseSummary.course_id == course_id
        )

        if days_back:
            query = query.filter(CourseSummary.days_back == days_back)

        summary = query.order_by(CourseSummary.generated_at.desc()).first()

        if not summary:
            return None

        return {
            "summary_id": str(summary.summary_id),
            "course_id": str(summary.course_id),
            "start_date": summary.start_date.isoformat(),
            "end_date": summary.end_date.isoformat(),
            "days_back": summary.days_back,
            "summary": summary.summary_text,
            "statistics": summary.statistics,
            "generated_at": summary.generated_at.isoformat()
        }


async def generate_and_store_summary(
    course_id: uuid.UUID,
    days_back: int = 7
) -> Dict[str, Any]:
    """
    Generate and store a course summary.

    Args:
        course_id: UUID of course
        days_back: Number of days to look back

    Returns:
        Summary data dict
    """
    db = SessionLocal()

    try:
        # Generate summary
        generator = CourseSummaryGenerator(db)
        summary_data = await generator.generate_course_summary(course_id, days_back)

        # Store summary
        storage = CourseSummaryStorage(db)
        summary_id = storage.store_summary(course_id, summary_data)

        summary_data["summary_id"] = str(summary_id)
        return summary_data

    finally:
        db.close()


if __name__ == "__main__":
    import asyncio
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 2:
        print("Usage: python course_summary_generator.py <course_id> [days_back]")
        sys.exit(1)

    course_id = uuid.UUID(sys.argv[1])
    days_back = int(sys.argv[2]) if len(sys.argv) > 2 else 7

    # Generate summary
    result = asyncio.run(generate_and_store_summary(course_id, days_back))

    print("\n" + "="*80)
    print("COURSE SUMMARY")
    print("="*80)
    print(f"\nCourse: {result['course_id']}")
    print(f"Period: {result['start_date']} to {result['end_date']}")
    print(f"\nStatistics:")
    for key, value in result['statistics'].items():
        print(f"  {key}: {value}")
    print(f"\n{result['summary']}")
    print("\n" + "="*80)
