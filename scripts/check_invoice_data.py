"""
Check invoice/receipt data in both databases
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connections
from django.db.utils import OperationalError

def check_database(db_alias, appointment_ids):
    """Check if receipts exist for given appointment IDs"""
    print(f"\n{'='*80}")
    print(f"Checking {db_alias.upper()} Database")
    print(f"{'='*80}")
    
    try:
        with connections[db_alias].cursor() as cursor:
            # Check appointments table structure
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'appointments'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()
            print(f"\n✓ Appointments table has {len(columns)} columns")
            
            # Check if appointments exist
            placeholders = ','.join(['%s'] * len(appointment_ids))
            cursor.execute(f"""
                SELECT id, patient_id, doctor_id, appointment_date, 
                       payment_status, payment_method
                FROM appointments
                WHERE id::text IN ({placeholders});
            """, appointment_ids)
            appointments = cursor.fetchall()
            print(f"\n📋 Found {len(appointments)} appointments:")
            for apt in appointments:
                print(f"   ID: {apt[0]}")
                print(f"   Patient: {apt[1]}")
                print(f"   Doctor: {apt[2]}")
                print(f"   Date: {apt[3]}")
                print(f"   Payment Status: {apt[4]}")
                print(f"   Payment Method: {apt[5]}")
                print()
            
            # Check payment_receipts table
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'payment_receipts';
            """)
            if cursor.fetchone():
                # First check what columns exist
                cursor.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'payment_receipts'
                    ORDER BY ordinal_position;
                """)
                receipt_columns = cursor.fetchall()
                print(f"\n💳 payment_receipts table columns:")
                for col in receipt_columns:
                    print(f"   - {col[0]}: {col[1]}")
                
                # Now query the receipts
                cursor.execute("""
                    SELECT * FROM payment_receipts LIMIT 5;
                """)
                receipts = cursor.fetchall()
                print(f"\n💰 Sample payment receipts ({len(receipts)} rows):")
                for receipt in receipts:
                    print(f"   {receipt}")
                    print()
            else:
                print("\n⚠️  payment_receipts table does NOT exist!")
            
    except OperationalError as e:
        print(f"\n❌ Error connecting to {db_alias}: {e}")
    except Exception as e:
        print(f"\n❌ Error querying {db_alias}: {e}")

def main():
    # Sample appointment IDs from the error messages
    appointment_ids = [
        '80e7e74c-a75b-4db1-8f7f-1635461eba21',
        'dc0866fc-847e-4cdb-a9ef-cd51eae99dd6',
        '0be3ab03-66f6-4a9d-8a3e-d8a2c7db0e8c',
        '0d84ba83-66f4-4989-8c72-dca0d87f6ea3',
        '262214cf-9356-4410-86c1-57699fc8f34c',
        'eca27867-325d-4708-8f9e-46264ce9ab48',
        '82be9b54-1e38-42a6-bea7-aebe1b97fd4d',
        '0f2fdeea-69a9-4c8a-9715-ac84c5b6e189',
        '734d97e1-f72f-49bd-8aba-b9b251494940'
    ]
    
    print("="*80)
    print("INVOICE DATA CHECK")
    print("="*80)
    print(f"\nChecking {len(appointment_ids)} appointment IDs")
    
    # Check both databases
    check_database('default', appointment_ids)
    check_database('frankfurt', appointment_ids)
    
    print("\n" + "="*80)
    print("CHECK COMPLETE")
    print("="*80)

if __name__ == '__main__':
    main()
