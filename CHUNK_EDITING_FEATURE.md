# Chunk-basiertes Editing Feature ✅

**Datum:** 11. Juni 2026, 22:15 Uhr  
**Status:** Implementiert und bereit zum Testen

---

## Was wurde hinzugefügt

### ✅ Neue UI-Component: EditChunksModal

**Datei:** `professor-dashboard/src/components/EditChunksModal.tsx`

**Features:**
- ✅ Zeigt alle Chunks einer Vorlesung an
- ✅ Chunk-Grenzen sichtbar mit farbigen Boxen
- ✅ Jeder Chunk einzeln bearbeitbar
- ✅ Zeigt Metadaten: Pages, Source, Timestamp
- ✅ Suche durch Chunks
- ✅ Ungespeicherte Änderungen werden markiert
- ✅ Speichern einzelner Chunks (nicht alle auf einmal!)

**UI-Struktur pro Chunk:**
```
┌─────────────────────────────────────────────┐
│ #42 📄 Seiten 15-17 🔄 reducto+kimi ● Geändert │
│ ✏️ Bearbeiten | Abbrechen | Speichern      │
├─────────────────────────────────────────────┤
│                                             │
│  [Chunk Content - Textarea oder Read-only] │
│                                             │
├─────────────────────────────────────────────┤
│ 1,234 Zeichen | Erstellt: 11.06.2026 21:30 │
└─────────────────────────────────────────────┘
```

**Visuelle Unterscheidung:**
- **Grün-Rahmen:** Unveränderte Chunks
- **Gelb-Rahmen:** Chunks mit ungespeicherten Änderungen
- **Edit-Modus:** Größeres Textarea mit Resize-Option

---

### ✅ Neue Backend-Endpoints

**Datei:** `api/professor_material_api.py`

#### 1. GET `/api/professor/materials/{material_id}/chunks`

**Response:**
```json
{
  "material_id": "uuid...",
  "material_type": "lecture_slide",
  "display_name": "Vorlesung 4",
  "chunks": [
    {
      "chunk_id": "uuid...",
      "chunk_index": 0,
      "content": "Erklärung von Folie 1...",
      "source_type": "reducto_synthesis",
      "pages": [1, 2],
      "metadata": {
        "pages": [1, 2],
        "source": "reducto+kimi",
        "synthesized_at": "2026-06-11T19:00:00Z",
        "batch_index": 0,
        "original_chunk_id": 0
      }
    }
  ]
}
```

**Funktionen:**
- Lädt alle Chunks einer Vorlesung
- Sortiert nach chunk_index
- Extrahiert Pages aus chunk_metadata
- Überprüft Permissions (nur Owner)

#### 2. PUT `/api/professor/materials/{material_id}/chunks/{chunk_id}`

**Request:**
```json
{
  "content": "Neue Erklärung..."
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Chunk updated successfully",
  "chunk_id": "uuid..."
}
```

**Funktionen:**
- Updated einzelnen Chunk
- Sanitized Content (NULL-Bytes entfernen)
- Regeneriert Embedding im Background
- Überprüft Permissions

---

### ✅ Frontend-Änderungen

**Datei:** `professor-dashboard/src/components/MaterialCard.tsx`

**Änderung:**
```tsx
// Unterscheidet jetzt zwischen lecture_slide und anderen Typen
{isProcessed && material.material_type === 'lecture_slide' && (
  <button onClick={() => setShowEditModal(true)}>
    📝 Chunks bearbeiten
  </button>
)}

{isProcessed && material.material_type !== 'lecture_slide' && (
  <button onClick={() => setShowEditModal(true)}>
    Bearbeiten
  </button>
)}
```

**Modal-Rendering:**
```tsx
// Lecture Slides → EditChunksModal
{showEditModal && material.material_type === 'lecture_slide' && (
  <EditChunksModal ... />
)}

// Andere Typen → EditMaterialModal (altes Behavior)
{showEditModal && material.material_type !== 'lecture_slide' && (
  <EditMaterialModal ... />
)}
```

---

### ✅ API-Services

**Datei:** `professor-dashboard/src/services/api.ts`

**Neue Funktionen:**
```typescript
getMaterialChunks: async (materialId: string): Promise<{ chunks: any[] }> => {
  const response = await api.get(`/professor/materials/${materialId}/chunks`);
  return response.data;
},

updateChunk: async (materialId: string, chunkId: string, content: string): Promise<void> => {
  await api.put(`/professor/materials/${materialId}/chunks/${chunkId}`, { content });
},
```

---

## Wie es funktioniert

### Workflow: Professor bearbeitet Chunk

1. **Professor öffnet Vorlesung 4 im Dashboard**
   - Klick auf "📝 Chunks bearbeiten"

2. **EditChunksModal lädt Chunks**
   - GET `/api/professor/materials/{id}/chunks`
   - 110 Chunks werden angezeigt

3. **Professor sucht nach "Stream API"**
   - Client-seitige Filterung
   - Zeigt nur relevante Chunks

4. **Professor klickt "Bearbeiten" bei Chunk #42**
   - Textarea erscheint
   - Content ist editierbar

5. **Professor ändert Text und klickt "Speichern"**
   - PUT `/api/professor/materials/{id}/chunks/{chunk_id}`
   - Backend sanitized Content
   - Backend updated Chunk in DB
   - Backend regeneriert Embedding (Background)

6. **UI zeigt Erfolg**
   - Chunk-Rahmen wird wieder grün
   - "Geändert" Badge verschwindet
   - Embedding wird im Background erneuert

---

## Vorteile des Chunk-basierten Editings

### 1. **Sichtbare Grenzen**
- ✅ Professor sieht genau wo ein Chunk aufhört
- ✅ Keine Verwirrung über Chunk-Struktur
- ✅ Kann gezielt einzelne Folien korrigieren

### 2. **Granulares Editing**
- ✅ Nur betroffener Chunk wird neu ge-embedded
- ✅ Andere Chunks bleiben unverändert
- ✅ Schneller als komplettes Re-Processing

### 3. **Kontextinformationen**
- ✅ Pages: "Dieser Chunk erklärt Seiten 15-17"
- ✅ Source: "Erstellt mit reducto+kimi"
- ✅ Timestamp: "Synthesized am 11.06.2026 19:30"

### 4. **Suchfunktion**
- ✅ Findet Chunks nach Inhalt
- ✅ Findet Chunks nach Nummer
- ✅ Schneller als manuelles Scrollen

### 5. **Änderungsverfolgung**
- ✅ Gelbe Rahmen zeigen ungespeicherte Änderungen
- ✅ Footer zeigt Anzahl geänderter Chunks
- ✅ Kann einzeln speichern oder verwerfen

---

## Was passiert beim Speichern

### Backend-Ablauf:

```
1. Chunk in DB updaten
   ├─ content = sanitized_content
   └─ commit()

2. Background Task starten
   └─ Regenerate Embedding:
      ├─ BedrockEmbedder laden
      ├─ embed_text(new_content)
      └─ chunk.embedding = new_vector
```

**Zeit:** ~1-2 Sekunden pro Chunk  
**User-Erfahrung:** Sofortiges Feedback, Embedding läuft im Hintergrund

---

## Test-Anleitung

### 1. Vorlesung 4 im Dashboard öffnen

```
http://localhost:5174/dashboard
→ Prog2 Kurs
→ Vorlesung 4
→ "📝 Chunks bearbeiten"
```

### 2. Chunks durchsuchen

```
Suchleiste: "Stream"
→ Zeigt alle Chunks mit "Stream" im Content
```

### 3. Chunk bearbeiten

```
Chunk #42 → "✏️ Bearbeiten"
→ Text ändern
→ "Speichern"
→ Chunk wird grün (gespeichert)
```

### 4. Mehrere Chunks ändern

```
Chunk #10 bearbeiten → NICHT speichern
Chunk #20 bearbeiten → NICHT speichern
→ Footer zeigt: "● 2 ungespeicherte Änderungen"
→ Beide Chunks haben gelben Rahmen
```

### 5. Änderungen verwerfen

```
Chunk #10 → "Abbrechen"
→ Original-Content wird wiederhergestellt
→ Gelber Rahmen verschwindet
```

---

## Datenbank-Schema

### MaterialChunk (bereits vorhanden)

```sql
CREATE TABLE material_chunks (
  chunk_id UUID PRIMARY KEY,
  material_id UUID REFERENCES course_materials,
  content TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  source_type VARCHAR(50),
  file_name TEXT,
  embedding VECTOR(1024),
  chunk_metadata JSONB,  -- NEU: Pages, Source, etc.
  created_at TIMESTAMP
);
```

**chunk_metadata Beispiel:**
```json
{
  "pages": [15, 16, 17],
  "source": "reducto+kimi",
  "synthesized_at": "2026-06-11T19:30:00Z",
  "batch_index": 2,
  "original_chunk_id": 42,
  "original_content_preview": "Original text..."
}
```

---

## Debugging

### Backend-Logs überprüfen:

```bash
tail -f /tmp/claude-1000/.../tasks/bs6hsaw3r.output | grep "chunk\|UPDATE"
```

### Datenbank-Abfrage:

```sql
-- Prüfe ob Chunk updated wurde
SELECT 
  chunk_index,
  LEFT(content, 100) as preview,
  chunk_metadata->>'pages' as pages,
  created_at
FROM material_chunks
WHERE material_id = '<vorlesung-4-uuid>'
  AND chunk_index = 42;
```

### Network-Tab im Browser:

```
PUT /api/professor/materials/{id}/chunks/{chunk_id}
Request: {"content": "..."}
Response: {"status": "success", ...}
```

---

## Offene Punkte / Future Improvements

### 1. Batch-Speichern
**Aktuell:** Ein Chunk zur Zeit  
**Verbesserung:** "Alle Speichern" Button für mehrere Chunks

### 2. Undo/Redo
**Aktuell:** Abbrechen = Original wiederherstellen  
**Verbesserung:** History mit mehreren Undo-Steps

### 3. Diff-Ansicht
**Aktuell:** Nur neuer Content sichtbar  
**Verbesserung:** Side-by-Side Vergleich mit Original

### 4. Chunk-Statistiken
**Aktuell:** Nur Zeichenanzahl  
**Verbesserung:** Token-Count, Lesbarkeits-Score

### 5. Chunk neu synthetisieren
**Aktuell:** Manuelles Editing  
**Verbesserung:** "Re-Synthesize mit Kimi K2.5" Button

---

## Rollback

Falls Probleme auftreten:

### Frontend:
```bash
git checkout professor-dashboard/src/components/EditChunksModal.tsx
git checkout professor-dashboard/src/components/MaterialCard.tsx
git checkout professor-dashboard/src/services/api.ts
```

### Backend:
```bash
git diff api/professor_material_api.py
# Check die letzten ~200 Zeilen
git checkout api/professor_material_api.py  # Falls nötig
```

---

**Feature bereit zum Testen! 🚀**

Alle Dateien sind:
1. ✅ Implementiert
2. ✅ TypeScript kompiliert
3. ✅ Backend-Endpoints aktiv
4. ✅ Frontend läuft im Dev-Mode
5. ✅ Vorlesung 4 ist bereits verarbeitet (110 Chunks)

Du kannst jetzt im Dashboard die Chunks bearbeiten!
