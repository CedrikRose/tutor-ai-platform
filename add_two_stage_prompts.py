"""
Add two-stage file analysis prompts to database.

Run once to add the new prompts for 2-stage material file filtering.
"""
import logging
from datetime import datetime, timezone
from database import SessionLocal, SystemPrompt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_two_stage_prompts():
    """Add Stage 1 and Stage 2 prompts to system_prompts table."""
    db = SessionLocal()

    try:
        # Stage 1 Prompt
        stage1_prompt = SystemPrompt(
            prompt_key="material_file_analysis_stage1_fast",
            prompt_name="Material File Analysis - Stage 1 (Fast Categorization)",
            prompt_content="""Du analysierst Kursmaterial-Dateien um zu bestimmen welche für Studenten wichtig sind.

**Kontext:**
Material-Typ: {material_type}
Material-Name: {display_name}

{pdf_context}

**Dateiliste:**
{filenames}

**Aufgabe:**
Kategorisiere ALLE Dateien in 3 Listen:

**1. definitely_important** - Dateien die mit sehr hoher Wahrscheinlichkeit wichtig sind:
- In der Aufgabenstellung direkt erwähnt (z.B. "Implementiere Factorial.java")
- Main-Dateien (Main.java, app.py, index.js, __main__.py)
- Test-Dateien (wenn das Projekt Tests enthält: *Test.java, test_*.py)
- Starter-Code-Dateien die Student bearbeiten soll

**2. definitely_unimportant** - Dateien die mit Sicherheit unwichtig sind:
- Build Artifacts: .class, .o, .pyc, .jar, .war, .exe
- Dependencies: node_modules/, lib/*.jar, .venv/, __pycache__/
- IDE Config: .classpath, .project, .idea/, .vscode/, .settings/
- Build Scripts: build.xml, Makefile, pom.xml, build.gradle, package-lock.json
- System Files: .DS_Store, Thumbs.db, desktop.ini
- Compiled/Generated: target/, dist/, build/, out/

**3. unsure** - Alle anderen Dateien:
- Utility-Klassen (Helper.java, Utils.py, Common.js)
- Config-Dateien (config.json, settings.xml, .properties)
- Dokumentation (README.md, INSTALL.txt, docs/)
- Ressourcen-Dateien (resources/, assets/)

**Wichtig:**
- Sei KONSERVATIV bei "definitely_important" (nur wenn sehr sicher!)
- Sei STRENG bei "definitely_unimportant" (nur offensichtliche Build-Artifacts)
- Im Zweifel → "unsure" Liste

**Output-Format:**
Strukturiertes JSON mit 3 Listen:
{
  "definitely_important": [{"filename": "...", "reason": "..."}],
  "definitely_unimportant": [{"filename": "...", "reason": "..."}],
  "unsure": [{"filename": "...", "reason": "..."}]
}""",
            description="Stage 1 des 2-stufigen File-Filterings. Schnelle Kategorisierung basierend nur auf Dateinamen und PDF-Kontext.",
            category="material",
            temperature=0.2,
            max_tokens=2000,
            updated_at=datetime.now(timezone.utc),
            updated_by="migration_script",
            version=1
        )

        # Stage 2 Prompt
        stage2_prompt = SystemPrompt(
            prompt_key="material_file_analysis_stage2_detailed",
            prompt_name="Material File Analysis - Stage 2 (Detailed Analysis)",
            prompt_content="""Du analysierst "unsure" Dateien um zu bestimmen ob sie essenziell zum Lösen der Aufgabe sind.

**Aufgabenstellung:**
{pdf_context}

**Bereits als wichtig erkannte Dateien:**
{important_files}

**Zu analysierende Dateien mit Preview (erste 500 Zeichen):**
{unsure_files_with_preview}

**Aufgabe:**
Für jede Datei: Ist sie ESSENZIELL zum Lösen der Aufgabe?

**Kriterien für "essential":**
✅ Wird von wichtigen Dateien importiert/verwendet
✅ Enthält Setup-/Build-Instruktionen die Student braucht
✅ Enthält notwendige Hilfsfunktionen für die Aufgabe
✅ README mit kritischen Informationen (wie kompilieren, wie testen)

**Kriterien für "not_essential":**
❌ Nur IDE-Konfiguration
❌ Nur Komfortfunktionen (nicht notwendig)
❌ Nur Beispiele/Demos (nicht Teil der Aufgabe)
❌ Nur Dokumentation ohne kritische Info

**Wichtig:**
Sei STRENG: Im Zweifel → "not_essential"
Nur ESSENZIELLES wird included!

**Output-Format:**
Strukturiertes JSON mit 2 Listen:
{
  "essential": [{"filename": "...", "reason": "..."}],
  "not_essential": [{"filename": "...", "reason": "..."}]
}""",
            description="Stage 2 des 2-stufigen File-Filterings. Detaillierte Analyse mit Content-Previews nur für unsichere Dateien.",
            category="material",
            temperature=0.3,
            max_tokens=1500,
            updated_at=datetime.now(timezone.utc),
            updated_by="migration_script",
            version=1
        )

        # Check if prompts already exist
        existing_stage1 = db.query(SystemPrompt).filter(
            SystemPrompt.prompt_key == "material_file_analysis_stage1_fast"
        ).first()

        existing_stage2 = db.query(SystemPrompt).filter(
            SystemPrompt.prompt_key == "material_file_analysis_stage2_detailed"
        ).first()

        if existing_stage1:
            logger.info("Stage 1 prompt already exists, updating...")
            existing_stage1.prompt_content = stage1_prompt.prompt_content
            existing_stage1.prompt_name = stage1_prompt.prompt_name
            existing_stage1.description = stage1_prompt.description
            existing_stage1.temperature = stage1_prompt.temperature
            existing_stage1.max_tokens = stage1_prompt.max_tokens
            existing_stage1.updated_at = datetime.now(timezone.utc)
            existing_stage1.version = (existing_stage1.version or 0) + 1
        else:
            logger.info("Adding Stage 1 prompt...")
            db.add(stage1_prompt)

        if existing_stage2:
            logger.info("Stage 2 prompt already exists, updating...")
            existing_stage2.prompt_content = stage2_prompt.prompt_content
            existing_stage2.prompt_name = stage2_prompt.prompt_name
            existing_stage2.description = stage2_prompt.description
            existing_stage2.temperature = stage2_prompt.temperature
            existing_stage2.max_tokens = stage2_prompt.max_tokens
            existing_stage2.updated_at = datetime.now(timezone.utc)
            existing_stage2.version = (existing_stage2.version or 0) + 1
        else:
            logger.info("Adding Stage 2 prompt...")
            db.add(stage2_prompt)

        db.commit()

        logger.info("✅ Two-stage prompts added successfully!")
        logger.info("   - material_file_analysis_stage1_fast")
        logger.info("   - material_file_analysis_stage2_detailed")

    except Exception as e:
        logger.error(f"Failed to add prompts: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    add_two_stage_prompts()
