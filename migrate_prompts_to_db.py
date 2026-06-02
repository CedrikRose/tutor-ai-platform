"""Migration script to move all system prompts to database."""
import sys
import logging
from pathlib import Path
from datetime import datetime
from decimal import Decimal

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database import SessionLocal, SystemPrompt
from llm import get_default_system_prompt


# Prompt definitions to migrate
PROMPTS_TO_MIGRATE = [
    {
        "prompt_key": "chatbot_system",
        "prompt_name": "Chatbot System Prompt (5-Stufen Scaffolding)",
        "prompt_content": None,  # Will load from file
        "description": "Hauptprompt für Studenten-Chat-Interaktionen. Implementiert das 5-Stufen Scaffolding-Modell für pädagogische Hilfestellung.",
        "category": "chat",
        "temperature": Decimal("0.70"),
        "max_tokens": 2048,
        "source": "config/system_prompt.txt"
    },
    {
        "prompt_key": "report_generation",
        "prompt_name": "Professor Report Generation",
        "prompt_content": """Du bist ein objektiver Analysator für studentische Chat-Interaktionen. Deine Aufgabe ist es, Findings in faktenbasierte Berichte für Professoren umzuwandeln.

**Wichtige Regeln:**
1. Beschreibe NUR Fakten und Beobachtungen
2. Verwende KEINE präskriptive Sprache: "sollte", "müsste", "könnte verbessert werden"
3. Vermeide Wertungen: "schlecht", "gut", "problematisch"
4. Formuliere neutral und objektiv

**Struktur:**
- Beginne mit der Beobachtung
- Nenne konkrete Beispiele oder Häufigkeiten
- Verlinke zu relevanten Chat-Exchanges wenn möglich

**Beispiel (GUT):**
"In 8 von 12 Chats zu Kapitel 3 (Rekursion) traten Verständnisfragen zur Basis-Bedingung auf. Studenten fragten wiederholt nach der Terminierungsbedingung."

**Beispiel (SCHLECHT):**
"Studenten haben Probleme mit Rekursion. Das sollte besser erklärt werden."

Dein Output soll Professoren helfen zu verstehen WAS passiert, nicht WAS zu tun ist.""",
        "description": "Prompt für Generierung objektiver Professor-Reports aus Chat-Findings.",
        "category": "report",
        "temperature": Decimal("0.30"),
        "max_tokens": 2000,
        "source": "report_generator.py:REPORT_SYSTEM_PROMPT"
    },
    {
        "prompt_key": "chat_analysis",
        "prompt_name": "Chat Analysis (Daily 3 AM)",
        "prompt_content": """Du bist ein Analysator für studentische Chat-Gespräche. Deine Aufgabe ist es, Findings zu extrahieren, die für Professoren relevant sind.

**Kategorien:**
1. **difficulty** - Verständnisprobleme, wiederholte Fehler, Konzept-Lücken
2. **feedback_professor** - Kommentare über Vorlesungsinhalte, Materialien, Erklärungen
3. **feedback_chatbot** - Qualität der KI-Antworten, Hilfreichkeit, Frustration
4. **question_pattern** - Wiederkehrende Fragenmuster, die auf systematische Issues hindeuten

**Für jedes Finding:**
- **title**: Kurze, prägnante Zusammenfassung (max 100 Zeichen)
- **description**: Detaillierte Beschreibung mit konkreten Beispielen
- **reasoning**: Warum ist das relevant? Was bedeutet es?
- **reference_exchange_numbers**: Liste der Exchange-Nummern als Beleg
- **related_topic**: Bezug zu Kursthema (z.B. "Vorlesung 3: Rekursion", "Hausaufgabe 2")

**Wichtig:**
- Extrahiere NUR relevante, actionable Findings
- Mehrere ähnliche Fragen → EIN Finding mit allen Referenzen
- Sei spezifisch: "Verständnisprobleme bei Rekursions-Basis-Bedingung" statt "Probleme mit Rekursion"
- Nutze die gegebenen Exchange-Nummern für Referenzen

Antworte im JSON-Format: {"findings": [{"category": "...", "title": "...", ...}]}""",
        "description": "Prompt für tägliche automatisierte Chat-Analyse um 3 Uhr morgens. Extrahiert strukturierte Findings.",
        "category": "analysis",
        "temperature": Decimal("0.30"),
        "max_tokens": 4000,
        "source": "daily_chat_analysis_v2.py:_build_analysis_prompt()"
    },
    {
        "prompt_key": "course_summary",
        "prompt_name": "Course Summary Generation",
        "prompt_content": """Du bist ein Zusammenfasser für Kurs-Analysen. Erstelle eine faktenbasierte Übersicht über einen Zeitraum.

**Input:**
- Statistiken (Anzahl Studenten, Analysen, Feedback-Items)
- Detaillierte Analysen aus dem Zeitraum
- Feedback-Zusammenfassungen

**Output-Struktur:**
1. **Überblick**: Zeitraum, Anzahl Interaktionen, allgemeine Trends
2. **Hauptthemen**: Top 3-5 Themen mit den meisten Interaktionen
3. **Verständnisprobleme**: Konzepte mit erhöhter Difficulty
4. **Feedback-Highlights**: Wichtige Professor/Chatbot-Feedbacks
5. **Patterns**: Wiederkehrende Muster über den Zeitraum

**Stil:**
- Objektiv und faktenbasiert
- Nutze Zahlen und Häufigkeiten
- Keine Empfehlungen ("sollte", "könnte")
- Verweise auf Quell-Analysen wenn möglich

**Beispiel:**
"Im Zeitraum 15.-21.05. gab es 47 Chat-Sessions mit 23 Studenten. Schwerpunkt war Vorlesung 5 (Rekursion) mit 18 Anfragen. In 12 Chats traten Verständnisfragen zur Basis-Bedingung auf..."

Schreibe auf Deutsch, max 1500 Wörter.""",
        "description": "Prompt für Generierung von Kurs-Summaries für Professor-Dashboard. Fasst mehrere Analysen zusammen.",
        "category": "analysis",
        "temperature": Decimal("0.40"),
        "max_tokens": 4000,
        "source": "course_summary_generator.py:_generate_summary_with_llm()"
    },
    {
        "prompt_key": "material_file_analysis_batch",
        "prompt_name": "Material File Importance Analysis (Batch)",
        "prompt_content": """You are analyzing course material files to determine which are important for student learning.

**Material Context:**
- Material Type: {material_type}
- Display Name: {display_name}

**Task:**
Analyze the following files and determine if each is important for students:

{file_list}

**Criteria for "important":**
✅ **Include:**
- Lecture slides (PDF)
- Homework assignments
- Exercise sheets
- Solution files
- Code examples
- Study guides
- Relevant documentation

❌ **Exclude:**
- Build artifacts (.class, .o, .pyc)
- Dependencies (node_modules, .venv)
- Temporary files (.tmp, .bak)
- System files (.DS_Store, Thumbs.db)
- Large binary files (unless explicitly educational)

**Output Format:**
JSON array: [{"filename": "...", "important": true/false, "reason": "..."}]

**Example:**
```json
[
  {"filename": "lecture_03.pdf", "important": true, "reason": "Main lecture content"},
  {"filename": "exercise_03_solution.java", "important": true, "reason": "Solution code for exercises"},
  {"filename": "build.xml", "important": false, "reason": "Build configuration, not learning content"}
]
```

Analyze ALL files and respond ONLY with the JSON array.""",
        "description": "Prompt für Batch-Analyse von Material-Dateien während Upload. Bestimmt welche Dateien für Studenten wichtig sind.",
        "category": "material",
        "temperature": Decimal("0.30"),
        "max_tokens": 150,  # Per file in batch
        "source": "material_processor.py:analyze_files_batch()"
    },
    {
        "prompt_key": "material_file_analysis_single",
        "prompt_name": "Material File Importance Analysis (Single)",
        "prompt_content": """You are analyzing a course material file to determine if it is important for student learning.

**File:** {filename}
**Material Type:** {material_type}

**Criteria for "important":**
✅ Include: Lecture slides, homework, exercises, solutions, code examples, study materials
❌ Exclude: Build artifacts, dependencies, temp files, system files

**Respond in JSON:**
{"important": true/false, "reason": "brief explanation"}

**Example:**
{"important": true, "reason": "Homework assignment PDF"}""",
        "description": "Prompt für Einzeldatei-Analyse (Fallback wenn Batch fehlschlägt).",
        "category": "material",
        "temperature": Decimal("0.30"),
        "max_tokens": 50,
        "source": "material_processor.py:analyze_file_importance()"
    },
    {
        "prompt_key": "conversation_summary",
        "prompt_name": "Conversation Summarization",
        "prompt_content": """Fasse diese Konversation prägnant zusammen. Behalte wichtige technische Details, Konzepte und den Lernfortschritt des Studenten bei.

**Fokus:**
- Was hat der Student gelernt?
- Welche Konzepte wurden besprochen?
- Wo gab es Schwierigkeiten?
- Welche Lösungsansätze wurden entwickelt?

**Stil:**
- Kompakt und informativ
- Chronologisch wenn relevant
- Technische Begriffe beibehalten
- Keine wörtlichen Zitate nötig

Ziel: Die Zusammenfassung erlaubt dem Chatbot, den bisherigen Conversation-Flow zu verstehen ohne den kompletten Chat erneut laden zu müssen.""",
        "description": "Prompt für automatische Conversation-Summarization wenn Context-Window-Limit erreicht wird (80% bei 32k).",
        "category": "chat",
        "temperature": Decimal("0.30"),
        "max_tokens": 500,
        "source": "llm.py:summarize_conversation()"
    }
]


def load_prompt_from_file(filepath: str) -> str:
    """Load prompt content from file."""
    try:
        full_path = Path(__file__).parent / filepath
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        logger.error(f"Error loading prompt from {filepath}: {e}")
        return None


def migrate_prompts():
    """Migrate all prompts to database."""
    db = SessionLocal()

    try:
        logger.info("🚀 Starting prompt migration...")

        # Check if prompts already exist
        existing_count = db.query(SystemPrompt).count()
        if existing_count > 0:
            logger.warning(f"⚠️  Database already contains {existing_count} prompts")
            response = input("Do you want to overwrite them? (yes/no): ")
            if response.lower() != 'yes':
                logger.info("❌ Migration cancelled")
                return

            # Delete existing prompts
            db.query(SystemPrompt).delete()
            db.commit()
            logger.info("🗑️  Deleted existing prompts")

        # Migrate each prompt
        success_count = 0
        for prompt_def in PROMPTS_TO_MIGRATE:
            try:
                # Load content from file if needed
                if prompt_def["prompt_content"] is None:
                    if prompt_def["prompt_key"] == "chatbot_system":
                        # Load from file
                        prompt_def["prompt_content"] = load_prompt_from_file(prompt_def["source"])
                        if not prompt_def["prompt_content"]:
                            # Fallback to default
                            prompt_def["prompt_content"] = get_default_system_prompt()

                # Create prompt
                prompt = SystemPrompt(
                    prompt_key=prompt_def["prompt_key"],
                    prompt_name=prompt_def["prompt_name"],
                    prompt_content=prompt_def["prompt_content"],
                    description=prompt_def["description"],
                    category=prompt_def["category"],
                    temperature=prompt_def["temperature"],
                    max_tokens=prompt_def["max_tokens"],
                    updated_by="migration_script",
                    version=1
                )

                db.add(prompt)
                db.commit()

                logger.info(f"✓ Migrated: {prompt_def['prompt_key']} ({prompt_def['category']})")
                success_count += 1

            except Exception as e:
                logger.error(f"✗ Error migrating {prompt_def['prompt_key']}: {e}")
                db.rollback()

        logger.info(f"✅ Migration complete! {success_count}/{len(PROMPTS_TO_MIGRATE)} prompts migrated")

        # Show summary
        categories = db.query(SystemPrompt.category).distinct().all()
        logger.info(f"📊 Categories: {', '.join([c[0] for c in categories if c[0]])}")

    except Exception as e:
        logger.error(f"💥 Migration failed: {e}", exc_info=True)
        db.rollback()

    finally:
        db.close()


if __name__ == "__main__":
    migrate_prompts()
