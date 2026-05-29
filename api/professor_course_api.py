"""
Professor Course Management API

Endpoints for creating, reading, updating, and deleting courses.
"""
import uuid
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db, Course, CoursePermission, CourseMaterial
from auth import get_current_user as get_current_professor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/professor", tags=["professor-courses"])


# ============================================================================
# Pydantic Models
# ============================================================================

class CreateCourseRequest(BaseModel):
    course_code: str = Field(..., min_length=1, max_length=50)
    course_name: str = Field(..., min_length=1, max_length=200)
    semester: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    is_active: bool = True
    student_access: bool = False


class CourseResponse(BaseModel):
    course_id: str
    course_code: str
    course_name: str
    semester: str
    description: Optional[str]
    is_active: bool
    student_access: bool
    created_at: datetime
    owner_user_id: str
    material_count: int = 0
    permission_level: str = "owner"


# ============================================================================
# Course Endpoints
# ============================================================================

@router.post("/courses", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    request: CreateCourseRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """
    Create a new course.
    """
    # Check for duplicate course_code
    existing = db.query(Course).filter(
        Course.course_code == request.course_code,
        Course.semester == request.semester
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Course with code '{request.course_code}' already exists in semester '{request.semester}'"
        )

    # Create course
    course = Course(
        course_code=request.course_code,
        course_name=request.course_name,
        semester=request.semester,
        description=request.description,
        is_active=request.is_active,
        student_access=request.student_access,
        owner_user_id=current_user.user_id
    )

    db.add(course)
    db.commit()
    db.refresh(course)

    logger.info(f"Course created: {course.course_code} by {current_user.email}")

    return CourseResponse(
        course_id=str(course.course_id),
        course_code=course.course_code,
        course_name=course.course_name,
        semester=course.semester,
        description=course.description,
        is_active=course.is_active,
        student_access=course.student_access,
        created_at=course.created_at,
        owner_user_id=str(course.owner_user_id),
        material_count=0,
        permission_level="owner"
    )


@router.get("/courses", response_model=List[CourseResponse])
def get_courses(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """
    Get all courses accessible by current professor.
    """
    # Get courses where user is owner or has permission
    owned_courses = db.query(Course).filter(
        Course.owner_user_id == current_user.user_id
    ).all()

    # Get shared courses
    shared_permissions = db.query(CoursePermission).filter(
        CoursePermission.user_id == current_user.user_id
    ).all()

    shared_course_ids = [p.course_id for p in shared_permissions]
    shared_courses = db.query(Course).filter(
        Course.course_id.in_(shared_course_ids)
    ).all() if shared_course_ids else []

    # Get material counts
    material_counts = {}
    for course in owned_courses + shared_courses:
        count = db.query(func.count(CourseMaterial.material_id)).filter(
            CourseMaterial.course_id == course.course_id,
            CourseMaterial.deleted_at == None
        ).scalar() or 0
        material_counts[course.course_id] = count

    # Build response
    courses = []
    for course in owned_courses:
        courses.append(CourseResponse(
            course_id=str(course.course_id),
            course_code=course.course_code,
            course_name=course.course_name,
            semester=course.semester,
            description=course.description,
            is_active=course.is_active,
            student_access=course.student_access,
            created_at=course.created_at,
            owner_user_id=str(course.owner_user_id),
            material_count=material_counts.get(course.course_id, 0),
            permission_level="owner"
        ))

    for course in shared_courses:
        perm = next((p for p in shared_permissions if p.course_id == course.course_id), None)
        courses.append(CourseResponse(
            course_id=str(course.course_id),
            course_code=course.course_code,
            course_name=course.course_name,
            semester=course.semester,
            description=course.description,
            is_active=course.is_active,
            student_access=course.student_access,
            created_at=course.created_at,
            owner_user_id=str(course.owner_user_id),
            material_count=material_counts.get(course.course_id, 0),
            permission_level=perm.permission_level if perm else "viewer"
        ))

    return courses


@router.get("/courses/{course_id}", response_model=CourseResponse)
def get_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """
    Get course details.
    """
    course = db.query(Course).filter(
        Course.course_id == uuid.UUID(course_id)
    ).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Check permission
    is_owner = course.owner_user_id == current_user.user_id
    permission = db.query(CoursePermission).filter(
        CoursePermission.course_id == course.course_id,
        CoursePermission.user_id == current_user.user_id
    ).first()

    if not is_owner and not permission:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get material count
    material_count = db.query(func.count(CourseMaterial.material_id)).filter(
        CourseMaterial.course_id == course.course_id,
        CourseMaterial.deleted_at == None
    ).scalar() or 0

    return CourseResponse(
        course_id=str(course.course_id),
        course_code=course.course_code,
        course_name=course.course_name,
        semester=course.semester,
        description=course.description,
        is_active=course.is_active,
        student_access=course.student_access,
        created_at=course.created_at,
        owner_user_id=str(course.owner_user_id),
        material_count=material_count,
        permission_level="owner" if is_owner else permission.permission_level
    )


@router.patch("/courses/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: str,
    request: CreateCourseRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """
    Update course details.
    """
    course = db.query(Course).filter(
        Course.course_id == uuid.UUID(course_id)
    ).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Check permission (owner or editor)
    is_owner = course.owner_user_id == current_user.user_id
    permission = db.query(CoursePermission).filter(
        CoursePermission.course_id == course.course_id,
        CoursePermission.user_id == current_user.user_id
    ).first()

    if not is_owner and (not permission or permission.permission_level not in ["owner", "editor"]):
        raise HTTPException(status_code=403, detail="Access denied")

    # Update fields
    course.course_code = request.course_code
    course.course_name = request.course_name
    course.semester = request.semester
    course.description = request.description
    course.is_active = request.is_active
    course.student_access = request.student_access
    course.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(course)

    logger.info(f"Course updated: {course.course_code} by {current_user.email}")

    # Get material count
    material_count = db.query(func.count(CourseMaterial.material_id)).filter(
        CourseMaterial.course_id == course.course_id,
        CourseMaterial.deleted_at == None
    ).scalar() or 0

    return CourseResponse(
        course_id=str(course.course_id),
        course_code=course.course_code,
        course_name=course.course_name,
        semester=course.semester,
        description=course.description,
        is_active=course.is_active,
        student_access=course.student_access,
        created_at=course.created_at,
        owner_user_id=str(course.owner_user_id),
        material_count=material_count,
        permission_level="owner" if is_owner else permission.permission_level
    )


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """
    Delete course (soft delete).
    """
    course = db.query(Course).filter(
        Course.course_id == uuid.UUID(course_id)
    ).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Only owner can delete
    if course.owner_user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Only course owner can delete")

    # Delete dependent data first to avoid foreign key constraint violations
    from database import ChatSnapshotV2
    
    # Delete chat snapshots
    db.query(ChatSnapshotV2).filter(
        ChatSnapshotV2.course_id == uuid.UUID(course_id)
    ).delete()

    # Soft delete
    db.delete(course)
    db.commit()

    logger.info(f"Course deleted: {course.course_code} by {current_user.email}")

    return None
