#!/usr/bin/env python
"""
Database Schema Audit Script
Compares actual database schema with Django models
"""

import os
import sys
import django
from django.db import connection
from collections import defaultdict

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()


def get_table_schema(table_name):
    """Get complete schema information for a table"""
    with connection.cursor() as cursor:
        # Get column information
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale
            FROM information_schema.columns 
            WHERE table_name = %s
            AND table_schema = 'public'
            ORDER BY ordinal_position;
        """, [table_name])
        
        columns = cursor.fetchall()
        
        # Get foreign keys
        cursor.execute("""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                rc.delete_rule
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
              AND ccu.table_schema = tc.table_schema
            LEFT JOIN information_schema.referential_constraints AS rc
              ON tc.constraint_name = rc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' 
            AND tc.table_name = %s
            AND tc.table_schema = 'public';
        """, [table_name])
        
        foreign_keys = cursor.fetchall()
        
        # Get unique constraints
        cursor.execute("""
            SELECT
                kcu.column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            WHERE tc.constraint_type = 'UNIQUE' 
            AND tc.table_name = %s
            AND tc.table_schema = 'public';
        """, [table_name])
        
        unique_cols = [row[0] for row in cursor.fetchall()]
        
        # Get check constraints
        cursor.execute("""
            SELECT
                cc.check_clause
            FROM information_schema.check_constraints AS cc
            JOIN information_schema.constraint_column_usage AS ccu
              ON cc.constraint_name = ccu.constraint_name
            WHERE ccu.table_name = %s
            AND ccu.table_schema = 'public';
        """, [table_name])
        
        check_constraints = [row[0] for row in cursor.fetchall()]
        
    return {
        'columns': columns,
        'foreign_keys': foreign_keys,
        'unique_columns': unique_cols,
        'check_constraints': check_constraints
    }


def audit_critical_tables():
    """Audit critical tables for payment system"""
    
    critical_tables = [
        'appointments',
        'payment_receipts',
        'service_transactions',
        'appointment_queues',
        'participants',
        'participant_services',
    ]
    
    print("=" * 80)
    print("🔍 DATABASE SCHEMA AUDIT")
    print("=" * 80)
    print()
    
    for table_name in critical_tables:
        print(f"\n📦 TABLE: {table_name}")
        print("-" * 80)
        
        try:
            schema = get_table_schema(table_name)
            
            # Display columns
            print("\n🔤 COLUMNS:")
            print(f"{'Column Name':<30} {'Type':<15} {'Nullable':<10} {'Default':<20}")
            print("-" * 80)
            
            for col in schema['columns']:
                col_name, data_type, is_nullable, default, max_len, precision, scale = col
                
                # Format type
                if data_type in ['character varying', 'varchar']:
                    type_str = f"varchar({max_len})"
                elif data_type in ['numeric', 'decimal']:
                    type_str = f"decimal({precision},{scale})"
                else:
                    type_str = data_type
                
                # Format default
                default_str = str(default)[:20] if default else '-'
                
                # Highlight issues
                flag = ""
                if is_nullable == 'NO' and not default and col_name != 'id':
                    flag = " ⚠️  NOT NULL"
                
                print(f"{col_name:<30} {type_str:<15} {is_nullable:<10} {default_str:<20} {flag}")
            
            # Display foreign keys
            if schema['foreign_keys']:
                print("\n🔗 FOREIGN KEYS:")
                print(f"{'Column':<30} {'References':<40} {'On Delete':<15}")
                print("-" * 80)
                for fk in schema['foreign_keys']:
                    col_name, foreign_table, foreign_col, delete_rule = fk
                    ref = f"{foreign_table}.{foreign_col}"
                    print(f"{col_name:<30} {ref:<40} {delete_rule:<15}")
            
            # Display unique constraints
            if schema['unique_columns']:
                print("\n🔑 UNIQUE CONSTRAINTS:")
                for col in schema['unique_columns']:
                    print(f"  - {col}")
            
            # Display check constraints
            if schema['check_constraints']:
                print("\n✓ CHECK CONSTRAINTS:")
                for check in schema['check_constraints']:
                    print(f"  - {check[:60]}...")
                    
        except Exception as e:
            print(f"❌ ERROR: {e}")
        
        print()


def check_payment_receipt_issues():
    """Specifically check payment_receipts for known issues"""
    print("\n" + "=" * 80)
    print("🔍 PAYMENT_RECEIPTS DETAILED AUDIT")
    print("=" * 80)
    print()
    
    with connection.cursor() as cursor:
        # Check participant_id constraint
        cursor.execute("""
            SELECT is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'payment_receipts'
            AND column_name = 'participant_id';
        """)
        
        result = cursor.fetchone()
        if result:
            is_nullable, default = result
            print(f"participant_id:")
            print(f"  - Nullable: {is_nullable}")
            print(f"  - Default: {default or 'None'}")
            if is_nullable == 'NO':
                print(f"  ❌ ISSUE: Should be nullable=True")
        
        # Check service_transaction_id constraint
        cursor.execute("""
            SELECT is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'payment_receipts'
            AND column_name = 'service_transaction_id';
        """)
        
        result = cursor.fetchone()
        if result:
            is_nullable, default = result
            print(f"\nservice_transaction_id:")
            print(f"  - Nullable: {is_nullable}")
            print(f"  - Default: {default or 'None'}")
            if is_nullable == 'NO':
                print(f"  ❌ ISSUE: Should be nullable=True")
        
        # Check if any receipts exist without these fields
        cursor.execute("""
            SELECT COUNT(*) 
            FROM payment_receipts 
            WHERE participant_id IS NULL;
        """)
        count = cursor.fetchone()[0]
        print(f"\nReceipts with NULL participant_id: {count}")
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM payment_receipts 
            WHERE service_transaction_id IS NULL;
        """)
        count = cursor.fetchone()[0]
        print(f"Receipts with NULL service_transaction_id: {count}")


def generate_fix_sql():
    """Generate SQL to fix known issues"""
    print("\n" + "=" * 80)
    print("🔧 SUGGESTED FIX SQL")
    print("=" * 80)
    print()
    
    fixes = [
        {
            'name': 'Make payment_receipts.participant_id nullable',
            'sql': 'ALTER TABLE payment_receipts ALTER COLUMN participant_id DROP NOT NULL;'
        },
        {
            'name': 'Make payment_receipts.service_transaction_id nullable',
            'sql': 'ALTER TABLE payment_receipts ALTER COLUMN service_transaction_id DROP NOT NULL;'
        },
        {
            'name': 'Make appointments.hospital_id nullable (if exists)',
            'sql': 'ALTER TABLE appointments ALTER COLUMN hospital_id DROP NOT NULL;'
        },
    ]
    
    print("-- Copy and run these SQL commands on your database:")
    print("-- (Test on Frankfurt DB first!)")
    print()
    
    for i, fix in enumerate(fixes, 1):
        print(f"-- Fix #{i}: {fix['name']}")
        print(fix['sql'])
        print()


if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    BINTACURA DATABASE SCHEMA AUDIT                          ║
║                                                                              ║
║  This script will analyze the database schema and identify mismatches       ║
║  between Django models and actual database constraints.                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        audit_critical_tables()
        check_payment_receipt_issues()
        generate_fix_sql()
        
        print("\n" + "=" * 80)
        print("✅ AUDIT COMPLETE")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Review the issues flagged above")
        print("2. Test the suggested SQL fixes on Frankfurt DB")
        print("3. Update Django models to match")
        print("4. Create a migration to document changes")
        print("5. Test payment flow thoroughly")
        
    except Exception as e:
        print(f"\n❌ AUDIT FAILED: {e}")
        import traceback
        traceback.print_exc()
