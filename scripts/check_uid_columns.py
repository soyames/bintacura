import os
import sys
import django

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

def check_uid_columns():
    with connection.cursor() as cursor:
        # Check appointments table
        cursor.execute("""
            SELECT column_name, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'appointments' AND column_name = 'uid'
        """)
        app_result = cursor.fetchone()
        
        print("🔍 Appointments table 'uid' column:")
        if app_result:
            print(f"   ✅ EXISTS - nullable: {app_result[1]}, default: {app_result[2]}")
        else:
            print("   ❌ DOES NOT EXIST")
        
        # Check core_transactions table
        cursor.execute("""
            SELECT column_name, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'core_transactions' AND column_name = 'uid'
        """)
        txn_result = cursor.fetchone()
        
        print("\n🔍 core_transactions table 'uid' column:")
        if txn_result:
            print(f"   ✅ EXISTS - nullable: {txn_result[1]}, default: {txn_result[2]}")
        else:
            print("   ❌ DOES NOT EXIST")

if __name__ == '__main__':
    check_uid_columns()
