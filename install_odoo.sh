#!/bin/bash
# Odoo 16 Community Edition Installation Script for Ubuntu/Debian
# For BINTACURA project - Connects to existing AWS RDS (odoo_db)
# Run this on your web server where Django is running

echo "════════════════════════════════════════════════════════════"
echo "  ODOO 16 COMMUNITY EDITION - INSTALLATION SCRIPT"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "⚠️  This will install Odoo on your web server"
echo "✅ Odoo will connect to RDS database: odoo_db"
echo "✅ Django database 'initialdbbintacura' will NOT be touched"
echo ""
read -p "Continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Installation cancelled."
    exit 0
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  STEP 1: Installing System Dependencies"
echo "════════════════════════════════════════════════════════════"

# Update system
sudo apt update
sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3-pip python3-dev python3-venv \
    libxml2-dev libxslt1-dev \
    libldap2-dev libsasl2-dev \
    libtiff5-dev libjpeg8-dev libopenjp2-7-dev \
    zlib1g-dev libfreetype6-dev liblcms2-dev \
    libwebp-dev libharfbuzz-dev libfribidi-dev \
    libxcb1-dev libpq-dev \
    node-less npm \
    git wget

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  STEP 2: Creating Odoo Directory"
echo "════════════════════════════════════════════════════════════"

# Create Odoo directory (separate from Django)
sudo mkdir -p /srv/odoo
sudo chown $USER:$USER /srv/odoo
cd /srv/odoo

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  STEP 3: Downloading Odoo Community Edition 16"
echo "════════════════════════════════════════════════════════════"

# Clone Odoo 16
if [ ! -d "/srv/odoo/.git" ]; then
    git clone https://github.com/odoo/odoo.git --depth 1 --branch 16.0 .
else
    echo "Odoo already cloned, updating..."
    git pull
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  STEP 4: Creating Python Virtual Environment"
echo "════════════════════════════════════════════════════════════"

# Create separate virtualenv for Odoo
python3 -m venv /srv/odoo/venv_odoo
source /srv/odoo/venv_odoo/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r /srv/odoo/requirements.txt
pip install psycopg2-binary

deactivate

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  STEP 5: Creating Odoo Configuration"
echo "════════════════════════════════════════════════════════════"

# Create logs directory
mkdir -p /srv/odoo/logs
mkdir -p /srv/odoo/custom_addons

# Get Odoo credentials
echo ""
echo "Please provide the following information:"
echo ""
read -sp "Enter password for odoo_user (from database creation): " ODOO_USER_PASSWORD
echo ""
read -sp "Create an Odoo admin master password (for web interface): " ODOO_ADMIN_PASSWORD
echo ""

# Create Odoo configuration file
cat > /srv/odoo/odoo.conf <<EOF
[options]
# Admin master password (for creating databases in web UI)
admin_passwd = $ODOO_ADMIN_PASSWORD

# Database connection - AWS RDS
db_host = bintacura-db-gb.c9uwsww6o8ky.eu-north-1.rds.amazonaws.com
db_port = 5432
db_user = odoo_user
db_password = $ODOO_USER_PASSWORD
db_name = odoo_db
dbfilter = ^odoo_db$

# Prevent listing other databases
list_db = False

# Server configuration
xmlrpc_port = 8069
logfile = /srv/odoo/logs/odoo.log
log_level = info

# Addons path
addons_path = /srv/odoo/addons,/srv/odoo/custom_addons

# Workers (for production)
workers = 2
max_cron_threads = 1

# Timeouts
limit_time_cpu = 600
limit_time_real = 1200
limit_memory_soft = 2147483648
limit_memory_hard = 2684354560

# HTTP options
proxy_mode = True
EOF

echo "✅ Configuration file created: /srv/odoo/odoo.conf"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  STEP 6: Creating Systemd Service"
echo "════════════════════════════════════════════════════════════"

# Create systemd service
sudo tee /etc/systemd/system/odoo.service > /dev/null <<EOF
[Unit]
Description=Odoo 16 Community Edition
Requires=network.target
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
ExecStart=/srv/odoo/venv_odoo/bin/python /srv/odoo/odoo-bin -c /srv/odoo/odoo.conf
WorkingDirectory=/srv/odoo
StandardOutput=journal+console
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Systemd service created"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  STEP 7: Starting Odoo Service"
echo "════════════════════════════════════════════════════════════"

# Reload systemd
sudo systemctl daemon-reload

# Enable Odoo to start on boot
sudo systemctl enable odoo

# Start Odoo
sudo systemctl start odoo

# Wait a moment for Odoo to start
sleep 5

# Check status
echo ""
echo "Checking Odoo status..."
sudo systemctl status odoo --no-pager

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  STEP 8: Testing Odoo Connection"
echo "════════════════════════════════════════════════════════════"

echo ""
echo "Testing if Odoo is responding..."
sleep 3

if curl -s http://localhost:8069/web/database/selector > /dev/null; then
    echo "✅ Odoo is running and responding!"
else
    echo "⚠️  Odoo might still be starting up..."
    echo "Check logs: sudo journalctl -u odoo -f"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✅ INSTALLATION COMPLETE!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📊 ODOO INFORMATION:"
echo "   • Installation: /srv/odoo/"
echo "   • Config file: /srv/odoo/odoo.conf"
echo "   • Logs: /srv/odoo/logs/odoo.log"
echo "   • Service: odoo.service"
echo "   • Port: 8069"
echo "   • Database: odoo_db (on RDS)"
echo ""
echo "🌐 ACCESS ODOO:"
echo "   • Local: http://localhost:8069"
echo "   • Network: http://YOUR_SERVER_IP:8069"
echo ""
echo "🔐 NEXT STEPS:"
echo "   1. Configure firewall (if needed):"
echo "      sudo ufw allow 8069/tcp"
echo ""
echo "   2. Configure Nginx reverse proxy (recommended):"
echo "      See ODOO_ERP_INTEGRATION.md for nginx config"
echo ""
echo "   3. Access Odoo web interface:"
echo "      http://localhost:8069"
echo ""
echo "   4. Initialize Odoo database:"
echo "      - Odoo will prompt to initialize odoo_db"
echo "      - Choose language, admin email, password"
echo "      - Select modules to install (HR first)"
echo ""
echo "🔧 USEFUL COMMANDS:"
echo "   • Check status:  sudo systemctl status odoo"
echo "   • View logs:     sudo journalctl -u odoo -f"
echo "   • Restart:       sudo systemctl restart odoo"
echo "   • Stop:          sudo systemctl stop odoo"
echo ""
echo "✅ Django database 'initialdbbintacura' is safe and untouched!"
echo ""
