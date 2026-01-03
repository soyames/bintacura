import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE '%service%' ORDER BY table_name")
tables = cursor.fetchall()
print("Tables containing 'service':")
for table in tables:
    print(f"  - {table[0]}")
