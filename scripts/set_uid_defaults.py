import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()

print("\n" + "="*70)
print("SETTING DATABASE-LEVEL UUID DEFAULTS")
print("="*70 + "\n")

tables = ['appointments', 'core_transactions', 'payment_receipts']

for table in tables:
    try:
        cursor.execute(f"ALTER TABLE {table} ALTER COLUMN uid SET DEFAULT gen_random_uuid()")
        print(f"✅ {table}.uid - DEFAULT set to gen_random_uuid()")
    except Exception as e:
        print(f"❌ {table}.uid - ERROR: {e}")

print("\n" + "="*70)
print("COMPLETE")
print("="*70 + "\n")
