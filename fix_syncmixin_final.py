#!/usr/bin/env python
"""
FINAL COMPREHENSIVE FIX - Add all SyncMixin columns to all tables that need them
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

def fix_syncmixin_columns():
    """Add all SyncMixin columns (version, created_by_instance, etc.) to all tables"""
    
    # List of all tables that should have SyncMixin fields
    tables_with_syncmixin = [
        'core_transactions',
        'appointment_history',
        'staff_tasks',
        'payment_receipts'
    ]
    
    syncmixin_columns = [
        ('version', 'INTEGER DEFAULT 1 NOT NULL'),
        ('created_by_instance', 'VARCHAR(100) DEFAULT \'online\' NOT NULL'),
        ('modified_by_instance', 'VARCHAR(100) DEFAULT \'online\' NOT NULL'),
        ('is_deleted', 'BOOLEAN DEFAULT FALSE NOT NULL'),
        ('deleted_at', 'TIMESTAMP WITH TIME ZONE NULL'),
        ('last_synced_at', 'TIMESTAMP WITH TIME ZONE NULL'),
        ('created_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL'),
        ('updated_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL'),
    ]
    
    # Extra columns specific to core_transactions
    transaction_specific_columns = [
        ('amount_local', 'DECIMAL(10,2) DEFAULT 0 NOT NULL'),
        ('currency_local', 'VARCHAR(3) DEFAULT \'XOF\' NOT NULL'),
    ]
    
    print("\n🔧 FINAL COMPREHENSIVE DATABASE FIX")
    print("="* 80)
    print("\n📋 Adding SyncMixin columns to all tables...")
    
    with connection.cursor() as cursor:
        for table in tables_with_syncmixin:
            print(f"\n📦 Table: {table}")
            print("-" * 80)
            
            for col_name, col_type in syncmixin_columns:
                # Check if column exists
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name=%s AND column_name=%s;
                """, [table, col_name])
                
                result = cursor.fetchone()
                
                if result:
                    print(f"   ⏭️  {col_name}")
                else:
                    print(f"   ➕ Adding {col_name}...", end='')
                    try:
                        sql = f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type};"
                        cursor.execute(sql)
                        print(" ✅")
                    except Exception as e:
                        print(f" ❌ {e}")
            
            # Add transaction-specific columns
            if table == 'core_transactions':
                for col_name, col_type in transaction_specific_columns:
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name=%s AND column_name=%s;
                    """, [table, col_name])
                    
                    result = cursor.fetchone()
                    
                    if result:
                        print(f"   ⏭️  {col_name}")
                    else:
                        print(f"   ➕ Adding {col_name}...", end='')
                        try:
                            sql = f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type};"
                            cursor.execute(sql)
                            print(" ✅")
                        except Exception as e:
                            print(f" ❌ {e}")
    
    print("\n" + "=" * 80)
    print("✅ DATABASE SCHEMA FIX COMPLETE!")
    print("\n📝 All SyncMixin columns have been added to:")
    for table in tables_with_syncmixin:
        print(f"   - {table}")

if __name__ == '__main__':
    fix_syncmixin_columns()
