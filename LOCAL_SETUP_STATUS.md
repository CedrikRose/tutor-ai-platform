# ✅ AI-Tutor Lokale Installation - Status

**Setup abgeschlossen am:** 11. Juni 2026, 18:35 Uhr

## 🎉 System läuft!

### Backend (FastAPI)
- **Status:** ✅ Läuft
- **URL:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Prozess ID:** 229325
- **Datenbank:** PostgreSQL (lokal) - ai_tutor_prod

### Frontend (React + Vite)
- **Status:** ✅ Läuft  
- **URL:** http://localhost:5173
- **Development Mode:** Aktiv mit Hot Reload

### Datenbank
- **Status:** ✅ Importiert
- **Name:** ai_tutor_prod
- **User:** ai_tutor_prod
- **Host:** localhost:5432
- **Größe:** 74 MB (vom AWS Server)
- **Extensions:** pgvector aktiviert

## 🔌 Zugriff

### Anwendung öffnen
```
http://localhost:5173
```

### API Dokumentation
```
http://localhost:8000/docs
```

### API Endpoints testen
```bash
# Health Check
curl http://localhost:8000/

# Courses
curl http://localhost:8000/api/courses
```

## 📊 Backend Features

Folgende APIs sind aktiv:
- ✅ Professor Course API
- ✅ Professor Material API  
- ✅ Manual Analysis Trigger API
- ✅ Scheduler Status API
- ✅ Chat API v2
- ✅ Prompts Admin API
- ✅ Daily Analysis Scheduler (läuft um 3:00 AM)

### Geladene Prompts
- 7 Prompts erfolgreich geladen

### LLM Konfiguration
- **Primary Model:** moonshotai.kimi-k2.5
- **Secondary Model:** minimax.minimax-m2.5
- **Embedding Model:** amazon.titan-embed-text-v2:0
- **Provider:** AWS Bedrock

## ⚠️ Bekannte Warnungen (nicht kritisch)

```
WARNING: Could not import auth_api: email-validator is not installed
WARNING: Could not import professor_analysis_api: email-validator is not installed
```

**Fix (optional):**
```bash
source .venv/bin/activate
pip install 'pydantic[email]'
```

## 🔧 Server Verwaltung

### Backend stoppen
```bash
# Prozess finden
ps aux | grep uvicorn

# Stoppen (ersetze PID mit der Prozess ID)
kill <PID>
```

### Frontend stoppen
```bash
# Prozess finden
ps aux | grep vite

# Stoppen
kill <PID>
```

### Beide Server neu starten

**Backend:**
```bash
cd /home/cedrik/AI-Tutor
source .venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd /home/cedrik/AI-Tutor/frontend
npm run dev
```

## 📁 Wichtige Dateien

### Konfiguration
- `/home/cedrik/AI-Tutor/.env` - Backend Umgebungsvariablen
- `/home/cedrik/AI-Tutor/frontend/.env` - Frontend Konfiguration (API URL)

### Logs
Backend Logs erscheinen direkt im Terminal, wo uvicorn läuft.

## 🔑 Zugangsdaten

### Datenbank
```
Host: localhost
Port: 5432
Database: ai_tutor_prod
User: ai_tutor_prod
Password: DBTutorSecure2026
```

### Professor Registration Code
```
PROFESSOR_REGISTRATION_CODE=!yAHeq2v@L59MV
```

Verwenden Sie diesen Code bei der Registrierung als Professor.

## 🔄 Sync mit AWS Server

### Lokale Änderungen zum Server hochladen
```bash
cd /home/cedrik/AI-Tutor

# Code hochladen
rsync -avz \
  --exclude='.venv' --exclude='node_modules' --exclude='.env' \
  --exclude='uploads' --exclude='__pycache__' --exclude='.git' \
  --exclude='dist' \
  -e "ssh -i /home/cedrik/Downloads/AI-Tutor.pem" \
  . ubuntu@98.91.21.41:/opt/ai-tutor/

# Auf Server deployen
ssh -i /home/cedrik/Downloads/AI-Tutor.pem ubuntu@98.91.21.41
cd /opt/ai-tutor
./deploy/update.sh
```

### Server Datenbank erneut holen
```bash
# Auf Server Dump erstellen
ssh -i /home/cedrik/Downloads/AI-Tutor.pem ubuntu@98.91.21.41 \
  "sudo -u postgres pg_dump ai_tutor_prod > /tmp/backup.sql"

# Lokal herunterladen
scp -i /home/cedrik/Downloads/AI-Tutor.pem \
  ubuntu@98.91.21.41:/tmp/backup.sql /tmp/

# Lokal importieren
psql -U ai_tutor_prod -d ai_tutor_prod < /tmp/backup.sql
```

## 🧪 Testen

### Frontend Funktionalität
1. Öffne http://localhost:5173
2. Registriere dich mit dem Professor Code
3. Logge dich ein
4. Erstelle einen Kurs
5. Lade Material hoch
6. Starte einen Chat

### Backend API
```bash
# Courses abrufen
curl http://localhost:8000/api/courses

# Oder via Browser: http://localhost:8000/docs
```

## 📦 Backups

Alle Backups befinden sich in:
```
/home/cedrik/backups/AI-Tutor/
├── local-backup-20260611-181932.tar.gz     # Lokaler Stand vor Setup
├── aws-server-backup/
│   ├── ai_tutor_prod_backup.sql            # Datenbank vom Server
│   └── ai-tutor/                           # Server Code
├── BACKUP_ZUSAMMENFASSUNG.md
└── RESTORE_ANLEITUNG.md
```

## 🎯 Nächste Schritte

1. ✅ System läuft lokal
2. Entwicklung an Features durchführen
3. Änderungen testen
4. Bei Bedarf auf AWS Server deployen
5. Optional: email-validator installieren für volle Auth-Funktionalität

## 🐛 Troubleshooting

### Backend startet nicht
```bash
# Logs prüfen
tail -50 /tmp/claude-1000/-home-cedrik-AI-Tutor/*/tasks/bqi8wwr5q.output

# Datenbank Verbindung testen
psql -U ai_tutor_prod -d ai_tutor_prod -h localhost -c "SELECT 1;"
```

### Frontend zeigt API Fehler
- Prüfe ob Backend auf Port 8000 läuft: `curl http://localhost:8000/docs`
- Prüfe Frontend .env: `cat frontend/.env` (sollte `VITE_API_URL=http://localhost:8000` sein)

### Port schon belegt
```bash
# Port 8000 freigeben
lsof -ti:8000 | xargs kill -9

# Port 5173 freigeben  
lsof -ti:5173 | xargs kill -9
```

## 📝 Unterschiede Lokal vs. Server

| Feature | Lokal | AWS Server |
|---------|-------|------------|
| URL | http://localhost:5173 | https://tutor-ai.me |
| Backend | Development (uvicorn) | Production (systemd) |
| Frontend | Vite Dev Server | Nginx (static) |
| SSL | Nein | Ja (Let's Encrypt) |
| Hot Reload | Ja | Nein |
| Datenbank | localhost | localhost (auf Server) |

## ✨ Fertig!

Ihre lokale AI-Tutor Entwicklungsumgebung ist vollständig eingerichtet und läuft!

**Backend:** http://localhost:8000  
**Frontend:** http://localhost:5173  
**API Docs:** http://localhost:8000/docs
