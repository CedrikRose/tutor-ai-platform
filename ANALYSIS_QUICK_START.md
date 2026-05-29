# Daily Chat Analysis - Quick Start

## Was macht das System?

Das System analysiert täglich um **4 Uhr morgens** alle Student-Chats:

1. **Snapshot-Erstellung**: Neue Nachrichten werden gespeichert
2. **Analyse**: Amazon Bedrock Minimax M2.5 analysiert den Lernfortschritt
3. **Strukturierung**: Ergebnisse werden in die Datenbank importiert

## Installation (einmalig)

```bash
./setup_analysis_system.sh
```

Das Script:
- Führt Datenbank-Migration durch
- Prüft AWS Credentials
- Richtet optional Cron Job ein
- Macht alle Scripts ausführbar

## Manuelle Ausführung (zum Testen)

```bash
# Komplette Analyse durchführen
python3 daily_chat_analysis.py

# Oder einzelne Schritte testen:
python3 test_daily_analysis.py stats       # Statistiken
python3 test_daily_analysis.py snapshots   # Snapshots erstellen
python3 test_daily_analysis.py analyze     # Analysieren
python3 test_daily_analysis.py import      # Importieren
python3 test_daily_analysis.py full        # Alles
```

## Voraussetzungen

### 1. AWS Credentials in .env

```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=XXXXX
AWS_SECRET_ACCESS_KEY=XXXXX
```

### 2. Chat-Sessions mit Kurs

Studenten müssen einen Kurs ausgewählt haben (`course_id` gesetzt).

### 3. Mindestens 2 Nachrichten

Jede Session muss mindestens eine User- und eine Assistant-Nachricht haben.

## Funktionsweise

### Snapshot-Logik

**Neuer Chat:**
```
Student schreibt -> um 4 Uhr -> ALLE Nachrichten als Snapshot
```

**Fortgeführter Chat:**
```
Vorher: MSG 1-5 (bereits analysiert)
Heute neu: MSG 6-10
um 4 Uhr -> Nur MSG 6-10 als neuer Snapshot
```

**Gelöschter Chat:**
```
Student löscht Chat -> letzter Snapshot bleibt erhalten
```

### Analyse-Prozess

1. **Primäres Modell** (Minimax M2.5):
   - Analysiert Wissensstand
   - Identifiziert Fehler und Lösungen
   - Sammelt Feedback

2. **Sekundäres Modell** (Kimi K2.5) - nur bei Bedarf:
   - Wird nur aufgerufen wenn Primär-Analyse unsicher ist
   - Markiert durch "[UNSICHER]" im Text
   - Kombiniert beide Ergebnisse

3. **Strukturierung**:
   - Extrahiert Daten via LLM
   - Speichert in `student_knowledge`
   - Speichert in `general_feedback`

## Datenbank-Tabellen

### `chat_snapshots`
Gespeicherte Chat-Inhalte zur Analyse

### `conversation_analyses`
Vollständige Analyse-Texte vom LLM

### `student_knowledge`
- Was Student verstand
- Was Student nicht verstand
- Fehler und Lösungen
- Referenzen auf Nachrichten

### `general_feedback`
- Professor-Erklärungen (gut/schlecht?)
- Tutor-Verhalten (zu nervig?)
- Material-Qualität

## Logs überwachen

```bash
# Live-Log
tail -f logs/daily_analysis.log

# Fehler suchen
grep ERROR logs/daily_analysis.log

# Erfolgreiche Analysen zählen
grep "Analysis completed" logs/daily_analysis.log | wc -l
```

## Troubleshooting

### Keine Snapshots erstellt

```bash
python3 test_daily_analysis.py stats
```

Prüfen:
- Gibt es Sessions mit `course_id != NULL`?
- Haben die Sessions >= 2 Nachrichten?
- Wurde heute schon ein Snapshot erstellt?

### AWS Fehler

```bash
# Credentials testen
aws bedrock list-foundation-models --region us-east-1

# Modell-Zugang prüfen
aws bedrock get-foundation-model \
  --model-identifier minimax.minimax-m2.5 \
  --region us-east-1
```

### Import schlägt fehl

Das ist nicht kritisch! Die Volltext-Analyse steht trotzdem in `conversation_analyses.analysis_text`.

## Kosten-Optimierung

✅ **Implementiert:**
- Nur neue Nachrichten werden analysiert (inkrementell)
- Primär nur 1 Modell, sekundär nur bei Unsicherheit
- Keine Vektor-DB (normale SQL-DB)

💰 **Geschätzte Kosten** (pro Tag bei 100 Chats):
- Minimax M2.5: ~100 * 1000 tokens = 100k tokens
- Kimi K2.5: ~10 * 1000 tokens = 10k tokens (nur bei Unsicherheit)
- Import LLM: ~100 * 500 tokens = 50k tokens

Total: ~160k tokens/Tag

## Nächste Schritte

Nach der Installation:

1. **Teste mit Beispieldaten:**
   ```bash
   python3 test_daily_analysis.py full
   ```

2. **Richte Cron ein** (automatisch um 4 Uhr):
   ```bash
   ./setup_analysis_system.sh
   ```

3. **Implementiere Professor Dashboard Endpoints:**
   - GET /api/professor/analyses
   - GET /api/professor/student-knowledge
   - GET /api/professor/feedback
   - GET /api/professor/chat/{session_id}

4. **Teste Produktiv:**
   - Warte auf echte Student-Chats
   - Check Logs am nächsten Tag
   - Validiere Ergebnisse

## Vollständige Dokumentation

Siehe: **DAILY_ANALYSIS_SYSTEM.md**
