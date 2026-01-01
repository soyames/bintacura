#!/usr/bin/env python
"""
Check all database constraints and compare with Django models
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection
from django.apps import apps

def check_table_constraints(table_name):
    """Check all constraints for a table"""
    with connection.cursor() as cursor:
        # Check NOT NULL constraints
        cursor.execute("""
            SELECT 
                column_name,
                is_nullable,
                column_default,
                data_type
            FROM information_schema.columns
            WHERE table_name = %s
            AND table_schema = 'public'
            ORDER BY ordinal_position;
        """, [table_name])
        
        columns = cursor.fetchall()
        
        # Check foreign keys
        cursor.execute("""
            SELECT
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name = %s;
        """, [table_name])
        
        foreign_keys = cursor.fetchall()
        
        # Check unique constraints
        cursor.execute("""
            SELECT
                tc.constraint_name,
                kcu.column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.constraint_type = 'UNIQUE'
            AND tc.table_name = %s;
        """, [table_name])
        
        unique_constraints = cursor.fetchall()
        
        return {
            'columns': columns,
            'foreign_keys': foreign_keys,
            'unique_constraints': unique_constraints
        }

def check_model_fields(model):
    """Check Django model field definitions"""
    fields_info = {}
    
    for field in model._meta.get_fields():
        if hasattr(field, 'null') and hasattr(field, 'blank'):
            fields_info[field.name] = {
                'null': field.null,
                'blank': field.blank,
                'required': not field.blank and not field.null,
                'has_default': field.has_default(),
                'type': type(field).__name__
            }
    
    return fields_info

def main():
    print("=" * 80)
    print("DATABASE CONSTRAINTS AUDIT")
    print("=" * 80)
    
    # Tables to check
    critical_tables = [
        ('appointments', 'appointments.Appointment'),
        ('appointment_queues', 'appointments.AppointmentQueue'),
        ('payment_receipts', 'payments.PaymentReceipt'),
        ('service_transactions', 'payments.ServiceTransaction'),
        ('participants', 'core.Participant'),
    ]
    
    for table_name, model_path in critical_tables:
        print(f"\n{'=' * 80}")
        print(f"📦 TABLE: {table_name}")
        print(f"🔧 MODEL: {model_path}")
        print("=" * 80)
        
        try:
            # Get database constraints
            db_constraints = check_table_constraints(table_name)
            
            # Get Django model
            app_label, model_name = model_path.split('.')
            model = apps.get_model(app_label, model_name)
            model_fields = check_model_fields(model)
            
            print("\n🔍 NOT NULL CONSTRAINTS IN DATABASE:")
            print("-" * 80)
            not_null_cols = [col for col in db_constraints['columns'] if col[1] == 'NO']
            for col in not_null_cols:
                col_name, nullable, default, data_type = col
                model_info = model_fields.get(col_name, {})
                
                # Check if model allows null but DB doesn't
                mismatch = ""
                if model_info.get('null', False) and nullable == 'NO':
                    mismatch = "⚠️ MISMATCH: Model allows NULL, DB doesn't!"
                elif not model_info.get('null', True) and nullable == 'YES':
                    mismatch = "⚠️ MISMATCH: Model requires value, DB allows NULL!"
                
                print(f"   • {col_name:<30} ({data_type:<15}) {mismatch}")
                if model_info:
                    print(f"      Model: null={model_info.get('null')}, blank={model_info.get('blank')}, has_default={model_info.get('has_default')}")
            
            print("\n🔗 FOREIGN KEY CONSTRAINTS:")
            print("-" * 80)
            if db_constraints['foreign_keys']:
                for fk in db_constraints['foreign_keys']:
                    constraint_name, column, foreign_table, foreign_column = fk
                    print(f"   • {column:<30} -> {foreign_table}.{foreign_column}")
            else:
                print("   (none)")
            
            print("\n✨ UNIQUE CONSTRAINTS:")
            print("-" * 80)
            if db_constraints['unique_constraints']:
                for uc in db_constraints['unique_constraints']:
                    constraint_name, column = uc
                    print(f"   • {column:<30} ({constraint_name})")
            else:
                print("   (none)")
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("✅ AUDIT COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    main()
