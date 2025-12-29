#!/bin/bash
# =============================================================================
# BintaCura EC2 Initial Setup Script
# Run this on your EC2 server (Amazon Linux 2023)
# =============================================================================

set -e

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  BintaCura EC2 Server Setup                                      ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Check if already setup
if [ -f ~/setup-complete.txt ]; then
    echo "⚠️  Setup was already run on: $(cat ~/setup-complete.txt)"
    read -p "Do you want to re-run setup? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Setup cancelled."
        exit 0
    fi
fi

echo "🚀 Starting BintaCura setup..."
echo ""

# Update system
echo "📦 Step 1/10: Updating system packages..."
sudo dnf update -y

# Install required packages
echo "📦 Step 2/10: Installing required packages..."
# Try PostgreSQL 17 first, fallback to 16 or 15 if not available
if sudo dnf install -y python3.11 python3.11-pip git postgresql17 nginx 2>/dev/null; then
    echo "✅ PostgreSQL 17 installed"
elif sudo dnf install -y python3.11 python3.11-pip git postgresql16 nginx 2>/dev/null; then
    echo "⚠️  PostgreSQL 17 not available, using PostgreSQL 16"
else
    echo "⚠️  PostgreSQL 17/16 not available, using PostgreSQL 15"
    sudo dnf install -y python3.11 python3.11-pip git postgresql15 nginx
fi

# Enable and start Nginx
echo "🌐 Step 3/10: Configuring Nginx..."
sudo systemctl enable nginx
sudo systemctl start nginx

# Navigate to project directory
echo "📁 Step 4/10: Setting up project directory..."
cd ~/bintacura

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3.11 -m venv venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🐍 Step 5/10: Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📚 Step 6/10: Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if doesn't exist
if [ ! -f .env ]; then
    echo "⚙️  Step 7/10: Creating .env file..."
    cat > .env << 'ENVEOF'
# Django Core
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
DEBUG=False
DJANGO_SETTINGS_MODULE=backend.settings
ALLOWED_HOSTS=13.53.194.95,ec2-13-53-194-95.eu-north-1.compute.amazonaws.com,bintacura.org,www.bintacura.org

# AWS RDS Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=initialdbbintacura
DB_USER=soyames_
DB_PASSWORD=DE7!S8gVDZqDU!N
DB_HOST=bintacura-db-gb.c9uwsww6o8ky.eu-north-1.rds.amazonaws.com
DB_PORT=5432

# Environment
ENVIRONMENT=production
DEPLOYMENT_REGION=eu-north-1
INSTANCE_TYPE=CLOUD

# Security
SECURITY_STRICT_MODE=True
ENABLE_ADVANCED_SECURITY_MIDDLEWARE=True
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False

# Email (Zoho)
EMAIL_HOST=smtppro.zoho.eu
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_USE_TLS=False
EMAIL_HOST_USER=contacts@bintacura.org
EMAIL_HOST_PASSWORD=your-zoho-password-here
DEFAULT_FROM_EMAIL=BintaCura <contacts@bintacura.org>

# Other settings
FRONTEND_URL=https://bintacura.org
SENTRY_DSN=

# AWS
AWS_REGION=eu-north-1
AWS_RDS_INSTANCE=bintacura-db-gb
ENVEOF
    echo "✅ .env file created"
else
    echo "✅ .env file already exists"
fi

# Run migrations
echo "🗄️  Step 8/10: Running database migrations..."
python manage.py migrate --no-input

# Collect static files
echo "📁 Step 9/10: Collecting static files..."
python manage.py collectstatic --no-input --clear

# Create log directory
echo "📝 Creating log directory..."
sudo mkdir -p /var/log/bintacura
sudo chown ec2-user:ec2-user /var/log/bintacura

# Create systemd service
echo "⚙️  Step 10/10: Creating systemd service..."
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
    server_name 13.53.194.95 ec2-13-53-194-95.eu-north-1.compute.amazonaws.com bintacura.org www.bintacura.org;

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

# Mark setup as complete
echo "$(date)" > ~/setup-complete.txt

# Check service status
echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  ✅ SETUP COMPLETE!                                              ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 Your application is now running at:"
echo "   • http://13.53.194.95"
echo "   • http://ec2-13-53-194-95.eu-north-1.compute.amazonaws.com"
echo ""
echo "⏳ After DNS propagates (1-4 hours):"
echo "   • http://bintacura.org"
echo "   • http://www.bintacura.org"
echo ""
echo "📋 Service Status:"
sudo systemctl status bintacura --no-pager | head -5
echo ""
echo "📝 View logs:"
echo "   sudo journalctl -u bintacura -f"
echo ""
echo "🔄 Restart services:"
echo "   sudo systemctl restart bintacura"
echo "   sudo systemctl reload nginx"
echo ""
echo "🎉 Setup completed at: $(date)"
