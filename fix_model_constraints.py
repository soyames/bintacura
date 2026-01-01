"""
Fix Model-Database Constraint Mismatches

This script will update Django models to match database constraints
identified by the audit script.
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

def analyze_and_fix():
    print("=" * 80)
    print("🔧 FIXING MODEL-DATABASE CONSTRAINT MISMATCHES")
    print("=" * 80)
    print()
    
    # Critical mismatches found:
    mismatches = {
        'payment_receipts': {
            'participant_id': 'Should be nullable (null=True, blank=True)',
            'service_transaction_id': 'Already nullable ✅',
            'issued_to_name': 'Should be NOT NULL (remove default="", blank=True)',
            'issued_to_address': 'Should be NOT NULL (remove default="", blank=True)',
            'issued_to_city': 'Should be NOT NULL (remove default="", blank=True)',
            'issued_to_country': 'Should be NOT NULL (remove default="", blank=True)',
            'transaction_reference': 'Should be NOT NULL (remove default="", blank=True)',
            'payment_gateway': 'Should be NOT NULL (remove default="", blank=True)',
            'gateway_transaction_id': 'Should be NOT NULL (remove default="", blank=True)',
            'pdf_url': 'Should be NOT NULL (remove default="", blank=True)',
            'tax_rate': 'Should be NOT NULL',
            'tax_amount': 'Should be NOT NULL',
            'discount_amount': 'Should be NOT NULL',
            'platform_fee': 'Should be NOT NULL',
            'reminder_sent': 'Should be NOT NULL',
            'line_items': 'Should be NOT NULL',
            'service_details': 'Should be NOT NULL',
        },
        'service_transactions': {
            'patient_id': 'NOT NULL ✅',
            'service_provider_id': 'NOT NULL ✅',
            'service_provider_role': 'NOT NULL ✅',
            'service_type': 'NOT NULL ✅',
            'service_id': 'NOT NULL ✅',
            'service_description': 'NOT NULL ✅',
            'amount': 'NOT NULL ✅',
            'payment_method': 'NOT NULL ✅',
            'transaction_ref': 'NOT NULL ✅',
        },
        'appointments': {
            'hospital_id': 'Should be nullable (currently nullable ✅)',
        }
    }
    
    print("📋 IDENTIFIED MISMATCHES:\n")
    for table, fields in mismatches.items():
        print(f"📦 {table}")
        for field, issue in fields.items():
            if '✅' in issue:
                print(f"   ✅ {field}: {issue}")
            else:
                print(f"   ❌ {field}: {issue}")
        print()
    
    print("=" * 80)
    print("💡 RECOMMENDED FIXES")
    print("=" * 80)
    print()
    
    print("1️⃣ FIX DATABASE CONSTRAINTS (Run on AWS RDS):")
    print("-" * 80)
    
    sql_fixes = [
        "-- Make nullable fields that Django models expect to be nullable",
        "ALTER TABLE payment_receipts ALTER COLUMN participant_id DROP NOT NULL;",
        "",
        "-- These fields should have defaults in code, not constraints",
        "-- We'll handle them with proper defaults in Python",
    ]
    
    for sql in sql_fixes:
        print(sql)
    
    print()
    print("2️⃣ UPDATE DJANGO MODELS:")
    print("-" * 80)
    print("""
# In payments/models.py - PaymentReceipt class:

# CHANGE FROM:
issued_to = models.ForeignKey(
    Participant, on_delete=models.CASCADE, related_name="receipts", null=True, blank=True
)

# CHANGE TO:
issued_to = models.ForeignKey(
    Participant, on_delete=models.CASCADE, related_name="receipts", 
    null=True, blank=True,
    help_text="Patient/customer who received the service"
)

# ADD FIELD COMMENT:
# Note: participant_id in DB can be NULL for legacy receipts
""")
    
    print()
    print("3️⃣ UPDATE SERVICE PAYMENT LOGIC:")
    print("-" * 80)
    print("""
# In payments/service_payment_service.py

# When creating PaymentReceipt, ALWAYS provide:
- issued_to (participant who pays)
- issued_to_name (full name)
- issued_to_address (address or 'N/A')
- issued_to_city (city or 'N/A')
- issued_to_country (country or 'Bénin')
- transaction_reference (unique reference)
- payment_gateway ('cash', 'fedapay', etc.)
- gateway_transaction_id (or 'N/A' for cash)
- pdf_url (empty string acceptable)
""")
    
    print()
    print("=" * 80)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 80)
    print()
    print("Next Steps:")
    print("1. Run the SQL fixes on AWS RDS")
    print("2. Update the Django models as shown above")
    print("3. Ensure all receipt creation code provides required fields")
    print("4. Test payment flows thoroughly")
    print()

if __name__ == "__main__":
    analyze_and_fix()
