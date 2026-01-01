#!/bin/bash

echo "🔧 Fixing PaymentReceipt database constraints..."
echo "=================================================="
echo ""

echo "📋 Step 1: Making service_transaction_id nullable..."
python manage.py shell <<EOF
from django.db import connection

with connection.cursor() as cursor:
    # Make service_transaction_id nullable
    cursor.execute("""
        ALTER TABLE payment_receipts 
        ALTER COLUMN service_transaction_id DROP NOT NULL;
    """)
    print("✅ service_transaction_id is now nullable")
    
    # Verify
    cursor.execute("""
        SELECT column_name, is_nullable, data_type
        FROM information_schema.columns
        WHERE table_name = 'payment_receipts' 
          AND column_name = 'service_transaction_id';
    """)
    result = cursor.fetchone()
    print(f"📊 Verification: {result}")

EOF

echo ""
echo "📋 Step 2: Restarting services..."
sudo systemctl restart bintacura
sudo systemctl restart bintacura-celery
sudo systemctl restart bintacura-celerybeat

echo ""
echo "✅ Fix complete! Test payment now:"
echo "   - Online payment: https://bintacura.org/patient/book-appointment/"
echo "   - Onsite payment should now work"
