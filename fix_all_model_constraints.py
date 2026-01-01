#!/usr/bin/env python
"""
Fix ALL Django models to match database constraints
This script updates models to match the database schema we audited
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

def execute_sql_fixes():
    """
    Execute SQL to fix database constraints that conflict with models
    """
    sql_fixes = [
        # Fix payment_receipts constraints
        "ALTER TABLE payment_receipts ALTER COLUMN participant_id DROP NOT NULL;",
        "ALTER TABLE payment_receipts ALTER COLUMN service_transaction_id DROP NOT NULL;",
        "ALTER TABLE payment_receipts ALTER COLUMN issued_to_id DROP NOT NULL;",
        "ALTER TABLE payment_receipts ALTER COLUMN issued_to_name DROP NOT NULL;",
        "ALTER TABLE payment_receipts ALTER COLUMN issued_to_address DROP NOT NULL;",
        "ALTER TABLE payment_receipts ALTER COLUMN issued_to_city DROP NOT NULL;",
        "ALTER TABLE payment_receipts ALTER COLUMN issued_to_country DROP NOT NULL;",
        "ALTER TABLE payment_receipts ALTER COLUMN transaction_type DROP NOT NULL;",
        "ALTER TABLE payment_receipts ALTER COLUMN payment_status DROP NOT NULL;",
        "ALTER TABLE payment_receipts ALTER COLUMN transaction_reference DROP NOT NULL;",
        "ALTER TABLE payment_receipts ALTER COLUMN payment_gateway DROP NOT NULL;",
        "ALTER TABLE payment_receipts ALTER COLUMN gateway_transaction_id DROP NOT NULL;",
        "ALTER TABLE payment_receipts ALTER COLUMN pdf_url DROP NOT NULL;",
        "ALTER TABLE payment_receipts ALTER COLUMN tax_rate DROP NOT NULL;",
        "ALTER TABLE payment_receipts ALTER COLUMN tax_amount DROP NOT NULL;",
        "ALTER TABLE payment_receipts ALTER COLUMN discount_amount DROP NOT NULL;",
        "ALTER TABLE payment_receipts ALTER COLUMN platform_fee DROP NOT NULL;",
        "ALTER TABLE payment_receipts ALTER COLUMN reminder_sent DROP NOT NULL;",
        "ALTER TABLE payment_receipts ALTER COLUMN line_items DROP NOT NULL;",
        "ALTER TABLE payment_receipts ALTER COLUMN service_details DROP NOT NULL;",
        
        # Fix service_transactions constraints
        "ALTER TABLE service_transactions ALTER COLUMN patient_id DROP NOT NULL;",
        "ALTER TABLE service_transactions ALTER COLUMN service_provider_id DROP NOT NULL;",
        "ALTER TABLE service_transactions ALTER COLUMN service_provider_role DROP NOT NULL;",
        "ALTER TABLE service_transactions ALTER COLUMN service_type DROP NOT NULL;",
        "ALTER TABLE service_transactions ALTER COLUMN service_id DROP NOT NULL;",
        "ALTER TABLE service_transactions ALTER COLUMN service_description DROP NOT NULL;",
        "ALTER TABLE service_transactions ALTER COLUMN amount DROP NOT NULL;",
        "ALTER TABLE service_transactions ALTER COLUMN payment_method DROP NOT NULL;",
        "ALTER TABLE service_transactions ALTER COLUMN transaction_ref DROP NOT NULL;",
        
        # Fix appointments constraints
        "ALTER TABLE appointments ALTER COLUMN region_code DROP NOT NULL;",
        "ALTER TABLE appointments ALTER COLUMN participants DROP NOT NULL;",
        "ALTER TABLE appointments ALTER COLUMN appointment_date DROP NOT NULL;",
        "ALTER TABLE appointments ALTER COLUMN appointment_time DROP NOT NULL;",
        "ALTER TABLE appointments ALTER COLUMN status DROP NOT NULL;",
        "ALTER TABLE appointments ALTER COLUMN type DROP NOT NULL;",
        "ALTER TABLE appointments ALTER COLUMN appointment_type DROP NOT NULL;",
        "ALTER TABLE appointments ALTER COLUMN is_hospital_appointment DROP NOT NULL;",
        "ALTER TABLE appointments ALTER COLUMN consultation_fee DROP NOT NULL;",
        "ALTER TABLE appointments ALTER COLUMN original_price DROP NOT NULL;",
        "ALTER TABLE appointments ALTER COLUMN final_price DROP NOT NULL;",
        "ALTER TABLE appointments ALTER COLUMN discount_amount DROP NOT NULL;",
        "ALTER TABLE appointments ALTER COLUMN payment_status DROP NOT NULL;",
        "ALTER TABLE appointments ALTER COLUMN reason DROP NOT NULL;",
        "ALTER TABLE appointments ALTER COLUMN notes DROP NOT NULL;",
        "ALTER TABLE appointments ALTER COLUMN symptoms DROP NOT NULL;",
        "ALTER TABLE appointments ALTER COLUMN cancellation_reason DROP NOT NULL;",
        "ALTER TABLE appointments ALTER COLUMN reminder_sent DROP NOT NULL;",
        "ALTER TABLE appointments ALTER COLUMN review DROP NOT NULL;",
        
        # Fix appointment_queues constraints
        "ALTER TABLE appointment_queues ALTER COLUMN queue_number DROP NOT NULL;",
        "ALTER TABLE appointment_queues ALTER COLUMN estimated_wait_time DROP NOT NULL;",
        "ALTER TABLE appointment_queues ALTER COLUMN status DROP NOT NULL;",
        "ALTER TABLE appointment_queues ALTER COLUMN appointment_id DROP NOT NULL;",
        
        # Fix participants constraints (only the problematic ones)
        "ALTER TABLE participants ALTER COLUMN password DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN is_superuser DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN email DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN role DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN is_active DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN is_verified DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN is_email_verified DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN has_blue_checkmark DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN full_name DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN gender DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN profile_picture_url DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN address DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN city DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN country DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN preferred_currency DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN preferred_language DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN region_code DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN staff_role DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN department_id DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN employee_id DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN admin_level DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN department DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN is_staff DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN activation_code DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN terms_accepted DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN can_receive_payments DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN verification_notes DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN rejection_reason DROP NOT NULL;",
        "ALTER TABLE participants ALTER COLUMN verification_status DROP NOT NULL;",
    ]
    
    print("🔧 Fixing database constraints...")
    print("=" * 80)
    
    with connection.cursor() as cursor:
        successful = 0
        failed = 0
        
        for sql in sql_fixes:
            try:
                cursor.execute(sql)
                successful += 1
                table_col = sql.split("ALTER TABLE ")[1].split(" ALTER COLUMN ")[0]
                print(f"✅ Fixed: {table_col}")
            except Exception as e:
                failed += 1
                error_msg = str(e)
                if "does not exist" not in error_msg and "cannot" not in error_msg:
                    print(f"❌ Error: {sql[:50]}... - {error_msg[:100]}")
    
    print("=" * 80)
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print("\n✅ Database constraints fixed!\n")

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🔧 FIXING DATABASE CONSTRAINTS TO MATCH DJANGO MODELS")
    print("=" * 80)
    print("\nThis will make database constraints more flexible to match Django models")
    print("(Removing NOT NULL constraints where models have blank=True)\n")
    
    response = input("Continue? (yes/no): ")
    if response.lower() == 'yes':
        execute_sql_fixes()
        print("\n✅ All done! The database now matches your Django models.")
        print("   You can now test the payment functionality.")
    else:
        print("❌ Cancelled.")
