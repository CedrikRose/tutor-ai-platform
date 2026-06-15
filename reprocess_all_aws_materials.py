"""
Re-process all AWS materials locally with new processing logic.

This script:
1. Finds all materials from AWS backup
2. Deletes old MaterialContent and MaterialChunk entries
3. Re-processes with new Reducto + Two-Stage filtering
4. Logs progress

Run this LOCALLY after restoring AWS database backup.
"""
import asyncio
import logging
from datetime import datetime, timezone
from database import SessionLocal, CourseMaterial, MaterialContent, MaterialChunk
from material_processor import MaterialProcessor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def reprocess_all_aws_materials():
    """Re-process all AWS materials locally."""

    db = SessionLocal()
    processor = MaterialProcessor()

    try:
        # Find all non-deleted materials
        materials = db.query(CourseMaterial).filter(
            CourseMaterial.deleted_at == None
        ).all()

        logger.info(f"Found {len(materials)} materials to reprocess")

        if not materials:
            logger.info("No materials to reprocess")
            return

        # Ask for confirmation
        print("\n" + "="*80)
        print(f"⚠️  About to re-process {len(materials)} materials")
        print("   This will:")
        print("   - Delete old MaterialContent and MaterialChunk entries")
        print("   - Re-run processing with new Reducto + Two-Stage filtering logic")
        print("   - Use your LOCAL PC's performance")
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
                # Delete old chunks (lectures)
                old_chunk_count = db.query(MaterialChunk).filter(
                    MaterialChunk.material_id == material.material_id
                ).delete()

                # Delete old content (non-lectures)
                old_content_count = db.query(MaterialContent).filter(
                    MaterialContent.material_id == material.material_id
                ).delete()

                db.commit()
                logger.info(f"  Deleted {old_chunk_count} chunks, {old_content_count} contents")

                # Reset processed_at to trigger re-processing
                material.processed_at = None
                db.commit()

                # Re-process with new logic
                await processor.process_material(material_id, db)

                # Check result
                new_chunk_count = db.query(MaterialChunk).filter(
                    MaterialChunk.material_id == material.material_id
                ).count()

                new_content_count = db.query(MaterialContent).filter(
                    MaterialContent.material_id == material.material_id
                ).count()

                logger.info(f"  ✅ Success: {new_chunk_count} chunks, {new_content_count} contents")

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
    asyncio.run(reprocess_all_aws_materials())
