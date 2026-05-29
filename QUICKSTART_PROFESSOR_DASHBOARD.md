# Quick Start: Professor Dashboard

**Get the Professor Dashboard API running in 5 minutes!**

---

## Prerequisites

✅ PostgreSQL running (with pgvector)  
✅ Python 3.11+  
✅ AWS Bedrock API key (for LLM analysis)  

---

## Step 1: Install Dependencies

```bash
cd /home/cedrik/AI-Tutor

# Install Python packages
pip install -r requirements.txt

# Verify installation
python3 -c "import fastapi, passlib, jose; print('✅ Dependencies OK')"
```

---

## Step 2: Database Setup

```bash
# Start PostgreSQL (if using Docker)
docker-compose up -d postgres

# Wait for DB ready
sleep 5

# Initialize database (creates all tables)
python3 -c "from database import init_db; init_db()"

# Expected output: "Database initialized successfully"
```

**Alternative (if psql available):**
```bash
psql -U ai_tutor -d ai_tutor -f migrations/add_auth_and_courses.sql
```

---

## Step 3: Generate JWT Secret

```bash
# Generate secure random key
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(32))"

# Copy output and add to .env file
```

**Edit `.env`:**
```bash
# Add the generated key:
JWT_SECRET_KEY=<your-generated-key-here>

# Ensure other settings are correct:
BEDROCK_API_KEY=<your-bedrock-key>
DATABASE_URL=postgresql://ai_tutor:password@localhost:5432/ai_tutor
FILE_STORAGE_TYPE=local
FILE_STORAGE_PATH=./uploads
```

---

## Step 4: Create Uploads Directory

```bash
mkdir -p uploads/courses
```

---

## Step 5: Test Authentication

```bash
python3 test_auth.py
```

**Expected output:**
```
================================================================================
TEST 1: Password Hashing
================================================================================
Original: SecurePassword123
Hashed: $2b$12$...
✅ Password hashing works!

...

================================================================================
✅ ALL TESTS PASSED!
================================================================================
```

---

## Step 6: Start API Server

```bash
# Start Professor Dashboard API
python3 -m uvicorn api.professor:app --host 0.0.0.0 --port 8001 --reload
```

**Expected output:**
```
INFO:     Will watch for changes in these directories: ['/home/cedrik/AI-Tutor']
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
INFO:     Started reloader process
🚀 Starting Professor Dashboard API
CORS Origins: http://localhost:5173,http://localhost:3000
INFO:     Application startup complete.
```

---

## Step 7: Test API

### Open Swagger UI

Visit: **http://localhost:8001/docs**

### 1. Login as Default Admin

**Endpoint:** `POST /api/auth/login`

**Request Body:**
```json
{
  "email": "admin@ai-tutor.local",
  "password": "changeme123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "550e8400-...",
  "token_type": "bearer"
}
```

### 2. Authorize in Swagger UI

1. Click **"Authorize"** button (top right)
2. Paste `access_token` from response
3. Click **"Authorize"**
4. Click **"Close"**

### 3. Create Your First Course

**Endpoint:** `POST /api/courses`

**Request Body:**
```json
{
  "course_code": "prog2",
  "course_name": "Programmieren 2",
  "semester": "WS 2025/26",
  "academic_year": 2025,
  "description": "Advanced programming with Scala",
  "student_access": true,
  "max_lecture_number": 12
}
```

**Response:**
```json
{
  "course_id": "550e8400-...",
  "course_code": "prog2",
  "course_name": "Programmieren 2",
  ...
}
```

### 4. Upload Files for Analysis

**Endpoint:** `POST /api/courses/{course_id}/files/upload`

**Parameters:**
- `course_id`: Use the ID from step 3

**Files:**
- Upload some test files (PDFs, code files)

**Response:**
```json
{
  "upload_session_id": "...",
  "total_files": 3,
  "analyzed_files": 3,
  "status": "ready",
  "file_analyses": [
    {
      "filename": "ha01.pdf",
      "content_type": "homework",
      "importance": "hoch",
      "sequence_number": 1,
      "analysis_reason": "Hausaufgabe 1 PDF",
      "user_decision": "pending"
    },
    {
      "filename": "build.gradle",
      "content_type": "setup",
      "importance": "niedrig",
      "sequence_number": null,
      "analysis_reason": "Setup/Config-Datei (automatisch gefiltert)",
      "user_decision": "pending"
    }
  ]
}
```

**✅ LLM Pre-Analysis is working!**

---

## Step 8: Register New Professor

### 1. Register Account

**Endpoint:** `POST /api/auth/register`

**Request Body:**
```json
{
  "email": "prof@university.edu",
  "password": "SecurePassword123",
  "full_name": "Dr. Jane Smith",
  "institution": "Example University"
}
```

**Response:**
```json
{
  "user_id": "...",
  "email": "prof@university.edu",
  "full_name": "Dr. Jane Smith",
  "is_active": false,  // ⚠️ Requires admin approval!
  ...
}
```

### 2. Approve User (as Admin)

**Endpoint:** `POST /api/admin/users/{user_id}/approve`

**Note:** You need to be logged in as admin (step 7.1)

**Response:**
```json
{
  "message": "User prof@university.edu approved",
  "user": {
    "is_active": true,
    ...
  }
}
```

### 3. Login as New Professor

**Endpoint:** `POST /api/auth/login`

Use the new professor's credentials.

---

## Common Issues

### ❌ "Connection refused" to Database

**Solution:**
```bash
# Check if PostgreSQL is running
docker-compose ps

# If not, start it:
docker-compose up -d postgres

# Check logs:
docker-compose logs postgres
```

### ❌ "Table does not exist"

**Solution:**
```bash
# Run database initialization
python3 -c "from database import init_db; init_db()"
```

### ❌ "ModuleNotFoundError: No module named 'jose'"

**Solution:**
```bash
pip install python-jose[cryptography] passlib[bcrypt]
```

### ❌ "Invalid JWT"

**Solution:**
- Make sure you copied the `access_token` (not `refresh_token`)
- Token expires after 1 hour - login again
- Check JWT_SECRET_KEY in .env matches

### ❌ "File upload fails"

**Solution:**
```bash
# Check uploads directory exists and is writable
mkdir -p uploads/courses
chmod 755 uploads
```

---

## Next Steps

**Now that the backend works:**

1. ✅ **Explore API** - Try all endpoints in Swagger UI
2. ✅ **Test File Analysis** - Upload different file types
3. ✅ **Create Homework** - Use `POST /api/courses/{id}/homework`
4. ✅ **Share Course** - Use `POST /api/courses/{id}/share`

**Then:**

5. ⏳ **Build Frontend** - React dashboard
6. ⏳ **Add Analytics** - Student progress, difficulties
7. ⏳ **Deploy to AWS** - ECS + S3 + RDS

---

## API Endpoints Overview

### Authentication
- `POST /api/auth/register` - Register new professor
- `POST /api/auth/login` - Login
- `POST /api/auth/refresh` - Refresh token
- `POST /api/auth/logout` - Logout
- `GET /api/auth/me` - Current user info

### Admin
- `GET /api/admin/users/pending` - List pending users
- `POST /api/admin/users/{id}/approve` - Approve user

### Courses
- `POST /api/courses` - Create course
- `GET /api/courses` - List my courses
- `GET /api/courses/{id}` - Get course
- `PATCH /api/courses/{id}` - Update course
- `DELETE /api/courses/{id}` - Delete course
- `POST /api/courses/{id}/share` - Share course

### Homework
- `POST /api/courses/{id}/homework` - Create homework
- `GET /api/courses/{id}/homework` - List homework
- `GET /api/homework/{id}` - Get homework
- `PATCH /api/homework/{id}` - Update homework
- `DELETE /api/homework/{id}` - Delete homework

### File Upload
- `POST /api/courses/{id}/files/upload` - Upload & analyze files
- `GET /api/upload-sessions/{id}` - Get analysis results
- `POST /api/upload-sessions/{id}/confirm` - Confirm file decisions

---

## Default Admin Credentials

⚠️ **CHANGE THESE IMMEDIATELY IN PRODUCTION!**

- **Email:** `admin@ai-tutor.local`
- **Password:** `changeme123`

**To change:**
```bash
# 1. Login as admin
# 2. Use /api/auth/me to get your user_id
# 3. Update password in database:

python3 -c "
from database import SessionLocal, User
from auth import hash_password
import uuid

db = SessionLocal()
admin = db.query(User).filter(User.email == 'admin@ai-tutor.local').first()
admin.password_hash = hash_password('YourNewSecurePassword123')
db.commit()
print('✅ Admin password changed')
"
```

---

## Port Configuration

- **Professor Dashboard API:** Port 8001
- **Student Chat API:** Port 8000 (optional, from existing system)
- **PostgreSQL:** Port 5432
- **Frontend (future):** Port 5173 (Vite) or 3000 (Create React App)

---

## Logs

**API Logs:**
- Console output (stdout)
- Uvicorn logs include HTTP requests

**Audit Logs:**
- Stored in database table `audit_log`
- Query: `SELECT * FROM audit_log ORDER BY timestamp DESC;`

**File Upload Logs:**
- Check API console for "File uploaded" / "File analyzed" messages

---

## Resources

- **API Docs:** http://localhost:8001/docs
- **Health Check:** http://localhost:8001/health
- **ReDoc:** http://localhost:8001/redoc

**Documentation:**
- `PROFESSOR_DASHBOARD_PLAN.md` - Full implementation plan
- `PROFESSOR_DASHBOARD_STATUS.md` - Current status & features
- `META_ANALYSIS_SYSTEM.md` - Analytics system docs

---

**✅ You're ready to go!** 🚀

Any issues? Check the **Common Issues** section or the documentation files.
