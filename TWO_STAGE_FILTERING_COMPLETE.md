# 2-Stufige Dateifilterung - Implementierung Abgeschlossen ✅

**Datum:** 12. Juni 2026  
**Status:** Implementiert, bereit für Testing

---

## Was wurde implementiert

### ✅ 1. Zwei neue Prompts in Datenbank
**Datei:** `add_two_stage_prompts.py`

- `material_file_analysis_stage1_fast` (Temperature: 0.2, Max Tokens: 2000)
- `material_file_analysis_stage2_detailed` (Temperature: 0.3, Max Tokens: 1500)

**Ausgeführt:** ✅ Prompts in `system_prompts` Tabelle eingefügt

### ✅ 2. Helper-Funktionen
**Datei:** `material_processor.py`

```python
def read_file_preview(self, file_path: str, max_chars: int = 500) -> str
def is_text_file(self, filename: str) -> bool
```

### ✅ 3. Hauptmethode analyze_files_two_stage()
**Datei:** `material_processor.py` (nach Zeile 318)

**Signatur:**
```python
async def analyze_files_two_stage(
    self,
    files: List,
    parsed_pdfs: Dict[str, str] = None,
    material_type: str = None,
    display_name: str = None
) -> Dict[str, Tuple[bool, str]]
```

**Features:**
- ✅ Stage 1: Schnelle Kategorisierung (nur Dateinamen + PDF-Kontext)
- ✅ Stage 2: Detaillierte Analyse (Content-Preview für "unsure" Dateien)
- ✅ Fallback zu `analyze_files_batch()` bei Fehlern
- ✅ Conservative defaults (bei Fehlern → include)
- ✅ Ausführliches Logging

### ✅ 4. Integration in process_material()
**Datei:** `material_processor.py` (Zeile 873-877)

```python
# ALT:
# analysis_results = await self.analyze_files_batch(files, parsed_pdfs)

# NEU:
analysis_results = await self.analyze_files_two_stage(
    files, parsed_pdfs,
    material_type=material.material_type,
    display_name=material.display_name
)
```

---

## Wie es funktioniert

### Stage 1: Schnelle Kategorisierung

**Input:**
- Alle Dateinamen
- PDF-Content (falls vorhanden, vollständig)
- Material-Typ und Name

**Output:**
```json
{
  "definitely_important": [
    {"filename": "Factorial.java", "reason": "Mentioned in assignment"}
  ],
  "definitely_unimportant": [
    {"filename": "Factorial.class", "reason": "Compiled bytecode"}
  ],
  "unsure": [
    {"filename": "MathUtils.java", "reason": "Utility class, unclear if needed"}
  ]
}
```

**Logik:**
- **definitely_important**: In Aufgabe erwähnt, Main-Dateien, Tests, Starter-Code
- **definitely_unimportant**: Build-Artifacts, Dependencies, IDE-Config
- **unsure**: Utility-Klassen, Config-Dateien, README, Ressourcen

### Stage 2: Detaillierte Analyse (nur bei "unsure" Dateien)

**Input:**
- PDF-Content
- Liste der "definitely_important" Dateien
- Content-Preview (500 Zeichen) der "unsure" Dateien

**Output:**
```json
{
  "essential": [
    {"filename": "MathUtils.java", "reason": "Imported by Factorial.java"}
  ],
  "not_essential": [
    {"filename": "config.json", "reason": "IDE configuration"}
  ]
}
```

**Logik:**
- **essential**: Wird importiert/referenziert, enthält Setup-Infos, notwendige Hilfsfunktionen
- **not_essential**: Nur IDE-Config, nur Komfort, nur Beispiele

---

## Logging-Ausgabe

**Stage 1:**
```
INFO: [STAGE 1] Analyzing 8 files (filenames only)
INFO: [STAGE 1] Results: 2 important, 3 unimportant, 3 unsure
```

**Stage 2:**
```
INFO: [STAGE 2] Analyzing 3 unsure files (with previews)
INFO: [STAGE 2] Results: 2 essential, 1 not essential
```

**Final:**
```
INFO: [2-STAGE] Final: 4 important, 4 unimportant
```

**In MaterialProcessingLog:**
- `"File is IMPORTANT: [Stage 1] Mentioned in assignment"`
- `"File is IMPORTANT: [Stage 2] Imported by Main.java"`
- `"File skipped: [Stage 1] Build artifact"`
- `"File skipped: [Stage 2] IDE configuration only"`

---

## Fallback-Verhalten

### Bei Stage 1 Fehler:
```python
except Exception as e:
    logger.error(f"[STAGE 1] Error: {e}")
    return await self.analyze_files_batch(files, parsed_pdfs)  # Alte 1-Stufen-Methode
```

### Bei Stage 2 Fehler:
```python
except Exception as e:
    logger.error(f"[STAGE 2] Error: {e}")
    essential = unsure  # Alle unsure Dateien als essential
    not_essential = []
```

**Konservatives Verhalten:** Bei Fehlern werden Dateien eher included als excluded

---

## Test-Szenarien

### Test 1: Programmier-Projekt mit vielen Dateien

**Upload:**
```
hw3-factorial.zip:
  - Aufgabenblatt.pdf (Aufgabenstellung)
  - src/Factorial.java (Haupt-Datei)
  - src/FactorialTest.java (Tests)
  - src/MathUtils.java (Utility)
  - lib/junit-4.12.jar (Dependency)
  - build.xml (Build-Script)
  - .classpath (IDE-Config)
  - README.txt (Setup-Anleitung)
```

**Expected Stage 1:**
- definitely_important: `Factorial.java`, `FactorialTest.java` (2)
- definitely_unimportant: `junit-4.12.jar`, `build.xml`, `.classpath` (3)
- unsure: `MathUtils.java`, `README.txt` (2)

**Expected Stage 2:**
- essential: `MathUtils.java` (wird importiert), `README.txt` (Build-Anleitung) (2)
- not_essential: (0)

**Final Result:** 5 Dateien gespeichert (PDF + 4 Code-Dateien)

### Test 2: Nur PDFs (Fast-Path)

**Upload:** `Aufgabenblatt.pdf`, `Lösungen.pdf`

**Expected:** Beide Stages übersprungen (existing optimization)

### Test 3: Gemischte Dateien ohne PDF

**Upload:** `Main.java`, `Helper.java`, `build.gradle`

**Expected:** 
- Stage 1 läuft ohne PDF-Kontext
- Stage 2 läuft falls nötig

---

## Verifikation über Dashboard

### 1. Material hochladen
- Type: homework
- Files: ZIP mit Programmier-Projekt

### 2. Process triggern
- Klick auf "Process" Button

### 3. Logs prüfen
```sql
SELECT 
    stage, 
    status, 
    message,
    details->>'reason' as reason
FROM material_processing_log
WHERE material_id = '<material_id>'
AND stage = 'file_analysis'
ORDER BY started_at;
```

**Expected:**
- Mehrere Einträge mit `[Stage 1]` prefix
- Mehrere Einträge mit `[Stage 2]` prefix
- Status `'completed'` für important files
- Status `'skipped'` für unimportant files

### 4. Content prüfen
```sql
SELECT 
    file_name,
    importance_reason,
    LENGTH(content) as content_length
FROM material_contents
WHERE material_id = '<material_id>'
ORDER BY file_name;
```

**Expected:**
- Nur important files gespeichert
- `importance_reason` enthält Stage-Info

---

## Vorteile der Implementation

### ✅ Genauigkeit
- Klare Kategorien statt binäre Entscheidung
- Stage 2 nur für Grenzfälle
- Strenges "essential"-Kriterium

### ✅ Effizienz
- Stage 1: Weniger Input-Tokens (nur Dateinamen)
- Stage 2: Nur für Subset (20-30% der Files)
- Content-Previews nur wo nötig (500 chars)

### ✅ Robustheit
- Fallback zu alter Methode bei Stage 1 Fehler
- Conservative defaults (include bei Unsicherheit)
- Ausführliches Logging für Debugging

### ✅ Transparenz
- Logging zeigt beide Stages
- Reasons enthalten Stage-Info (`[Stage 1]` / `[Stage 2]`)
- Nachvollziehbare Entscheidungen

### ✅ Wartbarkeit
- Getrennte Prompts für unterschiedliche Aufgaben
- Kompatibles Interface (keine Breaking Changes)
- Leicht anpassbar (Prompts via Dashboard editierbar!)

---

## Bekannte Limitationen

### 1. JSON-Parsing
**Problem:** LLM könnte ungültiges JSON zurückgeben  
**Mitigation:** Fallback zu alter Methode oder conservative defaults

### 2. Performance
**Problem:** 2 LLM-Calls statt 1  
**Mitigation:** Stage 1 schneller (weniger Input), Stage 2 nur Subset

### 3. False Negatives
**Problem:** Stage 2 könnte wichtige Dateien als "not_essential" markieren  
**Mitigation:** Ausführliches Logging, Student-Feedback möglich

---

## Prompt-Editierung über Dashboard

Die neuen Prompts können über das Prompts-Admin-Dashboard editiert werden:

**URL:** `http://localhost:5173/admin/prompts`

**Prompts:**
- `material_file_analysis_stage1_fast`
- `material_file_analysis_stage2_detailed`

**Änderungen möglich:**
- Kriterien für "definitely_important" verschärfen/lockern
- Kriterien für "definitely_unimportant" anpassen
- Output-Format-Beispiele hinzufügen
- Temperature/Max-Tokens anpassen

**Nach Änderung:** Cache reload erforderlich (Button im Dashboard)

---

## Nächste Schritte

### Sofort:
1. ✅ Implementation abgeschlossen
2. 🔄 Manuelle Tests über Dashboard durchführen
3. 📊 Logs prüfen und analysieren

### Kurzfristig:
1. A/B Testing mit echten Hausaufgaben
2. Prompt-Finetuning basierend auf Logs
3. Performance-Messung (Token-Verbrauch)

### Langfristig:
1. Metrics sammeln (False Positives/Negatives)
2. Student-Feedback auswerten ("Datei fehlt")
3. Automatische Re-Processing bei Feedback

---

## Rollback-Prozedur

Falls Probleme auftreten:

```python
# In material_processor.py Zeile 873-877:

# ROLLBACK:
analysis_results = await self.analyze_files_batch(files, parsed_pdfs)

# Statt:
# analysis_results = await self.analyze_files_two_stage(
#     files, parsed_pdfs,
#     material_type=material.material_type,
#     display_name=material.display_name
# )
```

**Vorteil:** Alte Methode bleibt intakt, einfacher Rollback

---

## Dateien geändert

1. ✅ `add_two_stage_prompts.py` - Neues Script (run once)
2. ✅ `material_processor.py` - Neue Methoden + Integration
3. ✅ `system_prompts` DB - 2 neue Prompts
4. ✅ `TWO_STAGE_FILTERING_COMPLETE.md` - Diese Dokumentation

---

**Implementation Status: ✅ COMPLETE - Ready for Testing**

Die 2-stufige Filterung ist vollständig implementiert und kann über das Professor-Dashboard getestet werden!
