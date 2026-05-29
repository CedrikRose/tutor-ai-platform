# AI-Tutor AWS Deployment - Vollständige Anleitung

Detaillierte Schritt-für-Schritt Anleitung zum Deployment auf AWS EC2.

## Überblick

Diese Anwendung besteht aus:
- **Backend API:** FastAPI Server (Port 8000)
- **Student Frontend:** React/Vite App (Port 80 via Nginx)
- **Professor Dashboard:** React/Vite App (Port 8080 via Nginx)
- **Datenbank:** PostgreSQL 16 mit pgvector

## Voraussetzungen

### AWS
- EC2 Instance (Ubuntu 26 LTS)
- Empfohlene Größe: t3.small oder größer
- Mindestens 20 GB Speicher
- SSH Key Pair

### API Keys
- AWS Bedrock API Zugangsdaten (für Claude & Titan Embeddings)
- LlamaParse API Key (für PDF Parsing)

### Lokal
- SSH Client
- rsync (für Code-Transfer)

## Schritt 1: EC2 Instance erstellen

1. In AWS Console → EC2 → Launch Instance
2. Wähle **Ubuntu 26.04 LTS**
3. Instance Type: **t3.small** (minimum)
4. Key Pair: Erstelle oder wähle einen Key
5. Network Settings:
   - Erstelle neue Security Group oder wähle existierende
   - Füge Inbound Rules hinzu (siehe unten)

### Security Group Rules

| Type       | Protocol | Port Range | Source    | Description          |
|------------|----------|------------|-----------|----------------------|
| SSH        | TCP      | 22         | Deine IP  | SSH Zugriff         |
| HTTP       | TCP      | 80         | 0.0.0.0/0 | Student Frontend    |
| Custom TCP | TCP      | 8080       | 0.0.0.0/0 | Professor Dashboard |
| Custom TCP | TCP      | 8000       | 0.0.0.0/0 | API (Debug, optional)|

⚠️ **Sicherheit:** Für Produktion Port 22 nur auf deine IP beschränken!

6. Storage: 20 GB (Standard)
7. Launch Instance

## Schritt 2: Mit EC2 verbinden

```bash
# SSH Key Berechtigungen setzen
chmod 400 ~/Downloads/dein-ec2-key.pem

# Mit EC2 verbinden (ersetze mit deiner Public IP)
ssh -i ~/Downloads/dein-ec2-key.pem ubuntu@12.34.56.78
```

## Schritt 3: Server Setup

Auf dem EC2 Server, kopiere das `setup_ec2.sh` Skript vom lokalen Rechner:

```bash
# Von deinem lokalen Rechner
scp -i ~/Downloads/dein-ec2-key.pem \
    /home/cedrik/AI-Tutor/deploy/setup_ec2.sh \
    ubuntu@12.34.56.78:~
```

Dann auf EC2:

```bash
chmod +x setup_ec2.sh
./setup_ec2.sh
```

Das Skript installiert:
- ✅ Python 3.12
- ✅ Node.js 20
- ✅ PostgreSQL 16 mit pgvector
- ✅ Nginx
- ✅ Git, build-essential, etc.

**⚠️ WICHTIG:** Das Skript generiert ein zufälliges Datenbank-Passwort.
Kopiere und speichere es sicher! Du brauchst es für die .env Datei.

Beispiel Output:
```
================================================================
Database Password: AbC123XyZ456...
================================================================
Add this to your .env file:
DATABASE_URL=postgresql://ai_tutor_prod:AbC123XyZ456...@localhost/ai_tutor_prod
```

## Schritt 4: Code auf EC2 kopieren

Von deinem lokalen Rechner:

```bash
# Mit rsync (empfohlen)
rsync -avz \
  --exclude='.venv' \
  --exclude='node_modules' \
  --exclude='.env' \
  --exclude='uploads' \
  --exclude='*.pid' \
  --exclude='*.log' \
  --exclude='.idea' \
  --exclude='__pycache__' \
  --exclude='.git' \
  -e "ssh -i ~/Downloads/dein-ec2-key.pem" \
  /home/cedrik/AI-Tutor/ \
  ubuntu@12.34.56.78:/opt/ai-tutor/
```

Dieser Befehl:
- Kopiert alle Dateien nach `/opt/ai-tutor/`
- Schließt node_modules und venv aus (werden neu erstellt)
- Behält Berechtigungen bei

**Alternative: Git**

Falls du ein Git Repository hast:

```bash
# Auf EC2
cd /opt/ai-tutor
git clone https://github.com/DEIN_REPO/AI-Tutor.git .
```

## Schritt 5: Umgebungsvariablen konfigurieren

Auf dem EC2 Server:

```bash
cd /opt/ai-tutor

# Template kopieren
cp deploy/.env.production.template .env

# Bearbeiten
nano .env
```

### Erforderliche Konfiguration

Fülle folgende Werte ein:

```bash
# 1. Datenbank (Passwort aus Schritt 3!)
DATABASE_URL=postgresql://ai_tutor_prod:DEIN_DB_PASSWORT@localhost/ai_tutor_prod

# 2. AWS Bedrock
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=DEIN_AWS_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=DEIN_AWS_SECRET_KEY

# 3. LlamaParse
LLAMA_CLOUD_API_KEY=DEIN_LLAMAPARSE_KEY

# 4. JWT Secret (generieren mit: openssl rand -base64 32)
JWT_SECRET_KEY=GENERIERTER_JWT_SECRET

# 5. Professor Registrierungs-Code (wähle einen sicheren Code)
PROFESSOR_REGISTRATION_CODE=DEIN_SICHERER_CODE

# 6. CORS Origins (füge deine EC2 IP hinzu)
CORS_ORIGINS=http://localhost:3000,http://12.34.56.78,http://12.34.56.78:8080
```

Speichern mit `Ctrl+O`, `Enter`, `Ctrl+X`

### Optional: Email Konfiguration

Für Email-Benachrichtigungen:

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=deine-email@gmail.com
SMTP_PASSWORD=dein-app-passwort
SMTP_FROM=deine-email@gmail.com
```

## Schritt 6: Application installieren

```bash
cd /opt/ai-tutor
chmod +x deploy/install_app.sh
./deploy/install_app.sh
```

Dieses Skript führt aus:

1. ✅ Erstellt Python Virtual Environment
2. ✅ Installiert Python Dependencies (aus requirements.txt)
3. ✅ Initialisiert Datenbank-Schema
4. ✅ Installiert Frontend Dependencies (npm install)
5. ✅ Baut Student Frontend
6. ✅ Baut Professor Dashboard
7. ✅ Konfiguriert Nginx (Reverse Proxy + Static Files)
8. ✅ Erstellt Systemd Service (ai-tutor-api.service)
9. ✅ Startet alle Services

Das dauert ca. 5-10 Minuten.

## Schritt 7: Installation überprüfen

### Services Status

```bash
# API Service
sudo systemctl status ai-tutor-api

# Sollte zeigen: "Active: active (running)"

# Nginx
sudo systemctl status nginx

# Sollte auch "active (running)" sein
```

### Logs ansehen

```bash
# API Logs (live)
sudo journalctl -u ai-tutor-api -f

# Oder:
sudo tail -f /var/log/ai-tutor-api.log

# Nginx Logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Ports prüfen

```bash
# Sollte Services auf 8000 und 80/8080 zeigen
sudo netstat -tulpn | grep LISTEN
```

## Schritt 8: Anwendung testen

### Im Browser öffnen

Ersetze `12.34.56.78` mit deiner EC2 Public IP:

- **Student Frontend:** http://12.34.56.78/
- **Professor Dashboard:** http://12.34.56.78:8080/
- **API Dokumentation:** http://12.34.56.78:8000/docs

### Ersten Professor Account erstellen

1. Öffne Professor Dashboard: http://12.34.56.78:8080/
2. Klicke auf "Registrieren"
3. Fülle Formular aus:
   - Name, Email, Passwort
   - **Registrierungs-Code:** Aus deiner .env (`PROFESSOR_REGISTRATION_CODE`)
4. Registriere Account
5. Logge dich ein

### Kurs und Materialien hochladen

1. Im Professor Dashboard → "Kurse"
2. Erstelle neuen Kurs
3. Lade Materialien hoch (PDFs, Code-Dateien)
4. Materialien werden automatisch verarbeitet

### Student Zugang testen

1. Öffne Student Frontend: http://12.34.56.78/
2. Wähle Kurs
3. Starte Chat
4. Stelle Fragen zu hochgeladenen Materialien

## Troubleshooting

### Problem: API startet nicht

```bash
# Logs ansehen
sudo journalctl -u ai-tutor-api -n 100

# Häufige Ursachen:
# - .env nicht korrekt konfiguriert
# - Datenbank-Verbindung fehlgeschlagen
# - Python Dependencies fehlen

# Service neu starten
sudo systemctl restart ai-tutor-api
```

### Problem: Datenbank-Verbindungsfehler

```bash
# PostgreSQL Status
sudo systemctl status postgresql

# Verbindung testen
psql -U ai_tutor_prod -d ai_tutor_prod -h localhost
# Passwort eingeben (aus .env)

# In psql:
\dt  # List tables
\q   # Quit
```

### Problem: Frontend zeigt "Cannot connect to API"

```bash
# Prüfe ob API läuft
curl http://localhost:8000/docs

# Nginx Logs
sudo tail -f /var/log/nginx/error.log

# Nginx Config testen
sudo nginx -t

# Nginx neu starten
sudo systemctl restart nginx
```

### Problem: Build-Fehler bei Frontend

```bash
# Frontend neu bauen
cd /opt/ai-tutor/frontend
npm install
npm run build

# Dashboard neu bauen
cd /opt/ai-tutor/professor-dashboard
npm install
npm run build

# Nginx neu laden
sudo systemctl reload nginx
```

### Problem: "Permission Denied" Fehler

```bash
# Prüfe Besitzer
ls -la /opt/ai-tutor

# Sollte ubuntu:ubuntu sein
# Falls nicht, korrigieren:
sudo chown -R ubuntu:ubuntu /opt/ai-tutor

# Auch für uploads
sudo chown -R ubuntu:ubuntu /opt/ai-tutor/uploads
```

## Updates durchführen

### Code aktualisieren

```bash
cd /opt/ai-tutor

# Falls Git verwendet:
git pull

# Falls rsync verwendet:
# (rsync Befehl von oben auf lokalem Rechner ausführen)
```

### Backend aktualisieren

```bash
cd /opt/ai-tutor
source .venv/bin/activate

# Dependencies aktualisieren
pip install -r requirements.txt

# Service neu starten
sudo systemctl restart ai-tutor-api
```

### Frontend aktualisieren

```bash
cd /opt/ai-tutor/frontend
npm install
npm run build

cd /opt/ai-tutor/professor-dashboard
npm install
npm run build

# Nginx neu laden
sudo systemctl reload nginx
```

## Datenbank Backups

### Manuelles Backup

```bash
# Backup erstellen
sudo -u postgres pg_dump ai_tutor_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# Mit Kompression
sudo -u postgres pg_dump ai_tutor_prod | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Backup wiederherstellen

```bash
# Aus SQL File
sudo -u postgres psql ai_tutor_prod < backup_20260519_120000.sql

# Aus gz File
gunzip -c backup_20260519.sql.gz | sudo -u postgres psql ai_tutor_prod
```

### Automatisches Backup (Cron)

```bash
# Backup-Verzeichnis erstellen
sudo mkdir -p /opt/backups
sudo chown ubuntu:ubuntu /opt/backups

# Backup-Script erstellen
sudo nano /etc/cron.daily/ai-tutor-backup
```

Inhalt:

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d)
sudo -u postgres pg_dump ai_tutor_prod | gzip > $BACKUP_DIR/ai_tutor_$DATE.sql.gz
# Behalte nur letzte 7 Tage
find $BACKUP_DIR -name "ai_tutor_*.sql.gz" -mtime +7 -delete
```

```bash
# Ausführbar machen
sudo chmod +x /etc/cron.daily/ai-tutor-backup
```

## SSL/HTTPS einrichten (Empfohlen für Produktion)

Mit Let's Encrypt (kostenlos):

### Voraussetzungen
- Domain-Name (z.B. ai-tutor.example.com)
- Domain zeigt auf deine EC2 IP (A Record in DNS)

### Certbot installieren

```bash
sudo apt update
sudo apt install certbot python3-certbot-nginx
```

### Zertifikat erstellen

```bash
# Für eine Domain
sudo certbot --nginx -d ai-tutor.example.com

# Für mehrere Domains/Subdomains
sudo certbot --nginx -d ai-tutor.example.com -d www.ai-tutor.example.com

# Folge den Prompts:
# - Email eingeben
# - Terms akzeptieren
# - Redirect HTTP zu HTTPS wählen
```

### Auto-Renewal prüfen

```bash
# Certbot richtet auto-renewal automatisch ein
# Testen:
sudo certbot renew --dry-run
```

Zertifikate werden automatisch alle 90 Tage erneuert.

## Monitoring und Wartung

### Logs überwachen

```bash
# API Logs (live)
sudo journalctl -u ai-tutor-api -f

# Nur Fehler
sudo journalctl -u ai-tutor-api -p err

# Letzte 100 Zeilen
sudo journalctl -u ai-tutor-api -n 100

# Seit heute
sudo journalctl -u ai-tutor-api --since today
```

### System-Ressourcen

```bash
# CPU/RAM
htop

# Disk Usage
df -h

# Disk Usage pro Verzeichnis
du -sh /opt/ai-tutor/*
du -sh /opt/ai-tutor/uploads
```

### Service Management

```bash
# Status anzeigen
sudo systemctl status ai-tutor-api
sudo systemctl status nginx
sudo systemctl status postgresql

# Service starten/stoppen
sudo systemctl start ai-tutor-api
sudo systemctl stop ai-tutor-api
sudo systemctl restart ai-tutor-api

# Service beim Boot aktivieren/deaktivieren
sudo systemctl enable ai-tutor-api
sudo systemctl disable ai-tutor-api
```

### Datenbank-Wartung

```bash
# Mit psql verbinden
sudo -u postgres psql ai_tutor_prod

# Nützliche Queries:
# Anzahl Chats
SELECT COUNT(*) FROM chat_sessions;

# Anzahl Materialien
SELECT COUNT(*) FROM materials;

# Datenbankgröße
SELECT pg_size_pretty(pg_database_size('ai_tutor_prod'));

# Verbindungen
SELECT * FROM pg_stat_activity;

# Beenden
\q
```

## Sicherheit Best Practices

### 1. SSH absichern

```bash
# SSH Config bearbeiten
sudo nano /etc/ssh/sshd_config

# Empfohlene Einstellungen:
# PermitRootLogin no
# PasswordAuthentication no
# Port 2222  (ändere Port)

# SSH neu starten
sudo systemctl restart sshd
```

### 2. fail2ban installieren

```bash
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 3. Firewall konfigurieren (ufw)

```bash
# Falls nicht über Security Group:
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 8080/tcp
sudo ufw allow 8000/tcp
sudo ufw enable
```

### 4. Secrets sicher aufbewahren

- ✅ .env nie in Git committen
- ✅ Sichere Passwörter verwenden
- ✅ JWT Secret regelmäßig rotieren
- ✅ AWS Keys mit minimalen Berechtigungen

### 5. Regelmäßige Updates

```bash
# System Updates
sudo apt update
sudo apt upgrade

# Python Dependencies
cd /opt/ai-tutor
source .venv/bin/activate
pip list --outdated
```

## Performance Optimierung

### 1. Uvicorn Workers anpassen

In `/etc/systemd/system/ai-tutor-api.service`:

```ini
ExecStart=/opt/ai-tutor/.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Faustregel: `workers = (2 * CPU_CORES) + 1`

### 2. PostgreSQL Tuning

```bash
sudo nano /etc/postgresql/16/main/postgresql.conf
```

Für t3.small (2GB RAM):

```
shared_buffers = 512MB
effective_cache_size = 1536MB
maintenance_work_mem = 128MB
checkpoint_completion_target = 0.9
```

```bash
sudo systemctl restart postgresql
```

### 3. Nginx Caching

Bereits in install_app.sh konfiguriert für statische Assets.

## Kosten-Abschätzung (AWS)

### EC2 t3.small (us-east-1)
- On-Demand: ~$15/Monat
- Reserved (1 Jahr): ~$10/Monat

### Datenübertragung
- Erste 100 GB/Monat: kostenlos
- Danach: $0.09/GB

### Storage (EBS)
- 20 GB gp3: ~$2/Monat

### AWS Bedrock (variabel)
- Claude API calls
- Titan Embeddings

**Gesamtkosten (geschätzt):** $20-30/Monat + Bedrock API Calls

## Support und Hilfe

### Nützliche Befehle Zusammenfassung

```bash
# Service Status
sudo systemctl status ai-tutor-api nginx postgresql

# Logs ansehen
sudo journalctl -u ai-tutor-api -f
sudo tail -f /var/log/ai-tutor-api.log
sudo tail -f /var/log/nginx/error.log

# Service neu starten
sudo systemctl restart ai-tutor-api nginx

# Config testen
sudo nginx -t
python -c "from api.main import app"

# Datenbank
sudo -u postgres psql ai_tutor_prod

# System-Info
htop
df -h
free -h
```

### Häufige Fehler

| Fehler | Ursache | Lösung |
|--------|---------|--------|
| 502 Bad Gateway | API läuft nicht | `sudo systemctl restart ai-tutor-api` |
| Connection refused | Falscher Port | Security Group & Port prüfen |
| Permission denied | Falsche Berechtigungen | `sudo chown -R ubuntu:ubuntu /opt/ai-tutor` |
| Database connection failed | Falsche .env | DATABASE_URL in .env prüfen |

---

## Checkliste

✅ EC2 Instance erstellt  
✅ Security Group konfiguriert  
✅ setup_ec2.sh ausgeführt  
✅ DB-Passwort gespeichert  
✅ Code auf EC2 kopiert  
✅ .env konfiguriert  
✅ install_app.sh ausgeführt  
✅ Services laufen  
✅ Frontend erreichbar  
✅ Professor Account erstellt  
✅ SSL eingerichtet (optional)  
✅ Backups konfiguriert (optional)  

**Fertig! 🎉**
