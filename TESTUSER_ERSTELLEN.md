# Test-User für lokale Entwicklung erstellen

Da Sie die Passwörter der AWS-Server User nicht kennen, erstellen wir einen Test-User:

## Option 1: Direkt in der Datenbank erstellen

```bash
# Python Script ausführen
cd /home/cedrik/AI-Tutor
source .venv/bin/activate
python3 << 'EOF'
from database import SessionLocal, User
from auth import hash_password
import uuid

db = SessionLocal()

# Test-User erstellen
user = User(
    user_id=uuid.uuid4(),
    email="test@professor.com",
    password_hash=hash_password("test123"),
    full_name="Test Professor",
    role="professor",
    institution="Test University",
    is_active=True,
    email_verified=True
)

db.add(user)
db.commit()

print(f"✅ Test-User erstellt:")
print(f"   Email: test@professor.com")
print(f"   Password: test123")

db.close()
EOF
```

## Option 2: Über die API mit Registration Code

```bash
curl -X POST http://localhost:8000/api/auth/register-with-code \
  -H "Content-Type: application/json" \
  -d '{
    "access_code": "!yAHeq2v@L59MV",
    "email": "test@professor.com",
    "password": "Test123!",
    "password_confirm": "Test123!",
    "full_name": "Test Professor",
    "institution": "Test University"
  }'
```

## Login Credentials

Nach Erstellung eines der beiden User können Sie sich einloggen mit:

- **Email:** test@professor.com
- **Password:** test123 (Option 1) oder Test123! (Option 2)

## Professor Dashboard Login

1. Öffne: http://localhost:5174/dashboard/
2. Oder direkt: http://localhost:5174/dashboard/login
3. Email: test@professor.com
4. Password: test123 (oder Test123!)
