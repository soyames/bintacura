#!/usr/bin/env python
"""
Fix NOT NULL constraints that are causing issues
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

def fix_null_constraints():
    """Remove NOT NULL constraint from created_by_instance and modified_by_instance"""
    
    print("\n[FIX NULL CONSTRAINTS]")
    print("=" * 80)
    
    with connection.cursor() as cursor:
        try:
            # Allow NULL for these columns since the application sets them
            print("\n[ALTER] core_transactions.created_by_instance - Allow NULL")
            cursor.execute("ALTER TABLE core_transactions ALTER COLUMN created_by_instance DROP NOT NULL;")
            print("[OK]")
            
            print("\n[ALTER] core_transactions.modified_by_instance - Allow NULL")
            cursor.execute("ALTER TABLE core_transactions ALTER COLUMN modified_by_instance DROP NOT NULL;")
            print("[OK]")
            
            print("\n[ALTER] appointment_queues.provider_id - Allow NULL")
            cursor.execute("ALTER TABLE appointment_queues ALTER COLUMN provider_id DROP NOT NULL;")
            print("[OK]")
            
        except Exception as e:
            print(f"[ERROR] {e}")
    
    print("\n" + "=" * 80)
    print("[COMPLETE]")

if __name__ == '__main__':
    fix_null_constraints()
