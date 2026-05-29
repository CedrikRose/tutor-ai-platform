# 🚀 AI-Tutor AWS Deployment Guide

## 📋 Übersicht

Dieses Projekt wird mit **Docker** auf **AWS EC2** deployed.

**Stack:**
- PostgreSQL (mit pgvector) - Container
- FastAPI Backend - Container  
- React Frontend (nginx) - Container
- Docker Compose orchestriert alles

---

## ✅ Voraussetzungen

- AWS Account
- EC2 Instance (empfohlen: t3.medium, Ubuntu 22.04)
- Domain (optional, später)
- Git installiert lokal

---

## 🔧 EC2 Instance Setup

### 1. EC2 Instance erstellen

**Im AWS Console:**
1. Gehe zu EC2 → Launch Instance
2. **Name:** ai-tutor-server
3. **AMI:** Ubuntu Server 22.04 LTS
4. **Instance Type:** t3.medium (2 vCPU, 4 GB RAM) - ~30€/Monat
5. **Key Pair:** Erstelle neuen Key Pair → Download `.pem` Datei
6. **Security Group:** Neue erstellen mit:
   - SSH (Port 22) - Nur deine IP
   - HTTP (Port 80) - Überall (0.0.0.0/0)
   - HTTPS (Port 443) - Überall (0.0.0.0/0) [für später]
   - Custom TCP (Port 8000) - Überall [für API]
7. **Storage:** 20 GB (GP3)
8. **Launch Instance**

### 2. Mit EC2 verbinden

```bash
# Lokal ausführen
chmod 400 ~/Downloads/ai-tutor-key.pem
ssh -i ~/Downloads/ai-tutor-key.pem ubuntu@<EC2-PUBLIC-IP>
```

Ersetze `<EC2-PUBLIC-IP>` mit der Public IP aus dem EC2 Dashboard.

---

## 🐳 Docker auf EC2 installieren

**Auf dem EC2 Server:**

```bash
# System updaten
sudo apt update && sudo apt upgrade -y

# Docker installieren
sudo apt install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker

# User zu docker group hinzufügen
sudo usermod -aG docker ubuntu
newgrp docker

# Testen
docker --version
docker-compose --version
```

---

## 📦 Projekt auf EC2 hochladen

### Option 1: Mit Git (empfohlen)

**Auf EC2:**
```bash
cd ~
git clone https://github.com/<dein-username>/AI-Tutor.git
cd AI-Tutor
```

### Option 2: Mit scp (falls kein Git)

**Lokal ausführen:**
```bash
cd /home/cedrik/AI-Tutor
tar czf ai-tutor.tar.gz --exclude=node_modules --exclude=venv --exclude=__pycache__ .
scp -i ~/Downloads/ai-tutor-key.pem ai-tutor.tar.gz ubuntu@<EC2-IP>:~

# Dann auf EC2:
ssh -i ~/Downloads/ai-tutor-key.pem ubuntu@<EC2-IP>
mkdir AI-Tutor
tar xzf ai-tutor.tar.gz -C AI-Tutor
cd AI-Tutor
```

---

## ⚙️ Konfiguration

**Auf EC2 im AI-Tutor Ordner:**

```bash
# .env.production bearbeiten
nano .env.production
```

**WICHTIG - Diese Zeile ändern:**
```bash
DB_PASSWORD=CHANGE_ME_TO_SECURE_PASSWORD
```

Ändere zu einem sicheren Passwort (z.B. `MeinSicheres2024Passwort!`)

Speichern mit `Ctrl+X` → `Y` → `Enter`

```bash
# Als .env speichern
cp .env.production .env
```

---

## 🚀 Deployment starten

```bash
# Docker Container bauen und starten
docker-compose up -d --build
```

**Was passiert:**
- PostgreSQL startet mit pgvector Extension
- Backend baut sich und wartet auf DB
- Frontend wird gebaut (React → Static Files)
- Nginx serviert Frontend

**Logs anschauen:**
```bash
docker-compose logs -f
```

Mit `Ctrl+C` beenden (Container laufen weiter!)

---

## ✅ Testen

**1. Backend testen:**
```bash
curl http://<EC2-IP>:8000/health
```

Sollte `{"status":"healthy"}` zurückgeben.

**2. Frontend testen:**

Öffne im Browser:
```
http://<EC2-IP>
```

Du solltest die AI-Tutor UI sehen! 🎉

---

## 🔄 Updates machen

**Wenn du lokal Änderungen gemacht hast:**

### Mit Git (empfohlen):

**Lokal:**
```bash
git add .
git commit -m "Update: neue Features"
git push origin main
```

**Auf EC2:**
```bash
cd ~/AI-Tutor
git pull
docker-compose up -d --build
```

Fertig! Updates sind live in ~2 Minuten.

### Ohne Git:

**Lokal:**
```bash
cd /home/cedrik/AI-Tutor
tar czf ai-tutor-update.tar.gz --exclude=node_modules --exclude=venv .
scp -i ~/Downloads/ai-tutor-key.pem ai-tutor-update.tar.gz ubuntu@<EC2-IP>:~/AI-Tutor/
```

**Auf EC2:**
```bash
cd ~/AI-Tutor
tar xzf ai-tutor-update.tar.gz
docker-compose up -d --build
```

---

## 🛠️ Nützliche Befehle

```bash
# Container Status
docker-compose ps

# Logs anzeigen
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres

# Container neustarten
docker-compose restart

# Container stoppen
docker-compose down

# Container stoppen + Daten löschen
docker-compose down -v

# In Container einloggen
docker exec -it ai-tutor-backend bash
docker exec -it ai-tutor-db psql -U ai_tutor -d ai_tutor_prod
```

---

## 🌐 Domain einrichten (später)

Wenn du eine Domain hast (z.B. von GitHub Student Pack):

1. Domain DNS zu EC2 Public IP zeigen lassen (A Record)
2. SSL-Zertifikat mit Let's Encrypt einrichten
3. Nginx Reverse Proxy konfigurieren

Guide folgt später! 🚀

---

## 💰 Kosten

**Geschätzte monatliche Kosten:**
- EC2 t3.medium: ~30€
- Storage (20 GB): ~2€
- Traffic: ~1€ (bei 100 Nutzern)

**Total: ~33€/Monat**

---

## 🆘 Troubleshooting

**Container startet nicht:**
```bash
docker-compose logs <service-name>
```

**PostgreSQL Connection Error:**
- Prüfe, ob DB Container läuft: `docker-compose ps`
- Warte 30 Sekunden nach Start (DB braucht Zeit)

**Frontend zeigt keine Daten:**
- Prüfe Backend: `curl http://localhost:8000/health`
- Prüfe Browser Console (F12)

**Port schon belegt:**
```bash
sudo lsof -i :8000
sudo kill <PID>
```

---

## 📞 Support

Bei Problemen:
1. `docker-compose logs -f` anschauen
2. GitHub Issues erstellen
3. Logs posten

---

Viel Erfolg! 🚀
