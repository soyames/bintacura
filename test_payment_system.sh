#!/bin/bash

echo "🧪 Testing Payment System"
echo "=========================="
echo ""

echo "📋 Step 1: Testing Currency Conversion Service..."
python3 manage.py shell <<'EOF'
from currency_converter.services import CurrencyConverterService
from decimal import Decimal

print("\n🔍 Testing CurrencyConverterService.convert()...")
print("=" * 60)

# Test 1: XOF to XOF (same currency)
result = CurrencyConverterService.convert(Decimal('1000'), 'XOF', 'XOF')
print(f"\n✅ Test 1: XOF to XOF")
print(f"   Result type: {type(result)}")
print(f"   Result: {result}")
assert isinstance(result, dict), "Result should be a dict"
assert 'converted_amount' in result, "Result should have 'converted_amount' key"
print(f"   Converted amount: {result['converted_amount']}")

# Test 2: XOF to USD
result = CurrencyConverterService.convert(Decimal('1000'), 'XOF', 'USD')
print(f"\n✅ Test 2: XOF to USD")
print(f"   Result: {result}")
print(f"   Converted amount: {result['converted_amount']}")
print(f"   Rate: {result['rate']}")

# Test 3: Get participant currency (default)
try:
    from django.conf import settings
    default_currency = getattr(settings, 'DEFAULT_CURRENCY', 'XOF')
    print(f"\n✅ Test 3: Default Currency")
    print(f"   Default currency: {default_currency}")
except Exception as e:
    print(f"\n❌ Test 3 Failed: {e}")

print("\n" + "=" * 60)
print("✅ All currency conversion tests passed!")
EOF

echo ""
echo "📋 Step 2: Checking appointment models..."
python3 manage.py shell <<'EOF'
from appointments.models import Appointment
from django.db import connection

print("\n🔍 Checking Appointment model fields...")
print("=" * 60)

# Check if version column exists
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='appointments' 
        AND column_name IN ('version', 'created_by_instance', 'payment_method');
    """)
    columns = [row[0] for row in cursor.fetchall()]
    
print(f"\n✅ Found columns: {columns}")

if 'version' in columns:
    print("   ✅ version column exists")
else:
    print("   ❌ version column missing")
    
if 'created_by_instance' in columns:
    print("   ✅ created_by_instance column exists")
else:
    print("   ❌ created_by_instance column missing")
    
if 'payment_method' in columns:
    print("   ✅ payment_method column exists")
else:
    print("   ❌ payment_method column missing")

print("\n" + "=" * 60)
EOF

echo ""
echo "📋 Step 3: Testing payment methods..."
python3 manage.py shell <<'EOF'
from appointments.models import Appointment

print("\n🔍 Testing Appointment Payment Methods...")
print("=" * 60)

# Check payment method choices
choices = Appointment.PAYMENT_METHOD_CHOICES if hasattr(Appointment, 'PAYMENT_METHOD_CHOICES') else []
print(f"\n✅ Payment method choices:")
for choice in choices:
    print(f"   - {choice[0]}: {choice[1]}")

print("\n" + "=" * 60)
EOF

echo ""
echo "📋 Step 4: Verifying all migrations..."
python3 manage.py showmigrations appointments | tail -20

echo ""
echo "✅ Payment System Test Complete!"
echo ""
echo "📝 Next Steps:"
echo "   1. Try booking an appointment with 'Payer sur place' (onsite payment)"
echo "   2. Try booking with 'Payer En ligne' (online payment)"
echo "   3. Monitor logs: sudo journalctl -u bintacura -f"
echo ""
