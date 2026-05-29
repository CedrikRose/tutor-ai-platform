# AI-Tutor

AI-assisted tutoring system for programming courses using RAG (Retrieval-Augmented Generation).

## Features

- 🤖 **Intelligent Chat Tutor** powered by Claude (AWS Bedrock)
- 📚 **RAG-based Knowledge Base** compiled from course materials
- 📄 **Automatic Material Parsing** (PDFs, code files)
- 👨‍🏫 **Professor Dashboard** for managing courses & materials
- 👨‍🎓 **Student Frontend** for interactive chat sessions
- 📊 **Conversation Analytics** & learning insights
- 🔐 **Secure Authentication** via JWT

## Architecture

### Backend
- **FastAPI** server (Python 3.12)
- **PostgreSQL 16** with pgvector for embeddings
- **AWS Bedrock** (Claude 4.5 Sonnet, Titan Embeddings)
- **LlamaParse** for PDF processing

### Frontend
- **Student Frontend:** React + Vite + TypeScript
- **Professor Dashboard:** React + Vite + TypeScript

## Quick Start (Local)

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16 with pgvector
- AWS Bedrock access
- LlamaParse API Key

### Installation

```bash
# Clone repository
git clone <your-repo-url>
cd AI-Tutor

# Configure environment
cp .env.template .env
nano .env  # Fill in API keys

# Python dependencies
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Initialize database
python migrations/init_db.py

# Start backend
cd api
uvicorn main:app --reload

# Student Frontend (new terminal)
cd frontend
npm install
npm run dev

# Professor Dashboard (new terminal)
cd professor-dashboard
npm install
npm run dev
```

### Access

- Student Frontend: http://localhost:5173
- Professor Dashboard: http://localhost:5174
- API Docs: http://localhost:8000/docs

## AWS Deployment

### Quick Start

For EC2 Ubuntu 26 LTS deployment:

```bash
# 1. On EC2: Server setup
./deploy/setup_ec2.sh

# 2. Locally: Copy code
rsync -avz --exclude='.venv' --exclude='node_modules' \
  -e "ssh -i key.pem" . ubuntu@EC2_IP:/opt/ai-tutor/

# 3. On EC2: Configure environment
cd /opt/ai-tutor
cp deploy/.env.production.template .env
nano .env

# 4. On EC2: Installation
./deploy/install_app.sh
```

**Full Guide:** See `DEPLOYMENT_QUICKSTART.md` or `deploy/DEPLOYMENT_FULL.md`

### Available after deployment

- Student Frontend: http://YOUR_EC2_IP/
- Professor Dashboard: http://YOUR_EC2_IP:8080/
- API: http://YOUR_EC2_IP:8000/docs

## Project Structure

```
AI-Tutor/
├── api/                          # FastAPI Backend
│   ├── main.py                   # Main API entry point
│   ├── chat_api_v2.py           # WebSocket Chat API
│   ├── auth_api.py              # Authentication
│   ├── professor_*.py           # Professor Endpoints
│   └── ...
├── frontend/                     # Student React App
│   ├── src/
│   └── dist/                    # Build output
├── professor-dashboard/          # Professor React App
│   ├── src/
│   └── dist/                    # Build output
├── migrations/                   # Database migrations
│   └── init_db.py
├── deploy/                       # Deployment scripts
│   ├── setup_ec2.sh             # EC2 server setup
│   ├── install_app.sh           # App installation
│   ├── update.sh                # Update script
│   └── DEPLOYMENT_FULL.md       # Complete deployment guide
├── database.py                   # SQLAlchemy models
├── config.py                     # Configuration
├── llm.py                        # LLM integration
├── rag.py                        # RAG retriever
├── embeddings.py                 # Embedding generation
├── material_processor.py         # Material processor
├── auth.py                       # Auth utilities
├── requirements.txt              # Python dependencies
├── .env.template                 # Environment template
└── README.md                     # This file
```

## Key Components

### Material Processing Pipeline

1. **Upload:** Professor uploads PDFs or code files.
2. **Parsing:** 
   - PDFs → LlamaParse → Text chunks
   - Code → Tree-sitter → Semantic chunks
3. **Embeddings:** AWS Titan Embeddings
4. **Storage:** PostgreSQL with pgvector

### RAG Chat Flow

1. Student asks a question.
2. Query → Embedding.
3. Vector search within material chunks.
4. Context + question → Claude.
5. Answer returned to student.

### Professor Dashboard

- Create & manage courses
- Upload materials
- Monitor processing status
- View chat analytics
- Generate email reports

### Student Frontend

- Select course
- Start chat sessions
- Ask questions about materials
- View chat history

## API Endpoints

### Public

- `POST /api/auth/register` - Professor registration
- `POST /api/auth/login` - Login
- `GET /api/courses/public` - Public courses

### Protected (Professor)

- `GET/POST/PUT/DELETE /api/professor/courses` - Course management
- `POST /api/professor/materials/upload` - Material upload
- `GET /api/professor/analytics/*` - Analytics

### Protected (Student)

- `WS /api/v2/ws/{session_id}` - Chat WebSocket
- `GET /api/v2/chat/sessions` - Chat sessions
- `POST /api/v2/chat/sessions` - New session

## Development

### Backend Development

```bash
# With auto-reload
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

### Database Migrations

```bash
# Create a new migration
cd migrations
# Create a new .py file with the migration

# Run migration
PYTHONPATH=/home/cedrik/AI-Tutor python migrations/your_migration.py
```

### Tests

```bash
# Backend tests
pytest

# Frontend tests
cd frontend
npm test

cd professor-dashboard
npm test
```

## Configuration

### Environment Variables

See `.env.template` for all available options.

Most Important:

```bash
# Database
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

### Local

```bash
# Backend Logs
# See console output

# Frontend Logs
# Browser DevTools console
```

### Production (EC2)

```bash
# API logs
sudo journalctl -u ai-tutor-api -f
sudo tail -f /var/log/ai-tutor-api.log

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# PostgreSQL logs
sudo journalctl -u postgresql -f
```

## Backups

### Database Backup

```bash
# Manual
pg_dump ai_tutor_prod > backup_$(date +%Y%m%d).sql

# Automatic (Cron)
# See deploy/DEPLOYMENT_FULL.md
```

## Troubleshooting

### Backend fails to start

- Check `.env` configuration
- Check database connection
- See logs: `tail -f api.log`

### Frontend build error

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Database Migration Error

```bash
# Reset (WARNING: Deletes all data!)
python migrations/init_db.py --reset

# Or manual:
psql -U ai_tutor -d ai_tutor_dev
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
```

## Support

- 📧 Email: cedrik.rosemann@tutor-ai.me
- 📖 Documentation: `deploy/DEPLOYMENT_FULL.md`

## 📝 License

This project is licensed under CC BY-NC-ND 4.0.

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
