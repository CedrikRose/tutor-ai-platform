"""
Scheduler Status API

Endpoint to check the status of the automated analysis scheduler.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List

from auth import get_current_user as get_current_professor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/professor", tags=["scheduler"])


class SchedulerJobInfo(BaseModel):
    id: str
    name: str
    next_run_time: Optional[str]
    trigger: str


class SchedulerStatusResponse(BaseModel):
    running: bool
    jobs: List[SchedulerJobInfo]
    message: str


@router.get("/scheduler-status", response_model=SchedulerStatusResponse)
def get_scheduler_status(current_user = Depends(get_current_professor)):
    """
    Get the status of the automated analysis scheduler.

    Returns:
    - running: Whether the scheduler is running
    - jobs: List of scheduled jobs with their next run times
    - message: Human-readable status message
    """
    try:
        from api.main import scheduler

        if not scheduler:
            return SchedulerStatusResponse(
                running=False,
                jobs=[],
                message="Scheduler is not initialized"
            )

        jobs = []
        for job in scheduler.get_jobs():
            next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else None
            jobs.append(SchedulerJobInfo(
                id=job.id,
                name=job.name,
                next_run_time=next_run,
                trigger=str(job.trigger)
            ))

        return SchedulerStatusResponse(
            running=scheduler.running,
            jobs=jobs,
            message=f"Scheduler is running. Next analysis: {jobs[0].next_run_time if jobs else 'N/A'}"
        )

    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}", exc_info=True)
        return SchedulerStatusResponse(
            running=False,
            jobs=[],
            message=f"Error: {str(e)}"
        )
