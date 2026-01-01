import os
import sys
import django

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

def check_columns():
    with connection.cursor() as cursor:
        cursor.execute("""
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'appointments'
AND column_name IN ('id', 'uid')
ORDER BY ordinal_position;
        """)
        
        print("Appointments table columns:")
        print("-" * 80)
        for row in cursor.fetchall():
            col_name, data_type, nullable, default = row
            print(f"{col_name:15} | {data_type:20} | nullable={nullable:3} | default={default}")

if __name__ == '__main__':
    check_columns()
