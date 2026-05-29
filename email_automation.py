"""
Email Automation System

Sends course summaries via email on a schedule.
Runs daily at 8 AM (configurable per automation).
"""
import logging
import uuid
import smtplib
from datetime import datetime, date, time
from typing import List, Dict, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session

from database import (
    SessionLocal,
    EmailAutomation,
    EmailLog,
    Course,
    User
)
from course_summary_generator import generate_and_store_summary
from config import settings

logger = logging.getLogger(__name__)


class EmailSender:
    """Sends emails via SMTP."""

    def __init__(self):
        """Initialize email sender with SMTP configuration."""
        # Get SMTP config from settings
        self.smtp_host = getattr(settings, 'smtp_host', 'localhost')
        self.smtp_port = getattr(settings, 'smtp_port', 587)
        self.smtp_user = getattr(settings, 'smtp_user', None)
        self.smtp_password = getattr(settings, 'smtp_password', None)
        self.from_email = getattr(settings, 'from_email', 'noreply@ai-tutor.local')

    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body_html: str,
        body_text: Optional[str] = None
    ) -> bool:
        """
        Send an email.

        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            body_html: HTML body
            body_text: Plain text body (optional)

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(to_emails)

            # Attach text and HTML parts
            if body_text:
                part1 = MIMEText(body_text, 'plain')
                msg.attach(part1)

            part2 = MIMEText(body_html, 'html')
            msg.attach(part2)

            # Send via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_user and self.smtp_password:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)

                server.send_message(msg)

            logger.info(f"Email sent to {to_emails}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_emails}: {e}", exc_info=True)
            return False


class EmailAutomationRunner:
    """Runs email automations on schedule."""

    def __init__(self, db: Session, email_sender: EmailSender):
        self.db = db
        self.email_sender = email_sender

    async def run_due_automations(self, current_hour: int):
        """
        Run all automations that are due at this hour.

        Logic: Alle X Tage um 8 Uhr → Zusammenfassung der letzten X Tage

        Args:
            current_hour: Current hour (0-23)
        """
        logger.info(f"Checking for due automations (hour={current_hour})")

        # Find enabled automations for this time (8 AM)
        if current_hour != 8:
            logger.debug(f"Not 8 AM, skipping automation check")
            return

        automations = self.db.query(EmailAutomation).filter(
            EmailAutomation.enabled == True,
            EmailAutomation.send_time_hour == 8
        ).all()

        logger.info(f"Found {len(automations)} enabled automations")

        for automation in automations:
            # Check if it's time to send (every X days)
            if automation.last_sent_at:
                days_since_last = (date.today() - automation.last_sent_at.date()).days

                if days_since_last < automation.days_back:
                    logger.debug(f"Skipping automation {automation.automation_id} - "
                               f"sent {days_since_last} days ago, needs {automation.days_back} days")
                    continue

            # It's time to send!
            try:
                await self._run_automation(automation)
            except Exception as e:
                logger.error(f"Error running automation {automation.automation_id}: {e}", exc_info=True)

    async def _run_automation(self, automation: EmailAutomation):
        """Run a single automation."""
        logger.info(f"Running automation {automation.automation_id} for course {automation.course_id}")

        # Generate summary
        try:
            summary_data = await generate_and_store_summary(
                course_id=automation.course_id,
                days_back=automation.days_back
            )
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}", exc_info=True)
            self._log_email_failure(automation, None, str(e))
            return

        # Get course info
        course = self.db.query(Course).filter(
            Course.course_id == automation.course_id
        ).first()

        if not course:
            logger.error(f"Course {automation.course_id} not found")
            return

        # Build email
        subject = f"Kurszusammenfassung: {course.course_name} (letzte {automation.days_back} Tage)"
        body_html = self._build_email_html(course, summary_data)
        body_text = self._build_email_text(course, summary_data)

        # Send email
        success = self.email_sender.send_email(
            to_emails=automation.recipient_emails,
            subject=subject,
            body_html=body_html,
            body_text=body_text
        )

        # Log result
        if success:
            self._log_email_success(automation, summary_data.get("summary_id"))
            # Update last_sent_at
            automation.last_sent_at = datetime.utcnow()
            self.db.commit()
        else:
            self._log_email_failure(automation, summary_data.get("summary_id"), "SMTP error")

    def _build_email_html(self, course: Course, summary_data: Dict[str, Any]) -> str:
        """Build HTML email body."""
        stats = summary_data.get("statistics", {})

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; }}
        .content {{ padding: 20px; }}
        .stats {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 15px 0; }}
        .stats-item {{ margin: 10px 0; }}
        .summary {{ background-color: white; padding: 15px; border-left: 4px solid #4CAF50; }}
        .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Kurszusammenfassung</h1>
        <p>{course.course_name}</p>
    </div>

    <div class="content">
        <h2>Zeitraum: {summary_data['start_date']} bis {summary_data['end_date']}</h2>

        <div class="stats">
            <h3>Statistiken</h3>
            <div class="stats-item"><strong>Studenten:</strong> {stats.get('unique_students', 0)}</div>
            <div class="stats-item"><strong>Analysen:</strong> {stats.get('total_analyses', 0)}</div>
            <div class="stats-item"><strong>Wissenseinträge:</strong> {stats.get('total_knowledge_entries', 0)}</div>
            <div class="stats-item"><strong>Feedback-Einträge:</strong> {stats.get('total_feedback_entries', 0)}</div>
        </div>

        <div class="summary">
            <h3>Zusammenfassung</h3>
            {self._markdown_to_html(summary_data['summary'])}
        </div>
    </div>

    <div class="footer">
        <p>Automatisch generiert vom AI-Tutor System</p>
        <p>Zeitpunkt: {summary_data['generated_at']}</p>
    </div>
</body>
</html>
"""
        return html

    def _build_email_text(self, course: Course, summary_data: Dict[str, Any]) -> str:
        """Build plain text email body."""
        stats = summary_data.get("statistics", {})

        text = f"""
KURSZUSAMMENFASSUNG
==================

Kurs: {course.course_name}
Zeitraum: {summary_data['start_date']} bis {summary_data['end_date']}

STATISTIKEN
-----------
Studenten: {stats.get('unique_students', 0)}
Analysen: {stats.get('total_analyses', 0)}
Wissenseinträge: {stats.get('total_knowledge_entries', 0)}
Feedback-Einträge: {stats.get('total_feedback_entries', 0)}

ZUSAMMENFASSUNG
---------------
{summary_data['summary']}

---
Automatisch generiert vom AI-Tutor System
Zeitpunkt: {summary_data['generated_at']}
"""
        return text

    def _markdown_to_html(self, markdown_text: str) -> str:
        """Simple markdown to HTML conversion."""
        # This is a very basic conversion, could use a library like markdown2
        html = markdown_text
        # Convert headers
        html = html.replace('\n# ', '\n<h1>').replace('\n## ', '\n<h2>').replace('\n### ', '\n<h3>')
        # Convert bold
        import re
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        # Convert line breaks
        html = html.replace('\n\n', '</p><p>').replace('\n', '<br>')
        html = '<p>' + html + '</p>'
        return html

    def _log_email_success(self, automation: EmailAutomation, summary_id: Optional[str]):
        """Log successful email send."""
        log = EmailLog(
            automation_id=automation.automation_id,
            summary_id=uuid.UUID(summary_id) if summary_id else None,
            recipient_emails=automation.recipient_emails,
            subject=f"Kurszusammenfassung (letzte {automation.days_back} Tage)",
            status="sent"
        )
        self.db.add(log)
        self.db.commit()

    def _log_email_failure(
        self,
        automation: EmailAutomation,
        summary_id: Optional[str],
        error_message: str
    ):
        """Log failed email send."""
        log = EmailLog(
            automation_id=automation.automation_id,
            summary_id=uuid.UUID(summary_id) if summary_id else None,
            recipient_emails=automation.recipient_emails,
            subject=f"Kurszusammenfassung (letzte {automation.days_back} Tage)",
            status="failed",
            error_message=error_message
        )
        self.db.add(log)
        self.db.commit()


async def run_email_automations():
    """
    Main entry point for email automation.
    Called by cron at 8 AM daily.
    """
    logger.info("=" * 80)
    logger.info("Starting email automation check (8 AM)")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        current_time = datetime.now()
        current_hour = current_time.hour

        email_sender = EmailSender()
        runner = EmailAutomationRunner(db, email_sender)

        await runner.run_due_automations(current_hour)

        logger.info("Email automation check completed")

    except Exception as e:
        logger.error(f"Fatal error in email automation: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run automation check
    asyncio.run(run_email_automations())
