# AI-Tutor AWS Deployment

Schritt-für-Schritt Anleitung zum Deployment auf AWS EC2.

## Voraussetzungen

- AWS EC2 Instance (Ubuntu 26 LTS, empfohlen: t3.small oder größer)
- SSH Key Pair für EC2 Zugriff
- AWS Bedrock API Zugangsdaten
- LlamaParse API Key

## Schritt 1: EC2 Instance Setup

### Security Group konfigurieren

Erstelle eine Security Group mit folgenden Inbound Rules:

| Type       | Port  | Source    | Description           |
|------------|-------|-----------|-----------------------|
| SSH        | 22    | Deine IP  | SSH Zugriff          |
| HTTP       | 80    | 0.0.0.0/0 | Student Frontend     |
| Custom TCP | 8080  | 0.0.0.0/0 | Professor Dashboard  |
| Custom TCP | 8000  | 0.0.0.0/0 | API (optional debug) |

⚠️ **Für Produktion:** Port 22 nur auf deine IP beschränken!

### Mit EC2 verbinden

```bash
# SSH Key Permissions setzen
chmod 400 ~/Downloads/dein-key.pem

# Mit EC2 verbinden
ssh -i ~/Downloads/dein-key.pem ubuntu@DEINE_EC2_IP
```

### Server Setup ausführen

```bash
# Setup-Skript auf EC2 kopieren und ausführen
chmod +x setup_ec2.sh
./setup_ec2.sh
```

**WICHTIG:** Speichere das generierte Datenbank-Passwort!

## Schritt 2: Code auf EC2 kopieren

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
  -e "ssh -i ~/Downloads/dein-key.pem" \
  /home/cedrik/AI-Tutor/ \
  ubuntu@DEINE_EC2_IP:/opt/ai-tutor/
```

## Schritt 3: Umgebungsvariablen konfigurieren

Auf dem EC2 Server:

```bash
cd /opt/ai-tutor

# Template kopieren
cp deploy/.env.production.template .env

# Bearbeiten
nano .env
```

Erforderliche Werte eintragen!

## Schritt 4: Application installieren

```bash
cd /opt/ai-tutor
./deploy/install_app.sh
```

## Services prüfen

```bash
sudo systemctl status ai-tutor-api
sudo systemctl status nginx
```

## Zugriff

- **Student Frontend:** http://DEINE_EC2_IP/
- **Professor Dashboard:** http://DEINE_EC2_IP:8080/
- **API Docs:** http://DEINE_EC2_IP:8000/docs
