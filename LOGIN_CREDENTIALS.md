# 🔐 Login Credentials für lokale Entwicklung

## ✅ Test-Account erstellt!

### Professor Dashboard Login

**URL:** http://localhost:5174/dashboard/login

**Credentials:**
- **Email:** `dev@test.com`
- **Password:** `DevTest123!`

## Alternative Registration

Falls Sie einen weiteren Account erstellen möchten:

### Via Browser
1. Öffne: http://localhost:5174/dashboard/register
2. Verwende Registration Code: `!yAHeq2v@L59MV`

### Via API
```bash
curl -X POST http://localhost:8000/api/auth/register-with-code \
  -H "Content-Type: application/json" \
  -d '{
    "access_code": "!yAHeq2v@L59MV",
    "email": "ihre@email.com",
    "password": "IhrPasswort123!",
    "password_confirm": "IhrPasswort123!",
    "full_name": "Ihr Name",
    "institution": "Ihre Institution"
  }'
```

## 🎓 Studenten Chat

**URL:** http://localhost:5173

Keine Anmeldung erforderlich - direkt loslegen!

## 🔧 Backend API

**API Docs:** http://localhost:8000/docs

Zum Testen der API verwenden Sie den Access Token aus der Login-Response.

## ⚠️ Hinweis zu AWS Datenbank-Usern

Die User aus der AWS Produktionsdatenbank (z.B. `david.bermbach@tu-berlin.de`) haben Passwörter, die lokal nicht funktionieren, da sie beim Import probleme mit bcrypt verursachen. 

Verwenden Sie stattdessen die neu erstellten lokalen Test-Accounts.

## 🐛 Problem behoben

Das bcrypt-Problem wurde gelöst durch:
1. Direkten Einsatz von bcrypt (statt passlib)
2. Explizites Truncating von Passwörtern > 72 Bytes
3. Besseres Error Handling

Neue User können jetzt problemlos erstellt und authentifiziert werden!
