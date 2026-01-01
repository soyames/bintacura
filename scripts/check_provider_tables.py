import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connections

# Check AWS database
print("=" * 80)
print("PROVIDER TABLES IN AWS (default)")
print("=" * 80)
cursor = connections['default'].cursor()
cursor.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema='public' 
    AND table_name LIKE '%provider%' 
    ORDER BY table_name
""")
aws_tables = cursor.fetchall()
for table in aws_tables:
    print(f"  - {table[0]}")

print(f"\nTotal: {len(aws_tables)} tables")

# Check table structure
if aws_tables:
    print("\n" + "=" * 80)
    print("TABLE STRUCTURES")
    print("=" * 80)
    for table in aws_tables:
        table_name = table[0]
        print(f"\n📋 {table_name}:")
        cursor.execute(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        for col in columns:
            nullable = "NULL" if col[2] == "YES" else "NOT NULL"
            print(f"   - {col[0]}: {col[1]} {nullable}")
