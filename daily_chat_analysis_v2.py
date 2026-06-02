"""
Daily Chat Analysis System V2

Runs at 4 AM to analyze new student chats using the new ChatConversation/ChatExchange structure.
- Creates snapshots of conversations with unanalyzed exchanges
- Analyzes using Amazon Bedrock LLM
- Extracts structured findings (difficulties, feedback, patterns)
- Marks exchanges as analyzed
"""
import logging
import uuid
import json
import boto3
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from database import (
    SessionLocal,
    ChatConversation,
    ChatExchange,
    ChatSnapshotV2,
    ConversationAnalysisV2,
    ConversationFinding
)
from config import settings

logger = logging.getLogger(__name__)


class SnapshotCreator:
    """Creates conversation snapshots for analysis."""

    def __init__(self, db: Session):
        self.db = db

    def create_daily_snapshots(self, snapshot_date: Optional[date] = None) -> List[ChatSnapshotV2]:
        """
        Create snapshots for all conversations with unanalyzed exchanges.

        Args:
            snapshot_date: Date for snapshot (default: today)

        Returns:
            List of created snapshots
        """
        if snapshot_date is None:
            snapshot_date = date.today()

        logger.info(f"Creating chat snapshots for {snapshot_date}")

        # Find conversations with unanalyzed exchanges
        conversations = self._find_conversations_needing_snapshots()

        logger.info(f"Found {len(conversations)} conversations with unanalyzed exchanges")

        snapshots = []
        for conversation in conversations:
            try:
                snapshot = self._create_snapshot_for_conversation(conversation, snapshot_date)
                if snapshot:
                    snapshots.append(snapshot)
                    logger.info(f"Created snapshot {snapshot.snapshot_id} for conversation {conversation.conversation_id}")
            except Exception as e:
                logger.error(f"Error creating snapshot for conversation {conversation.conversation_id}: {e}", exc_info=True)

        self.db.commit()
        logger.info(f"Created {len(snapshots)} snapshots")
        return snapshots

    def _find_conversations_needing_snapshots(self) -> List[ChatConversation]:
        """Find conversations that have unanalyzed exchanges with a course assigned."""

        # Find conversations with at least one unanalyzed exchange AND with course_id
        conversations_with_unanalyzed = (
            self.db.query(ChatConversation)
            .join(ChatExchange, ChatConversation.conversation_id == ChatExchange.conversation_id)
            .filter(
                ChatExchange.analyzed == False,
                ChatExchange.course_id.isnot(None)  # Only exchanges with course assigned
            )
            .distinct()
            .all()
        )

        return conversations_with_unanalyzed

    def _create_snapshot_for_conversation(
        self,
        conversation: ChatConversation,
        snapshot_date: date
    ) -> Optional[ChatSnapshotV2]:
        """Create a snapshot for a conversation with unanalyzed exchanges.

        Limits to max 20 exchanges per snapshot for performance.
        """

        # Get unanalyzed exchanges with course_id, ordered by exchange_number
        unanalyzed_exchanges = (
            self.db.query(ChatExchange)
            .filter(
                ChatExchange.conversation_id == conversation.conversation_id,
                ChatExchange.analyzed == False,
                ChatExchange.course_id.isnot(None)  # Only exchanges with course
            )
            .order_by(ChatExchange.exchange_number)
            .limit(20)  # Max 20 exchanges per snapshot for performance
            .all()
        )

        if not unanalyzed_exchanges:
            return None

        # Get the range
        from_exchange_number = unanalyzed_exchanges[0].exchange_number
        to_exchange_number = unanalyzed_exchanges[-1].exchange_number
        exchange_count = len(unanalyzed_exchanges)

        # Format chat content for analysis
        chat_content = self._format_exchanges_for_analysis(unanalyzed_exchanges)

        # Get course_id from exchanges (should be same for all, or None)
        course_id = unanalyzed_exchanges[0].course_id if unanalyzed_exchanges else None

        # Create snapshot
        snapshot = ChatSnapshotV2(
            snapshot_id=uuid.uuid4(),
            conversation_id=conversation.conversation_id,
            snapshot_date=snapshot_date,
            from_exchange_number=from_exchange_number,
            to_exchange_number=to_exchange_number,
            exchange_count=exchange_count,
            chat_content=chat_content,
            course_id=course_id,
            cookie_id=conversation.cookie_id,
            analysis_status="pending"
        )

        self.db.add(snapshot)
        return snapshot

    def _format_exchanges_for_analysis(self, exchanges: List[ChatExchange]) -> str:
        """Format exchanges into text for LLM analysis."""

        lines = []
        for exchange in exchanges:
            lines.append(f"EXCHANGE-{exchange.exchange_number}:")
            lines.append(f"User: {exchange.user_question}")
            lines.append(f"Assistant: {exchange.assistant_answer}")

            # Add RAG context if available
            if exchange.rag_metadata:
                lines.append(f"RAG-Context: {json.dumps(exchange.rag_metadata, ensure_ascii=False)}")

            lines.append("")  # Empty line between exchanges

        return "\n".join(lines)


class ChatAnalyzer:
    """Analyzes chat snapshots using Amazon Bedrock LLM."""

    def __init__(self, db: Session):
        self.db = db
        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=settings.aws_region
        )
        self.primary_model = settings.bedrock_llm_model_primary
        self.secondary_model = settings.bedrock_llm_model_secondary

    def analyze_pending_snapshots(self) -> List[ConversationAnalysisV2]:
        """Analyze all pending snapshots."""

        pending_snapshots = (
            self.db.query(ChatSnapshotV2)
            .filter(ChatSnapshotV2.analysis_status == "pending")
            .all()
        )

        logger.info(f"Found {len(pending_snapshots)} pending snapshots to analyze")

        analyses = []
        for snapshot in pending_snapshots:
            try:
                snapshot.analysis_status = "analyzing"
                self.db.commit()

                analysis = self._analyze_snapshot(snapshot)
                analyses.append(analysis)

                snapshot.analysis_status = "completed"
                snapshot.analyzed_at = datetime.utcnow()

            except Exception as e:
                logger.error(f"Error analyzing snapshot {snapshot.snapshot_id}: {e}", exc_info=True)
                snapshot.analysis_status = "error"

            self.db.commit()

        logger.info(f"Completed {len(analyses)} analyses")
        return analyses

    def _analyze_snapshot(self, snapshot: ChatSnapshotV2) -> ConversationAnalysisV2:
        """Analyze a single snapshot."""

        logger.info(f"Analyzing snapshot {snapshot.snapshot_id}")

        # Build analysis prompt
        prompt = self._build_analysis_prompt(snapshot.chat_content)

        # Call LLM
        result = self._call_bedrock_model(self.primary_model, prompt)

        # Create analysis record
        analysis = ConversationAnalysisV2(
            analysis_id=uuid.uuid4(),
            snapshot_id=snapshot.snapshot_id,
            conversation_id=snapshot.conversation_id,
            primary_model=self.primary_model,
            exchange_count=snapshot.exchange_count,
            course_id=snapshot.course_id,
            tokens_used=result.get("tokens", 0),
            status="completed",
            analysis_text=result.get("text", "")
        )

        self.db.add(analysis)
        self.db.commit()

        logger.info(f"Created analysis {analysis.analysis_id} for snapshot {snapshot.snapshot_id}")

        return analysis, result["text"]

    def _build_analysis_prompt(self, chat_content: str) -> str:
        """Build prompt for LLM to analyze chat."""

        # Get analysis system prompt from manager
        try:
            from prompt_manager import prompt_manager
            analysis_prompt_template = prompt_manager.get_prompt("chat_analysis")
        except Exception as e:
            logger.warning(f"Could not load chat analysis prompt: {e}")
            # Fallback to hardcoded prompt
            analysis_prompt_template = """Du bist ein Analysator für studentische Chat-Gespräche. Deine Aufgabe ist es, Findings zu extrahieren, die für Professoren relevant sind.

**Kategorien:**
1. **difficulty** - Verständnisprobleme, wiederholte Fehler, Konzept-Lücken
2. **feedback_professor** - Kommentare über Vorlesungsinhalte, Materialien, Erklärungen
3. **feedback_chatbot** - Qualität der KI-Antworten, Hilfreichkeit, Frustration
4. **question_pattern** - Wiederkehrende Fragenmuster, die auf systematische Issues hindeuten

**Für jedes Finding:**
- **title**: Kurze, prägnante Zusammenfassung (max 100 Zeichen)
- **description**: Detaillierte Beschreibung mit konkreten Beispielen
- **reasoning**: Warum ist das relevant? Was bedeutet es?
- **reference_exchange_numbers**: Liste der Exchange-Nummern als Beleg
- **related_topic**: Bezug zu Kursthema (z.B. "Vorlesung 3: Rekursion", "Hausaufgabe 2")

**Wichtig:**
- Extrahiere NUR relevante, actionable Findings
- Mehrere ähnliche Fragen → EIN Finding mit allen Referenzen
- Sei spezifisch: "Verständnisprobleme bei Rekursions-Basis-Bedingung" statt "Probleme mit Rekursion"
- Nutze die gegebenen Exchange-Nummern für Referenzen

Antworte im JSON-Format: {"findings": [{"category": "...", "title": "...", ...}]}"""

        prompt = f"""{analysis_prompt_template}

Chat-Verlauf:
{chat_content}

JSON-Antwort:"""

        return prompt

    def _call_bedrock_model(self, model_id: str, prompt: str) -> Dict[str, Any]:
        """Call Amazon Bedrock model."""

        # Build request body
        if "minimax" in model_id:
            body = json.dumps({
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 4000
            })
        elif "moonshot" in model_id or "kimi" in model_id:
            body = json.dumps({
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 4000
            })
        else:
            raise ValueError(f"Unknown model: {model_id}")

        # Call model
        response = self.bedrock_runtime.invoke_model(
            modelId=model_id,
            body=body,
            contentType="application/json",
            accept="application/json"
        )

        # Parse response
        response_body = json.loads(response["body"].read())

        # Extract text and tokens
        if "choices" in response_body:
            text = response_body["choices"][0]["message"]["content"]
            tokens = response_body.get("usage", {}).get("total_tokens", 0)
        elif "content" in response_body:
            text = response_body["content"][0]["text"]
            tokens = response_body.get("usage", {}).get("total_tokens", 0)
        else:
            text = str(response_body)
            tokens = 0

        return {
            "text": text,
            "tokens": tokens
        }


class FindingExtractor:
    """Extracts structured findings from LLM analysis and stores them in database."""

    def __init__(self, db: Session):
        self.db = db

    def extract_findings_from_analysis(
        self,
        analysis: ConversationAnalysisV2,
        llm_response: str
    ) -> List[ConversationFinding]:
        """Extract findings from LLM response and save to database."""

        logger.info(f"Extracting findings from analysis {analysis.analysis_id}")

        try:
            # Parse JSON from LLM response
            findings_data = self._parse_llm_response(llm_response)

            if not findings_data.get("findings"):
                logger.info(f"No findings in analysis {analysis.analysis_id}")
                return []

            findings = []
            for finding_data in findings_data["findings"]:
                finding = self._create_finding(analysis, finding_data)
                if finding:
                    findings.append(finding)

            # Mark exchanges as analyzed
            if findings:
                self._mark_exchanges_analyzed(analysis)

            self.db.commit()
            logger.info(f"Created {len(findings)} findings from analysis {analysis.analysis_id}")

            return findings

        except Exception as e:
            logger.error(f"Error extracting findings from analysis {analysis.analysis_id}: {e}", exc_info=True)
            return []

    def _parse_llm_response(self, llm_response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""

        # Try to extract JSON from response (LLM might add extra text)
        try:
            # Find JSON block
            start = llm_response.find("{")
            end = llm_response.rfind("}") + 1

            if start == -1 or end == 0:
                logger.warning("No JSON found in LLM response")
                return {"findings": []}

            json_str = llm_response[start:end]
            return json.loads(json_str)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {e}")
            logger.debug(f"LLM response: {llm_response}")
            return {"findings": []}

    def _create_finding(
        self,
        analysis: ConversationAnalysisV2,
        finding_data: Dict[str, Any]
    ) -> Optional[ConversationFinding]:
        """Create a ConversationFinding from parsed data."""

        try:
            # Validate required fields
            if not all(k in finding_data for k in ["category", "title", "description", "reasoning", "reference_exchange_numbers"]):
                logger.warning(f"Missing required fields in finding data: {finding_data}")
                return None

            # Validate category
            valid_categories = ["difficulty", "feedback_professor", "feedback_chatbot", "question_pattern"]
            if finding_data["category"] not in valid_categories:
                logger.warning(f"Invalid category: {finding_data['category']}")
                return None

            # Get snapshot to extract related_material_id
            snapshot = self.db.query(ChatSnapshotV2).filter(
                ChatSnapshotV2.snapshot_id == analysis.snapshot_id
            ).first()

            # Try to find related_material_id from the exchanges
            related_material_id = self._extract_related_material_id(
                snapshot.conversation_id,
                finding_data["reference_exchange_numbers"]
            )

            # Create finding
            finding = ConversationFinding(
                finding_id=uuid.uuid4(),
                conversation_id=analysis.conversation_id,
                snapshot_id=analysis.snapshot_id,
                course_id=analysis.course_id,
                category=finding_data["category"],
                title=finding_data["title"][:255],  # Truncate to max length
                description=finding_data["description"],
                reasoning=finding_data["reasoning"],
                reference_exchange_numbers=finding_data["reference_exchange_numbers"],
                related_material_id=related_material_id,
                related_topic=finding_data.get("related_topic"),
                analysis_model=analysis.primary_model
            )

            self.db.add(finding)
            return finding

        except Exception as e:
            logger.error(f"Error creating finding: {e}", exc_info=True)
            return None

    def _extract_related_material_id(
        self,
        conversation_id: uuid.UUID,
        exchange_numbers: List[int]
    ) -> Optional[uuid.UUID]:
        """Extract related_material_id from referenced exchanges."""

        if not exchange_numbers:
            return None

        # Get exchanges
        exchanges = (
            self.db.query(ChatExchange)
            .filter(
                ChatExchange.conversation_id == conversation_id,
                ChatExchange.exchange_number.in_(exchange_numbers)
            )
            .all()
        )

        # Find most common material_id (if any)
        material_ids = [ex.selected_material_id for ex in exchanges if ex.selected_material_id]

        if not material_ids:
            return None

        # Return most common
        from collections import Counter
        most_common = Counter(material_ids).most_common(1)
        return most_common[0][0] if most_common else None

    def _mark_exchanges_analyzed(self, analysis: ConversationAnalysisV2):
        """Mark all exchanges in the snapshot as analyzed."""

        snapshot = self.db.query(ChatSnapshotV2).filter(
            ChatSnapshotV2.snapshot_id == analysis.snapshot_id
        ).first()

        if not snapshot:
            return

        # Update exchanges
        exchanges = (
            self.db.query(ChatExchange)
            .filter(
                ChatExchange.conversation_id == snapshot.conversation_id,
                ChatExchange.exchange_number >= snapshot.from_exchange_number,
                ChatExchange.exchange_number <= snapshot.to_exchange_number
            )
            .all()
        )

        for exchange in exchanges:
            exchange.analyzed = True
            exchange.analyzed_at = datetime.utcnow()

        logger.info(f"Marked {len(exchanges)} exchanges as analyzed")


def run_daily_analysis(dry_run: bool = False):
    """Main function to run daily chat analysis."""

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("=" * 80)
    logger.info("Starting Daily Chat Analysis V2")
    logger.info(f"Dry run: {dry_run}")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # Step 1: Create snapshots
        logger.info("\n[Step 1] Creating snapshots...")
        snapshot_creator = SnapshotCreator(db)
        snapshots = snapshot_creator.create_daily_snapshots()

        if dry_run:
            logger.info("DRY RUN: Rolling back snapshot creation")
            db.rollback()
            return

        # Step 2: Analyze snapshots
        logger.info("\n[Step 2] Analyzing snapshots...")
        analyzer = ChatAnalyzer(db)
        analyses_with_responses = analyzer.analyze_pending_snapshots()

        # Step 3: Extract findings
        logger.info("\n[Step 3] Extracting findings...")
        extractor = FindingExtractor(db)

        total_findings = 0
        for analysis, llm_response in analyses_with_responses:
            findings = extractor.extract_findings_from_analysis(analysis, llm_response)
            total_findings += len(findings)

        logger.info("\n" + "=" * 80)
        logger.info(f"Daily Analysis Complete!")
        logger.info(f"  Snapshots created: {len(snapshots)}")
        logger.info(f"  Analyses completed: {len(analyses_with_responses)}")
        logger.info(f"  Findings extracted: {total_findings}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Error in daily analysis: {e}", exc_info=True)
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run daily chat analysis")
    parser.add_argument("--dry-run", action="store_true", help="Run without committing changes")

    args = parser.parse_args()

    run_daily_analysis(dry_run=args.dry_run)
