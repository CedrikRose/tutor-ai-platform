#!/bin/bash
# AI-Tutor EC2 Setup Script
# Run this on a fresh Ubuntu 26 LTS instance

set -e  # Exit on error

echo "🚀 AI-Tutor EC2 Setup Starting..."
echo ""

# Update system
echo "📦 Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    postgresql-16 \
    postgresql-contrib-16 \
    nginx \
    git \
    curl \
    build-essential

# Install Node.js 20.x
echo "📦 Installing Node.js 20..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify installations
echo ""
echo "✓ Installed versions:"
python3.12 --version
node --version
npm --version
psql --version

# Configure PostgreSQL
echo ""
echo "🗄️  Configuring PostgreSQL..."
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Generate secure database password
DB_PASSWORD=$(openssl rand -base64 32)

# Create database and user
sudo -u postgres psql <<EOF
-- Create user and database
CREATE USER ai_tutor_prod WITH PASSWORD '$DB_PASSWORD';
CREATE DATABASE ai_tutor_prod OWNER ai_tutor_prod;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ai_tutor_prod TO ai_tutor_prod;

-- Connect to database and add extensions
\c ai_tutor_prod
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO ai_tutor_prod;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ai_tutor_prod;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ai_tutor_prod;
EOF

echo ""
echo "✅ PostgreSQL configured successfully"
echo ""
echo "⚠️  IMPORTANT: Save this database password!"
echo "================================================================"
echo "Database Password: $DB_PASSWORD"
echo "================================================================"
echo ""
echo "Add this to your .env file:"
echo "DATABASE_URL=postgresql://ai_tutor_prod:$DB_PASSWORD@localhost/ai_tutor_prod"
echo ""

# Create app directory
echo "📁 Creating application directory..."
sudo mkdir -p /opt/ai-tutor
sudo chown -R ubuntu:ubuntu /opt/ai-tutor

# Configure firewall (optional, security group handles this)
echo ""
echo "🔒 Firewall configuration (handled by AWS Security Group)"
echo "   Make sure your security group allows:"
echo "   - Port 22 (SSH)"
echo "   - Port 80 (HTTP - Student Frontend)"
echo "   - Port 8080 (Professor Dashboard)"
echo "   - Port 8000 (API - for debugging)"

echo ""
echo "✅ EC2 Setup Complete!"
echo ""
echo "📝 Next steps:"
echo "1. Transfer your code to /opt/ai-tutor"
echo "   rsync -avz --exclude='.venv' --exclude='node_modules' --exclude='.env' \\"
echo "     -e 'ssh -i ~/.ssh/YOUR_KEY.pem' \\"
echo "     /path/to/AI-Tutor/ ubuntu@YOUR_EC2_IP:/opt/ai-tutor/"
echo ""
echo "2. Create .env file with the database password above"
echo ""
echo "3. Run: cd /opt/ai-tutor && ./deploy/install_app.sh"
echo ""
