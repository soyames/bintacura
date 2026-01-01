#!/bin/bash
# BINTACURA Emergency Fix Script
# Run this to check and fix all payment errors

echo "🔧 BINTACURA Emergency Fix - Starting..."
echo "=========================================="
echo ""

# Step 1: Check server logs for errors
echo "📋 Step 1: Checking recent errors..."
echo "-----------------------------------"
sudo journalctl -u bintacura -n 100 --no-pager | grep -i "error\|exception\|failed" | tail -20

echo ""
echo "📋 Step 2: Checking migration status..."
echo "----------------------------------------"
cd /home/ec2-user/bintacura
source venv/bin/activate
python manage.py showmigrations appointments | grep -E "\[ \]|\[X\]"

echo ""
echo "📋 Step 3: Running migrations..."
echo "---------------------------------"
python manage.py makemigrations
python manage.py migrate

echo ""
echo "📋 Step 4: Checking database columns..."
echo "----------------------------------------"
python manage.py dbshell <<EOF
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'appointments' 
AND column_name IN ('version', 'last_synced_at', 'is_deleted');
\q
EOF

echo ""
echo "📋 Step 5: Verifying Django settings..."
echo "----------------------------------------"
python manage.py check --deploy

echo ""
echo "📋 Step 6: Testing imports..."
echo "------------------------------"
python manage.py shell <<EOF
try:
    from payments.service_payment_service import ServicePaymentService
    print("✅ ServicePaymentService imported successfully")
    print("   Methods:", [m for m in dir(ServicePaymentService) if not m.startswith('_')])
except Exception as e:
    print("❌ ServicePaymentService import failed:", str(e))

try:
    from payments.fedapay_webhook_handler import FedaPayWalletService
    print("✅ FedaPayWalletService imported successfully")
    print("   Methods:", [m for m in dir(FedaPayWalletService) if not m.startswith('_')])
except Exception as e:
    print("❌ FedaPayWalletService import failed:", str(e))

try:
    from queue_management.services import QueueManagementService
    print("✅ QueueManagementService imported successfully")
except Exception as e:
    print("❌ QueueManagementService import failed:", str(e))

exit()
EOF

echo ""
echo "📋 Step 7: Restarting all services..."
echo "--------------------------------------"
sudo systemctl restart bintacura
sleep 2
sudo systemctl restart bintacura-celery
sleep 1
sudo systemctl restart bintacura-celerybeat

echo ""
echo "📋 Step 8: Checking service status..."
echo "--------------------------------------"
sudo systemctl status bintacura --no-pager | head -15

echo ""
echo "📋 Step 9: Testing API endpoint..."
echo "-----------------------------------"
curl -s http://localhost/api/v1/doctor/data/ | head -100

echo ""
echo "=========================================="
echo "🎯 Fix Complete! Check output above for errors."
echo ""
echo "Next steps:"
echo "1. If you see 'version column missing' - run manual SQL fix"
echo "2. If you see import errors - check file paths"
echo "3. Test booking at: https://bintacura.org/patient/book-appointment/"
echo ""
echo "To view live logs: sudo journalctl -u bintacura -f"
echo "=========================================="
