"""
Add file_intelligent_truncation prompt to database.

Run once to add the missing prompt for large file handling.
"""
import logging
from datetime import datetime, timezone
from database import SessionLocal, SystemPrompt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_truncation_prompt():
    """Add file_intelligent_truncation prompt to system_prompts table."""
    db = SessionLocal()

    try:
        truncation_prompt = SystemPrompt(
            prompt_key="file_intelligent_truncation",
            prompt_name="Intelligente Datei-Kürzung für große Code-Dateien",
            prompt_content="""Du bist ein Code-Analyzer. Deine Aufgabe ist es, große Code-Dateien intelligent zu kürzen.

**Datei:** {file_name}

{content_info}

**Aufgabe:**
Analysiere die Datei und entscheide:

1. **Behalten (shortened_content: null)** - Wenn:
   - Die Datei wichtigen, nicht-redundanten Code enthält
   - Setup-Code, Konfiguration oder wichtige Imports
   - Die Länge vertretbar ist (<15KB)

2. **Kürzen (shortened_content: string)** - Wenn:
   - Viele repetitive Funktionen/Klassen
   - Boilerplate-Code (Getter/Setter, Standard-Implementierungen)
   - Test-Daten oder Mock-Objekte
   - Kommentare ohne kritische Info
   - Die Datei >15KB ist

**Beim Kürzen:**
- Behalte: Klassen-/Funktions-Signaturen, wichtige Logik, Imports
- Entferne: Repetitive Implementations, Boilerplate, verbose Kommentare
- Markiere gekürzte Stellen mit `[... gekürzt: X Zeilen ...]`
- Ziel: Max 50% der Original-Länge

**Output-Format (JSON):**
{
  "shortened_content": null oder "gekürzter Text",
  "reason": "Begründung für Entscheidung"
}

**Wichtig:** Sei KONSERVATIV beim Kürzen. Im Zweifel → nicht kürzen!""",
            description="Intelligente Kürzung großer Code-Dateien (>10KB) durch LLM. Entfernt Boilerplate und Redundanz, behält wichtige Logik.",
            category="material",
            temperature=0.3,
            max_tokens=16384,
            updated_at=datetime.now(timezone.utc),
            updated_by="migration_script",
            version=1
        )

        # Check if prompt already exists
        existing = db.query(SystemPrompt).filter(
            SystemPrompt.prompt_key == "file_intelligent_truncation"
        ).first()

        if existing:
            logger.info("Truncation prompt already exists, updating...")
            existing.prompt_content = truncation_prompt.prompt_content
            existing.prompt_name = truncation_prompt.prompt_name
            existing.description = truncation_prompt.description
            existing.temperature = truncation_prompt.temperature
            existing.max_tokens = truncation_prompt.max_tokens
            existing.updated_at = datetime.now(timezone.utc)
            existing.version = (existing.version or 0) + 1
        else:
            logger.info("Adding truncation prompt...")
            db.add(truncation_prompt)

        db.commit()

        logger.info("✅ Truncation prompt added successfully!")
        logger.info("   - file_intelligent_truncation")

    except Exception as e:
        logger.error(f"Failed to add prompt: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    add_truncation_prompt()
