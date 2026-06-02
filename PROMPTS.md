# System Prompts Dokumentation

Alle System-Prompts werden zentral in der PostgreSQL-Datenbank verwaltet und können über die Admin-Seite unter `/prompts` bearbeitet werden.

## Admin-Zugang

**URL:** https://tutor-ai.me/prompts  
**Passwort:** `zp63hC!dmov*XyYgt%%j`

Änderungen an Prompts werden **sofort wirksam** ohne Server-Neustart.

---

## Verfügbare Prompts

### 1. **Chatbot System Prompt** (`chatbot_system`)

**Kategorie:** Chat  
**Verwendet für:** Alle Student-Chat-Interaktionen  
**Verwendet in:** `llm.py` → `get_chatbot_system_prompt()`  
**Temperature:** 0.7  
**Max Tokens:** 2048

**Beschreibung:**  
Hauptprompt für den pädagogischen KI-Tutor. Definiert das Scaffolding-Verhalten:
- Keine direkten Lösungen zu Hausaufgaben
- Gegenfragen und Hints geben
- Ermutigend und geduldig
- Hilfe zur Selbsthilfe

**Test:**  
Stelle eine Frage im Chatbot und prüfe ob die Antwort das Scaffolding-Verhalten zeigt.

---

### 2. **Report Generation** (`report_generation`)

**Kategorie:** Report  
**Verwendet für:** Professor Reports (Aggregation von Conversation Findings)  
**Verwendet in:** `report_generator.py` → `_get_report_prompt()`  
**Temperature:** 0.3  
**Max Tokens:** 2000

**Beschreibung:**  
Erstellt objektive Berichte für Professoren aus studentischen Chat-Findings:
- KEINE Empfehlungen/Verbesserungsvorschläge (nur deskriptiv)
- Strukturiert nach: Schwierigkeiten, Feedback, Nutzungsmuster
- Professioneller, akademischer Stil
- Konkrete Themen und Häufigkeiten nennen

**Test:**  
Generiere einen Report im Professor Dashboard und prüfe ob der Stil objektiv/deskriptiv ist.

---

### 3. **Chat Analysis** (`chat_analysis`)

**Kategorie:** Analysis  
**Verwendet für:** Daily 3 AM Analyse (extrahiert Findings aus Chats)  
**Verwendet in:** `daily_chat_analysis_v2.py` → `_build_analysis_prompt()`  
**Temperature:** 0.3  
**Max Tokens:** 4000

**Beschreibung:**  
Analysiert studentische Chats und extrahiert strukturierte Findings in 4 Kategorien:
1. **difficulty** - Verständnisprobleme, Konzept-Lücken
2. **feedback_professor** - Kommentare über Vorlesungsinhalte
3. **feedback_chatbot** - Qualität der KI-Antworten
4. **question_pattern** - Wiederkehrende Fragenmuster

**Output:** JSON mit findings-Array

**Test:**  
Warte auf 3 AM Analyse oder triggere manuell, prüfe ob Findings extrahiert werden.

---

### 4. **Course Summary Generation** (`course_summary`)

**Kategorie:** Report  
**Verwendet für:** Kurs-Übersichten für Professoren  
**Verwendet in:** `course_summary_generator.py` → `_generate_summary_with_llm()`  
**Temperature:** 0.3  
**Max Tokens:** 2000

**Beschreibung:**  
Erstellt faktenbasierte Übersichten über einen Zeitraum:
- Überblick (Anzahl Interaktionen, Trends)
- Hauptthemen (Top 3-5)
- Verständnisprobleme
- Feedback-Highlights

**Test:**  
Generiere Course Summary im Professor Dashboard.

---

### 5. **Material File Analysis (Batch)** (`material_file_analysis_batch`)

**Kategorie:** Material  
**Verwendet für:** Batch-Analyse welche Dateien wichtig sind (beim Upload)  
**Verwendet in:** `material_processor.py` → `analyze_files_batch()`  
**Temperature:** 0.3  
**Max Tokens:** 2000

**Beschreibung:**  
Analysiert mehrere Dateien gleichzeitig und entscheidet welche wichtig sind:
- ✅ Include: Lecture slides, homework, exercises, solutions
- ❌ Exclude: Build artifacts, dependencies, temp files

**Output:** JSON mit decisions-Array

**Test:**  
Lade Material hoch und prüfe welche Dateien als wichtig markiert werden.

---

### 6. **Material File Analysis (Single)** (`material_file_analysis_single`)

**Kategorie:** Material  
**Verwendet für:** Einzeldatei-Analyse (Fallback wenn Batch fehlschlägt)  
**Verwendet in:** `material_processor.py` → `analyze_file_importance()`  
**Temperature:** 0.3  
**Max Tokens:** 500

**Beschreibung:**  
Analysiert eine einzelne Datei:
- Gleiche Kriterien wie Batch
- Kleinerer Output (nur true/false + reason)

**Output:** JSON `{"important": true/false, "reason": "..."}`

**Test:**  
Lade einzelne Datei hoch und prüfe Importance-Bewertung.

---

## Technische Details

### Architektur

1. **Datenbank:** `system_prompts` Tabelle in PostgreSQL
2. **Caching:** In-Memory Cache im `prompt_manager` (lädt bei Server-Start)
3. **Fallback:** Hardcoded Prompts in den Files falls DB nicht verfügbar

### Prompt Manager

**Datei:** `prompt_manager.py`

**Funktionen:**
- `get_prompt(prompt_key)` - Prompt aus Cache holen
- `update_prompt(prompt_key, content, updated_by)` - Prompt updaten (DB + Cache)
- `reload_all()` - Alle Prompts neu laden
- `list_all()` - Alle Prompts mit Metadata

**Initialisierung:** In `api/main.py` beim Server-Start

### Admin API Endpoints

**Base URL:** `/api/prompts`

- `POST /authenticate` - Login mit Passwort → Token
- `GET /list` - Alle Prompts (requires token)
- `POST /update` - Prompt updaten (requires token)
- `POST /reload` - Force reload aus DB (requires token)
- `GET /health` - Cache Status (no auth)

### Versionierung

Jeder Prompt hat:
- `version` - Inkrementiert bei jedem Update
- `updated_at` - Timestamp der letzten Änderung
- `updated_by` - Wer hat geändert (z.B. "admin")

### Fallback-Kette

Für jeden Prompt:
1. **Cache** (prompt_manager) → schnellster Zugriff
2. **Datenbank** (falls Cache leer) → lädt und cached
3. **Hardcoded** (falls DB nicht verfügbar) → Sicherheits-Fallback

Die Datei `config/system_prompt.txt` wird als **letzter Fallback** für den Chatbot-Prompt behalten.

---

## Wartung

### Prompt ändern

1. Gehe zu https://tutor-ai.me/prompts
2. Login mit Passwort
3. Klicke "Bearbeiten" bei gewünschtem Prompt
4. Ändere Inhalt
5. Klicke "Speichern"
6. **Fertig!** Änderung sofort aktiv (kein Neustart nötig)

### Prompt neu laden

Falls ein Prompt direkt in der DB geändert wurde (z.B. via psql):
- Klicke "Neu laden" Button in der Admin-Seite
- Oder: API-Call zu `/api/prompts/reload`

### Neuen Prompt hinzufügen

1. Füge Eintrag in `system_prompts` Tabelle hinzu (via psql oder Migration)
2. Lade Prompts neu (`/api/prompts/reload`)
3. Verwende im Code: `prompt_manager.get_prompt("new_key")`

---

## Sicherheit

- Passwort-Schutz für Admin-Seite
- Token-basierte Session (1 Stunde gültig)
- Token in localStorage gespeichert
- API-Endpoints prüfen Token bei jeder Anfrage

---

## Monitoring

**Cache Status prüfen:**
```bash
curl http://localhost:8000/api/prompts/health
```

**Output:**
```json
{
  "status": "ok",
  "cache_size": 6,
  "last_reload": "2026-06-02T12:48:54.325163",
  "active_sessions": 1
}
```

**Logs prüfen:**
```bash
grep -i "prompt" logs/api.log
```

Sollte zeigen:
- "✓ Loaded 6 prompts into cache" beim Start
- "✓ Using chatbot prompt from cache" bei Chatbot-Nutzung
- "✓ Updated prompt: chatbot_system (v2) by admin" bei Änderungen
