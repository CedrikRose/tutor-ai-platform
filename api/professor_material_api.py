"""
Professor Material Management API

Endpoints for uploading, viewing, and managing course materials.
"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db, CourseMaterial, MaterialFile, Course, MaterialChunk, MaterialContent, MaterialProcessingLog
from auth import get_current_user as get_current_professor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/professor", tags=["professor-materials"])


# ============================================================================
# Pydantic Models
# ============================================================================

class MaterialFileResponse(BaseModel):
    file_id: str
    filename: str
    file_path: str
    file_size: Optional[int] = 0


class CourseMaterialResponse(BaseModel):
    material_id: str
    course_id: str
    material_type: str
    display_name: str
    original_filename: Optional[str]
    sequence_number: Optional[int]
    file_count: int
    files: List[MaterialFileResponse] = []
    processed_at: Optional[datetime]
    created_at: datetime


class MaterialContentResponse(BaseModel):
    material_id: str
    material_type: str
    display_name: str
    content: str
    is_editable: bool


class UpdateMaterialContentRequest(BaseModel):
    content: str


# ============================================================================
# Material Endpoints
# ============================================================================

@router.get("/courses/{course_id}/materials", response_model=List[CourseMaterialResponse])
async def get_course_materials(
    course_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """Get all materials for a course."""
    # Check course access
    course = db.query(Course).filter(
        Course.course_id == uuid.UUID(course_id)
    ).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Check if user has access (owner or has permission)
    if course.owner_user_id != current_user.user_id:
        # Check if user has shared access
        from database import CoursePermission
        permission = db.query(CoursePermission).filter(
            CoursePermission.course_id == course.course_id,
            CoursePermission.user_id == current_user.user_id
        ).first()

        if not permission:
            raise HTTPException(status_code=403, detail="Access denied")

    # Get materials
    materials = db.query(CourseMaterial).filter(
        CourseMaterial.course_id == uuid.UUID(course_id),
        CourseMaterial.deleted_at == None
    ).order_by(CourseMaterial.sequence_number.nullslast(), CourseMaterial.created_at).all()

    return [
        CourseMaterialResponse(
            material_id=str(m.material_id),
            course_id=str(m.course_id),
            material_type=m.material_type,
            display_name=m.display_name,
            original_filename=m.original_filename,
            sequence_number=m.sequence_number,
            file_count=m.file_count,
            files=[
                MaterialFileResponse(
                    file_id=str(f.file_id),
                    filename=f.filename,
                    file_path=f.file_path,
                    file_size=f.file_size
                )
                for f in m.files
            ],
            processed_at=m.processed_at,
            created_at=m.created_at
        )
        for m in materials
    ]


@router.post("/courses/{course_id}/materials/upload")
async def upload_course_material(
    course_id: str,
    files: List[UploadFile] = File(...),
    material_type: str = Form(...),
    custom_name: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """Upload course material with review period."""
    from file_storage import get_storage

    # Check course access (must be owner or editor)
    course = db.query(Course).filter(
        Course.course_id == uuid.UUID(course_id)
    ).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    is_owner = course.owner_user_id == current_user.user_id

    if not is_owner:
        from database import CoursePermission
        permission = db.query(CoursePermission).filter(
            CoursePermission.course_id == course.course_id,
            CoursePermission.user_id == current_user.user_id
        ).first()

        if not permission or permission.permission_level not in ["owner", "editor"]:
            raise HTTPException(status_code=403, detail="Access denied")

    # Get next sequence number for this type (only count non-deleted materials)
    max_seq = db.query(func.max(CourseMaterial.sequence_number)).filter(
        CourseMaterial.course_id == uuid.UUID(course_id),
        CourseMaterial.material_type == material_type,
        CourseMaterial.deleted_at == None
    ).scalar()
    next_seq = (max_seq or 0) + 1

    # Determine display name
    if material_type == 'other' and custom_name:
        display_name = custom_name
    elif material_type == 'lecture_slide':
        display_name = f"Vorlesung {next_seq}"
    elif material_type == 'homework':
        display_name = f"Hausaufgabe {next_seq}"
    elif material_type == 'tutorium':
        display_name = f"Tutorium {next_seq}"
    else:
        display_name = custom_name or files[0].filename

    # Create material (no review period - process immediately on demand)
    all_filenames = ", ".join([f.filename for f in files])

    material = CourseMaterial(
        material_id=uuid.uuid4(),
        course_id=uuid.UUID(course_id),
        uploaded_by=current_user.user_id,
        material_type=material_type,
        display_name=display_name,
        original_filename=all_filenames,
        sequence_number=next_seq if material_type != 'other' else None,
        file_count=len(files)
    )

    db.add(material)
    db.commit()
    db.refresh(material)

    # Save files (with ZIP extraction support)
    storage = get_storage()
    saved_files = []
    from io import BytesIO

    for file in files:
        file_content = await file.read()

        # Check if file is a ZIP - if so, extract it
        if file.filename.lower().endswith('.zip'):
            logger.info(f"Detected ZIP file: {file.filename}, extracting...")

            # Save ZIP temporarily
            file_bytes = BytesIO(file_content)
            temp_zip_path = storage.save_file(
                file_content=file_bytes,
                original_filename=file.filename,
                course_id=f"{course_id}/materials/{material.material_id}"
            )

            try:
                # Extract ZIP contents
                extracted_files = storage.extract_zip(
                    temp_zip_path,
                    f"{course_id}/materials/{material.material_id}"
                )

                # Create file records for each extracted file
                for original_name, stored_path in extracted_files:
                    material_file = MaterialFile(
                        material_id=material.material_id,
                        filename=original_name,
                        file_path=stored_path,
                        file_size=None,  # Size not tracked for extracted files
                        file_type='extracted_from_zip'
                    )
                    db.add(material_file)
                    saved_files.append(material_file)

                # Delete the temporary ZIP file
                storage.delete_file(temp_zip_path)

                logger.info(f"Extracted {len(extracted_files)} files from {file.filename}")

            except Exception as e:
                logger.error(f"Failed to extract ZIP {file.filename}: {e}", exc_info=True)
                # If extraction fails, save ZIP as-is
                material_file = MaterialFile(
                    material_id=material.material_id,
                    filename=file.filename,
                    file_path=temp_zip_path,
                    file_size=len(file_content),
                    file_type='application/zip'
                )
                db.add(material_file)
                saved_files.append(material_file)
        else:
            # Regular file - save normally
            file_bytes = BytesIO(file_content)
            file_path = storage.save_file(
                file_content=file_bytes,
                original_filename=file.filename,
                course_id=f"{course_id}/materials/{material.material_id}"
            )

            material_file = MaterialFile(
                material_id=material.material_id,
                filename=file.filename,
                file_path=file_path,
                file_size=len(file_content)
            )
            db.add(material_file)
            saved_files.append(material_file)

    # Update file count based on actual files saved (extracted files count individually)
    material.file_count = len(saved_files)
    db.commit()

    logger.info(f"Material uploaded: {material.display_name} ({len(saved_files)} files) by {current_user.email}")

    return {
        "material_id": str(material.material_id),
        "display_name": material.display_name,
        "file_count": len(saved_files),
        "files": [{"filename": f.filename, "file_size": f.file_size or 0} for f in saved_files],
        "processed_at": None,
        "message": "Material uploaded successfully. Click 'Process' to make it available for students."
    }


@router.delete("/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material(
    material_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """Delete material (soft delete)."""
    material = db.query(CourseMaterial).filter(
        CourseMaterial.material_id == uuid.UUID(material_id)
    ).first()

    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    # Check course access
    course = db.query(Course).filter(
        Course.course_id == material.course_id
    ).first()

    is_owner = course.owner_user_id == current_user.user_id

    if not is_owner:
        from database import CoursePermission
        permission = db.query(CoursePermission).filter(
            CoursePermission.course_id == course.course_id,
            CoursePermission.user_id == current_user.user_id
        ).first()

        if not permission or permission.permission_level not in ["owner", "editor"]:
            raise HTTPException(status_code=403, detail="Access denied")

    # Soft delete
    material_type = material.material_type
    course_id = material.course_id
    material.deleted_at = datetime.utcnow()
    db.commit()

    # Reorder sequence numbers for remaining materials of same type
    if material.sequence_number is not None:
        remaining_materials = db.query(CourseMaterial).filter(
            CourseMaterial.course_id == course_id,
            CourseMaterial.material_type == material_type,
            CourseMaterial.deleted_at == None
        ).order_by(CourseMaterial.sequence_number).all()

        # Renumber sequentially starting from 1
        for idx, mat in enumerate(remaining_materials, start=1):
            mat.sequence_number = idx

        db.commit()

    logger.info(f"Material deleted: {material.display_name} by {current_user.email}")

    return None


@router.post("/materials/{material_id}/process")
async def process_material(
    material_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_professor)
):
    """Process material (parse and embed)."""
    material = db.query(CourseMaterial).filter(
        CourseMaterial.material_id == uuid.UUID(material_id)
    ).first()

    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    # Check course access
    course = db.query(Course).filter(
        Course.course_id == material.course_id
    ).first()

    is_owner = course.owner_user_id == current_user.user_id

    if not is_owner:
        from database import CoursePermission
        permission = db.query(CoursePermission).filter(
            CoursePermission.course_id == course.course_id,
            CoursePermission.user_id == current_user.user_id
        ).first()

        if not permission or permission.permission_level not in ["owner", "editor"]:
            raise HTTPException(status_code=403, detail="Access denied")

    # Check if already processed or currently processing
    from datetime import datetime, timezone
    PROCESSING_MARKER = datetime(1970, 1, 1, tzinfo=timezone.utc)

    if material.processed_at:
        if material.processed_at > PROCESSING_MARKER:
            return {"message": "Material bereits verarbeitet", "status": "already_processed"}
        else:
            # Already being processed
            return {"message": "Material wird bereits verarbeitet", "status": "already_processing"}

    # Mark as "processing" with epoch timestamp
    material.processed_at = PROCESSING_MARKER
    db.commit()

    # Queue background processing
    from material_processor import MaterialProcessor
    from database import SessionLocal

    async def process_material_task():
        # Use a new DB session for background task
        task_db = SessionLocal()
        try:
            processor = MaterialProcessor()
            await processor.process_material(str(material.material_id), task_db)
            logger.info(f"Material {material.material_id} successfully processed")
        except Exception as e:
            logger.error(f"Failed to process material {material.material_id}: {e}", exc_info=True)
        finally:
            task_db.close()

    background_tasks.add_task(process_material_task)

    logger.info(f"Material queued for processing: {material.display_name} by {current_user.email}")

    return {
        "material_id": str(material.material_id),
        "status": "processing",
        "message": "Verarbeitung gestartet"
    }


@router.get("/materials/{material_id}/content", response_model=MaterialContentResponse)
async def get_material_content(
    material_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_professor)
):
    """
    Get material content for editing.

    For lecture_slide: Combines all chunks from MaterialChunk
    For homework/tutorium/other: Combines all content from MaterialContent
    """
    try:
        material_uuid = uuid.UUID(material_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid material_id format")

    # Get material
    material = db.query(CourseMaterial).filter(
        CourseMaterial.material_id == material_uuid,
        CourseMaterial.deleted_at.is_(None)
    ).first()

    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    # Check permissions
    course = db.query(Course).filter(Course.course_id == material.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if course.owner_user_id != current_user.user_id:
        # TODO: Check if user is editor once we have permissions table
        raise HTTPException(status_code=403, detail="No permission to view this material")

    # Check if processed
    PROCESSING_MARKER = datetime(1970, 1, 1, 0, 0, 0)
    if not material.processed_at or material.processed_at <= PROCESSING_MARKER:
        raise HTTPException(status_code=400, detail="Material not yet processed")

    # Get content based on material type
    content_parts = []

    if material.material_type == 'lecture_slide':
        # Get all chunks, ordered by file_name and chunk_index
        chunks = db.query(MaterialChunk).filter(
            MaterialChunk.material_id == material_uuid
        ).order_by(
            MaterialChunk.file_name,
            MaterialChunk.chunk_index
        ).all()

        if not chunks:
            raise HTTPException(status_code=404, detail="No content found for this material")

        # Group by file_name and combine
        current_file = None
        for chunk in chunks:
            if chunk.file_name != current_file:
                if current_file is not None:
                    content_parts.append("")  # Empty line between files
                content_parts.append(f"--- File: {chunk.file_name} ---")
                content_parts.append("")
                current_file = chunk.file_name
            content_parts.append(chunk.content)

    else:
        # Get all content entries, ordered by file_name
        contents = db.query(MaterialContent).filter(
            MaterialContent.material_id == material_uuid
        ).order_by(MaterialContent.file_name).all()

        if not contents:
            raise HTTPException(status_code=404, detail="No content found for this material")

        # Combine with file separators
        for content_entry in contents:
            content_parts.append(f"--- File: {content_entry.file_name} ---")
            content_parts.append("")
            content_parts.append(content_entry.content)
            content_parts.append("")

    combined_content = "\n".join(content_parts)

    return MaterialContentResponse(
        material_id=str(material.material_id),
        material_type=material.material_type,
        display_name=material.display_name,
        content=combined_content,
        is_editable=True
    )


@router.put("/materials/{material_id}/content")
async def update_material_content(
    material_id: str,
    request: UpdateMaterialContentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_professor)
):
    """
    Update material content.

    For lecture_slide: Deletes old chunks, re-chunks, re-embeds
    For homework/tutorium/other: Updates MaterialContent entries
    """
    try:
        material_uuid = uuid.UUID(material_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid material_id format")

    # Get material
    material = db.query(CourseMaterial).filter(
        CourseMaterial.material_id == material_uuid,
        CourseMaterial.deleted_at.is_(None)
    ).first()

    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    # Check permissions
    course = db.query(Course).filter(Course.course_id == material.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if course.owner_user_id != current_user.user_id:
        # TODO: Check if user is editor once we have permissions table
        raise HTTPException(status_code=403, detail="No permission to edit this material")

    logger.info(f"Updating content for material {material.display_name} (type: {material.material_type})")

    if material.material_type == 'lecture_slide':
        # Process lecture: Delete old chunks, re-chunk, re-embed in background
        async def process_lecture_update():
            from material_processor import MaterialProcessor
            from embeddings import BedrockEmbedder
            from datetime import datetime, timezone

            task_db = next(get_db())
            try:
                processor = MaterialProcessor()
                embedder = await processor._get_embedder()

                # Log start
                processor.log_processing(
                    task_db, str(material_uuid), 'manual_edit', 'started',
                    f"Manual edit by {current_user.email}"
                )

                # Delete old chunks
                logger.info(f"Deleting old chunks for material {material_uuid}")
                deleted_count = task_db.query(MaterialChunk).filter(
                    MaterialChunk.material_id == material_uuid
                ).delete()
                task_db.commit()
                logger.info(f"Deleted {deleted_count} old chunks")

                # Chunk new content
                logger.info("Chunking new content")
                chunks = processor.chunk_text(
                    request.content,
                    chunk_size=2000,
                    overlap=300,
                    max_chunks=50
                )

                if not chunks:
                    logger.error("No chunks created from new content")
                    processor.log_processing(
                        task_db, str(material_uuid), 'chunking', 'failed',
                        "No chunks created from content"
                    )
                    return

                logger.info(f"Created {len(chunks)} new chunks")

                # Generate embeddings and save
                logger.info("Generating embeddings for new chunks")
                for i, chunk in enumerate(chunks):
                    try:
                        # Generate embedding
                        embedding = await embedder.embed_text(chunk['content'])

                        # Save chunk
                        new_chunk = MaterialChunk(
                            material_id=material_uuid,
                            file_id=None,  # No specific file for manual edits
                            content=processor.sanitize_content(chunk['content']),
                            chunk_index=i,
                            source_type='manual_edit',
                            file_name='manual_edit.md',
                            start_char=chunk.get('start_char', 0),
                            end_char=chunk.get('end_char', 0),
                            embedding=embedding
                        )
                        task_db.add(new_chunk)

                        # Commit every 10 chunks
                        if (i + 1) % 10 == 0:
                            task_db.commit()
                            logger.info(f"Saved chunks {i - 8} to {i + 1}")

                    except Exception as e:
                        logger.error(f"Error processing chunk {i}: {e}")
                        continue

                # Final commit
                task_db.commit()

                # Update processed_at
                material_obj = task_db.query(CourseMaterial).filter(
                    CourseMaterial.material_id == material_uuid
                ).first()
                material_obj.processed_at = datetime.now(timezone.utc)
                task_db.commit()

                # Log success
                processor.log_processing(
                    task_db, str(material_uuid), 'manual_edit', 'completed',
                    f"Successfully re-processed {len(chunks)} chunks"
                )

                logger.info(f"Successfully updated lecture material {material_uuid}")

            except Exception as e:
                logger.error(f"Error updating lecture material: {e}")
                processor = MaterialProcessor()
                processor.log_processing(
                    task_db, str(material_uuid), 'manual_edit', 'failed',
                    f"Error: {str(e)}"
                )
                task_db.rollback()
            finally:
                task_db.close()

        # Start background processing
        background_tasks.add_task(process_lecture_update)

        # Set processing marker immediately
        material.processed_at = datetime(1970, 1, 1, 0, 0, 0)
        db.commit()

        return {
            "material_id": str(material.material_id),
            "status": "processing",
            "message": "Lecture wird neu verarbeitet (Chunking & Embedding)"
        }

    else:
        # Update homework/tutorium/other: Update MaterialContent directly
        try:
            # Update all content entries for this material
            contents = db.query(MaterialContent).filter(
                MaterialContent.material_id == material_uuid
            ).all()

            if not contents:
                # Create new content entry if none exists
                new_content = MaterialContent(
                    material_id=material_uuid,
                    file_id=None,
                    content=request.content,
                    source_type='manual_edit',
                    file_name='manual_edit.md',
                    file_size=len(request.content),
                    importance_reason='Manual edit by professor'
                )
                db.add(new_content)
            else:
                # Update first content entry, delete others (simplification)
                contents[0].content = request.content
                contents[0].file_name = 'manual_edit.md'
                contents[0].file_size = len(request.content)
                contents[0].source_type = 'manual_edit'

                # Delete other content entries
                for content in contents[1:]:
                    db.delete(content)

            # Update processed_at
            material.processed_at = datetime.now()

            # Log
            log = MaterialProcessingLog(
                material_id=material_uuid,
                stage='manual_edit',
                status='completed',
                message=f"Manual edit by {current_user.email}",
                started_at=datetime.now(),
                completed_at=datetime.now()
            )
            db.add(log)

            db.commit()

            logger.info(f"Successfully updated {material.material_type} material {material_uuid}")

            return {
                "material_id": str(material.material_id),
                "status": "completed",
                "message": "Material erfolgreich aktualisiert"
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating material content: {e}")
            raise HTTPException(status_code=500, detail=f"Error updating material: {str(e)}")
