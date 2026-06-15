"""
Re-process all non-lecture materials with new 2-stage filtering.

This script:
1. Finds all non-lecture materials (homework, tutorium, other)
2. Deletes old MaterialContent entries
3. Re-processes with new 2-stage filtering
4. Logs results

IMPORTANT: Run this only after backup!
"""
import asyncio
import logging
from datetime import datetime, timezone
from database import SessionLocal, CourseMaterial, MaterialContent
from material_processor import MaterialProcessor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def reprocess_all_non_lectures():
    """Re-process all non-lecture materials."""

    db = SessionLocal()
    processor = MaterialProcessor()

    try:
        # Find all non-lecture materials
        PROCESSING_MARKER = datetime(1970, 1, 1, tzinfo=timezone.utc)

        materials = db.query(CourseMaterial).filter(
            CourseMaterial.material_type != 'lecture_slide',
            CourseMaterial.deleted_at == None,
            CourseMaterial.processed_at != None,
            CourseMaterial.processed_at > PROCESSING_MARKER
        ).all()

        logger.info(f"Found {len(materials)} non-lecture materials to reprocess")

        if not materials:
            logger.info("No materials to reprocess")
            return

        # Ask for confirmation
        print("\n" + "="*80)
        print(f"⚠️  About to re-process {len(materials)} non-lecture materials")
        print("   This will:")
        print("   - Delete old MaterialContent entries")
        print("   - Re-run 2-stage filtering")
        print("   - Potentially store FEWER files than before")
        print("="*80 + "\n")

        confirm = input("Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            logger.info("Aborted by user")
            return

        # Statistics
        success_count = 0
        failed_count = 0
        skipped_count = 0

        # Process each material
        for idx, material in enumerate(materials, 1):
            material_id = str(material.material_id)

            logger.info(f"\n[{idx}/{len(materials)}] Processing: {material.display_name} ({material.material_type})")

            try:
                # Delete old content
                old_content_count = db.query(MaterialContent).filter(
                    MaterialContent.material_id == material.material_id
                ).delete()

                db.commit()
                logger.info(f"  Deleted {old_content_count} old content entries")

                # Reset processed_at to trigger re-processing
                material.processed_at = None
                db.commit()

                # Re-process with new 2-stage filtering
                await processor.process_material(material_id, db)

                # Check result
                new_content_count = db.query(MaterialContent).filter(
                    MaterialContent.material_id == material.material_id
                ).count()

                logger.info(f"  ✅ Success: {new_content_count} new content entries (was: {old_content_count})")

                if new_content_count < old_content_count:
                    logger.warning(f"  ⚠️  Stored FEWER files: {old_content_count} → {new_content_count}")

                success_count += 1

            except Exception as e:
                logger.error(f"  ❌ Failed: {e}", exc_info=True)
                failed_count += 1
                db.rollback()
                continue

        # Final summary
        print("\n" + "="*80)
        print("Re-processing Complete!")
        print(f"  ✅ Success: {success_count}")
        print(f"  ❌ Failed: {failed_count}")
        print(f"  Total: {len(materials)}")
        print("="*80 + "\n")

        logger.info("Re-processing complete")

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(reprocess_all_non_lectures())
