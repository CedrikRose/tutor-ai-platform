# 🎉 AI-Tutor - Lokale Server Übersicht

**Alle Server laufen!** Stand: 11. Juni 2026, 18:40 Uhr

## 🌐 Zugriff auf die Anwendungen

### 📚 Studenten Chat (Frontend)
**URL:** http://localhost:5173

Der Hauptchat für Studenten zum Lernen und Fragen stellen.

### 👨‍🏫 Professor Dashboard
**URL:** http://localhost:5174/dashboard/

Dashboard für Professoren zum Verwalten von:
- Kursen
- Materialien
- Studenten-Analysen
- Prompts

⚠️ **Wichtig:** Die Professor Dashboard URL ist `/dashboard/` mit Slash am Ende!

### 🔌 Backend API
**URL:** http://localhost:8000
**Dokumentation:** http://localhost:8000/docs

Die FastAPI Backend-Schnittstelle.

## ✅ Laufende Services

| Service | Port | Status | URL |
|---------|------|--------|-----|
| Backend API | 8000 | ✅ Läuft | http://localhost:8000 |
| Studenten Frontend | 5173 | ✅ Läuft | http://localhost:5173 |
| Professor Dashboard | 5174 | ✅ Läuft | http://localhost:5174/dashboard/ |
| PostgreSQL | 5432 | ✅ Läuft | localhost:5432/ai_tutor_prod |

## 🐛 Probleme gelöst

### Problem 1: Chatbot zeigte "Offline"
**Ursache:** Frontend config.ts verwendete nicht die .env Variable  
**Lösung:** ✅ `config.ts` aktualisiert um `VITE_API_URL` zu verwenden  
**Status:** Backend ist jetzt erreichbar unter `http://localhost:8000`

### Problem 2: /dashboard Route nicht gefunden
**Ursache:** Professor Dashboard ist separate App auf eigenem Port  
**Lösung:** ✅ Professor Dashboard läuft auf Port 5174  
**URL:** http://localhost:5174/dashboard/

## 📁 Projekt Struktur

```
/home/cedrik/AI-Tutor/
├── api/                    # Backend API (FastAPI)
│   └── main.py            # Hauptserver
├── frontend/              # Studenten Frontend (React + Vite)
│   ├── .env              # VITE_API_URL=http://localhost:8000
│   └── src/
│       ├── App.tsx       # Hauptrouting
│       └── config.ts     # API Konfiguration (FIXED)
├── professor-dashboard/   # Professor Frontend (React + Vite)
│   ├── .env              # VITE_API_URL=http://localhost:8000
│   └── package.json      # Port 5174 (FIXED)
├── .venv/                # Python Virtual Environment
└── .env                  # Backend Konfiguration
```

## 🔧 Konfigurationsänderungen

### 1. Frontend config.ts (FIXED)
**Datei:** `/home/cedrik/AI-Tutor/frontend/src/config.ts`

**Vorher:**
```typescript
const API_URL = '';  // Leer!
```

**Nachher:**
```typescript
const API_URL = import.meta.env.VITE_API_URL || '';  // Liest .env
```

### 2. Frontend .env (FIXED)
**Datei:** `/home/cedrik/AI-Tutor/frontend/.env`
```
VITE_API_URL=http://localhost:8000
```

### 3. Professor Dashboard .env (FIXED)
**Datei:** `/home/cedrik/AI-Tutor/professor-dashboard/.env`
```
VITE_API_URL=http://localhost:8000
```

### 4. Professor Dashboard Port (FIXED)
**Datei:** `/home/cedrik/AI-Tutor/professor-dashboard/package.json`
```json
"scripts": {
  "dev": "vite --port 5174"  // Geändert von 5173 auf 5174
}
```

## 🚀 Server Management

### Alle Server stoppen
```bash
ps aux | grep -E "vite|uvicorn" | grep -v grep | awk '{print $2}' | xargs kill
```

### Backend starten
```bash
cd /home/cedrik/AI-Tutor
source .venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Studenten Frontend starten
```bash
cd /home/cedrik/AI-Tutor/frontend
npm run dev
# Läuft auf Port 5173
```

### Professor Dashboard starten
```bash
cd /home/cedrik/AI-Tutor/professor-dashboard
npm run dev
# Läuft auf Port 5174
```

### Alle gleichzeitig starten (separates Terminal für jeden)
```bash
# Terminal 1 - Backend
cd /home/cedrik/AI-Tutor && source .venv/bin/activate && uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Studenten Frontend
cd /home/cedrik/AI-Tutor/frontend && npm run dev

# Terminal 3 - Professor Dashboard
cd /home/cedrik/AI-Tutor/professor-dashboard && npm run dev
```

## 🎯 Typische Workflows

### Als Student verwenden
1. Öffne http://localhost:5173
2. Klicke "Neuen Chat starten"
3. Stelle Fragen zum Lernen

### Als Professor verwenden
1. Öffne http://localhost:5174/dashboard/
2. Logge dich ein (Registration Code: `!yAHeq2v@L59MV`)
3. Verwalte Kurse und Materialien

### API testen
1. Öffne http://localhost:8000/docs
2. Teste verschiedene Endpoints
3. Verwende "Try it out" für API Calls

## 🔍 Debugging

### Backend API prüfen
```bash
# Conversations abrufen (benötigt Cookie)
curl http://localhost:8000/api/courses

# API Docs im Browser
xdg-open http://localhost:8000/docs
```

### Frontend Logs ansehen
```bash
# Im Browser DevTools -> Console
# Oder Terminal wo npm run dev läuft
```

### Datenbank Verbindung testen
```bash
PGPASSWORD='DBTutorSecure2026' psql -U ai_tutor_prod -d ai_tutor_prod -h localhost -c "SELECT COUNT(*) FROM users;"
```

## 📊 Backend Status

### Geladene APIs
- ✅ Professor Course API
- ✅ Professor Material API
- ✅ Manual Analysis Trigger API
- ✅ Scheduler Status API
- ✅ Chat API v2
- ✅ Prompts Admin API

### LLM Konfiguration
- **Model:** moonshotai.kimi-k2.5
- **Embedding:** amazon.titan-embed-text-v2:0
- **Provider:** AWS Bedrock
- **Prompts:** 7 geladen

### Scheduler
- ✅ Daily Analysis läuft um 3:00 AM

## ⚠️ Bekannte Warnungen (nicht kritisch)

```
WARNING: Could not import auth_api: email-validator is not installed
```

**Optional beheben:**
```bash
source .venv/bin/activate
pip install 'pydantic[email]'
```

## 🔄 Unterschiede: Lokal vs. AWS Server

| Feature | Lokal | AWS Server |
|---------|-------|------------|
| Studenten Chat | http://localhost:5173 | https://tutor-ai.me |
| Professor Dashboard | http://localhost:5174/dashboard/ | https://tutor-ai.me/dashboard/ |
| Backend API | http://localhost:8000 | https://tutor-ai.me/api/ |
| Ports | 3 separate (8000, 5173, 5174) | 1 (443 HTTPS) |
| Web Server | Vite Dev Server | Nginx |
| Hot Reload | ✅ Ja | ❌ Nein |
| SSL | ❌ Nein | ✅ Ja (Let's Encrypt) |

## 🎉 Alles funktioniert!

Die Probleme wurden behoben:
1. ✅ Backend ist erreichbar
2. ✅ Chatbot zeigt "Online"
3. ✅ Professor Dashboard ist zugänglich auf Port 5174
4. ✅ Alle APIs funktionieren

**Quick Links:**
- 📚 Student: http://localhost:5173
- 👨‍🏫 Professor: http://localhost:5174/dashboard/
- 🔌 API Docs: http://localhost:8000/docs

Viel Erfolg beim Entwickeln! 🚀
