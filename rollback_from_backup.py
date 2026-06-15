"""
Rollback material_contents from backup JSON file.
"""
import json
import logging
from datetime import datetime
from database import SessionLocal, MaterialContent
from uuid import UUID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def rollback_from_backup(backup_file: str):
    """Restore material_contents from backup."""

    db = SessionLocal()

    try:
        # Load backup
        logger.info(f"Loading backup from {backup_file}...")
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)

        logger.info(f"Loaded {len(backup_data)} records from backup")

        # Delete current data
        logger.info("Deleting current material_contents...")
        deleted = db.query(MaterialContent).delete()
        db.commit()
        logger.info(f"Deleted {deleted} current records")

        # Restore from backup
        logger.info("Restoring from backup...")
        for idx, record in enumerate(backup_data, 1):
            content = MaterialContent(
                content_id=UUID(record['content_id']),
                material_id=UUID(record['material_id']),
                file_id=UUID(record['file_id']) if record['file_id'] else None,
                content=record['content'],
                source_type=record['source_type'],
                file_name=record['file_name'],
                file_size=record['file_size'],
                importance_reason=record['importance_reason'],
                created_at=datetime.fromisoformat(record['created_at']) if record['created_at'] else None
            )
            db.add(content)

            if idx % 100 == 0:
                db.commit()
                logger.info(f"  Restored {idx}/{len(backup_data)}...")

        db.commit()
        logger.info(f"✅ Rollback complete: {len(backup_data)} records restored")

    except Exception as e:
        logger.error(f"Rollback failed: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    rollback_from_backup("backup_material_contents_20260612_191658.json")
