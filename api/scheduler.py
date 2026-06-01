"""
Automated Chat Analysis Scheduler

Runs daily at 3:00 AM to analyze all unanalyzed chats across all courses.
"""
import logging
from datetime import datetime, date
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from database import SessionLocal, Course, ChatConversation, ChatExchange

logger = logging.getLogger(__name__)


def analyze_all_courses():
    """
    Analyze all unanalyzed exchanges for all active courses.

    This function runs daily at 3:00 AM and processes:
    1. All active courses
    2. All conversations with unanalyzed exchanges
    3. Creates snapshots and runs LLM analysis
    """
    db = SessionLocal()

    try:
        logger.info("=" * 80)
        logger.info("🔄 Starting automated daily chat analysis...")
        logger.info(f"⏰ Triggered at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        # Import analysis components
        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from daily_chat_analysis_v2 import SnapshotCreator, ChatAnalyzer, FindingExtractor

        # Get all active courses
        active_courses = db.query(Course).filter(
            Course.is_active == True
        ).all()

        logger.info(f"📚 Found {len(active_courses)} active courses to analyze")

        total_snapshots = 0
        total_analyses = 0
        total_findings = 0

        for course in active_courses:
            try:
                logger.info(f"\n📖 Processing course: {course.course_name} ({course.course_id})")

                # Get conversations with unanalyzed exchanges for this course
                conversations_to_analyze = (
                    db.query(ChatConversation)
                    .join(ChatExchange, ChatConversation.conversation_id == ChatExchange.conversation_id)
                    .filter(
                        ChatExchange.analyzed == False,
                        ChatExchange.course_id == course.course_id
                    )
                    .distinct()
                    .all()
                )

                if not conversations_to_analyze:
                    logger.info(f"  ✓ No unanalyzed exchanges for {course.course_name}")
                    continue

                logger.info(f"  → Found {len(conversations_to_analyze)} conversations with unanalyzed exchanges")

                # Step 1: Create snapshots
                snapshot_creator = SnapshotCreator(db)
                snapshots = []

                for conversation in conversations_to_analyze:
                    snapshot = snapshot_creator._create_snapshot_for_conversation(
                        conversation,
                        date.today()
                    )
                    if snapshot:
                        snapshots.append(snapshot)

                db.commit()
                logger.info(f"  → Created {len(snapshots)} snapshots")
                total_snapshots += len(snapshots)

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
                        logger.error(f"  ✗ Error analyzing snapshot {snapshot.snapshot_id}: {e}")
                        snapshot.analysis_status = "error"

                    db.commit()

                logger.info(f"  → Completed {len(analyses_with_responses)} analyses")
                total_analyses += len(analyses_with_responses)

                # Step 3: Extract findings
                extractor = FindingExtractor(db)
                course_findings = 0

                for analysis, llm_response in analyses_with_responses:
                    findings = extractor.extract_findings_from_analysis(analysis, llm_response)
                    course_findings += len(findings)

                db.commit()
                logger.info(f"  → Extracted {course_findings} findings")
                total_findings += course_findings

                logger.info(f"  ✅ Completed analysis for {course.course_name}")

            except Exception as e:
                logger.error(f"  ✗ Error processing course {course.course_name}: {e}", exc_info=True)
                db.rollback()
                continue

        # Final summary
        logger.info("\n" + "=" * 80)
        logger.info("✅ Automated daily analysis completed!")
        logger.info(f"📊 Summary:")
        logger.info(f"  • Courses processed: {len(active_courses)}")
        logger.info(f"  • Snapshots created: {total_snapshots}")
        logger.info(f"  • Analyses completed: {total_analyses}")
        logger.info(f"  • Findings extracted: {total_findings}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"✗ Fatal error in automated analysis: {e}", exc_info=True)
        db.rollback()

    finally:
        db.close()


def start_scheduler():
    """
    Start the background scheduler for automated daily analysis.

    Schedules:
    - Daily at 3:00 AM: Analyze all unanalyzed chats
    """
    scheduler = BackgroundScheduler()

    # Schedule daily analysis at 3:00 AM
    scheduler.add_job(
        analyze_all_courses,
        trigger=CronTrigger(hour=3, minute=0),
        id='daily_chat_analysis',
        name='Daily Chat Analysis at 3:00 AM',
        replace_existing=True
    )

    scheduler.start()
    logger.info("✅ Scheduler started - Daily analysis will run at 3:00 AM")

    return scheduler


def stop_scheduler(scheduler):
    """Stop the scheduler."""
    if scheduler:
        scheduler.shutdown()
        logger.info("👋 Scheduler stopped")
