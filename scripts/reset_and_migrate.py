"""
Reset migration history and recreate all tables for AWS database
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection
from django.core.management import call_command

print("\n" + "="*70)
print("RESETTING MIGRATION HISTORY AND RECREATING TABLES")
print("="*70)

apps_to_fix = [
    'hospital',
    'payments',
    'financial',
    'pharmacy',
    'insurance',
    'communication',
    'health_records',
    'transport',
    'hr',
]

print("\nStep 1: Clearing migration history for apps with missing tables...")
with connection.cursor() as cursor:
    for app in apps_to_fix:
        cursor.execute("""
            DELETE FROM django_migrations WHERE app = %s
        """, [app])
        print(f"  ✅ Cleared {app}")

connection.commit()

print("\nStep 2: Re-applying migrations...")
try:
    call_command('migrate', '--database=default', '--run-syncdb')
    print("✅ Migrations applied successfully!")
except Exception as e:
    print(f"❌ Error applying migrations: {e}")

print("\n" + "="*70)
print("Run verify_database_tables.py to check results")
print("="*70)
