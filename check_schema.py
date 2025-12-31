import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connections

for db_name in ['default', 'frankfurt']:
    print(f"\n{'='*60}")
    print(f"DATABASE: {db_name}")
    print(f"{'='*60}")
    
    cursor = connections[db_name].cursor()
    
    # Check doctor_services
    print("\nDOCTOR_SERVICES columns:")
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name='doctor_services' 
        ORDER BY ordinal_position
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    # Check doctor_data
    print("\nDOCTOR_DATA columns:")
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name='doctor_data' 
        ORDER BY ordinal_position
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
