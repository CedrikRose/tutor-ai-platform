"""
Test the synthesis improvements.
"""
import asyncio
import json
from lecture_synthesizer import LectureSynthesizer
from llm import BedrockLLM
from prompt_manager import PromptManager
from database import SessionLocal
from config import settings
from retry_utils import BedrockCircuitBreaker


def test_page_extraction():
    """Test that _extract_pages correctly extracts all unique pages."""
    print("\n=== Test 1: Page Extraction ===")

    db = SessionLocal()
    prompt_manager = PromptManager()
    prompt_manager.initialize(db)

    circuit_breaker = BedrockCircuitBreaker(name="test_llm")
    llm = BedrockLLM(config=settings, circuit_breaker=circuit_breaker)
    synthesizer = LectureSynthesizer(llm, prompt_manager)

    # Test case 1: Multiple pages
    chunk1 = {
        "content": "Test content",
        "blocks": [
            {"bbox": {"page": 5}},
            {"bbox": {"page": 6}},
            {"bbox": {"page": 5}}  # Duplicate
        ]
    }
    pages1 = synthesizer._extract_pages(chunk1)
    assert pages1 == [5, 6], f"Expected [5, 6], got {pages1}"
    print(f"✅ Multiple pages: {pages1}")

    # Test case 2: Single page
    chunk2 = {
        "content": "Test",
        "blocks": [{"bbox": {"page": 3}}]
    }
    pages2 = synthesizer._extract_pages(chunk2)
    assert pages2 == [3], f"Expected [3], got {pages2}"
    print(f"✅ Single page: {pages2}")

    # Test case 3: No pages (fallback to 0)
    chunk3 = {
        "content": "Test",
        "blocks": []
    }
    pages3 = synthesizer._extract_pages(chunk3)
    assert pages3 == [0], f"Expected [0], got {pages3}"
    print(f"✅ No pages (fallback): {pages3}")

    # Test case 4: Top-level bbox
    chunk4 = {
        "content": "Test",
        "bbox": {"page": 10},
        "blocks": [{"bbox": {"page": 11}}]
    }
    pages4 = synthesizer._extract_pages(chunk4)
    assert pages4 == [10, 11], f"Expected [10, 11], got {pages4}"
    print(f"✅ Top-level + block bbox: {pages4}")

    db.close()
    print("✅ All page extraction tests passed!")


def test_json_parsing():
    """Test that _parse_json_response handles various formats."""
    print("\n=== Test 2: JSON Parsing ===")

    db = SessionLocal()
    prompt_manager = PromptManager()
    prompt_manager.initialize(db)

    circuit_breaker = BedrockCircuitBreaker(name="test_llm")
    llm = BedrockLLM(config=settings, circuit_breaker=circuit_breaker)
    synthesizer = LectureSynthesizer(llm, prompt_manager)

    # Test case 1: Clean JSON
    response1 = '[{"chunk_id": "0", "erklaerung": "Test 1"}]'
    result1 = synthesizer._parse_json_response(response1)
    assert result1 == [{"chunk_id": "0", "erklaerung": "Test 1"}]
    print("✅ Clean JSON parsed")

    # Test case 2: JSON in markdown block
    response2 = """Here's the result:
```json
[{"chunk_id": "0", "erklaerung": "Test 2"}]
```
Done!"""
    result2 = synthesizer._parse_json_response(response2)
    assert result2 == [{"chunk_id": "0", "erklaerung": "Test 2"}]
    print("✅ Markdown block JSON parsed")

    # Test case 3: Text before and after
    response3 = """I'll provide the synthesis now:
[{"chunk_id": "0", "erklaerung": "Test 3"}]
That's it!"""
    result3 = synthesizer._parse_json_response(response3)
    assert result3 == [{"chunk_id": "0", "erklaerung": "Test 3"}]
    print("✅ JSON with surrounding text parsed")

    # Test case 4: Multiple chunks
    response4 = '[{"chunk_id": "0", "erklaerung": "A"}, {"chunk_id": "1", "erklaerung": "B"}]'
    result4 = synthesizer._parse_json_response(response4)
    assert len(result4) == 2
    print("✅ Multiple chunks parsed")

    db.close()
    print("✅ All JSON parsing tests passed!")


def test_batch_chunks():
    """Test that batch_chunks includes pages and original_content."""
    print("\n=== Test 3: Batch Chunks ===")

    db = SessionLocal()
    prompt_manager = PromptManager()
    prompt_manager.initialize(db)

    circuit_breaker = BedrockCircuitBreaker(name="test_llm")
    llm = BedrockLLM(config=settings, circuit_breaker=circuit_breaker)
    synthesizer = LectureSynthesizer(llm, prompt_manager)

    # Mock Reducto chunks
    reducto_chunks = [
        {
            "content": "This is chunk 1 with some content that should be previewed in metadata.",
            "blocks": [{"bbox": {"page": 1}}, {"bbox": {"page": 2}}]
        },
        {
            "content": "This is chunk 2.",
            "blocks": [{"bbox": {"page": 2}}]
        }
    ]

    batches = synthesizer.batch_chunks(reducto_chunks, max_chars=15000)

    assert len(batches) == 1, f"Expected 1 batch, got {len(batches)}"
    batch = batches[0]

    assert len(batch) == 2, f"Expected 2 chunks in batch, got {len(batch)}"

    # Check first chunk
    chunk0 = batch[0]
    assert chunk0["chunk_id"] == 0
    assert chunk0["pages"] == [1, 2], f"Expected [1, 2], got {chunk0['pages']}"
    assert "original_content" in chunk0
    assert len(chunk0["original_content"]) <= 200
    print(f"✅ Chunk 0: pages={chunk0['pages']}, preview_len={len(chunk0['original_content'])}")

    # Check second chunk
    chunk1 = batch[1]
    assert chunk1["chunk_id"] == 1
    assert chunk1["pages"] == [2], f"Expected [2], got {chunk1['pages']}"
    print(f"✅ Chunk 1: pages={chunk1['pages']}")

    db.close()
    print("✅ Batch chunks test passed!")


def check_database_schema():
    """Check that the chunk_metadata column exists."""
    print("\n=== Test 4: Database Schema ===")

    from sqlalchemy import text
    from database import engine

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name='material_chunks' AND column_name='chunk_metadata'
        """))

        row = result.fetchone()
        if row:
            print(f"✅ chunk_metadata column exists: {row[0]} ({row[1]})")
        else:
            print("❌ chunk_metadata column NOT found!")
            return False

        # Check index
        result = conn.execute(text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename='material_chunks' AND indexname='idx_material_chunks_metadata_source'
        """))

        row = result.fetchone()
        if row:
            print(f"✅ Metadata index exists: {row[0]}")
        else:
            print("⚠️  Metadata index NOT found (optional)")

    print("✅ Database schema check passed!")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Synthesis Improvements")
    print("=" * 60)

    try:
        # Test database schema first
        if not check_database_schema():
            print("\n❌ Database schema check failed - skipping other tests")
            exit(1)

        # Test functions
        test_page_extraction()
        test_json_parsing()
        test_batch_chunks()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
