# HTTPS Setup für Professor Dashboard

## Status: ✅ Implementiert (2026-05-28)

Das Professor Dashboard ist jetzt über HTTPS erreichbar unter:
**https://tutor-ai.me/dashboard/**

## Änderungen

### 1. Vite-Konfiguration angepasst
**Datei:** `professor-dashboard/vite.config.ts`
- `base: '/dashboard/'` hinzugefügt
- Sorgt dafür, dass Assets korrekt unter `/dashboard/assets/` geladen werden

### 2. Nginx-Konfiguration aktualisiert
**Datei auf Server:** `/etc/nginx/sites-available/ai-tutor`

Das Dashboard läuft nun auf demselben HTTPS-Port (443) wie das Student Frontend:
- Student Frontend: `https://tutor-ai.me/`
- Professor Dashboard: `https://tutor-ai.me/dashboard/`
- API: `https://tutor-ai.me/api/`

**Konfiguration:**
```nginx
location /dashboard/ {
    alias /opt/ai-tutor/professor-dashboard/dist/;
    try_files $uri $uri/ /dashboard/index.html;
}

location = /dashboard {
    return 301 /dashboard/;
}
```

### 3. Dashboard neu gebaut
```bash
cd /opt/ai-tutor/professor-dashboard
npm run build
```

## Vorteile dieser Lösung

- ✅ Nur ein Port (443) nötig - keine zusätzlichen Firewall-Regeln
- ✅ Nutzt bestehende SSL-Zertifikate von Let's Encrypt
- ✅ Einheitliche URL-Struktur (kein Port im URL)
- ✅ Automatischer HTTP → HTTPS Redirect
- ✅ Standard Web-App Architektur

## URLs

| Service | URL |
|---------|-----|
| Student Frontend | https://tutor-ai.me/ |
| Professor Dashboard | https://tutor-ai.me/dashboard/ |
| API | https://tutor-ai.me/api/ |

## Alte Konfiguration (entfernt)

Vorher:
- Port 8080 (HTTP): Professor Dashboard
- Port 8443 (HTTPS): War konfiguriert, aber durch AWS Security Group blockiert

Diese Ports werden nicht mehr verwendet.

## Backup

Die alte Konfiguration wurde gesichert:
- `/etc/nginx/sites-available/ai-tutor.backup-YYYYMMDD-HHMMSS`

## Deployment

Bei zukünftigen Updates muss das Dashboard mit dem richtigen base path gebaut werden:

```bash
# Lokal
cd professor-dashboard
npm run build

# Auf Server
cd /opt/ai-tutor/professor-dashboard
npm run build

# Nginx neu laden
sudo systemctl reload nginx
```

## Rollback

Falls Probleme auftreten:

```bash
# Auf dem Server
sudo cp /etc/nginx/sites-available/ai-tutor.backup-YYYYMMDD-HHMMSS /etc/nginx/sites-available/ai-tutor
sudo systemctl reload nginx
```

Dann Dashboard neu bauen ohne base path in vite.config.ts
