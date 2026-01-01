#!/usr/bin/env python
"""
Add all missing columns to appointments table
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

def add_missing_columns():
    """Add all missing columns to appointments table"""
    
    columns_to_add = [
        {
            'name': 'currency',
            'sql': "ALTER TABLE appointments ADD COLUMN currency VARCHAR(3) DEFAULT 'XOF' NOT NULL;"
        },
        {
            'name': 'payment_method',
            'sql': "ALTER TABLE appointments ADD COLUMN payment_method VARCHAR(20) DEFAULT 'cash' NOT NULL;"
        },
        {
            'name': 'payment_reference',
            'sql': "ALTER TABLE appointments ADD COLUMN payment_reference VARCHAR(100) DEFAULT '';"
        },
        {
            'name': 'payment_id',
            'sql': "ALTER TABLE appointments ADD COLUMN payment_id UUID NULL;"
        },
        {
            'name': 'additional_services_total',
            'sql': "ALTER TABLE appointments ADD COLUMN additional_services_total DECIMAL(10,2) DEFAULT 0 NOT NULL;"
        },
        {
            'name': 'original_price',
            'sql': "ALTER TABLE appointments ADD COLUMN original_price DECIMAL(10,2) DEFAULT 0 NOT NULL;"
        },
        {
            'name': 'final_price',
            'sql': "ALTER TABLE appointments ADD COLUMN final_price DECIMAL(10,2) DEFAULT 0 NOT NULL;"
        },
        {
            'name': 'discount_amount',
            'sql': "ALTER TABLE appointments ADD COLUMN discount_amount DECIMAL(10,2) DEFAULT 0 NOT NULL;"
        },
        {
            'name': 'insurance_package_id',
            'sql': "ALTER TABLE appointments ADD COLUMN insurance_package_id UUID NULL;"
        },
        {
            'name': 'service_id',
            'sql': """ALTER TABLE appointments ADD COLUMN service_id UUID NULL;
                      ALTER TABLE appointments ADD CONSTRAINT appointments_service_id_fkey 
                      FOREIGN KEY (service_id) REFERENCES participant_services(id) ON DELETE SET NULL;"""
        }
    ]
    
    with connection.cursor() as cursor:
        for col in columns_to_add:
            # Check if column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='appointments' AND column_name=%s;
            """, [col['name']])
            
            result = cursor.fetchone()
            
            if result:
                print(f"⏭️  {col['name']} already exists")
            else:
                print(f"➕ Adding {col['name']}...")
                try:
                    cursor.execute(col['sql'])
                    print(f"✅ Added {col['name']}")
                except Exception as e:
                    print(f"❌ Error adding {col['name']}: {e}")

if __name__ == '__main__':
    print("🔧 Adding missing columns to appointments table...")
    print("=" * 60)
    add_missing_columns()
    print("=" * 60)
    print("✅ Complete!")
