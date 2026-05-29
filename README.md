# AI-Tutor

KI-gestütztes Tutorsystem für Programmier-Kurse mit RAG (Retrieval-Augmented Generation).

## Features

- 🤖 **Intelligenter Chat-Tutor** mit Claude (AWS Bedrock)
- 📚 **RAG-basierte Wissensbasis** aus Kurs-Materialien
- 📄 **Automatisches Material-Parsing** (PDFs, Code-Dateien)
- 👨‍🏫 **Professor Dashboard** zum Verwalten von Kursen & Materialien
- 👨‍🎓 **Student Frontend** für interaktive Chat-Sessions
- 📊 **Conversation Analytics** & Learning Insights
- 🔐 **Sichere Authentifizierung** mit JWT

## Architektur

### Backend
- **FastAPI** Server (Python 3.12)
- **PostgreSQL 16** mit pgvector für Embeddings
- **AWS Bedrock** (Claude 4.5 Sonnet, Titan Embeddings)
- **LlamaParse** für PDF-Verarbeitung

### Frontend
- **Student Frontend:** React + Vite + TypeScript
- **Professor Dashboard:** React + Vite + TypeScript

## Schnellstart (Lokal)

### Voraussetzungen

- Python 3.12+
- Node.js 20+
- PostgreSQL 16 mit pgvector
- AWS Bedrock Zugang
- LlamaParse API Key

### Installation

```bash
# Repository klonen
git clone <your-repo-url>
cd AI-Tutor

# Environment konfigurieren
cp .env.template .env
nano .env  # Fülle API Keys aus

# Python Dependencies
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Datenbank initialisieren
python migrations/init_db.py

# Backend starten
cd api
uvicorn main:app --reload

# Student Frontend (neues Terminal)
cd frontend
npm install
npm run dev

# Professor Dashboard (neues Terminal)
cd professor-dashboard
npm install
npm run dev
```

### Zugriff

- Student Frontend: http://localhost:5173
- Professor Dashboard: http://localhost:5174
- API Docs: http://localhost:8000/docs

## AWS Deployment

### Quick Start

Für EC2 Ubuntu 26 LTS Deployment:

```bash
# 1. Auf EC2: Server Setup
./deploy/setup_ec2.sh

# 2. Lokal: Code kopieren
rsync -avz --exclude='.venv' --exclude='node_modules' \
  -e "ssh -i key.pem" . ubuntu@EC2_IP:/opt/ai-tutor/

# 3. Auf EC2: Environment konfigurieren
cd /opt/ai-tutor
cp deploy/.env.production.template .env
nano .env

# 4. Auf EC2: Installation
./deploy/install_app.sh
```

**Vollständige Anleitung:** Siehe `DEPLOYMENT_QUICKSTART.md` oder `deploy/DEPLOYMENT_FULL.md`

### Nach Deployment verfügbar

- Student Frontend: http://YOUR_EC2_IP/
- Professor Dashboard: http://YOUR_EC2_IP:8080/
- API: http://YOUR_EC2_IP:8000/docs

## Projekt-Struktur

```
AI-Tutor/
├── api/                          # FastAPI Backend
│   ├── main.py                   # Haupt-API Einstiegspunkt
│   ├── chat_api_v2.py           # WebSocket Chat API
│   ├── auth_api.py              # Authentifizierung
│   ├── professor_*.py           # Professor Endpoints
│   └── ...
├── frontend/                     # Student React App
│   ├── src/
│   └── dist/                    # Build Output
├── professor-dashboard/          # Professor React App
│   ├── src/
│   └── dist/                    # Build Output
├── migrations/                   # Datenbank Migrations
│   └── init_db.py
├── deploy/                       # Deployment Skripte
│   ├── setup_ec2.sh             # EC2 Server Setup
│   ├── install_app.sh           # App Installation
│   ├── update.sh                # Update Skript
│   └── DEPLOYMENT_FULL.md       # Vollständige Anleitung
├── database.py                   # SQLAlchemy Models
├── config.py                     # Konfiguration
├── llm.py                        # LLM Integration
├── rag.py                        # RAG Retriever
├── embeddings.py                 # Embedding Generation
├── material_processor.py         # Material Verarbeitung
├── auth.py                       # Auth Utilities
├── requirements.txt              # Python Dependencies
├── .env.template                 # Environment Template
└── README.md                     # Diese Datei
```

## Wichtige Komponenten

### Material Processing Pipeline

1. **Upload:** Professor lädt PDFs/Code hoch
2. **Parsing:** 
   - PDFs → LlamaParse → Text Chunks
   - Code → Tree-sitter → Semantische Chunks
3. **Embeddings:** AWS Titan Embeddings
4. **Storage:** PostgreSQL mit pgvector

### RAG Chat Flow

1. Student stellt Frage
2. Query → Embedding
3. Vector-Suche in Material-Chunks
4. Kontext + Frage → Claude
5. Antwort zurück an Student

### Professor Dashboard

- Kurse erstellen & verwalten
- Materialien hochladen
- Verarbeitungsstatus überwachen
- Chat-Analytics ansehen
- Email-Reports generieren

### Student Frontend

- Kurs wählen
- Chat-Sessions starten
- Fragen zu Materialien stellen
- Chat-Historie ansehen

## API Endpoints

### Public

- `POST /api/auth/register` - Professor Registrierung
- `POST /api/auth/login` - Login
- `GET /api/courses/public` - Öffentliche Kurse

### Protected (Professor)

- `GET/POST/PUT/DELETE /api/professor/courses` - Kursverwaltung
- `POST /api/professor/materials/upload` - Material Upload
- `GET /api/professor/analytics/*` - Analytics

### Protected (Student)

- `WS /api/v2/ws/{session_id}` - Chat WebSocket
- `GET /api/v2/chat/sessions` - Chat Sessions
- `POST /api/v2/chat/sessions` - Neue Session

## Development

### Backend Development

```bash
# Mit auto-reload
cd api
uvicorn main:app --reload --port 8000
```

### Frontend Development

```bash
# Student Frontend
cd frontend
npm run dev  # Port 5173

# Professor Dashboard
cd professor-dashboard
npm run dev  # Port 5174
```

### Datenbank Migrations

```bash
# Neue Migration erstellen
cd migrations
# Erstelle neue .py Datei mit Migration

# Migration ausführen
PYTHONPATH=/home/cedrik/AI-Tutor python migrations/your_migration.py
```

### Tests

```bash
# Backend Tests
pytest

# Frontend Tests
cd frontend
npm test

cd professor-dashboard
npm test
```

## Konfiguration

### Environment Variables

Siehe `.env.template` für alle verfügbaren Optionen.

Wichtigste:

```bash
# Datenbank
DATABASE_URL=postgresql://user:pass@localhost/ai_tutor_dev

# AWS Bedrock
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...

# LlamaParse
LLAMA_CLOUD_API_KEY=...

# Auth
JWT_SECRET_KEY=...
PROFESSOR_REGISTRATION_CODE=...

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## Monitoring & Logs

### Lokal

```bash
# Backend Logs
# Siehe Console Output

# Frontend Logs
# Browser DevTools Console
```

### Produktion (EC2)

```bash
# API Logs
sudo journalctl -u ai-tutor-api -f
sudo tail -f /var/log/ai-tutor-api.log

# Nginx Logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# PostgreSQL Logs
sudo journalctl -u postgresql -f
```

## Backups

### Datenbank Backup

```bash
# Manuell
pg_dump ai_tutor_prod > backup_$(date +%Y%m%d).sql

# Automatisch (Cron)
# Siehe deploy/DEPLOYMENT_FULL.md
```

## Troubleshooting

### Backend startet nicht

- Prüfe `.env` Konfiguration
- Prüfe Datenbank-Verbindung
- Siehe Logs: `tail -f api.log`

### Frontend build error

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Datenbank Migration Fehler

```bash
# Reset (ACHTUNG: Löscht alle Daten!)
python migrations/init_db.py --reset

# Oder manuell:
psql -U ai_tutor -d ai_tutor_dev
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
```

## Support

- 📧 Email: cedrik.rosemann@tutor-ai.me
- 📖 Dokumentation: `deploy/DEPLOYMENT_FULL.md`

## 📝 License

This project is licensed under CC BY-NC-ND 4.0.

[![License: CC BY-NC-ND 4.0](https://img.shields.io/badge/License-CC%20BY--NC-
-ND%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-nd/4.0/)

**You are free to:**
- 👀 View and study the code
- 📚 Use it for learning purposes

**Under the following terms:**
- 📛 **Attribution** — You must give appropriate credit
- 💰 **NonCommercial** — You may not use the material for commercial purposes
- 🚫 **NoDerivatives** — You may not distribute modified versions

For commercial use or custom licensing, please contact me.

## Credits

- **LLM:** Claude 4.5 Sonnet (AWS Bedrock)
- **Embeddings:** Amazon Titan (AWS Bedrock)
- **PDF Parsing:** LlamaParse
- **Framework:** FastAPI, React
- **Database:** PostgreSQL + pgvector
