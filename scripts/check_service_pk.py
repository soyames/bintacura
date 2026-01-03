import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("""
    SELECT column_name, data_type, is_nullable 
    FROM information_schema.columns 
    WHERE table_name = 'participant_services' 
    AND column_name IN ('id', 'uid')
    ORDER BY ordinal_position
""")
columns = cursor.fetchall()
print("participant_services PK columns:")
for col in columns:
    print(f"  {col[0]:20} {col[1]:20} NULL:{col[2]}")

print("\nChecking foreign key constraint...")
cursor.execute("""
    SELECT
        tc.constraint_name,
        tc.table_name,
        kcu.column_name,
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
      AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
      AND ccu.table_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_name = 'appointments'
      AND kcu.column_name = 'service_id'
""")
fk = cursor.fetchone()
if fk:
    print(f"  FK: {fk[0]}")
    print(f"  From: {fk[1]}.{fk[2]}")
    print(f"  To: {fk[3]}.{fk[4]}")
else:
    print("  No FK constraint found!")
