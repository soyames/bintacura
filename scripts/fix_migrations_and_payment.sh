#!/bin/bash
# Fix Migration and Payment Issues
# Run this on your EC2 server

set -e  # Exit on error

echo "🔧 BINTACURA Migration & Payment Fix Script"
echo "==========================================="
echo ""

# Activate virtual environment
source venv/bin/activate

echo "1️⃣ Faking problematic migrations..."
echo "-----------------------------------"
python manage.py migrate appointments 0013 --fake
python manage.py migrate appointments 0014 --fake
python manage.py migrate appointments 0015 --fake
python manage.py migrate appointments 0016 --fake
python manage.py migrate appointments 0017 --fake

echo ""
echo "2️⃣ Applying remaining migrations..."
echo "-----------------------------------"
python manage.py migrate

echo ""
echo "3️⃣ Checking database columns..."
echo "-----------------------------------"
python manage.py shell <<EOF
from django.db import connection
cursor = connection.cursor()

# Check appointments table
cursor.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name='appointments' 
    ORDER BY column_name;
""")
cols = [row[0] for row in cursor.fetchall()]
print(f"Appointments columns: {len(cols)}")
print("Has 'version':", 'version' in cols)
print("Has 'created_by_instance':", 'created_by_instance' in cols)
print("Has 'idempotency_key':", 'idempotency_key' in cols)
EOF

echo ""
echo "4️⃣ Restarting services..."
echo "-----------------------------------"
sudo systemctl restart bintacura
sudo systemctl restart bintacura-celery
sudo systemctl restart bintacura-celerybeat
sudo systemctl restart nginx

echo ""
echo "5️⃣ Waiting for services to start..."
sleep 5

echo ""
echo "6️⃣ Checking service status..."
echo "-----------------------------------"
sudo systemctl status bintacura --no-pager | head -15

echo ""
echo "✅ Fix script completed!"
echo ""
echo "📝 Next steps:"
echo "   1. Test payment: https://bintacura.org/patient/book-appointment/"
echo "   2. Check logs: sudo journalctl -u bintacura -f"
echo "   3. If still issues, check: sudo journalctl -u bintacura -n 50"
