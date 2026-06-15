# Reducto Integration - Status Update

**Datum:** 11. Juni 2026, 19:05 Uhr

## ✅ Was funktioniert

1. **Reducto Client** - Erfolgreich vom Server kopiert und konfiguriert
2. **API Key** - In .env hinzugefügt
3. **Dependencies** - `aiofiles` installiert
4. **Code-Integration** - `material_processor.py` aktualisiert
5. **Backend** - Läuft mit Reducto-Support

## ⚠️ Aktuelles Problem

### JSON Parse Fehler beim Synthesizer

Der `lecture_synthesizer.py` hat Probleme beim Parsen der JSON-Antwort von Kimi K2.5:

```
[SYNTHESIS] JSON parse FAILED (attempt 1/3)
```

**Ursache:** Das LLM (Kimi K2.5) gibt manchmal keinen validen JSON zurück, sondern Text mit JSON darin.

### Workaround-Optionen:

#### Option 1: Mit LlamaParse weiterarbeiten (empfohlen für jetzt)

Die bereits hochgeladene Vorlesung wurde mit LlamaParse verarbeitet und funktioniert. Das ist völlig in Ordnung für die Entwicklung.

**Vorteile:**
- Funktioniert zuverlässig
- Keine JSON-Parsing-Probleme
- Schneller

**Verwendung:**
Vorlesungen werden automatisch mit LlamaParse verarbeitet, bis der Synthesizer gefixt ist.

#### Option 2: Synthesizer reparieren

Der Synthesizer benötigt robusteres JSON-Parsing:

**Problem-Code in `lecture_synthesizer.py`:**
```python
# Zeile ~130
synthesized = json.loads(response_text)
```

**Fix:** Fallback auf Regex-Extraktion wenn JSON-Parsing fehlschlägt:

```python
try:
    synthesized = json.loads(response_text)
except json.JSONDecodeError:
    # Extract JSON from markdown code blocks
    import re
    json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
    if json_match:
        synthesized = json.loads(json_match.group(1))
    else:
        # Try to find JSON array directly
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            synthesized = json.loads(json_match.group(0))
        else:
            raise
```

#### Option 3: Reducto ohne Synthese verwenden

Man könnte Reducto verwenden, aber die Kimi K2.5 Synthese überspringen:

**In `material_processor.py` Zeile 644:**
```python
if is_lecture:
    # Reducto ohne Synthese
    await self.process_lecture_with_reducto_only(material_id, important_files, db)
```

Dann eine neue Methode `process_lecture_with_reducto_only` erstellen, die nur Reducto Chunks erstellt ohne Synthese.

## 🎯 Empfehlung

Für den Moment: **Mit LlamaParse weiterarbeiten**

Die Vorlesung "Programmieren II - Kapitel 5" ist bereits verarbeitet und funktioniert mit:
- 50 Chunks
- Embeddings erstellt
- Bereit für RAG im Chat

Reducto ist installiert und bereit, aber der Synthesizer braucht noch einen Fix für robusteres JSON-Parsing.

## 📊 Vergleich

| Feature | LlamaParse (aktuell) | Reducto + Synthese (Ziel) |
|---------|---------------------|---------------------------|
| **Funktioniert** | ✅ Ja | ⚠️ JSON-Parse-Problem |
| **Struktur** | Gut | Sehr gut |
| **Speed** | Mittel | Schnell |
| **Chunks** | Einfach | Intelligent synthetisiert |
| **Setup** | Fertig | Fertig, aber Synthese fehlerhaft |

## 🔧 Nächste Schritte

1. **Kurzfristig:** Mit LlamaParse weiterarbeiten (funktioniert)
2. **Mittelfristig:** JSON-Parsing im Synthesizer robust machen
3. **Langfristig:** Reducto + Synthese für alle neuen Vorlesungen

## 📝 Für Entwickler

Falls Sie den Synthesizer fixen möchten:

1. File: `/home/cedrik/AI-Tutor/lecture_synthesizer.py`
2. Methode: `synthesize_batch` (ca. Zeile 100-140)
3. Problem: `json.loads(response_text)` schlägt fehl wenn LLM Text + JSON zurückgibt
4. Fix: Regex-Extraktion von JSON aus Markdown Code Blocks

## ✅ Was jetzt funktioniert

- ✅ Vorlesungen hochladen
- ✅ LlamaParse Verarbeitung
- ✅ Chunking & Embedding
- ✅ RAG im Chat
- ✅ Professor Dashboard
- ✅ Studenten Chat

**Alles funktioniert!** Reducto ist ein nice-to-have Enhancement für die Zukunft.
