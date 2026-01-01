#!/usr/bin/env python
"""
Database Schema Checker
Compares Django models with actual database schema to find mismatches
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection
from django.apps import apps

def get_table_columns(table_name):
    """Get all columns for a given table from the database"""
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()
        return {col[0]: {'type': col[1], 'nullable': col[2], 'default': col[3]} 
                for col in columns}

def get_model_fields(model):
    """Get all fields defined in Django model"""
    fields = {}
    for field in model._meta.get_fields():
        if hasattr(field, 'column'):
            fields[field.column] = {
                'type': field.get_internal_type(),
                'nullable': field.null,
                'name': field.name
            }
    return fields

def check_schema():
    """Check all models against database schema"""
    print("=" * 80)
    print("DATABASE SCHEMA VALIDATION")
    print("=" * 80)
    print()
    
    issues = []
    checked_tables = []
    
    # Models to check
    critical_models = [
        ('appointments', 'Appointment'),
        ('appointments', 'AppointmentQueue'),
        ('payments', 'PaymentReceipt'),
        ('payments', 'ServiceTransaction'),
        ('core', 'Transaction'),
    ]
    
    for app_name, model_name in critical_models:
        try:
            model = apps.get_model(app_name, model_name)
            table_name = model._meta.db_table
            
            print(f"\n📋 Checking: {app_name}.{model_name} (table: {table_name})")
            print("-" * 80)
            
            # Check if table exists
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table_name}'
                    );
                """)
                table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                issues.append(f"❌ Table {table_name} does NOT exist in database!")
                print(f"   ❌ Table does NOT exist!")
                continue
            
            print(f"   ✅ Table exists")
            checked_tables.append(table_name)
            
            # Get columns from database and model
            db_columns = get_table_columns(table_name)
            model_fields = get_model_fields(model)
            
            # Check for missing columns in database
            missing_in_db = set(model_fields.keys()) - set(db_columns.keys())
            if missing_in_db:
                print(f"\n   ⚠️  Columns in MODEL but NOT in DATABASE:")
                for col in sorted(missing_in_db):
                    field_info = model_fields[col]
                    print(f"      - {col} ({field_info['type']}) - Field name: {field_info['name']}")
                    issues.append(f"Missing column: {table_name}.{col}")
            
            # Check for extra columns in database
            extra_in_db = set(db_columns.keys()) - set(model_fields.keys())
            if extra_in_db:
                print(f"\n   ℹ️  Columns in DATABASE but NOT in MODEL:")
                for col in sorted(extra_in_db):
                    col_info = db_columns[col]
                    print(f"      - {col} ({col_info['type']})")
            
            if not missing_in_db and not extra_in_db:
                print(f"\n   ✅ All columns match!")
                
        except Exception as e:
            issues.append(f"Error checking {app_name}.{model_name}: {str(e)}")
            print(f"   ❌ Error: {str(e)}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if issues:
        print(f"\n❌ Found {len(issues)} issue(s):\n")
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue}")
    else:
        print("\n✅ No schema mismatches found!")
    
    print(f"\n📊 Checked {len(checked_tables)} tables")
    print("\nTables checked:", ", ".join(checked_tables))
    
    return len(issues) == 0

if __name__ == "__main__":
    success = check_schema()
    sys.exit(0 if success else 1)
