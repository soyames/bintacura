#!/usr/bin/env python
"""
Fix missing hospital_id column in appointments table
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

def check_and_fix_hospital_column():
    """Check if hospital_id column exists, if not add it"""
    
    with connection.cursor() as cursor:
        # Check if column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='appointments' AND column_name='hospital_id';
        """)
        
        result = cursor.fetchone()
        
        if result:
            print("✅ hospital_id column already exists in appointments table")
            return True
        else:
            print("❌ hospital_id column does NOT exist")
            print("➕ Adding hospital_id column...")
            
            try:
                # Add the column
                cursor.execute("""
                    ALTER TABLE appointments 
                    ADD COLUMN hospital_id UUID NULL;
                """)
                
                # Add foreign key constraint
                cursor.execute("""
                    ALTER TABLE appointments
                    ADD CONSTRAINT appointments_hospital_id_fkey
                    FOREIGN KEY (hospital_id) 
                    REFERENCES participants(uid)
                    ON DELETE CASCADE;
                """)
                
                # Add index
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS appointments_hospital_id_idx 
                    ON appointments(hospital_id);
                """)
                
                print("✅ Successfully added hospital_id column with constraints")
                return True
                
            except Exception as e:
                print(f"❌ Error adding hospital_id column: {e}")
                return False

if __name__ == '__main__':
    print("🔧 Checking appointments table structure...")
    print("=" * 60)
    check_and_fix_hospital_column()
    print("=" * 60)
    print("✅ Check complete!")
