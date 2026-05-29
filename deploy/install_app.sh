#!/bin/bash
# Install AI-Tutor application
# Run this after setup_ec2.sh and copying code to /opt/ai-tutor

set -e

APP_DIR="/opt/ai-tutor"

# Check if running as correct user
if [ "$USER" != "ubuntu" ]; then
    echo "⚠️  Warning: This script should be run as the ubuntu user"
    echo "Current user: $USER"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

cd $APP_DIR

echo "🚀 Installing AI-Tutor application..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create .env file from deploy/.env.production.template"
    exit 1
fi

echo "✓ .env file found"

# Create Python virtual environment
echo ""
echo "🐍 Setting up Python environment..."
python3.12 -m venv .venv
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
echo "📦 Installing Python packages..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p uploads
mkdir -p logs

# Initialize database schema
echo ""
echo "🗄️  Initializing database schema..."
PYTHONPATH=$APP_DIR python3.12 migrations/init_db.py

echo "✓ Database initialized"

# Build student frontend
echo ""
echo "🎨 Building student frontend..."
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Build
npm run build

if [ ! -d "dist" ]; then
    echo "❌ Error: Frontend build failed - dist directory not created"
    exit 1
fi

echo "✓ Student frontend built"

cd ..

# Build professor dashboard
echo ""
echo "🎨 Building professor dashboard..."
cd professor-dashboard

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dashboard dependencies..."
    npm install
fi

# Build
npm run build

if [ ! -d "dist" ]; then
    echo "❌ Error: Professor dashboard build failed - dist directory not created"
    exit 1
fi

echo "✓ Professor dashboard built"

cd ..

# Create systemd service for backend API
echo ""
echo "⚙️  Creating systemd service..."
sudo tee /etc/systemd/system/ai-tutor-api.service > /dev/null <<EOF
[Unit]
Description=AI-Tutor FastAPI Backend
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$APP_DIR"
ExecStart=$APP_DIR/.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10
StandardOutput=append:/var/log/ai-tutor-api.log
StandardError=append:/var/log/ai-tutor-api-error.log

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR/uploads $APP_DIR/logs

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Systemd service created"

# Configure Nginx
echo ""
echo "🌐 Configuring Nginx..."
sudo tee /etc/nginx/sites-available/ai-tutor > /dev/null <<'EOF'
# Student Frontend (Port 80)
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    # Student frontend static files
    location / {
        root /opt/ai-tutor/frontend/dist;
        try_files $uri $uri/ /index.html;

        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # API proxy
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long-running requests
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }

    # WebSocket support for chat
    location /api/v2/ws/ {
        proxy_pass http://localhost:8000/api/v2/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # WebSocket timeouts
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
}

# Professor Dashboard (Port 8080)
server {
    listen 8080;
    listen [::]:8080;
    server_name _;

    # Professor dashboard static files
    location / {
        root /opt/ai-tutor/professor-dashboard/dist;
        try_files $uri $uri/ /index.html;

        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # API proxy (same backend)
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long-running requests
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
}
EOF

echo "✓ Nginx configuration created"

# Remove default nginx site
sudo rm -f /etc/nginx/sites-enabled/default

# Enable our site
sudo ln -sf /etc/nginx/sites-available/ai-tutor /etc/nginx/sites-enabled/

# Test Nginx configuration
echo ""
echo "🧪 Testing Nginx configuration..."
sudo nginx -t

# Restart Nginx
echo "Restarting Nginx..."
sudo systemctl restart nginx
sudo systemctl enable nginx

echo "✓ Nginx configured and running"

# Create log files with correct permissions
sudo touch /var/log/ai-tutor-api.log
sudo touch /var/log/ai-tutor-api-error.log
sudo chown ubuntu:ubuntu /var/log/ai-tutor-api*.log

# Reload systemd and start API service
echo ""
echo "🚀 Starting API service..."
sudo systemctl daemon-reload
sudo systemctl start ai-tutor-api
sudo systemctl enable ai-tutor-api

# Wait a moment for service to start
sleep 3

# Check service status
if sudo systemctl is-active --quiet ai-tutor-api; then
    echo "✓ API service is running"
else
    echo "⚠️  API service may have issues, checking logs..."
    sudo journalctl -u ai-tutor-api -n 20 --no-pager
fi

echo ""
echo "================================================================"
echo "✅ AI-Tutor installation complete!"
echo "================================================================"
echo ""
echo "🌐 Access your application:"
echo "   Student Frontend:    http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/"
echo "   Professor Dashboard: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8080/"
echo "   API Documentation:   http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000/docs"
echo ""
echo "📊 Check status:"
echo "   sudo systemctl status ai-tutor-api"
echo "   sudo systemctl status nginx"
echo ""
echo "📝 View logs:"
echo "   sudo journalctl -u ai-tutor-api -f"
echo "   sudo tail -f /var/log/ai-tutor-api.log"
echo "   sudo tail -f /var/log/nginx/error.log"
echo ""
echo "🔄 Restart services:"
echo "   sudo systemctl restart ai-tutor-api"
echo "   sudo systemctl restart nginx"
echo ""
