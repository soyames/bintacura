"""
Fix critical database constraint issues identified in audit
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

def fix_payment_receipts_constraints():
    """Fix payment_receipts constraints to allow NULL where needed"""
    print("\n🔧 Fixing payment_receipts constraints...")
    
    with connection.cursor() as cursor:
        # Allow NULL for service_transaction_id (not all receipts have transactions)
        cursor.execute("""
            ALTER TABLE payment_receipts 
            ALTER COLUMN service_transaction_id DROP NOT NULL;
        """)
        print("   ✅ service_transaction_id now allows NULL")
        
        # Allow NULL for transaction_id  
        cursor.execute("""
            ALTER TABLE payment_receipts 
            ALTER COLUMN transaction_id DROP NOT NULL;
        """)
        print("   ✅ transaction_id now allows NULL")
        
        # Allow NULL for created_by_instance
        cursor.execute("""
            ALTER TABLE payment_receipts 
            ALTER COLUMN created_by_instance DROP NOT NULL;
        """)
        print("   ✅ created_by_instance now allows NULL")
        
        # Allow NULL for modified_by_instance
        cursor.execute("""
            ALTER TABLE payment_receipts 
            ALTER COLUMN modified_by_instance DROP NOT NULL;
        """)
        print("   ✅ modified_by_instance now allows NULL")
        
        # Allow NULL for subtotal
        cursor.execute("""
            ALTER TABLE payment_receipts 
            ALTER COLUMN subtotal DROP NOT NULL;
        """)
        print("   ✅ subtotal now allows NULL")
        
        # Allow NULL for total_amount
        cursor.execute("""
            ALTER TABLE payment_receipts 
            ALTER COLUMN total_amount DROP NOT NULL;
        """)
        print("   ✅ total_amount now allows NULL")

def fix_appointments_hospital_column():
    """Add hospital_id column if it doesn't exist"""
    print("\n🔧 Fixing appointments.hospital_id column...")
    
    with connection.cursor() as cursor:
        # Check if column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='appointments' 
            AND column_name='hospital_id';
        """)
        
        if not cursor.fetchone():
            print("   Adding hospital_id column...")
            cursor.execute("""
                ALTER TABLE appointments 
                ADD COLUMN hospital_id UUID NULL;
            """)
            print("   ✅ hospital_id column added")
        else:
            print("   ℹ️  hospital_id column already exists")

def fix_appointments_constraints():
    """Fix appointments table constraints"""
    print("\n🔧 Fixing appointments constraints...")
    
    with connection.cursor() as cursor:
        # Allow NULL for created_by_instance
        cursor.execute("""
            ALTER TABLE appointments 
            ALTER COLUMN created_by_instance DROP NOT NULL;
        """)
        print("   ✅ created_by_instance now allows NULL")
        
        # Allow NULL for modified_by_instance
        cursor.execute("""
            ALTER TABLE appointments 
            ALTER COLUMN modified_by_instance DROP NOT NULL;
        """)
        print("   ✅ modified_by_instance now allows NULL")

def fix_appointment_queues_constraints():
    """Fix appointment_queues table constraints"""
    print("\n🔧 Fixing appointment_queues constraints...")
    
    with connection.cursor() as cursor:
        # Allow NULL for created_by_instance
        cursor.execute("""
            ALTER TABLE appointment_queues 
            ALTER COLUMN created_by_instance DROP NOT NULL;
        """)
        print("   ✅ created_by_instance now allows NULL")
        
        # Allow NULL for modified_by_instance
        cursor.execute("""
            ALTER TABLE appointment_queues 
            ALTER COLUMN modified_by_instance DROP NOT NULL;
        """)
        print("   ✅ modified_by_instance now allows NULL")

def main():
    print("=" * 80)
    print("🔧 FIXING DATABASE CONSTRAINTS")
    print("=" * 80)
    
    try:
        fix_payment_receipts_constraints()
        fix_appointments_hospital_column()
        fix_appointments_constraints()
        fix_appointment_queues_constraints()
        
        print("\n" + "=" * 80)
        print("✅ ALL FIXES APPLIED SUCCESSFULLY!")
        print("=" * 80)
        print("\n📋 Next steps:")
        print("   1. Restart Django server")
        print("   2. Test payment booking (both online and cash)")
        print("   3. Check for any remaining errors")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
