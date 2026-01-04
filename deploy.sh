#!/bin/bash
echo "=== BintaCura Deployment Started ==="
echo "Time: $(date)"

cd /home/ec2-user/bintacura

# Activate venv
source venv/bin/activate

# Pull latest code
echo "Pulling from GitHub..."
git pull origin main

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt --quiet

# Run migrations
echo "Migrating AWS RDS..."
python manage.py migrate --database=default

echo "Migrating Render..."
python manage.py migrate --database=frankfurt

# Collect static
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Restart services
echo "Restarting services..."
sudo systemctl restart bintacura
sudo systemctl restart bintacura-celery
sudo systemctl restart bintacura-celerybeat
sudo systemctl reload nginx

echo "=== Deployment Complete ==="
echo "Site: https://bintacura.org"
