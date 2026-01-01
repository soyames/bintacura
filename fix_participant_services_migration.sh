#!/bin/bash

echo "🔧 Fixing participant_services migration issue..."
echo "================================================="

# Activate virtual environment
source venv/bin/activate

# Check if table exists
echo ""
echo "📋 Step 1: Checking if participant_services table exists..."
python manage.py shell << 'EOF'
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'participant_services'
        );
    """)
    exists = cursor.fetchone()[0]
    if exists:
        print("✅ participant_services table exists")
    else:
        print("❌ participant_services table does NOT exist")
        print("   This is expected - the table was already deleted")
EOF

echo ""
echo "📋 Step 2: Faking the problematic migration..."
python manage.py migrate core 0027 --fake

echo ""
echo "📋 Step 3: Running all pending migrations..."
python manage.py migrate

echo ""
echo "📋 Step 4: Verifying migration state..."
python manage.py showmigrations core | tail -10

echo ""
echo "✅ Migration fix complete!"
echo ""
echo "📋 Next: Restart services with:"
echo "   sudo systemctl restart bintacura"
echo "   sudo systemctl restart bintacura-celery"
echo "   sudo systemctl restart bintacura-celerybeat"
