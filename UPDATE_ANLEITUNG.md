# 🚀 Server-Update Anleitung

## Zusammenfassung der Änderungen
1. **Datenbank**: `review_deadline` Spalte aus `course_materials` entfernt
2. **Frontend**: Alle "AI-Tutor" → "Tutor AI" umbenannt
3. **Neue Feature**: About/Impressum Seite hinzugefügt (`/about`)

---

## Schritt 1: Code hochladen (auf lokalem PC ausführen)

```bash
rsync -avz \
  --exclude='.venv' \
  --exclude='node_modules' \
  --exclude='.env' \
  --exclude='uploads' \
  --exclude='__pycache__' \
  --exclude='.git' \
  -e "ssh -i ~/Downloads/AI-Tutor.pem" \
  /home/cedrik/AI-Tutor/ \
  ubuntu@98.91.21.41:/opt/ai-tutor/
```

**Was passiert?**
- Code wird zum Server hochgeladen
- `.venv`, `node_modules`, `.env` werden NICHT überschrieben (bleiben auf Server)
- Uploads-Ordner bleibt unverändert

---

## Schritt 2: Auf Server einloggen

```bash
ssh -i ~/Downloads/AI-Tutor.pem ubuntu@98.91.21.41
```

---

## Schritt 3: Datenbank-Migration ausführen

```bash
cd /opt/ai-tutor
source .venv/bin/activate

# Migration ausführen
psql $DATABASE_URL -f migrations/005_remove_review_period.sql
```

**Erwartete Ausgabe:**
```
ALTER TABLE
UPDATE 0
ALTER TABLE
UPDATE 0
```

**Überprüfung:**
```bash
psql $DATABASE_URL -c "\d course_materials" | grep review_deadline
```
Sollte NICHTS ausgeben (Spalte ist weg).

---

## Schritt 4: Anwendung aktualisieren

```bash
cd /opt/ai-tutor
./deploy/update.sh
```

**Was passiert?**
1. Python-Dependencies werden aktualisiert
2. Student Frontend wird neu gebaut
3. Professor Dashboard wird neu gebaut
4. API-Service wird neu gestartet
5. Nginx wird neu geladen

**Dauer:** Ca. 2-3 Minuten

---

## Schritt 5: Verifizierung

### API Status prüfen:
```bash
sudo systemctl status ai-tutor-api
```
Sollte "active (running)" zeigen.

### Logs anschauen:
```bash
sudo journalctl -u ai-tutor-api -n 50 --no-pager
```

### Website testen:
Öffne im Browser: `http://98.91.21.41`

**Prüfe:**
- ✅ Steht jetzt "Tutor AI" statt "AI-Tutor"?
- ✅ Gibt es den Link "Info & Impressum" in der Sidebar?
- ✅ Funktioniert die About-Seite (`/about`)?
- ✅ Funktioniert der Chat wie vorher?

---

## Falls etwas schiefgeht

### Service läuft nicht:
```bash
# Logs anschauen
sudo journalctl -u ai-tutor-api -n 100 --no-pager

# Service manuell starten
sudo systemctl start ai-tutor-api
```

### Frontend zeigt alte Version:
```bash
# Browser-Cache leeren (Strg + Shift + R)
# Oder Nginx-Cache leeren:
sudo systemctl restart nginx
```

### Datenbank-Problem:
```bash
# Migration rückgängig machen (nur im Notfall):
psql $DATABASE_URL -c "ALTER TABLE course_materials ADD COLUMN review_deadline TIMESTAMPTZ;"
```

---

## Schnell-Checkliste

- [ ] Code mit rsync hochgeladen
- [ ] Auf Server eingeloggt
- [ ] Datenbank-Migration ausgeführt
- [ ] `update.sh` erfolgreich durchgelaufen
- [ ] Website im Browser getestet
- [ ] "Tutor AI" wird angezeigt
- [ ] About-Seite funktioniert
- [ ] Chat funktioniert normal

---

## Wichtige Dateien auf dem Server

- **Code:** `/opt/ai-tutor/`
- **Logs:** `sudo journalctl -u ai-tutor-api -f`
- **Service Config:** `/etc/systemd/system/ai-tutor-api.service`
- **Nginx Config:** `/etc/nginx/sites-available/ai-tutor`
- **Environment:** `/opt/ai-tutor/.env` (NICHT überschrieben!)
- **Uploads:** `/opt/ai-tutor/uploads/` (bleiben erhalten)

---

🎉 **Viel Erfolg!**
