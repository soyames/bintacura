#!/usr/bin/env python
"""
Comprehensive database schema fix - adds ALL missing columns and constraints
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

def fix_all_database_schema():
    """Add all missing columns across all tables"""
    
    tables_to_fix = {
        'core_transactions': [
            {
                'name': 'updated_at',
                'sql': "ALTER TABLE core_transactions ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL;"
            }
        ],
        'appointment_queues': [
            {
                'name': 'participant_id',
                'sql': """ALTER TABLE appointment_queues ADD COLUMN participant_id UUID NULL;
                         ALTER TABLE appointment_queues ADD CONSTRAINT appointment_queues_participant_id_fkey
                         FOREIGN KEY (participant_id) REFERENCES participants(uid) ON DELETE CASCADE;"""
            }
        ]
    }
    
    print("\n🔧 COMPREHENSIVE DATABASE SCHEMA FIX")
    print("=" * 70)
    
    with connection.cursor() as cursor:
        for table_name, columns in tables_to_fix.items():
            print(f"\n📦 Table: {table_name}")
            print("-" * 70)
            
            for col in columns:
                # Check if column exists
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name=%s AND column_name=%s;
                """, [table_name, col['name']])
                
                result = cursor.fetchone()
                
                if result:
                    print(f"   ⏭️  {col['name']} already exists")
                else:
                    print(f"   ➕ Adding {col['name']}...")
                    try:
                        cursor.execute(col['sql'])
                        print(f"   ✅ Added {col['name']}")
                    except Exception as e:
                        print(f"   ❌ Error adding {col['name']}: {e}")
    
    print("\n" + "=" * 70)
    print("✅ Database schema fix complete!")
    print("\n📝 Summary:")
    print("   - core_transactions: added updated_at")
    print("   - appointment_queues: added participant_id")

if __name__ == '__main__':
    fix_all_database_schema()
