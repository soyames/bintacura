#!/usr/bin/env python
"""Check if participant_services table exists in database"""

from django.db import connection

def check_table():
    with connection.cursor() as cursor:
        print(f"Connected to database: {connection.settings_dict['NAME']}")
        print(f"Host: {connection.settings_dict['HOST']}")
        
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'participant_services'
            );
        """)
        exists = cursor.fetchone()[0]
        print(f"\n✓ participant_services table exists: {exists}")
        
        if exists:
            # Get column names
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'participant_services'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()
            print(f"\n✓ Columns in participant_services:")
            for col in columns:
                print(f"  - {col[0]}: {col[1]}")
            
            # Count rows
            cursor.execute("SELECT COUNT(*) FROM participant_services;")
            count = cursor.fetchone()[0]
            print(f"\n✓ Rows in participant_services: {count}")

if __name__ == '__main__':
    check_table()
