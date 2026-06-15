# ✅ Reducto Integration Update

**Datum:** 11. Juni 2026, 19:00 Uhr

## Was wurde aktualisiert?

Die lokale Installation verwendet jetzt **Reducto statt LlamaParse** für Vorlesungsfolien!

### Neue Dateien vom AWS Server kopiert:

1. ✅ **reducto_client.py** - Reducto API Client mit Caching
2. ✅ **lecture_synthesizer.py** - Kimi K2.5 Synthese für Vorlesungen
3. ✅ **material_processor.py** - Aktualisierte Version mit Reducto-Integration

### Konfiguration:

**API Key hinzugefügt in `.env`:**
```
REDUCTO_API_KEY=0c9711db91971a433a6b1b0e7669dc1607613b2a1f79b3606cc9aecc2328a74c88070c115956d5f7f5174acae58c61a4
```

**Config.py aktualisiert:**
```python
reducto_api_key: str = Field(..., description="Reducto API key")
```

### Dependencies installiert:

```bash
pip install aiofiles
```

## Wie funktioniert es jetzt?

### Für Vorlesungsfolien (`lecture_slide`):

1. **Reducto Parsing** - Extraktion von Text und Struktur
2. **Kimi K2.5 Synthese** - Zusammenfassung und Anreicherung der Chunks
3. **Embedding** - Vektor-Embeddings für RAG
4. **Datenbank** - Speicherung der synthetisierten Chunks

### Für andere Materialien (Homework, Tutorium):

Weiterhin **LlamaParse** (wie vorher)

## Code-Logik

```python
# In material_processor.py, Zeile 550+
is_lecture = material.material_type == 'lecture_slide'

if is_lecture:
    # Zeile 644: Neue Methode verwenden
    await self.process_lecture_with_synthesis(material_id, important_files, db)
else:
    # Alte Methode für non-lecture materials
    await self.process_files(material_id, important_files, db)
```

## Test

Um zu testen, laden Sie eine neue Vorlesung hoch:

1. Öffne: http://localhost:5174/dashboard/
2. Gehe zu "Prog 2" Kurs
3. Lade eine PDF-Vorlesung hoch
4. Type: "Vorlesung / Lecture Slide"

Die Backend-Logs sollten zeigen:
```
INFO:material_processor:[LECTURE] Reducto returned X chunks for filename.pdf
INFO:material_processor:[LECTURE] Synthesizing with Kimi K2.5: X chunks
INFO:material_processor:[LECTURE] Synthesized X chunks
```

## Unterschiede Reducto vs. LlamaParse

| Feature | LlamaParse | Reducto |
|---------|-----------|---------|
| **Struktur-Erkennung** | Gut | Sehr gut |
| **Tabellen** | Mittel | Sehr gut |
| **Formeln** | Gut | Sehr gut |
| **Layout** | Einfach | Layout-aware chunks |
| **Geschwindigkeit** | Mittel | Schnell |
| **Synthese** | Nein | Ja (mit Kimi K2.5) |

## Vorteile der neuen Pipeline

1. **Bessere Struktur-Erkennung** durch Reducto
2. **Intelligente Synthese** - Kimi K2.5 fasst Chunks zusammen
3. **Kontextbewusst** - Chunks enthalten mehr semantischen Kontext
4. **Optimiert für Vorlesungen** - Speziell für akademische Folien

## Backup

Falls Probleme auftreten, die alte Version ist gesichert:
```
/home/cedrik/AI-Tutor/material_processor.py.backup
```

Wiederherstellen:
```bash
cp material_processor.py.backup material_processor.py
```

## Status

✅ Backend neu gestartet
✅ Reducto Client geladen
✅ Lecture Synthesizer verfügbar
✅ Kimi K2.5 konfiguriert

**Die nächste hochgeladene Vorlesung wird mit Reducto verarbeitet!**
