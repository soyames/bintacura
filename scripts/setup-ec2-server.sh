#!/bin/bash

# =============================================================================
# BintaCura EC2 Initial Setup Script
# =============================================================================
# This script sets up your EC2 instance for the first time
# Run this ONCE on your EC2 server after creation
# =============================================================================

set -e

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  BintaCura EC2 Server Initial Setup                             ║"
echo "╚══════════════════════════════════════════════════════════════════╝"

# Update system
echo "📦 Updating system packages..."
sudo dnf update -y

# Install required packages (if not already installed)
echo "📦 Installing required packages..."
sudo dnf install -y python3.11 python3.11-pip git postgresql17 nginx

# Enable and start Nginx
echo "🌐 Configuring Nginx..."
sudo systemctl enable nginx
sudo systemctl start nginx

# Create project directory
echo "📁 Creating project directory..."
mkdir -p /home/ec2-user/bintacura
cd /home/ec2-user

# Clone repository
if [ ! -d "bintacura/.git" ]; then
    echo "📥 Cloning BintaCura repository..."
    git clone https://github.com/soyames/bintacura.git
    cd bintacura
else
    echo "✅ Repository already cloned"
    cd bintacura
    git pull origin main
fi

# Create virtual environment
echo "🐍 Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3.11 -m venv venv
fi
source venv/bin/activate

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
echo "⚙️  Creating environment configuration..."
cat > .env << 'ENVEOF'
# Django Core
SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
DEBUG=False
DJANGO_SETTINGS_MODULE=backend.settings
ALLOWED_HOSTS=16.171.180.104,*.compute.amazonaws.com,bintacura.org,www.bintacura.org,localhost,127.0.0.1

# AWS RDS Database (PostgreSQL 17.6)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=initialdbbintacura
DB_USER=soyames_
DB_PASSWORD=DE7!S8gVDZqDU!N
DB_HOST=bintacura-db-gb.c9uwsww6o8ky.eu-north-1.rds.amazonaws.com
DB_PORT=5432

# Currency Settings (Base: XOF)
DEFAULT_CURRENCY=XOF
SUPPORTED_CURRENCIES=XOF,USD,EUR,GNF,NGN,GHS,ZAR,XAF,MAD,TND

# Environment
ENVIRONMENT=production
DEPLOYMENT_REGION=eu-north-1
INSTANCE_TYPE=CLOUD

# Render Configuration (Keep active)
RENDER_SERVICE_ID=srv-d4qoujp5pdvs738ru6q0
RENDER_EXTERNAL_URL=https://bintacura.onrender.com
SYNC_CLOUD_PUSH_URL=https://bintacura.onrender.com/api/v1/sync/push/
SYNC_CLOUD_PULL_URL=https://bintacura.onrender.com/api/v1/sync/pull/

# Security
SECURITY_STRICT_MODE=True
ENABLE_ADVANCED_SECURITY_MIDDLEWARE=True
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Email (Zoho)
EMAIL_HOST=smtppro.zoho.eu
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_USE_TLS=False
EMAIL_HOST_USER=contacts@bintacura.org
EMAIL_HOST_PASSWORD=your-zoho-password
DEFAULT_FROM_EMAIL=BintaCura <contacts@bintacura.org>

# Other settings
FRONTEND_URL=https://bintacura.org
SENTRY_DSN=

# AWS
AWS_REGION=eu-north-1
AWS_RDS_INSTANCE=bintacura-db-gb
ENVEOF

echo "✅ .env file created (update with your actual credentials later)"

# Run migrations
echo "🗄️  Running database migrations..."
python manage.py migrate --no-input

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --no-input --clear

# Create log directory
echo "📝 Creating log directory..."
sudo mkdir -p /var/log/bintacura
sudo chown ec2-user:ec2-user /var/log/bintacura

# Create systemd service
echo "⚙️  Creating systemd service..."
sudo tee /etc/systemd/system/bintacura.service > /dev/null << 'SERVICEEOF'
[Unit]
Description=BintaCura Django Application
After=network.target

[Service]
Type=exec
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/bintacura
Environment="PATH=/home/ec2-user/bintacura/venv/bin"
ExecStart=/home/ec2-user/bintacura/venv/bin/gunicorn \
    --bind 0.0.0.0:8080 \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile /var/log/bintacura/access.log \
    --error-logfile /var/log/bintacura/error.log \
    backend.wsgi:application
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICEEOF

# Configure Nginx
echo "🌐 Configuring Nginx..."
sudo tee /etc/nginx/conf.d/bintacura.conf > /dev/null << 'NGINXEOF'
server {
    listen 80;
    server_name 16.171.180.104 *.compute.amazonaws.com bintacura.org www.bintacura.org;

    client_max_body_size 20M;

    # Static files
    location /static/ {
        alias /home/ec2-user/bintacura/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /home/ec2-user/bintacura/media/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Proxy to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }
}
NGINXEOF

# Test Nginx configuration
echo "✅ Testing Nginx configuration..."
sudo nginx -t

# Reload systemd and enable services
echo "🔄 Enabling and starting services..."
sudo systemctl daemon-reload
sudo systemctl enable bintacura
sudo systemctl start bintacura
sudo systemctl reload nginx

# Check service status
echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  Service Status                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
sudo systemctl status bintacura --no-pager | head -10

echo ""
echo "✅ Initial setup completed successfully!"
echo ""
echo "🌐 Your application is now available at:"
echo "   http://13.53.194.95"
echo "   http://ec2-13-53-194-95.eu-north-1.compute.amazonaws.com"
echo ""
echo "📋 Next steps:"
echo "   1. Update .env file with your actual credentials"
echo "   2. Add EC2_SSH_KEY secret to GitHub"
echo "   3. Configure DNS to point bintacura.org to 13.53.194.95"
echo "   4. Set up SSL with: sudo certbot --nginx -d bintacura.org -d www.bintacura.org"
echo ""
