"""
Verification command to check database table consistency across all database instances
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connections
from django.conf import settings

print("\n" + "="*80)
print("DATABASE TABLE VERIFICATION REPORT")
print("="*80 + "\n")

# Get all configured databases
databases = settings.DATABASES.keys()

# Store table info for each database
db_info = {}

for db_name in databases:
    try:
        with connections[db_name].cursor() as cursor:
            # Get table count
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema='public' AND table_type='BASE TABLE'
            """)
            table_count = cursor.fetchone()[0]
            
            # Get list of tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema='public' AND table_type='BASE TABLE'
                ORDER BY table_name
            """)
            tables = set([row[0] for row in cursor.fetchall()])
            
            db_info[db_name] = {
                'count': table_count,
                'tables': tables,
                'config': settings.DATABASES[db_name]
            }
            
            print(f"✓ {db_name.upper():15} - {table_count:3} tables")
            print(f"  Host: {db_info[db_name]['config'].get('HOST', 'N/A')}")
            print(f"  Name: {db_info[db_name]['config'].get('NAME', 'N/A')}\n")
    except Exception as e:
        print(f"✗ {db_name.upper():15} - ERROR: {str(e)}\n")
        db_info[db_name] = {'count': 0, 'tables': set(), 'error': str(e)}

# Compare tables across databases
if len(db_info) > 1:
    print("=" *80)
    print("TABLE COMPARISON")
    print("="*80 + "\n")
    
    # Get all unique tables
    all_tables = set()
    for db_name, info in db_info.items():
        if 'error' not in info:
            all_tables.update(info['tables'])
    
    # Find tables missing in any database
    for db_name, info in db_info.items():
        if 'error' not in info:
            missing = all_tables - info['tables']
            extra = info['tables'] - all_tables
            
            if missing:
                print(f"\n⚠️  {db_name.upper()} - MISSING {len(missing)} TABLES:")
                for table in sorted(missing)[:10]:  # Show first 10
                    print(f"   - {table}")
                if len(missing) > 10:
                    print(f"   ... and {len(missing) - 10} more")
            
            if extra:
                print(f"\n✓ {db_name.upper()} - HAS {len(extra)} EXTRA TABLES:")
                for table in sorted(extra)[:10]:
                    print(f"   - {table}")
                if len(extra) > 10:
                    print(f"   ... and {len(extra) - 10} more")

# Check if all databases have the same tables
print("\n" + "="*80)
all_same = len(set(info['count'] for info in db_info.values() if 'error' not in info)) == 1
if all_same:
    print("✅ STATUS: ALL DATABASES HAVE CONSISTENT TABLE COUNTS!")
else:
    print("⚠️  STATUS: DATABASES HAVE DIFFERENT TABLE COUNTS - REVIEW REQUIRED")
print("="*80 + "\n")
