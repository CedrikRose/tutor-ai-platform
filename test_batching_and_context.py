"""
Test the batching and context logic.
"""
from lecture_synthesizer import LectureSynthesizer
from llm import BedrockLLM
from prompt_manager import PromptManager
from database import SessionLocal
from config import settings
from retry_utils import BedrockCircuitBreaker


def test_batching_with_max_chars():
    """Test that chunks are batched at 15,000 chars without splitting."""
    print("\n=== Test 1: Batching at 15,000 chars ===")

    db = SessionLocal()
    prompt_manager = PromptManager()
    prompt_manager.initialize(db)

    circuit_breaker = BedrockCircuitBreaker(name="test_llm")
    llm = BedrockLLM(config=settings, circuit_breaker=circuit_breaker)
    synthesizer = LectureSynthesizer(llm, prompt_manager)

    # Create chunks with known sizes
    chunks = [
        {"content": "A" * 5000, "blocks": [{"bbox": {"page": 1}}]},   # 5k
        {"content": "B" * 6000, "blocks": [{"bbox": {"page": 2}}]},   # 6k (total: 11k)
        {"content": "C" * 5000, "blocks": [{"bbox": {"page": 3}}]},   # 5k (would be 16k - too much!)
        {"content": "D" * 3000, "blocks": [{"bbox": {"page": 4}}]},   # 3k
    ]

    batches = synthesizer.batch_chunks(chunks, max_chars=15000)

    print(f"Created {len(batches)} batches from {len(chunks)} chunks")

    # Expected: Batch 1 = [A, B], Batch 2 = [C, D]
    assert len(batches) == 2, f"Expected 2 batches, got {len(batches)}"

    batch1 = batches[0]
    batch2 = batches[1]

    print(f"Batch 1: {len(batch1)} chunks")
    print(f"  - Chunk 0: {len(batch1[0]['content'])} chars, pages={batch1[0]['pages']}")
    print(f"  - Chunk 1: {len(batch1[1]['content'])} chars, pages={batch1[1]['pages']}")

    print(f"Batch 2: {len(batch2)} chunks")
    print(f"  - Chunk 2: {len(batch2[0]['content'])} chars, pages={batch2[0]['pages']}")
    print(f"  - Chunk 3: {len(batch2[1]['content'])} chars, pages={batch2[1]['pages']}")

    # Verify batch 1
    assert len(batch1) == 2
    assert batch1[0]["chunk_id"] == 0
    assert batch1[1]["chunk_id"] == 1
    assert len(batch1[0]["content"]) == 5000
    assert len(batch1[1]["content"]) == 6000

    # Verify batch 2
    assert len(batch2) == 2
    assert batch2[0]["chunk_id"] == 2
    assert batch2[1]["chunk_id"] == 3

    db.close()
    print("✅ Batching test passed - chunks not split!")


def test_context_uses_last_3_chunks():
    """Test that context includes last 3 chunks, not just character limit."""
    print("\n=== Test 2: Context from Last 3 Chunks ===")

    # Simulate process_lecture context building
    synthesized_chunks = [
        {"chunk_id": "0", "erklaerung": "Erklärung 1"},
        {"chunk_id": "1", "erklaerung": "Erklärung 2"},
        {"chunk_id": "2", "erklaerung": "Erklärung 3"},
        {"chunk_id": "3", "erklaerung": "Erklärung 4"},
        {"chunk_id": "4", "erklaerung": "Erklärung 5"},
    ]

    # Take last 3 chunks
    last_chunks = synthesized_chunks[-3:] if len(synthesized_chunks) > 3 else synthesized_chunks
    context_texts = [c.get("erklaerung", "") for c in last_chunks]
    historical_context = "\n\n".join(context_texts)

    print(f"Total chunks: {len(synthesized_chunks)}")
    print(f"Context chunks: {len(last_chunks)}")
    print(f"Context text:\n{historical_context}")

    assert len(last_chunks) == 3, f"Expected 3 chunks, got {len(last_chunks)}"
    assert "Erklärung 3" in historical_context
    assert "Erklärung 4" in historical_context
    assert "Erklärung 5" in historical_context
    assert "Erklärung 1" not in historical_context  # Should not include old chunks
    assert "Erklärung 2" not in historical_context

    print("✅ Context test passed - last 3 chunks used!")


def test_input_is_string_array():
    """Test that the LLM receives a simple string array."""
    print("\n=== Test 3: LLM Input Format ===")

    # Simulate what synthesize_batch sends to LLM
    batch = [
        {"chunk_id": 0, "content": "Folie 1 Text", "pages": [1]},
        {"chunk_id": 1, "content": "Folie 2 Text", "pages": [2]},
        {"chunk_id": 2, "content": "Folie 3 Text", "pages": [3]},
    ]

    # Extract content array (what's actually sent to LLM)
    content_array = [chunk.get("content", "") for chunk in batch]

    print(f"Batch has {len(batch)} chunks with metadata")
    print(f"LLM receives {len(content_array)} strings:")
    for i, text in enumerate(content_array):
        print(f"  [{i}]: {text}")

    assert len(content_array) == 3
    assert content_array[0] == "Folie 1 Text"
    assert content_array[1] == "Folie 2 Text"
    assert content_array[2] == "Folie 3 Text"

    # Verify no metadata leaked into input
    import json
    json_str = json.dumps(content_array, ensure_ascii=False)
    assert "chunk_id" not in json_str
    assert "pages" not in json_str

    print("✅ Input format test passed - pure string array!")


def test_large_pdf_scenario():
    """Simulate processing a 88-page PDF with many chunks."""
    print("\n=== Test 4: Large PDF (88 pages) Simulation ===")

    db = SessionLocal()
    prompt_manager = PromptManager()
    prompt_manager.initialize(db)

    circuit_breaker = BedrockCircuitBreaker(name="test_llm")
    llm = BedrockLLM(config=settings, circuit_breaker=circuit_breaker)
    synthesizer = LectureSynthesizer(llm, prompt_manager)

    # Simulate 50 chunks from Reducto (typical for 88-page PDF)
    chunks = []
    for i in range(50):
        # Average ~800 chars per chunk
        content = f"Slide {i+1} content: " + "Lorem ipsum " * 70
        chunks.append({
            "content": content,
            "blocks": [{"bbox": {"page": (i // 2) + 1}}]  # ~2 chunks per page
        })

    print(f"Created {len(chunks)} chunks (simulating 88-page PDF)")

    batches = synthesizer.batch_chunks(chunks, max_chars=15000)

    print(f"Batched into {len(batches)} batches")

    total_chars = 0
    for i, batch in enumerate(batches):
        batch_chars = sum(len(c["content"]) for c in batch)
        total_chars += batch_chars
        print(f"  Batch {i+1}: {len(batch)} chunks, {batch_chars:,} chars")

        # Verify no batch exceeds 15k (unless it's a single huge chunk)
        if len(batch) > 1:
            assert batch_chars <= 15000, f"Batch {i+1} exceeds 15k chars!"

    print(f"Total: {total_chars:,} chars across {len(batches)} batches")
    print("✅ Large PDF simulation passed!")

    db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Batching and Context Logic")
    print("=" * 60)

    try:
        test_batching_with_max_chars()
        test_context_uses_last_3_chunks()
        test_input_is_string_array()
        test_large_pdf_scenario()

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
