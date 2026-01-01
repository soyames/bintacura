#!/usr/bin/env python3
"""
Database Schema Sync: Frankfurt → AWS
Executes SQL migration and verifies schema alignment
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connections, transaction
from django.core.management import call_command


def execute_sql_file(database_alias, sql_file_path):
    """Execute SQL file on specified database"""
    print(f"\n{'='*80}")
    print(f"Executing SQL on database: {database_alias}")
    print(f"{'='*80}\n")
    
    with open(sql_file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Split by statement (basic split on semicolon)
    statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]
    
    with connections[database_alias].cursor() as cursor:
        executed = 0
        failed = 0
        
        for statement in statements:
            # Skip comments and empty statements
            if not statement or statement.startswith('--') or statement.upper().startswith('COMMENT'):
                continue
                
            try:
                cursor.execute(statement)
                executed += 1
                print(f"✓ Executed statement {executed}")
            except Exception as e:
                failed += 1
                print(f"✗ Failed statement {failed}: {str(e)[:100]}")
                if 'SELECT' not in statement.upper():  # Don't fail on verification queries
                    print(f"   Statement: {statement[:200]}")
    
    print(f"\n📊 Summary:")
    print(f"   Executed: {executed}")
    print(f"   Failed: {failed}")
    return executed, failed


def verify_schema_alignment():
    """Verify that AWS schema now matches Frankfurt"""
    print(f"\n{'='*80}")
    print(f"SCHEMA VERIFICATION")
    print(f"{'='*80}\n")
    
    tables_to_check = [
        'journal_entry_lines',
        'operating_rooms',
        'projects',
        'surgery_schedules',
        'transaction_fees'
    ]
    
    for table in tables_to_check:
        print(f"\n📋 Checking table: {table}")
        
        # Check AWS
        with connections['default'].cursor() as cursor:
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, [table])
            aws_columns = cursor.fetchall()
        
        # Check Frankfurt
        try:
            with connections['frankfurt'].cursor() as cursor:
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """, [table])
                frankfurt_columns = cursor.fetchall()
        except Exception as e:
            print(f"   ⚠️  Could not query Frankfurt: {e}")
            frankfurt_columns = []
        
        # Compare
        aws_col_names = {col[0] for col in aws_columns}
        frankfurt_col_names = {col[0] for col in frankfurt_columns}
        
        missing_in_aws = frankfurt_col_names - aws_col_names
        extra_in_aws = aws_col_names - frankfurt_col_names
        
        if missing_in_aws:
            print(f"   ⚠️  Columns in Frankfurt but NOT in AWS: {missing_in_aws}")
        if extra_in_aws:
            print(f"   ℹ️  Columns in AWS but NOT in Frankfurt: {extra_in_aws}")
        
        if not missing_in_aws and not extra_in_aws:
            print(f"   ✓ Schema matches!")
        elif not missing_in_aws:
            print(f"   ✓ AWS has all Frankfurt columns (plus extras)")


def main():
    print("\n" + "="*80)
    print("DATABASE SCHEMA SYNCHRONIZATION: Frankfurt → AWS")
    print("="*80)
    
    # Get SQL file path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sql_file = os.path.join(script_dir, 'sync_frankfurt_to_aws.sql')
    
    if not os.path.exists(sql_file):
        print(f"\n❌ SQL file not found: {sql_file}")
        return 1
    
    print(f"\n📄 SQL File: {sql_file}")
    
    # Confirm
    response = input("\n⚠️  This will modify the AWS database schema. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("\n❌ Aborted by user")
        return 0
    
    # Execute SQL
    try:
        executed, failed = execute_sql_file('default', sql_file)
        
        if failed > 0:
            print(f"\n⚠️  {failed} statements failed. Review errors above.")
        else:
            print(f"\n✅ All statements executed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error executing SQL: {e}")
        return 1
    
    # Verify alignment
    verify_schema_alignment()
    
    print(f"\n{'='*80}")
    print("SYNC COMPLETE")
    print(f"{'='*80}\n")
    
    print("📝 Next Steps:")
    print("   1. Review verification results above")
    print("   2. Update Django models to match new schema")
    print("   3. Run makemigrations and migrate")
    print("   4. Test invoice display issue")
    print("   5. Migrate data from Frankfurt if needed")
    print("   6. Comment out Frankfurt database config\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
