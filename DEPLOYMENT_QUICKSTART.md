# AI-Tutor AWS Deployment - Quick Start

Minimale Schritte zum Deployment auf AWS EC2 Ubuntu 26 LTS.

## Voraussetzungen

- ✅ AWS EC2 Instance (Ubuntu 26 LTS, t3.small)
- ✅ Security Group: Ports 22, 80, 8080, 8000
- ✅ SSH Key
- ✅ AWS Bedrock & LlamaParse API Keys

## Deployment in 5 Schritten

### 1. Mit EC2 verbinden

```bash
ssh -i ~/Downloads/your-key.pem ubuntu@YOUR_EC2_IP
```

### 2. Server einrichten

Kopiere `deploy/setup_ec2.sh` auf EC2 und führe aus:

```bash
chmod +x setup_ec2.sh
./setup_ec2.sh
```

⚠️ **Speichere das generierte Datenbank-Passwort!**

### 3. Code kopieren

Von deinem lokalen Rechner:

```bash
rsync -avz --exclude='.venv' --exclude='node_modules' --exclude='.env' \
  -e "ssh -i ~/Downloads/your-key.pem" \
  /home/cedrik/AI-Tutor/ ubuntu@YOUR_EC2_IP:/opt/ai-tutor/
```

### 4. Environment konfigurieren

Auf EC2:

```bash
cd /opt/ai-tutor
cp deploy/.env.production.template .env
nano .env  # Fülle alle Werte aus!
```

Benötigte Werte:
- `DATABASE_URL` (mit Passwort aus Schritt 2)
- `AWS_ACCESS_KEY_ID` & `AWS_SECRET_ACCESS_KEY`
- `LLAMA_CLOUD_API_KEY`
- `JWT_SECRET_KEY` (generiere mit `openssl rand -base64 32`)
- `PROFESSOR_REGISTRATION_CODE` (wähle einen sicheren Code)
- `CORS_ORIGINS` (füge deine EC2 IP hinzu)

### 5. Application installieren

```bash
cd /opt/ai-tutor
./deploy/install_app.sh
```

Dauert ca. 5-10 Minuten.

## Fertig!

Öffne im Browser:
- **Student Frontend:** http://YOUR_EC2_IP/
- **Professor Dashboard:** http://YOUR_EC2_IP:8080/
- **API Docs:** http://YOUR_EC2_IP:8000/docs

## Ersten Professor Account erstellen

1. Gehe zu http://YOUR_EC2_IP:8080/
2. Registriere mit deinem `PROFESSOR_REGISTRATION_CODE`
3. Logge dich ein

## Updates deployen

```bash
# Code per rsync aktualisieren (auf lokalem Rechner)
rsync -avz --exclude='.venv' --exclude='node_modules' --exclude='.env' \
  -e "ssh -i ~/Downloads/your-key.pem" \
  /home/cedrik/AI-Tutor/ ubuntu@YOUR_EC2_IP:/opt/ai-tutor/

# Auf EC2: Update-Skript ausführen
cd /opt/ai-tutor
./deploy/update.sh
```

## Troubleshooting

### API läuft nicht
```bash
sudo journalctl -u ai-tutor-api -f
sudo systemctl restart ai-tutor-api
```

### Frontend nicht erreichbar
```bash
sudo systemctl status nginx
sudo nginx -t
sudo systemctl restart nginx
```

### Datenbank-Fehler
```bash
sudo systemctl status postgresql
psql -U ai_tutor_prod -d ai_tutor_prod -h localhost
```

## Vollständige Dokumentation

Siehe `deploy/DEPLOYMENT_FULL.md` für:
- SSL/HTTPS Setup
- Monitoring & Logs
- Backups
- Sicherheit
- Performance-Optimierung
