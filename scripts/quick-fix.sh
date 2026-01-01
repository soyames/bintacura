#!/bin/bash
# Quick Fix Script for Payment Errors
# Run this on your AWS server

echo "🔧 BINTACURA Payment Fix Script"
echo "================================"
echo ""

# Navigate to project
cd /home/ec2-user/bintacura || exit 1
source venv/bin/activate

echo "✅ Step 1: Checking migrations..."
python manage.py showmigrations appointments | grep "\[ \]"

echo ""
echo "✅ Step 2: Running migrations..."
python manage.py migrate

echo ""
echo "✅ Step 3: Verifying database..."
python manage.py check

echo ""
echo "✅ Step 4: Restarting services..."
sudo systemctl restart bintacura
sudo systemctl restart bintacura-celery
sudo systemctl restart bintacura-celerybeat

echo ""
echo "✅ Step 5: Checking service status..."
sudo systemctl status bintacura --no-pager | head -10

echo ""
echo "🎉 Done! Check for errors above."
echo ""
echo "To test payments:"
echo "1. Try booking with 'Payer sur place (Cash)'"
echo "2. Try booking with 'Payer En ligne'"
echo ""
echo "If still errors, run: sudo journalctl -u bintacura -n 100"
