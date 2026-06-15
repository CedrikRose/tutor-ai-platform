# Batching & Context Update - Zusammenfassung

**Datum:** 11. Juni 2026, 21:30 Uhr  
**Status:** Implementiert und getestet ✅

---

## Was wurde geändert

### 1. ✅ Input-Format zum LLM: String-Array statt JSON

**Vorher:**
```json
[
  {
    "chunk_id": 0,
    "content": "Folie 1 Text...",
    "pages": [1, 2]
  },
  ...
]
```

**Jetzt:**
```json
[
  "Folie 1 Text...",
  "Folie 2 Text...",
  "Folie 3 Text..."
]
```

**Datei:** `lecture_synthesizer.py`, Zeile 178-180

Das LLM erhält nur die reinen Texte, keine Metadaten. Die chunk_id entspricht dem Array-Index (0, 1, 2, ...).

---

### 2. ✅ Kontext: Letzte 3 Chunks statt 1500 Zeichen

**Vorher:**
```python
combined = "\n\n".join([c.get("erklaerung", "") for c in synthesized_chunks])
historical_context = combined[-1500:] if len(combined) > 1500 else combined
```
❌ Problem: Nimmt die letzten 1500 Zeichen aller Erklärungen (kann Chunks abschneiden!)

**Jetzt:**
```python
last_chunks = synthesized_chunks[-3:] if len(synthesized_chunks) > 3 else synthesized_chunks
context_texts = [c.get("erklaerung", "") for c in last_chunks]
historical_context = "\n\n".join(context_texts)
```
✅ Nimmt die letzten 3 kompletten Chunks

**Datei:** `lecture_synthesizer.py`, Zeile 302-307

---

### 3. ✅ Batching bleibt bei 15.000 Zeichen

**Keine Änderung nötig** - das war schon korrekt implementiert:

```python
def batch_chunks(self, reducto_chunks: List[Dict], max_chars: int = 15000)
```

- Chunks werden **NICHT** halbiert
- Wenn ein Chunk die Grenze überschreitet → kommt in nächsten Batch
- Test mit 88-Seiten-PDF: 50 Chunks → 3 Batches (17, 17, 16 Chunks)

**Datei:** `lecture_synthesizer.py`, Zeile 44-74

---

## Wie es jetzt funktioniert

### Beispiel: 88-Seiten-Vorlesung

1. **Reducto parst PDF:**
   - 88 Seiten → ~50 Chunks (ca. 800 Zeichen pro Chunk)
   - Total: ~40.000 Zeichen

2. **Batching (15k Limit):**
   - Batch 1: 17 Chunks (~14.577 Zeichen)
   - Batch 2: 17 Chunks (~14.586 Zeichen)
   - Batch 3: 16 Chunks (~13.728 Zeichen)

3. **Synthesis:**

   **Batch 1 (erste Runde):**
   ```
   Kontext: (Beginn der Vorlesung)
   Input: ["Text 1", "Text 2", ..., "Text 17"]
   Output: 17 Erklärungen
   ```

   **Batch 2 (mit Kontext):**
   ```
   Kontext: Erklärung 15 + Erklärung 16 + Erklärung 17
   Input: ["Text 18", "Text 19", ..., "Text 34"]
   Output: 17 Erklärungen
   ```

   **Batch 3 (mit Kontext):**
   ```
   Kontext: Erklärung 32 + Erklärung 33 + Erklärung 34
   Input: ["Text 35", "Text 36", ..., "Text 50"]
   Output: 16 Erklärungen
   ```

4. **Speichern:**
   - 50 MaterialChunk Records (1:1 mit Reducto Chunks!)
   - Jeder Chunk hat Metadata mit Pages, Source, Timestamps

---

## Was das LLM jetzt sieht

### User Prompt Format:
```
**Historischer Kontext (letzte verarbeitete Folien):**
[Erklärung von Folie 15]

[Erklärung von Folie 16]

[Erklärung von Folie 17]

**Zu analysierende Abschnitte (Array von 17 Folien-Texten):**
[
  "Text von Folie 18...",
  "Text von Folie 19...",
  ...
  "Text von Folie 34..."
]

**WICHTIG:** Du erhältst ein Array mit 17 Folien-Texten. Gib für JEDEN Text (Index 0 bis 16) GENAU EINE Erklärung zurück mit entsprechender chunk_id!
```

### System Prompt Update:
```
**Eingabeformat:**
Du erhältst ein einfaches String-Array mit den Texten der Folien:
```json
["Text von Folie 1...", "Text von Folie 2...", "Text von Folie 3..."]
```

Der Index im Array entspricht der chunk_id (0, 1, 2, ...).
Falls historischer Kontext vorhanden ist, siehst du die Erklärungen der letzten 3 verarbeiteten Folien als normalen Text (NICHT im JSON-Format).
```

---

## Test-Ergebnisse

### ✅ Test 1: Batching bei 15k Zeichen
- 4 Chunks (5k, 6k, 5k, 3k) → 2 Batches
- Batch 1: 11k (Chunks 0+1)
- Batch 2: 8k (Chunks 2+3)
- **Keine Chunks halbiert!**

### ✅ Test 2: Kontext nutzt letzte 3 Chunks
- 5 Chunks verarbeitet
- Kontext: Erklärungen 3, 4, 5
- Alte Chunks (1, 2) **nicht** im Kontext

### ✅ Test 3: LLM Input = String Array
- Input: `["Folie 1 Text", "Folie 2 Text", "Folie 3 Text"]`
- Keine Metadaten (chunk_id, pages) im Input
- Pure Strings

### ✅ Test 4: 88-Seiten-PDF Simulation
- 50 Chunks → 3 Batches (17, 17, 16)
- Kein Batch > 15k Zeichen
- Total: 42.891 Zeichen

---

## Geänderte Dateien

1. **lecture_synthesizer.py**
   - Zeile 178-191: Input als String-Array
   - Zeile 302-307: Kontext von letzten 3 Chunks

2. **system_prompts** (Datenbank)
   - Neue Erklärung des Input-Formats
   - Länge: 1905 → 2278 Zeichen (+373)

---

## Nachvollziehbarkeit

### Kontext-Tracking im Log:
```
INFO: [SYNTHESIS] Processing batch 1/3...
INFO: [SYNTHESIS] Batch attempt 1: 17 chunks
INFO: [SYNTHESIS] Strategy 1 (direct) succeeded
INFO: [SYNTHESIS] Batch successful: 17 chunks
INFO: [SYNTHESIS] Context updated with last 3 chunks (1234 chars)

INFO: [SYNTHESIS] Processing batch 2/3...
INFO: [SYNTHESIS] Batch attempt 1: 17 chunks
INFO: [SYNTHESIS] Context updated with last 3 chunks (1456 chars)
...
```

### Datenbank-Abfrage:
```sql
-- Prüfe die ersten 5 Chunks einer Vorlesung
SELECT 
  chunk_index,
  LEFT(content, 100) as preview,
  chunk_metadata->>'pages' as pages,
  chunk_metadata->>'batch_index' as batch
FROM material_chunks
WHERE material_id = '<uuid>'
  AND source_type = 'reducto_synthesis'
ORDER BY chunk_index
LIMIT 5;
```

---

## Vorteile der neuen Implementierung

### 1. Saubereres Input-Format
- ✅ LLM sieht nur relevante Daten (Text)
- ✅ Weniger Token verschwendet für Metadaten
- ✅ Klarer: Index = chunk_id

### 2. Besserer Kontext
- ✅ Immer die letzten **3 kompletten Chunks**
- ✅ Keine abgeschnittenen Sätze
- ✅ Konsistente Kontext-Größe

### 3. Nachvollziehbar
- ✅ Logs zeigen Kontext-Updates
- ✅ Batch-Größen transparent
- ✅ Metadata in DB gespeichert

### 4. Skalierbar
- ✅ Funktioniert für 5-Seiten-PDFs
- ✅ Funktioniert für 88-Seiten-PDFs
- ✅ Automatisches Batching

---

## Nächste Schritte zum Testen

1. **Backend neu starten** (lädt neue Prompt-Version):
   ```bash
   # Stoppe aktuelles Backend
   # Starte neu mit: python3 -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Kleine PDF hochladen** (5-10 Seiten):
   - Professor Dashboard → Materials → Upload
   - Prüfe Logs: Kontext sollte bei Batch 2 erscheinen
   - Prüfe DB: `chunk_metadata` enthält Pages

3. **Große PDF hochladen** (88 Seiten):
   - Erwarte 3-4 Batches
   - Jeder Batch hat Kontext (außer der erste)
   - Chunks = Reducto Chunks (1:1)

4. **RAG-Test**:
   - "Was haben wir auf Seite 5 gelernt?"
   - Sollte Chunks mit `pages @> '[5]'` finden

---

## Rollback

Falls Probleme auftreten:

```bash
git diff lecture_synthesizer.py
# Zeigt Änderungen
git checkout lecture_synthesizer.py
# Stellt alte Version wieder her
```

Prompt-Update rückgängig:
```sql
UPDATE system_prompts 
SET version = version - 1
WHERE prompt_key = 'lecture_synthesis_universal';
```

---

**Alles bereit zum Testen! 🚀**

Die neuen Änderungen sind:
1. ✅ Implementiert
2. ✅ Getestet
3. ✅ Dokumentiert
4. ✅ Im laufenden Server aktiv (nach Backend-Reload)
