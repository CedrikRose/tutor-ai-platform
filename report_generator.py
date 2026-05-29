"""Report Generator for aggregating conversation findings into comprehensive reports."""
import asyncio
import logging
import uuid
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
from collections import Counter
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database import CourseReport, ConversationFinding, Course
from llm import BedrockLLM
from config import settings
from retry_utils import BedrockCircuitBreaker

logger = logging.getLogger(__name__)

REPORT_SYSTEM_PROMPT = """Du bist ein Analysesystem für Lern-Chatbot-Daten.
Deine Aufgabe: Erstelle einen objektiven Bericht für den Professor über die
Erkenntnisse aus Student-Chats.

WICHTIG:
- Beschreibe NUR was IST (keine Empfehlungen/Verbesserungsvorschläge)
- Fokus: Wo hatten Studenten Probleme, welches Feedback gab es, welche Themen wurden besprochen
- Strukturiere nach: Schwierigkeiten, Feedback, Nutzungsmuster
- Sei konkret: Nenne Themen, Häufigkeiten, Muster
- KEINE präskriptive Sprache ("sollte", "könnte verbessert werden", "es wäre besser", etc.)

Dein Bericht soll dem Professor helfen zu verstehen:
1. Wo Studenten Schwierigkeiten hatten (welche Konzepte, Fehler, Missverständnisse)
2. Welches Feedback die Studenten gegeben haben (zum Professor, zu Materialien, zum Chatbot)
3. Wie intensiv der Bot genutzt wurde und für welche Themen
4. Welche Fragemuster auftraten

Schreibe in professionellem, akademischem Stil. Nutze Markdown-Formatierung für bessere Lesbarkeit."""


class ReportGenerator:
    """Generator for creating aggregated reports from conversation findings."""

    def __init__(self, db: Session, llm: BedrockLLM):
        """
        Initialize report generator.

        Args:
            db: Database session
            llm: BedrockLLM instance for text generation
        """
        self.db = db
        self.llm = llm

    async def generate_report(
        self,
        course_id: uuid.UUID,
        days_back: int,
        end_date: Optional[date] = None,
        generated_by: Optional[uuid.UUID] = None
    ) -> CourseReport:
        """
        Generate an aggregated report from conversation findings.

        Args:
            course_id: UUID of the course
            days_back: Number of days to look back
            end_date: End date for report (default: today)
            generated_by: User ID who generated the report

        Returns:
            CourseReport object

        Process:
        1. Fetch all findings in date range for course
        2. Create hierarchical summary (max 50 findings per LLM call)
        3. Calculate statistics
        4. Save to database
        """
        # Default to today if no end_date provided
        if end_date is None:
            end_date = date.today()

        start_date = end_date - timedelta(days=days_back - 1)

        logger.info(f"Generating report for course {course_id}, period: {start_date} to {end_date}")

        # Fetch findings in date range
        findings = self._fetch_findings(course_id, start_date, end_date)

        if not findings:
            logger.warning(f"No findings found for course {course_id} in specified date range")
            # Create empty report
            report_text = self._generate_empty_report(start_date, end_date)
            statistics = {"total_findings": 0, "by_category": {}, "unique_conversations": 0}
            finding_ids = []
        else:
            # Generate report text via hierarchical summarization
            report_text = await self._hierarchical_summarize(findings, start_date, end_date)

            # Calculate statistics
            statistics = self._calculate_statistics(findings)
            finding_ids = [f.finding_id for f in findings]

        # Save to database
        report = CourseReport(
            course_id=course_id,
            start_date=start_date,
            end_date=end_date,
            days_back=days_back,
            report_text=report_text,
            finding_ids=finding_ids,
            generated_by=generated_by,
            statistics=statistics
        )

        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)

        logger.info(f"Report {report.report_id} generated successfully with {len(findings)} findings")

        return report

    def _fetch_findings(
        self,
        course_id: uuid.UUID,
        start_date: date,
        end_date: date
    ) -> List[ConversationFinding]:
        """
        Fetch all findings for a course within date range.

        Args:
            course_id: Course UUID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of ConversationFinding objects
        """
        findings = self.db.query(ConversationFinding).filter(
            and_(
                ConversationFinding.course_id == course_id,
                ConversationFinding.created_at >= datetime.combine(start_date, datetime.min.time()),
                ConversationFinding.created_at <= datetime.combine(end_date, datetime.max.time())
            )
        ).order_by(ConversationFinding.created_at.asc()).all()

        logger.info(f"Fetched {len(findings)} findings for course {course_id}")
        return findings

    async def _hierarchical_summarize(
        self,
        findings: List[ConversationFinding],
        start_date: date,
        end_date: date
    ) -> str:
        """
        Hierarchically summarize findings to handle large numbers.

        Process:
        - If <= 50 findings: summarize directly
        - If > 50: Create batches of 50, summarize each, then merge summaries (max 5 at a time)
        - Repeat merging until single summary remains

        Args:
            findings: List of findings to summarize
            start_date: Report start date
            end_date: Report end date

        Returns:
            Final summarized report text
        """
        logger.info(f"Starting hierarchical summarization for {len(findings)} findings")

        if len(findings) <= 50:
            return await self._summarize_batch(findings, start_date, end_date, is_final=True)

        # Level 1: Create 50-finding batches
        batches = [findings[i:i+50] for i in range(0, len(findings), 50)]
        logger.info(f"Level 1: Creating {len(batches)} batches of up to 50 findings")

        summaries_level1 = await asyncio.gather(*[
            self._summarize_batch(batch, start_date, end_date, is_final=False, batch_num=i+1)
            for i, batch in enumerate(batches)
        ])

        # Level 2+: Merge summaries (5 at a time) until only 1 remains
        current_summaries = summaries_level1
        level = 2

        while len(current_summaries) > 1:
            logger.info(f"Level {level}: Merging {len(current_summaries)} summaries")
            batches = [current_summaries[i:i+5] for i in range(0, len(current_summaries), 5)]

            current_summaries = await asyncio.gather(*[
                self._merge_summaries(batch, start_date, end_date, is_final=(level > 2 and len(batches) == 1))
                for batch in batches
            ])
            level += 1

        logger.info(f"Hierarchical summarization complete after {level-1} levels")
        return current_summaries[0]

    async def _summarize_batch(
        self,
        findings: List[ConversationFinding],
        start_date: date,
        end_date: date,
        is_final: bool = False,
        batch_num: Optional[int] = None
    ) -> str:
        """
        Summarize a single batch of findings (max 50).

        Args:
            findings: List of findings (max 50)
            start_date: Report start date
            end_date: Report end date
            is_final: Whether this is the final summary
            batch_num: Batch number for logging

        Returns:
            Summary text
        """
        batch_label = f"Batch {batch_num}" if batch_num else "Findings"
        logger.info(f"Summarizing {len(findings)} findings ({batch_label})")

        # Build context from finding descriptions
        context_parts = []
        for i, finding in enumerate(findings, 1):
            context_parts.append(
                f"{i}. [{finding.category}] {finding.title}\n"
                f"   {finding.description}\n"
                f"   (Datum: {finding.created_at.strftime('%Y-%m-%d')})"
            )

        context = "\n\n".join(context_parts)

        # Build prompt
        if is_final:
            prompt = f"""Erstelle einen umfassenden Bericht über die folgenden {len(findings)} Erkenntnisse aus Student-Chats.

Zeitraum: {start_date.strftime('%d.%m.%Y')} bis {end_date.strftime('%d.%m.%Y')}

Erkenntnisse:

{context}

Erstelle einen strukturierten Bericht, der die wichtigsten Muster, Schwierigkeiten und Feedback-Punkte zusammenfasst."""
        else:
            prompt = f"""Fasse die folgenden {len(findings)} Erkenntnisse aus Student-Chats zusammen.

Erkenntnisse:

{context}

Fasse die wichtigsten Punkte zusammen. Dies ist eine Zwischenzusammenfassung, die später mit anderen zusammengeführt wird."""

        # Call LLM (non-streaming for batch processing)
        try:
            summary = await self.llm.complete(
                prompt=prompt,
                system_prompt=REPORT_SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=2000 if is_final else 1000
            )
            return summary
        except Exception as e:
            logger.error(f"Error summarizing batch: {e}")
            raise

    async def _merge_summaries(
        self,
        summaries: List[str],
        start_date: date,
        end_date: date,
        is_final: bool = False
    ) -> str:
        """
        Merge multiple summaries into one.

        Args:
            summaries: List of summary texts (max 5)
            start_date: Report start date
            end_date: Report end date
            is_final: Whether this is the final merge

        Returns:
            Merged summary text
        """
        logger.info(f"Merging {len(summaries)} summaries")

        # Build context from summaries
        context_parts = []
        for i, summary in enumerate(summaries, 1):
            context_parts.append(f"Teil {i}:\n{summary}")

        context = "\n\n---\n\n".join(context_parts)

        # Build prompt
        if is_final:
            prompt = f"""Erstelle einen finalen, umfassenden Bericht aus den folgenden Teil-Berichten.

Zeitraum: {start_date.strftime('%d.%m.%Y')} bis {end_date.strftime('%d.%m.%Y')}

Teil-Berichte:

{context}

Erstelle einen kohärenten Gesamtbericht, der alle wichtigen Informationen aus den Teil-Berichten integriert."""
        else:
            prompt = f"""Fasse die folgenden Teil-Berichte zu einem zusammen:

{context}

Erstelle eine kompakte Zusammenfassung, die die wichtigsten Punkte aus allen Teil-Berichten enthält."""

        # Call LLM
        try:
            merged = await self.llm.complete(
                prompt=prompt,
                system_prompt=REPORT_SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=2000 if is_final else 1000
            )
            return merged
        except Exception as e:
            logger.error(f"Error merging summaries: {e}")
            raise

    def _calculate_statistics(self, findings: List[ConversationFinding]) -> Dict:
        """
        Calculate statistics from findings.

        Args:
            findings: List of findings

        Returns:
            Dictionary with statistics
        """
        if not findings:
            return {
                "total_findings": 0,
                "by_category": {},
                "unique_conversations": 0,
                "topics_mentioned": [],
                "date_range": {}
            }

        # Category distribution
        category_counts = Counter([f.category for f in findings])

        # Unique conversations
        unique_conversations = len(set([f.conversation_id for f in findings]))

        # Topics mentioned (from related_topic field)
        topics = [f.related_topic for f in findings if f.related_topic]
        topic_counts = Counter(topics)
        top_topics = [{"topic": topic, "count": count} for topic, count in topic_counts.most_common(10)]

        # Date range
        dates = [f.created_at for f in findings]
        date_range = {
            "start": min(dates).isoformat() if dates else None,
            "end": max(dates).isoformat() if dates else None
        }

        return {
            "total_findings": len(findings),
            "by_category": dict(category_counts),
            "unique_conversations": unique_conversations,
            "topics_mentioned": top_topics,
            "date_range": date_range
        }

    def _generate_empty_report(self, start_date: date, end_date: date) -> str:
        """
        Generate a report text for when no findings are found.

        Args:
            start_date: Report start date
            end_date: Report end date

        Returns:
            Empty report text
        """
        return f"""# Bericht: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}

## Zusammenfassung

Für den angegebenen Zeitraum wurden keine Erkenntnisse aus Student-Chats gefunden.

Mögliche Gründe:
- Der Chatbot wurde in diesem Zeitraum nicht genutzt
- Es wurden noch keine Chats analysiert
- Der ausgewählte Kurs hatte keine Chat-Aktivität

Bitte prüfen Sie, ob für diesen Kurs Chat-Aktivität vorliegt und ob die automatische Analyse aktiviert ist."""


# Factory function for easy instantiation
def create_report_generator(db: Session) -> ReportGenerator:
    """
    Create a ReportGenerator instance with default configuration.

    Args:
        db: Database session

    Returns:
        ReportGenerator instance
    """
    # Use default circuit breaker settings
    circuit_breaker = BedrockCircuitBreaker(
        failure_threshold=5,
        timeout=60
    )
    llm = BedrockLLM(settings, circuit_breaker)
    return ReportGenerator(db, llm)
