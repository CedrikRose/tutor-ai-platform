"""
Reprocess Failed Materials

Reprocesses the 12 materials that failed during the initial Reducto migration.
"""
import asyncio
import sys
from database import SessionLocal
from material_processor import MaterialProcessor
from prompt_manager import prompt_manager

async def main():
    # Initialize prompt manager first
    db = SessionLocal()
    try:
        print("Initializing prompt manager...")
        prompt_manager.initialize(db)
        print(f"✓ Loaded {prompt_manager.cache_size} prompts\n")
    finally:
        db.close()

    processor = MaterialProcessor()

    # Read failed IDs
    try:
        with open('failed_material_ids.txt', 'r') as f:
            material_ids = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("ERROR: failed_material_ids.txt not found!")
        sys.exit(1)

    print(f"=== Reprocessing {len(material_ids)} failed materials ===\n")

    successes = []
    failures = []

    for i, material_id in enumerate(material_ids, 1):
        print(f"[{i}/{len(material_ids)}] Processing: {material_id}")
        db = SessionLocal()
        try:
            await processor.process_material(material_id, db)
            print(f"  ✅ Success\n")
            successes.append(material_id)
        except Exception as e:
            print(f"  ❌ Failed: {e}\n")
            failures.append((material_id, str(e)))
        finally:
            db.close()

    # Summary
    print("\n" + "="*60)
    print(f"SUMMARY:")
    print(f"  Total:     {len(material_ids)}")
    print(f"  Successes: {len(successes)}")
    print(f"  Failures:  {len(failures)}")
    print("="*60)

    if successes:
        print("\n✅ Successfully processed:")
        for mat_id in successes:
            print(f"  - {mat_id}")

    if failures:
        print("\n❌ Failed materials:")
        for mat_id, error in failures:
            print(f"  - {mat_id}: {error}")

if __name__ == "__main__":
    asyncio.run(main())
