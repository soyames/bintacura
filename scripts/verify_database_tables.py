"""
Verify and create all database tables for AWS database
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection
from django.core.management import call_command

print("\nChecking database tables...")
print("="*70)

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    """)
    count = cursor.fetchone()[0]
    print(f"Total tables in database: {count}")
    
    # Check for specific missing tables
    missing_tables = [
        'hospital_admissions',
        'hospital_beds',
        'hospital_staff',
        'hospital_bills',
        'participant_phones',
        'service_catalog',
        'gateway_transactions',
        'service_transactions',
        'journal_entries',
        'projects',
    ]
    
    print(f"\nChecking critical tables:")
    for table in missing_tables:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            );
        """, [table])
        exists = cursor.fetchone()[0]
        status = "✅" if exists else "❌"
        print(f"  {status} {table}")

print("\n" + "="*70)
print("\nTo fix missing tables, run:")
print("  python manage.py migrate --run-syncdb --database=default --fake-initial")
