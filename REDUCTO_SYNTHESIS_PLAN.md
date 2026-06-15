# Reducto + Kimi K2.5 Synthese - Implementierungsplan

**Stand:** 11. Juni 2026, 20:00 Uhr
**Status:** Reducto installiert, Synthesizer hat JSON-Parse-Problem

---

## Ziel

Vorlesungsfolien mit Reducto parsen und durch Kimi K2.5 in verständliche Erklärungen umwandeln, die dann editierbar im Dashboard sind und ins RAG gehen.

---

## Die komplette Pipeline

### 1. Reducto Response → Vereinfachte Struktur

**Input von Reducto:**
```json
{
  "result": {
    "chunks": [
      {
        "content": "Folie 1 Text...",
        "blocks": [
          {"type": "Title", "bbox": {"page": 1}, ...},
          {"type": "Text", "bbox": {"page": 2}, ...}
        ]
      }
    ]
  }
}
```

**Output (unsere Struktur):**
```json
[
  {
    "material": "Prog2 Vorlesung 1",
    "chunk_id": 0,
    "pages": [1, 2],
    "content": "Folie 1 Text..."
  }
]
```

**Was wegwerfen:**
- ❌ API-Meta: `response_type`, `job_id`, `duration`, `usage`
- ❌ Redundantes: `embed` field
- ❌ Block-Details: `blocks[].type`, `blocks[].content` (schon in chunk.content)
- ❌ Koordinaten: `bbox.left`, `bbox.top`, `bbox.width`, `bbox.height`
- ❌ Confidence scores

**Was behalten:**
- ✅ `chunk.content` (der komplette Text)
- ✅ `blocks[].bbox.page` → extrahieren in `pages` Array
- ✅ Material-Name (Kontext)
- ✅ Chunk-IDs (für Reihenfolge)

---

### 2. Ans LLM → Nur Content Array

**Input für Kimi K2.5:**
```json
[
  "Folie 1 Text...",
  "Folie 2 Text...",
  "Folie 3 Text..."
]
```

Nur purer Text, keine Metadaten!

---

### 3. Vom LLM → Erklärungen Array

**Erwarteter Output:**
```json
[
  "Erklärung von Folie 1 (neu formuliert)...",
  "Erklärung von Folie 2 (neu formuliert)...",
  "Erklärung von Folie 3 (neu formuliert)..."
]
```

**Kritisch:**
- Anzahl Output MUSS gleich Anzahl Input sein
- Reihenfolge MUSS erhalten bleiben
- Nur JSON Array, kein Text drumherum

---

### 4. Validierung & Zusammenführen

```python
if len(llm_output) == len(our_chunks):
    # ✅ Alles gut - zusammenbauen
    result = [
      {
        "material": "Prog2 Vorlesung 1",
        "chunk_id": 0,
        "pages": [1, 2],
        "content": "Erklärung von Folie 1..."  # <-- Neue Erklärung!
      }
    ]
else:
    # ❌ FEHLER - Anzahl stimmt nicht
    raise Exception(f"Expected {len(our_chunks)} outputs, got {len(llm_output)}")
```

---

### 5. Als editierbares Material speichern

```json
{
  "material_id": "uuid...",
  "material_name": "Prog2 Vorlesung 1",
  "chunks": [...],
  "metadata": {
    "total_chunks": 50,
    "pages_covered": [1, 2, 3, ..., 88],
    "synthesized_at": "2026-06-11T19:00:00Z",
    "source": "reducto+kimi"
  }
}
```

**Professor kann dann:**
- Einzelne Chunks im Dashboard bearbeiten
- Erklärungen anpassen
- Chunks neu generieren lassen

---

### 6. Ins RAG integrieren

```python
for chunk in material_chunks:
    embedding = await embedder.embed(chunk["content"])
    
    store_in_vector_db({
        "material_id": material_id,
        "chunk_id": chunk["chunk_id"],
        "content": chunk["content"],
        "pages": chunk["pages"],
        "embedding": embedding
    })
```

---

## Implementierungsaufgaben

### Task 1: Chunk-Extraktion verbessern
**File:** `lecture_synthesizer.py`, Zeile 27-57

**Aktuell:**
```python
chunk_data = {
    "chunk_id": idx,
    "content": chunk_content,
    "page": chunk.get("bbox", {}).get("page", 0)  # Nur eine Page!
}
```

**Neu:**
```python
chunk_data = {
    "chunk_id": idx,
    "content": chunk_content,
    "pages": self._extract_pages(chunk)  # Alle Pages aus blocks!
}

def _extract_pages(self, chunk):
    """Extract all unique page numbers from blocks."""
    pages = set()
    for block in chunk.get("blocks", []):
        bbox = block.get("bbox", {})
        if isinstance(bbox, dict) and "page" in bbox:
            pages.add(bbox["page"])
    return sorted(list(pages))
```

---

### Task 2: JSON-Parser robuster machen
**File:** `lecture_synthesizer.py`, Zeile 59-94

**Neue Strategien hinzufügen:**

```python
def _parse_json_response(self, response_text: str) -> Optional[List[Dict]]:
    """Parse JSON from LLM response with multiple strategies."""
    
    # Strategy 1: Direct parse
    try:
        data = json.loads(response_text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Extract from markdown code block
    try:
        match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response_text, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, AttributeError):
        pass
    
    # Strategy 3: Find JSON array with chunk_id
    try:
        match = re.search(r'\[[\s\S]*"chunk_id"[\s\S]*\]', response_text)
        if match:
            data = json.loads(match.group(0))
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, AttributeError):
        pass
    
    # Strategy 4: Cut everything outside [ and ]
    try:
        start = response_text.find('[')
        end = response_text.rfind(']')
        if start != -1 and end != -1 and end > start:
            json_str = response_text[start:end+1]
            data = json.loads(json_str)
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Strategy 5: Line-by-line extraction
    try:
        lines = response_text.split('\n')
        json_lines = []
        in_json = False
        
        for line in lines:
            if '[' in line:
                in_json = True
            if in_json:
                json_lines.append(line)
            if ']' in line and in_json:
                break
        
        if json_lines:
            json_str = '\n'.join(json_lines)
            data = json.loads(json_str)
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Log was nicht funktioniert hat
    logger.error(f"[SYNTHESIS] All 5 parsing strategies failed!")
    logger.error(f"[SYNTHESIS] Response preview: {response_text[:500]}")
    
    return None
```

---

### Task 3: Prompt anpassen
**Datenbank:** `system_prompts` Tabelle, Key: `lecture_synthesis_universal`

**Aktueller Prompt-Ausschnitt:**
```
**Ausgabeformat (JSON):**
Antworte NUR mit einem JSON-Array, kein zusätzlicher Text davor oder danach:
```

**Verstärkte Version:**
```
**Ausgabeformat (JSON) - SEHR WICHTIG:**

Du MUSST für JEDEN Input-Chunk GENAU EINE Erklärung zurückgeben!
Anzahl Input-Chunks = Anzahl Output-Chunks (sonst Fehler!)

Antworte NUR mit einem JSON-Array, KEIN Text davor oder danach:
- Kein "Hier ist die Antwort:"
- Keine Markdown-Code-Blöcke
- Kein Kommentar
- NUR das JSON-Array!

Format:
[
  {
    "chunk_id": "0",
    "erklaerung": "..."
  },
  {
    "chunk_id": "1",
    "erklaerung": "..."
  }
]

WICHTIG: 
- Behalte die chunk_ids EXAKT wie im Input bei
- Gleiche Reihenfolge wie Input
- Alle chunk_ids müssen vorhanden sein
```

---

### Task 4: Validierung einbauen
**File:** `lecture_synthesizer.py`, Zeile 143-149

**Nach dem Parsing hinzufügen:**

```python
parsed_result = self._parse_json_response(response)

if parsed_result is None:
    # Parsing fehlgeschlagen
    ...
else:
    # NEU: Validierung
    if len(parsed_result) != len(batch):
        logger.error(f"[SYNTHESIS] Count mismatch! Expected {len(batch)}, got {len(parsed_result)}")
        logger.error(f"[SYNTHESIS] Input chunk_ids: {[c['chunk_id'] for c in batch]}")
        logger.error(f"[SYNTHESIS] Output chunk_ids: {[r.get('chunk_id') for r in parsed_result]}")
        
        if attempt < 3:
            await asyncio.sleep(2)
            return await self.synthesize_batch(batch, historical_context, attempt + 1)
        else:
            raise Exception(f"Synthesis count mismatch after 3 attempts: expected {len(batch)}, got {len(parsed_result)}")
    
    # Prüfe ob alle chunk_ids vorhanden sind
    input_ids = {c["chunk_id"] for c in batch}
    output_ids = {r.get("chunk_id") for r in parsed_result}
    
    if input_ids != output_ids:
        logger.error(f"[SYNTHESIS] chunk_id mismatch!")
        logger.error(f"[SYNTHESIS] Missing: {input_ids - output_ids}")
        logger.error(f"[SYNTHESIS] Extra: {output_ids - input_ids}")
        
        if attempt < 3:
            await asyncio.sleep(2)
            return await self.synthesize_batch(batch, historical_context, attempt + 1)
        else:
            raise Exception(f"Synthesis chunk_id mismatch after 3 attempts")
```

---

### Task 5: Material-Name durchreichen
**File:** `material_processor.py`, Zeile 426+

**Aktuell:**
```python
synthesis_result = await synthesizer.process_lecture(reducto_chunks)
```

**Neu:**
```python
material_name = material.display_name  # z.B. "Vorlesung 5"
synthesis_result = await synthesizer.process_lecture(
    reducto_chunks, 
    material_name=material_name
)
```

**In `lecture_synthesizer.py`:**
```python
async def process_lecture(self, reducto_chunks: List[Dict], material_name: str = "Unknown"):
    ...
    # Bei der Chunk-Erstellung:
    chunk_data = {
        "material": material_name,  # <-- NEU!
        "chunk_id": idx,
        "pages": self._extract_pages(chunk),
        "content": chunk_content
    }
```

---

### Task 6: Synthesized Chunks speichern
**File:** `material_processor.py`, nach Zeile 461

**Aktuell:**
```python
all_synthesized_chunks.extend(synthesis_result['synthesized_chunks'])
```

**Neu - nach allen Files:**
```python
# Alle Chunks gesammelt, jetzt speichern
if all_synthesized_chunks:
    self.log_processing(db, str(material_id), 'storage', 'started',
                       f"Storing {len(all_synthesized_chunks)} synthesized chunks")
    
    # Als MaterialChunks in DB speichern
    for chunk in all_synthesized_chunks:
        db_chunk = MaterialChunk(
            material_id=material_id,
            chunk_index=chunk["chunk_id"],
            content=chunk.get("erklaerung", chunk.get("content")),  # Synthesized content!
            page_numbers=chunk.get("pages", [chunk.get("page", 0)]),
            chunk_metadata={
                "synthesized": True,
                "source": "reducto+kimi",
                "original_content": chunk.get("original_content", "")
            }
        )
        db.add(db_chunk)
    
    db.commit()
    
    self.log_processing(db, str(material_id), 'storage', 'completed',
                       f"Stored {len(all_synthesized_chunks)} chunks")
```

---

### Task 7: Embeddings generieren
**File:** `material_processor.py`, nach Task 6

```python
# Nach dem Speichern der Chunks: Embeddings generieren
embedder = await self._get_embedder()

self.log_processing(db, str(material_id), 'embedding', 'started',
                   f"Generating embeddings for {len(all_synthesized_chunks)} chunks")

for chunk in all_synthesized_chunks:
    content = chunk.get("erklaerung", chunk.get("content"))
    
    embedding = await embedder.embed_text(content)
    
    # ChunkEmbedding in DB speichern
    chunk_record = db.query(MaterialChunk).filter(
        MaterialChunk.material_id == material_id,
        MaterialChunk.chunk_index == chunk["chunk_id"]
    ).first()
    
    if chunk_record:
        db_embedding = ChunkEmbedding(
            chunk_id=chunk_record.chunk_id,
            embedding=embedding
        )
        db.add(db_embedding)

db.commit()

self.log_processing(db, str(material_id), 'embedding', 'completed',
                   f"Generated {len(all_synthesized_chunks)} embeddings")
```

---

## Test-Plan

### Test 1: Einzelner Chunk
```python
# Reducto Response mit 1 Chunk mocken
test_chunks = [{
    "content": "Test content",
    "blocks": [{"bbox": {"page": 1}}]
}]

result = await synthesizer.process_lecture(test_chunks, "Test Material")

assert len(result['synthesized_chunks']) == 1
assert result['synthesized_chunks'][0]['chunk_id'] == 0
assert result['synthesized_chunks'][0]['pages'] == [1]
```

### Test 2: Multiple Chunks
```python
# 3 Chunks, verschiedene Pages
test_chunks = [
    {"content": "Chunk 1", "blocks": [{"bbox": {"page": 1}}]},
    {"content": "Chunk 2", "blocks": [{"bbox": {"page": 2}}, {"bbox": {"page": 3}}]},
    {"content": "Chunk 3", "blocks": [{"bbox": {"page": 3}}]}
]

result = await synthesizer.process_lecture(test_chunks, "Test")

assert len(result['synthesized_chunks']) == 3
assert result['synthesized_chunks'][1]['pages'] == [2, 3]
```

### Test 3: JSON-Parsing mit Text drumherum
```python
llm_response = """
Hier ist die Synthese:

```json
[
  {"chunk_id": "0", "erklaerung": "Test 1"},
  {"chunk_id": "1", "erklaerung": "Test 2"}
]
```

Fertig!
"""

result = synthesizer._parse_json_response(llm_response)
assert len(result) == 2
assert result[0]["chunk_id"] == "0"
```

### Test 4: Echte PDF
```bash
# Die bereits hochgeladene Vorlesung neu verarbeiten
python3 << 'EOF'
import asyncio
from material_processor import MaterialProcessor
from database import SessionLocal
from prompt_manager import prompt_manager

async def test():
    db = SessionLocal()
    prompt_manager.initialize(db)
    
    processor = MaterialProcessor()
    await processor.process_material('0708e4e8-59d6-4842-89c0-85f49b912402', db)
    
    db.close()

asyncio.run(test())
EOF
```

---

## Erfolgskriterien

✅ **Reducto parst PDF** → Chunks mit Content + Pages
✅ **LLM erhält nur Content** → Einfaches String-Array
✅ **LLM gibt gleichviele zurück** → len(input) == len(output)
✅ **JSON-Parsing funktioniert** → Auch mit Text drumherum
✅ **Chunks werden gespeichert** → In material_chunks Tabelle
✅ **Embeddings werden erstellt** → In chunk_embeddings Tabelle
✅ **Im Dashboard editierbar** → Professor kann Chunks anpassen
✅ **Im Chat nutzbar** → RAG findet die Chunks

---

## Nächste Schritte morgen

1. **Task 1-2 implementieren** (Chunk-Extraktion + JSON-Parser)
2. **Testen mit kleiner PDF** (z.B. Tutorium 04)
3. **Prompt anpassen** wenn nötig (Task 3)
4. **Task 4-5 implementieren** (Validierung + Material-Name)
5. **Task 6-7 implementieren** (Speichern + Embeddings)
6. **Große PDF testen** (Prog2 Vorlesung 5 neu verarbeiten)
7. **Dashboard-Integration prüfen** (Können Chunks bearbeitet werden?)

---

## Offene Fragen

- [ ] Wie werden Chunks im Dashboard angezeigt/editiert?
- [ ] Gibt es eine API zum Re-Synthetisieren einzelner Chunks?
- [ ] Soll der Original-Content auch gespeichert werden? (für Vergleich)
- [ ] Was passiert bei Fehlern nach 3 Retries? Material komplett ablehnen oder teilweise speichern?

---

## Dateien die geändert werden

- `lecture_synthesizer.py` - Tasks 1, 2, 4
- `material_processor.py` - Tasks 5, 6, 7
- `system_prompts` (DB) - Task 3
- Evtl. `database.py` - Falls MaterialChunk Schema angepasst werden muss

---

**Status:** Bereit für Implementierung morgen! 🚀
