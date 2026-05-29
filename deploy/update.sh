#!/bin/bash
# Update AI-Tutor application
# Run this after deploying new code to EC2

set -e

APP_DIR="/opt/ai-tutor"

echo "🔄 Updating AI-Tutor application..."
echo ""

cd $APP_DIR

# Pull latest code (if using git)
if [ -d .git ]; then
    echo "📥 Pulling latest code from git..."
    git pull
    echo "✓ Code updated"
else
    echo "ℹ️  Not a git repository - assuming code was updated via rsync"
fi

# Activate virtual environment
source .venv/bin/activate

# Update Python dependencies
echo ""
echo "📦 Updating Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Python dependencies updated"

# Run database migrations (if any)
if [ -d migrations ]; then
    echo ""
    echo "🗄️  Running database migrations..."
    PYTHONPATH=$APP_DIR python3.12 migrations/migrate.py 2>/dev/null || echo "ℹ️  No migrations to run"
fi

# Rebuild student frontend
echo ""
echo "🎨 Rebuilding student frontend..."
cd frontend
npm install
npm run build

if [ ! -d "dist" ]; then
    echo "❌ Error: Frontend build failed"
    exit 1
fi

echo "✓ Student frontend rebuilt"

# Rebuild professor dashboard
echo ""
echo "🎨 Rebuilding professor dashboard..."
cd ../professor-dashboard
npm install
npm run build

if [ ! -d "dist" ]; then
    echo "❌ Error: Dashboard build failed"
    exit 1
fi

echo "✓ Professor dashboard rebuilt"

cd ..

# Restart API service
echo ""
echo "🔄 Restarting API service..."
sudo systemctl restart ai-tutor-api

# Wait for service to start
sleep 3

# Check if service is running
if sudo systemctl is-active --quiet ai-tutor-api; then
    echo "✓ API service restarted successfully"
else
    echo "❌ API service failed to start"
    echo "Checking logs..."
    sudo journalctl -u ai-tutor-api -n 20 --no-pager
    exit 1
fi

# Reload Nginx
echo ""
echo "🌐 Reloading Nginx..."
sudo nginx -t && sudo systemctl reload nginx
echo "✓ Nginx reloaded"

echo ""
echo "================================================================"
echo "✅ Update complete!"
echo "================================================================"
echo ""
echo "🌐 Your application is now running with the latest code"
echo ""
echo "📊 Check status:"
echo "   sudo systemctl status ai-tutor-api"
echo ""
echo "📝 View logs:"
echo "   sudo journalctl -u ai-tutor-api -f"
echo ""
