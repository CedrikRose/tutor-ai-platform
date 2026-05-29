# AI Tutor - Datenbankschema

## Überblick

**Eine zentrale PostgreSQL Datenbank** mit pgvector Extension für Vektor-Embeddings.

```
┌─────────────────────────────────────────┐
│     PostgreSQL (Port 5432)              │
│     Datenbank: ai_tutor                 │
│     Extension: pgvector                 │
└─────────────────────────────────────────┘
          ↑              ↑
          │              │
    Backend API    Material Processor
    (Port 8000)    (Background Jobs)
```

## Tabellen-Struktur (34 Tabellen)

### 🎓 1. Professor & Kursverwaltung (7 Tabellen)

#### `users` - Professor-Accounts
- `user_id` (UUID, PK)
- `email` (unique)
- `password_hash`
- `full_name`, `institution`
- `role` (professor, admin)
- `is_active` (muss von Admin freigegeben werden)
- `email_verified`

**Beziehungen:**
- Hat viele Kurse (`owned_courses`)
- Hat viele Refresh Tokens (`refresh_tokens`)
- Hat Kurs-Permissions (`course_permissions`)

#### `courses` - Kurse
- `course_id` (UUID, PK)
- `course_code` (z.B. "CS101")
- `course_name` (z.B. "Programmierung 2")
- `semester`, `academic_year`
- `owner_user_id` → `users.user_id` (FK)
- `is_active`, `student_access`
- `max_lecture_number`

**Beziehungen:**
- Gehört zu einem Professor (`owner`)
- Hat viele Materials (`course_materials`)
- Hat viele Hausaufgaben (`homeworks`)
- Hat viele Sessions (`chat_sessions`)

#### `course_permissions` - Kurs-Zugriff teilen
- `permission_id` (UUID, PK)
- `course_id` → `courses.course_id` (FK)
- `user_id` → `users.user_id` (FK)
- `permission_level` (owner, editor, viewer)
- `granted_by` → `users.user_id` (FK)

**Use Case:** Professor kann Kurs mit Assistenten teilen

#### `course_materials` - Kursmaterialien
- `material_id` (UUID, PK)
- `course_id` → `courses.course_id` (FK)
- `uploaded_by` → `users.user_id` (FK)
- `material_type` (lecture_slide, homework, tutorium, other)
- `display_name` (z.B. "Vorlesung 3")
- `sequence_number` (für Sortierung)
- `file_count` (Anzahl Dateien)
- `pending_review` (Boolean, 1h Review-Period)
- `review_deadline` (Timestamp)
- `processed_at` (Wann wurde verarbeitet)

**Beziehungen:**
- Hat viele Dateien (`files` → `material_files`)
- Hat viele Chunks (`material_chunks`)

#### `material_files` - Einzelne Dateien pro Material
- `file_id` (UUID, PK)
- `material_id` → `course_materials.material_id` (FK)
- `filename`, `file_path`, `file_size`

**Beziehungen:**
- Gehört zu einem Material (`material`)

#### `homeworks` - Hausaufgaben
- `homework_id` (UUID, PK)
- `course_id` → `courses.course_id` (FK)
- `homework_code` (z.B. "HA01")
- `title`, `description`
- `sequence_number`
- `start_date`, `due_date`
- `max_points`
- `is_published`

#### `homework_documents` - Verknüpfung Hausaufgabe ↔ Dokumente
- `homework_document_id` (UUID, PK)
- `homework_id` → `homeworks.homework_id` (FK)
- `doc_id` → `documents.doc_id` (FK)

---

### 📚 2. Dokumente & RAG System (8 Tabellen)

#### `parsing_jobs` - Parsing-Job Tracking
- `job_id` (UUID, PK)
- `name`
- `total_documents`, `completed_documents`, `failed_documents`
- `status` (pending, in_progress, completed)

#### `documents` - Geparste Dokumente
- `doc_id` (UUID, PK)
- `job_id` → `parsing_jobs.job_id` (FK)
- `file_path`, `file_name`, `file_size_bytes`
- `file_type` (pdf, c, java, scala)
- `course_module`, `content_type`
- `sequence_number`

**Beziehungen:**
- Hat einen Parsing-Status (`parsing_state`)
- Hat viele Chunks (`chunks` → `parsed_chunks`)

#### `parsing_state` - Parsing-Status pro Dokument
- `state_id` (UUID, PK)
- `doc_id` → `documents.doc_id` (FK)
- `status` (pending, in_progress, completed, failed)
- `attempt_count`, `max_attempts`
- `last_error`, `llama_parse_job_id`

#### `parsed_chunks` - Text-Chunks aus Dokumenten
- `chunk_id` (UUID, PK)
- `doc_id` → `documents.doc_id` (FK)
- `chunk_index`, `chunk_type`
- `content` (Text)
- `token_count`

**Beziehungen:**
- Hat ein Embedding (`embedding` → `chunk_embeddings`)

#### `chunk_embeddings` - Vektor-Embeddings für RAG
- `embedding_id` (UUID, PK)
- `chunk_id` → `parsed_chunks.chunk_id` (FK)
- `embedding` **Vector(1024)** ← pgvector!
- `model_id` (amazon.titan-embed-text-v2:0)

**Index:** IVFFlat Index für schnelle Vektor-Suche (cosine similarity)

#### `material_chunks` - Chunks aus Course Materials
- `chunk_id` (UUID, PK)
- `material_id` → `course_materials.material_id` (FK)
- `file_id` → `material_files.file_id` (FK)
- `content` (Text)
- `chunk_index`
- `embedding` **Vector(1024)** ← pgvector!
- `source_type` (pdf, code, text)

**Wichtig:** Das ist der Haupt-RAG Speicher für Kursmaterialien!

#### `material_processing_log` - Processing-Logs
- `log_id` (UUID, PK)
- `material_id` → `course_materials.material_id` (FK)
- `stage` (file_analysis, parsing, chunking, embedding)
- `status` (started, completed, failed)
- `message`, `details` (JSONB)

#### `file_upload_sessions` & `file_pre_analysis`
Upload-Sessions mit LLM Pre-Analysis (erkennt Material-Typ automatisch)

---

### 💬 3. Chat System (3 Tabellen)

#### `chat_sessions` - Chat-Sitzungen
- `session_id` (UUID, PK)
- `cookie_id` (Browser Cookie, kein Login nötig!)
- `course_id` → `courses.course_id` (FK)
- `course_module` (DEPRECATED)
- `homework_id`, `lecture_number`
- `max_lecture_sequence` (Content Gating!)
- `material_types` (JSONB Array: welche Material-Typen?)
- `selected_material_id` → `course_materials.material_id` (FK)
- `title`, `message_count`, `total_tokens`

**Beziehungen:**
- Hat viele Messages (`messages` → `chat_messages`)
- Hat viele Snapshots (`chat_snapshots`)

#### `chat_messages` - Einzelne Chat-Nachrichten
- `message_id` (UUID, PK)
- `session_id` → `chat_sessions.session_id` (FK)
- `role` (user, assistant)
- `content` (Text)
- `timestamp`
- `tokens_used`
- `rag_chunks` (JSONB - welche Chunks wurden verwendet)

**Wichtig:** RAG-Context wird gespeichert, aber NICHT an User gezeigt!

#### `conversation_exports` - Export Tracking
- `export_id` (UUID, PK)
- `export_date` (Date, unique)
- `sessions_exported`, `messages_exported`
- `status`

---

### 📊 4. Analyse System (6 Tabellen)

#### `chat_snapshots` - Tägliche Chat-Snapshots
- `snapshot_id` (UUID, PK)
- `session_id` → `chat_sessions.session_id` (FK)
- `snapshot_date` (Datum des Snapshots)
- `created_at` (4 AM Zeitpunkt)
- `from_message_id`, `to_message_id` (Message Range)
- `message_count`
- `chat_content` (Formatierter Chat-Text)
- `course_id` → `courses.course_id` (FK)
- `cookie_id`
- `analysis_status` (pending, analyzing, completed, error)
- `analyzed_at`

**Use Case:** Um 4 AM werden Snapshots erstellt von neuen Messages

#### `conversation_analyses` - LLM Analyse-Ergebnisse
- `analysis_id` (UUID, PK)
- `snapshot_id` → `chat_snapshots.snapshot_id` (FK)
- `session_id` → `chat_sessions.session_id` (FK)
- `analyzed_at`
- `primary_model` (minimax.minimax-m2.5)
- `secondary_model` (moonshotai.kimi-k2.5, optional)
- `required_secondary` (Boolean)
- `analysis_text` (Voller LLM-Output)
- `message_count`, `tokens_used`
- `course_id` → `courses.course_id` (FK)

**Use Case:** Eine Analyse pro Snapshot, enthält komplette LLM-Antwort

#### `student_knowledge` - Extrahiertes Wissen
- `knowledge_id` (UUID, PK)
- `analysis_id` → `conversation_analyses.analysis_id` (FK)
- `session_id` → `chat_sessions.session_id` (FK)
- `cookie_id`
- `understood_concepts` (Array of Text)
- `struggled_concept` (String)
- `error_description` (Text)
- `solution_description` (Text)
- `reference_message_ids` (Array of UUIDs - MSG-3, MSG-5)

**Use Case:** Strukturierte Daten aus Analyse extrahiert

#### `general_feedback` - Professor-Feedback
- `feedback_id` (UUID, PK)
- `analysis_id` → `conversation_analyses.analysis_id` (FK)
- `session_id` → `chat_sessions.session_id` (FK)
- `feedback_type` (professor_explanation, tutor_behavior, material_quality)
- `feedback_text` (Text)
- `sentiment` (positive, negative, neutral)
- `reference_message_ids` (Array of UUIDs)
- `course_id` → `courses.course_id` (FK)

**Use Case:** Feedback über Erklärungen, Material-Qualität etc.

#### `course_summaries` - Generierte Zusammenfassungen
- `summary_id` (UUID, PK)
- `course_id` → `courses.course_id` (FK)
- `start_date`, `end_date`, `days_back`
- `summary_text` (Text)
- `statistics` (JSONB)
- `generated_at`
- `generated_by` (system, professor_manual, automation)

**Use Case:** 1-7 Tage Zusammenfassungen für Professor

#### `email_automations` - Email-Automatisierung
- `automation_id` (UUID, PK)
- `course_id` → `courses.course_id` (FK)
- `professor_id` → `users.user_id` (FK)
- `enabled` (Boolean)
- `days_back` (Alle X Tage → Summary der letzten X Tage)
- `send_time_hour` (Immer 8 AM)
- `recipient_emails` (Array of Strings)
- `last_sent_at`

**Use Case:** Automatischer Email-Versand alle X Tage um 8 AM

---

### 🔒 5. Authentifizierung (2 Tabellen)

#### `refresh_tokens` - JWT Refresh Tokens
- `token_id` (UUID, PK)
- `user_id` → `users.user_id` (FK)
- `token_hash`
- `expires_at` (7 Tage)
- `created_at`, `last_used_at`
- `user_agent`, `ip_address`
- `is_revoked`, `revoked_at`

**Use Case:** Refresh Token für Access Token Erneuerung

#### `audit_log` - Security Audit Log
- `log_id` (UUID, PK)
- `user_id` → `users.user_id` (FK)
- `timestamp`
- `action`, `resource_type`, `resource_id`
- `details` (JSONB)
- `ip_address`, `user_agent`

---

### 📈 6. Analytics & Aggregation (8 Tabellen)

Legacy Tabellen für Aggregation (teilweise deprecated):

- `topics` - Master-Liste von Topics
- `difficulty_types` - Fehler-Typen
- `session_difficulties` - **DEPRECATED, use student_knowledge**
- `feedback_entries` - Legacy Feedback
- `learning_progress` - Pro-Student Fortschritt
- `error_patterns` - Wiederkehrende Fehler
- `difficulty_embeddings` - Vektor-Embeddings für Fehler
- `feedback_embeddings` - Vektor-Embeddings für Feedback
- `daily_stats` - Tägliche Statistiken
- `email_logs` - Email-Versand Log

---

## Datenbankverbindungen

### In Docker Compose (Lokal)

```yaml
# docker-compose.yml
services:
  postgres:
    image: pgvector/pgvector:pg16
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: your_password
      POSTGRES_DB: ai_tutor
```

### In Backend (FastAPI)

```python
# config.py
DATABASE_URL = "postgresql://postgres:password@postgres:5432/ai_tutor"

# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    """FastAPI Dependency für DB-Session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# In API Endpoints
@router.get("/courses")
def get_courses(db: Session = Depends(get_db)):
    courses = db.query(Course).all()
    return courses
```

### In Production (AWS)

```yaml
# docker-compose.prod.yml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    environment:
      DATABASE_URL: postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/ai_tutor
```

**Wichtig:** Postgres Container ist NICHT von außen erreichbar, nur Backend-Container!

---

## Haupt-Datenflüsse

### 1. Material Upload Flow

```
Professor Dashboard
  ↓ POST /api/professor/courses/{id}/materials/upload
Backend (professor_material_api.py)
  ↓ INSERT INTO course_materials
  ↓ INSERT INTO material_files
PostgreSQL
  ↓ Background Task
MaterialProcessor
  ↓ PDF Parsing
  ↓ Chunking
  ↓ AWS Bedrock Embeddings
  ↓ INSERT INTO material_chunks (mit Vector)
PostgreSQL
```

### 2. Student Chat Flow

```
Student Frontend
  ↓ POST /api/chat
Backend (main.py)
  ↓ SELECT FROM material_chunks WHERE <vector similarity>
PostgreSQL (pgvector IVFFlat Index)
  ↓ Top-K Chunks
Backend
  ↓ AWS Bedrock (Kimi K2.5)
  ↓ INSERT INTO chat_messages
PostgreSQL
```

### 3. Daily Analysis Flow (4 AM Cron)

```
Cron Job (analysis_cron.py)
  ↓ SELECT sessions mit neuen Messages
PostgreSQL
  ↓ CREATE chat_snapshots
  ↓ Formatiere Chat-Content
PostgreSQL
  ↓ Für jeden Snapshot
Backend (daily_chat_analysis.py)
  ↓ AWS Bedrock (Minimax M2.5)
  ↓ INSERT INTO conversation_analyses
  ↓ Parse LLM Output
  ↓ INSERT INTO student_knowledge
  ↓ INSERT INTO general_feedback
PostgreSQL
```

### 4. Manual Analysis Trigger

```
Professor Dashboard (ManualAnalysisTrigger.tsx)
  ↓ POST /api/professor/trigger-analysis
Backend (manual_analysis_trigger.py)
  ↓ SnapshotCreator.create_daily_snapshots()
  ↓ ChatAnalyzer.analyze_pending_snapshots()
  ↓ AnalysisImporter.import_analysis()
PostgreSQL (idempotent - keine Duplikate!)
```

---

## Wichtige Indizes

### Vektor-Indizes (pgvector)
```sql
CREATE INDEX idx_chunk_embeddings_vector 
  ON chunk_embeddings 
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

CREATE INDEX idx_material_chunks_embedding
  ON material_chunks
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

### Häufige Queries
```sql
-- Vektor-Suche (RAG)
SELECT content, embedding <=> query_embedding AS distance
FROM material_chunks
WHERE material_id IN (...)
ORDER BY distance
LIMIT 5;

-- Pending Snapshots
SELECT * FROM chat_snapshots
WHERE analysis_status = 'pending'
ORDER BY created_at;

-- Student Knowledge by Course
SELECT * FROM student_knowledge sk
JOIN conversation_analyses ca ON sk.analysis_id = ca.analysis_id
WHERE ca.course_id = ?;
```

---

## Schema Evolution

### Bereits durchgeführte Migrationen
1. Initial Schema (parsing_jobs, documents, chat_sessions)
2. Professor Dashboard (users, courses, course_materials)
3. Analysis System (chat_snapshots, conversation_analyses, student_knowledge)

### Migration Command
```bash
# PostgreSQL direkt
psql -h localhost -U postgres -d ai_tutor -f migrations/add_analysis_tables.sql

# In Docker
cat migrations/add_analysis_tables.sql | docker exec -i ai-tutor-postgres psql -U postgres -d ai_tutor
```

---

## Connection Pooling

```python
engine = create_engine(
    DATABASE_URL,
    pool_size=10,        # 10 permanente Connections
    max_overflow=20,     # + 20 temporäre = max 30
    pool_pre_ping=True,  # Test Connection vor Verwendung
    echo=False           # SQL Logging aus
)
```

**Production Empfehlung:**
- `pool_size=20` für hohe Last
- `max_overflow=40`
- Connection Timeout: 30s

---

## Backup & Recovery

### Backup
```bash
# Vollbackup
docker exec ai-tutor-postgres pg_dump -U postgres ai_tutor > backup.sql

# Nur Schema
docker exec ai-tutor-postgres pg_dump -U postgres --schema-only ai_tutor > schema.sql

# Nur Daten
docker exec ai-tutor-postgres pg_dump -U postgres --data-only ai_tutor > data.sql
```

### Restore
```bash
cat backup.sql | docker exec -i ai-tutor-postgres psql -U postgres ai_tutor
```

### Production: Automated Daily Backups
```bash
# Cron: Jeden Tag um 2 AM
0 2 * * * docker exec ai-tutor-postgres pg_dump -U postgres ai_tutor | gzip > /backups/ai_tutor_$(date +\%Y\%m\%d).sql.gz
```

---

## Monitoring Queries

```sql
-- Aktive Connections
SELECT count(*) FROM pg_stat_activity;

-- Datenbank Größe
SELECT pg_size_pretty(pg_database_size('ai_tutor'));

-- Tabellen Größen
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Index Usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan;

-- Slow Queries (requires pg_stat_statements extension)
SELECT query, calls, mean_exec_time, max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```
