"""
Sync AWS Database Schema with Frankfurt
Adds missing columns to AWS database tables
"""
import os
import sys
import django

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connections

def execute_sql(database, sql, description):
    """Execute SQL and handle errors gracefully"""
    try:
        with connections[database].cursor() as cursor:
            cursor.execute(sql)
        print(f"   ✓ {description}")
        return True
    except Exception as e:
        if "already exists" in str(e) or "duplicate column" in str(e):
            print(f"   ⚠ {description} - Column already exists")
            return True
        else:
            print(f"   ✗ {description} - Error: {e}")
            return False

def sync_aws_schema():
    """Add missing columns to AWS database"""
    
    print("\n" + "="*80)
    print("AWS DATABASE SCHEMA SYNC")
    print("="*80)
    
    migrations = [
        # 1. appointment_queues
        {
            "table": "appointment_queues",
            "columns": [
                ("provider_id", "ALTER TABLE appointment_queues ADD COLUMN IF NOT EXISTS provider_id UUID NULL"),
            ]
        },
        
        # 2. appointments
        {
            "table": "appointments",
            "columns": [
                ("doctor_uid", "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS doctor_uid UUID NULL"),
                ("facility_id", "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS facility_id UUID NULL"),
                ("patient_uid", "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS patient_uid UUID NULL"),
                ("provider_id", "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS provider_id UUID NULL"),
            ]
        },
        
        # 3. availabilities
        {
            "table": "availabilities",
            "columns": [
                ("last_modified_instance", "ALTER TABLE availabilities ADD COLUMN IF NOT EXISTS last_modified_instance VARCHAR(255) NULL"),
                ("origin_instance", "ALTER TABLE availabilities ADD COLUMN IF NOT EXISTS origin_instance VARCHAR(255) NULL"),
                ("region_code", "ALTER TABLE availabilities ADD COLUMN IF NOT EXISTS region_code VARCHAR(10) NULL"),
                ("sync_hash", "ALTER TABLE availabilities ADD COLUMN IF NOT EXISTS sync_hash VARCHAR(64) NULL"),
            ]
        },
        
        # 4. core_transactions
        {
            "table": "core_transactions",
            "columns": [
                ("currency_local", "ALTER TABLE core_transactions ADD COLUMN IF NOT EXISTS currency_local VARCHAR(3) NOT NULL DEFAULT 'XOF'"),
            ]
        },
        
        # 5. payment_receipts
        {
            "table": "payment_receipts",
            "columns": [
                ("participant_id", "ALTER TABLE payment_receipts ADD COLUMN IF NOT EXISTS participant_id UUID NULL"),
                ("receipt_data", "ALTER TABLE payment_receipts ADD COLUMN IF NOT EXISTS receipt_data JSONB NULL"),
                ("sync_status", "ALTER TABLE payment_receipts ADD COLUMN IF NOT EXISTS sync_status VARCHAR(20) DEFAULT 'pending'"),
                ("sync_version", "ALTER TABLE payment_receipts ADD COLUMN IF NOT EXISTS sync_version INTEGER DEFAULT 1"),
            ]
        },
        
        # 6. service_transactions
        {
            "table": "service_transactions",
            "columns": [
                ("sync_status", "ALTER TABLE service_transactions ADD COLUMN IF NOT EXISTS sync_status VARCHAR(20) DEFAULT 'pending'"),
                ("sync_version", "ALTER TABLE service_transactions ADD COLUMN IF NOT EXISTS sync_version INTEGER DEFAULT 1"),
            ]
        },
    ]
    
    success_count = 0
    total_count = 0
    
    for migration in migrations:
        table = migration["table"]
        print(f"\n📋 Table: {table}")
        
        for col_name, sql in migration["columns"]:
            total_count += 1
            if execute_sql('default', sql, f"Add column '{col_name}'"):
                success_count += 1
    
    print("\n" + "="*80)
    print(f"SYNC COMPLETE: {success_count}/{total_count} columns processed successfully")
    print("="*80)
    
    if success_count == total_count:
        print("✅ All schema updates applied successfully!")
    else:
        print(f"⚠️  {total_count - success_count} columns failed to update")
    
    return success_count == total_count

if __name__ == "__main__":
    try:
        sync_aws_schema()
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
