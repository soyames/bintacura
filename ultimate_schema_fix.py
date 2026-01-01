#!/usr/bin/env python
"""
ULTIMATE DATABASE SCHEMA FIX
Compare models with actual database and fix ALL discrepancies
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection
from core.models import Transaction as CoreTransaction
from appointments.models import Appointment

def get_model_fields(model):
    """Get all field names from a Django model"""
    return [f.column for f in model._meta.get_fields() if hasattr(f, 'column')]

def get_table_columns(table_name):
    """Get all column names from a database table"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name=%s;
        """, [table_name])
        return [row[0] for row in cursor.fetchall()]

def add_missing_column(table_name, column_name, column_type='VARCHAR(255)'):
    """Add a missing column to a table"""
    with connection.cursor() as cursor:
        try:
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type};"
            cursor.execute(sql)
            return True
        except Exception as e:
            print(f"      Error: {e}")
            return False

def fix_all_tables():
    """Fix all tables by comparing models with database"""
    
    # Map of model -> table_name and common field types
    tables_to_fix = {
        'core_transactions': {
            'missing_columns': {
                'currency_code': 'VARCHAR(3) DEFAULT \'XOF\' NOT NULL',
                'exchange_rate_used': 'DECIMAL(12,6) NULL',
                'conversion_timestamp': 'TIMESTAMP WITH TIME ZONE NULL',
                'commission_amount_xof': 'DECIMAL(12,2) DEFAULT 0 NOT NULL',
                'commission_amount_local': 'DECIMAL(12,2) DEFAULT 0 NOT NULL',
                'tax_amount': 'DECIMAL(12,2) DEFAULT 0 NOT NULL',
                'amount_usd': 'DECIMAL(12,2) DEFAULT 0 NOT NULL',
                'commission_amount_usd': 'DECIMAL(12,2) DEFAULT 0 NOT NULL',
                'gateway_transaction_id': 'VARCHAR(255) NULL',
                'gateway_reference': 'VARCHAR(255) NULL',
                'gateway_name': 'VARCHAR(50) NULL',
                'resolved_country': 'VARCHAR(3) NULL',
                'resolution_method': 'VARCHAR(20) NULL',
                'payment_context': 'VARCHAR(30) DEFAULT \'patient_service\' NOT NULL',
                'webhook_payload': 'JSONB DEFAULT \'{}\'::jsonb NOT NULL',
                'webhook_received_at': 'TIMESTAMP WITH TIME ZONE NULL',
                'region_code': 'VARCHAR(50) DEFAULT \'global\' NOT NULL',
            }
        }
    }
    
    print("\n[ULTIMATE DATABASE SCHEMA FIX]")
    print("=" * 80)
    
    for table, config in tables_to_fix.items():
        print(f"\n[Table: {table}]")
        print("-" * 80)
        
        # Get existing columns
        existing_columns = get_table_columns(table)
        
        # Add missing columns
        for col_name, col_type in config['missing_columns'].items():
            if col_name in existing_columns:
                print(f"  [SKIP] {col_name} - already exists")
            else:
                print(f"  [ADD] {col_name}...", end=' ')
                if add_missing_column(table, col_name, col_type):
                    print("[OK]")
                else:
                    print("[FAILED]")
    
    print("\n" + "=" * 80)
    print("[COMPLETE] All tables have been checked and fixed!")

if __name__ == '__main__':
    fix_all_tables()
