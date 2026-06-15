# Reducto Migration für Non-Lecture Materialien - Abgeschlossen ✅

**Datum:** 12. Juni 2026  
**Status:** Implementierung abgeschlossen, bereit für Testing

---

## Was wurde geändert

### 1. Neue Methode: `parse_pdf_with_reducto()`
**Datei:** `material_processor.py` (nach Zeile 375)

```python
async def parse_pdf_with_reducto(self, file_path: str) -> str:
    """
    Parse PDF using Reducto and combine all chunk content.
    
    Returns: Combined content from all Reducto chunks with \n\n separator
    """
```

**Funktionsweise:**
1. Ruft Reducto API über `reducto_client.parse_pdf()` auf
2. Extrahiert alle `chunks` aus dem Response
3. Nimmt `chunk.get("content", "")` von jedem Chunk
4. Fügt alle Chunks mit `\n\n` Separator zusammen
5. Loggt: `"Reducto parsed X chunks → Y chars"`

**Error Handling:**
- Keine Chunks: `"[Empty PDF or parsing failed: filename.pdf]"`
- Exception: `"[PDF Parsing Error for filename.pdf: error message]"`

### 2. LlamaParse Aufrufe ersetzt (2 Stellen)

**Stelle 1: Batch-Analyse** (Zeile ~632)
```python
# ALT: pdf_content = await self.parse_pdf(file.file_path)
# NEU:
pdf_content = await self.parse_pdf_with_reducto(file.file_path)
```

**Stelle 2: Finale Speicherung** (Zeile ~684)
```python
# ALT: content = await self.parse_pdf(file.file_path)
# NEU:
content = await self.parse_pdf_with_reducto(file.file_path)
```

Beide Stellen loggen jetzt: `"Parsing PDF with Reducto: filename.pdf"`

### 3. Cleanup: LlamaParse Code entfernt

**Entfernt:**
- ❌ `from llama_parse_client import get_llama_parse_client` (Zeile 30)
- ❌ `self.llama_parse = None` aus `__init__()` (Zeile 45)
- ❌ `async def parse_pdf()` Methode (Zeile 376-406)

**Verbleibend (für später):**
- ⏳ `llama_parse_client.py` - Datei existiert noch (nicht verwendet)
- ⏳ `uploads/.llama_parse_cache/` - Cache-Verzeichnis existiert noch
- ⏳ `config.py` - `llama_cloud_api_key` noch in Config
- ⏳ `parsers/pdf_parser.py` - Nutzt noch LlamaParse (nur für ParsedChunkData Typ)

---

## Verhalten VORHER vs NACHHER

### VORHER (LlamaParse)
```
PDF → LlamaParse API → Vollständiger Markdown String → Speichern
```

**Eigenschaften:**
- Ein API-Call
- Direkt zusammenhängender Text
- Deutsche Sprache, Code/Tabellen/Formeln erhalten
- Cache in `uploads/.llama_parse_cache/`

### NACHHER (Reducto)
```
PDF → Reducto API → Chunks → Content extrahieren → Mit \n\n joinen → Speichern
```

**Eigenschaften:**
- Ein API-Call (gleich wie vorher)
- Chunks werden kombiniert mit `\n\n` Separator
- Markdown-Tabellen erhalten (`table_output_format: "md"`)
- Cache in `uploads/.reducto_cache/`
- **Nutzt gleichen Parser wie Lectures!** (Kostenersparnis, Konsistenz)

---

## Was bleibt UNVERÄNDERT

✅ **Dateifilterung:** LLM Batch-Analyse funktioniert weiter  
✅ **Code-Files:** Werden weiter direkt gelesen  
✅ **Text-Files:** Werden weiter direkt gelesen  
✅ **MaterialContent Schema:** Keine DB-Änderungen nötig  
✅ **RAG Retrieval:** `retrieve_all_from_material()` unverändert  
✅ **Chat Integration:** Studenten sehen keinen Unterschied  
✅ **Professor Editing:** Content-Editierung funktioniert weiter  

---

## Verifikation & Testing

### Manueller Test (Professor Dashboard)

1. **Material hochladen:**
   - Typ: `homework` oder `tutorium`
   - Files: 1-2 PDFs (z.B. Aufgabenblatt)

2. **"Process" klicken**

3. **Logs prüfen:**
   ```sql
   SELECT stage, status, message, started_at
   FROM material_processing_log 
   WHERE material_id = '<material_id>' 
   ORDER BY started_at;
   ```

   **Erwartete Logs:**
   - `parsing, started, "Parsing PDF with Reducto: Aufgabenblatt.pdf"`
   - `parsing, completed, "Stored full content (X chars)"`

4. **Content prüfen:**
   ```sql
   SELECT 
     file_name, 
     source_type, 
     LENGTH(content) as chars,
     LEFT(content, 200) as preview
   FROM material_contents
   WHERE material_id = '<material_id>';
   ```

   **Erwartungen:**
   - `source_type` = `'pdf_markdown'`
   - `chars` > 0 (sollte mehrere KB sein)
   - `preview` zeigt Markdown-Text (Überschriften, Tabellen, etc.)

### Automatisierter Test

```bash
python test_reducto_non_lecture.py
```

**Testet:**
- ✅ PDF-Parsing mit Reducto
- ✅ Chunk-Kombinierung
- ✅ Error Handling (nicht-existente Datei)
- ✅ Content-Länge und Vorschau

### Chat-Integration Test

1. **Student wählt Homework Material aus**
2. **Frage stellen:** "Was ist die Aufgabenstellung?"
3. **LLM sollte antworten** basierend auf PDF-Content

**Backend Check:**
```python
# In rag.py wird aufgerufen:
contents = retrieve_all_from_material(material_id)
# Sollte MaterialContent Einträge mit Reducto-geparsten PDFs liefern
```

---

## Vorteile der Migration

### ✅ Kostenersparnis
- Nur noch **ein** PDF-Parser-Abonnement nötig (Reducto)
- LlamaParse API-Key kann deaktiviert werden

### ✅ Konsistenz
- Lectures UND Non-Lectures nutzen gleichen Parser
- Gleiche Qualität bei Tabellen, Formeln, Struktur
- Einheitliches Caching (`uploads/.reducto_cache/`)

### ✅ Wartbarkeit
- Weniger Code (`parse_pdf()` Methode entfernt)
- Weniger Dependencies (`llama_parse_client.py` nicht mehr nötig)
- Ein Parser für alle PDF-Verarbeitungen

### ✅ Qualität
- Reducto hat sich bei Lectures bereits bewährt
- Markdown-Tabellen bleiben erhalten
- Page-Markers werden korrekt verarbeitet

---

## Nächste Schritte (Optional)

### Schritt 1: Testing in Production
1. Material hochladen (Typ: homework)
2. Processing beobachten
3. Logs prüfen
4. Content-Qualität verifizieren
5. Chat-Integration testen

### Schritt 2: Cleanup (nach erfolgreichem Testing)
```bash
# LlamaParse Client entfernen
rm /home/cedrik/AI-Tutor/llama_parse_client.py

# Cache-Verzeichnis entfernen
rm -rf /home/cedrik/AI-Tutor/uploads/.llama_parse_cache/

# Config bereinigen (optional)
# Entferne llama_cloud_api_key aus config.py
```

### Schritt 3: Config Update
**Datei:** `config.py`

```python
# ENTFERNEN (falls nicht mehr gebraucht):
llama_cloud_api_key: str = Field(..., description="LlamaParse API key")
```

**Hinweis:** Erst entfernen nachdem sichergestellt wurde, dass `parsers/pdf_parser.py` nicht mehr aktiv genutzt wird!

---

## Risiken & Mitigationen

### ✅ Chunk-Separator
**Risiko:** `\n\n` könnte zu viel/wenig Whitespace sein  
**Status:** `\n\n` ist Standard in RAG-Systemen  
**Fallback:** Leicht änderbar zu `\n\n---\n\n` falls nötig

### ✅ Qualitätsunterschied
**Risiko:** Reducto könnte schlechtere Qualität haben als LlamaParse  
**Status:** Reducto wird bereits für Lectures verwendet (bewährt)  
**Mitigation:** A/B Test mit 1-2 PDFs vor Vollausrollung

### ✅ Cache-Konflikte
**Risiko:** Gleicher Cache für Lecture/Non-Lecture  
**Status:** Kein Problem - Cache-Key ist file_path (eindeutig)  
**Verhalten:** Gleiche PDFs nutzen gleichen Cache (Effizienz!)

### ✅ Backwards Compatibility
**Risiko:** Alte Materials nicht mehr lesbar  
**Status:** Kein Problem - alte Materials behalten ihre gespeicherten Contents  
**Verhalten:** Nur neue/re-prozessierte Materials nutzen Reducto

---

## Rollback Procedure

Falls Probleme auftreten:

```bash
# Git revert der Änderungen
git revert <commit-hash>

# Oder manuell:
# 1. parse_pdf() Methode wieder hinzufügen
# 2. Import wieder hinzufügen
# 3. 2 Aufrufe zurück zu parse_pdf() ändern
```

**Vorteil:** Keine DB-Änderungen → Rollback ist safe!

---

## Dateien geändert

1. **material_processor.py** - Hauptänderungen (neue Methode, 2 Replacements, Cleanups)
2. **test_reducto_non_lecture.py** - Neues Testskript
3. **REDUCTO_MIGRATION_COMPLETE.md** - Diese Dokumentation

## Dateien NICHT geändert

- `database.py` - Keine Schema-Änderungen nötig
- `rag.py` - Retrieval-Logik unverändert
- `reducto_client.py` - Keine Änderungen nötig (funktioniert out-of-the-box)
- `api/professor_material_api.py` - Upload/Edit Endpoints unverändert
- `config.py` - Config bleibt vorerst unverändert

---

**Migration Status: ✅ COMPLETE - Ready for Testing**

Alle Code-Änderungen sind implementiert. Nächster Schritt: Manuelle Verifikation mit einem Test-PDF über das Professor Dashboard.
