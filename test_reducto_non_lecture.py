"""
Test script for Reducto integration with non-lecture materials.

Tests the new parse_pdf_with_reducto() method to ensure it correctly:
1. Parses PDFs with Reducto
2. Combines all chunks into a single string
3. Returns proper error messages on failure
"""
import asyncio
import logging
from pathlib import Path

from material_processor import MaterialProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_reducto_parsing():
    """Test the new Reducto parsing for non-lecture materials."""

    processor = MaterialProcessor()

    # Test 1: Parse a real PDF if available
    test_pdf_paths = [
        "uploads/courses/*/materials/*/Aufgabenblatt.pdf",
        "uploads/courses/*/materials/*/*.pdf",
    ]

    # Find a test PDF
    test_pdf = None
    for pattern in test_pdf_paths:
        from glob import glob
        matches = glob(pattern)
        if matches:
            test_pdf = matches[0]
            break

    if test_pdf:
        logger.info(f"Testing with PDF: {test_pdf}")

        try:
            content = await processor.parse_pdf_with_reducto(test_pdf)

            logger.info("=" * 80)
            logger.info("PARSE RESULT:")
            logger.info(f"Content length: {len(content)} characters")
            logger.info(f"First 500 chars:\n{content[:500]}")
            logger.info(f"Last 200 chars:\n{content[-200:]}")
            logger.info("=" * 80)

            # Verify it's not an error message
            if content.startswith("[") and "Error" in content:
                logger.error("❌ Parsing returned an error message")
            elif len(content) < 100:
                logger.warning("⚠️  Content seems very short")
            else:
                logger.info("✅ Parsing successful!")

        except Exception as e:
            logger.error(f"❌ Test failed with exception: {e}", exc_info=True)

    else:
        logger.warning("No test PDF found. Upload a homework PDF to test.")
        logger.info("Testing with mock data instead...")

        # Test 2: Test error handling with non-existent file
        fake_path = "uploads/nonexistent.pdf"
        logger.info(f"\nTesting error handling with: {fake_path}")

        try:
            content = await processor.parse_pdf_with_reducto(fake_path)
            logger.info(f"Result: {content}")

            if "Error" in content or "failed" in content:
                logger.info("✅ Error handling works correctly!")
            else:
                logger.error("❌ Error handling didn't work as expected")
        except Exception as e:
            logger.info(f"✅ Exception raised as expected: {e}")


if __name__ == "__main__":
    asyncio.run(test_reducto_parsing())
