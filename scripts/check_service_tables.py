#!/usr/bin/env python
"""Check service-related tables in database"""

from django.db import connection

def check_tables():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public' 
            AND table_name LIKE '%%service%%' 
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        print("\n=== Service-related tables ===")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Check for participant_services specific
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'participant_services'
            );
        """)
        exists = cursor.fetchone()[0]
        print(f"\n'participant_services' table exists: {exists}")
        
        # Also check for columns in appointments that reference services
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'appointments'
            AND column_name LIKE '%%service%%'
            ORDER BY ordinal_position;
        """)
        cols = cursor.fetchall()
        print(f"\n=== Service columns in appointments table ===")
        for col in cols:
            print(f"  - {col[0]}: {col[1]}")

if __name__ == '__main__':
    check_tables()
