import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("""
    SELECT column_name, data_type, is_nullable, column_default 
    FROM information_schema.columns 
    WHERE table_name = 'appointments' 
    ORDER BY ordinal_position
""")
columns = cursor.fetchall()
print("Appointments table schema:")
for col in columns:
    print(f"  {col[0]:30} {col[1]:20} NULL:{col[2]:5} DEFAULT:{col[3]}")
