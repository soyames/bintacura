"""
Database Comparison Script
Compares Frankfurt and AWS databases to identify missing tables and columns
"""
import os
import sys
import django
from pathlib import Path

# Setup Django environment
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connections
from collections import defaultdict

def get_database_schema(db_alias):
    """Get complete schema for a database"""
    with connections[db_alias].cursor() as cursor:
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        schema = {}
        for table in tables:
            # Get columns with constraints
            cursor.execute("""
                SELECT 
                    c.column_name,
                    c.data_type,
                    c.is_nullable,
                    c.column_default,
                    c.character_maximum_length,
                    tc.constraint_type
                FROM information_schema.columns c
                LEFT JOIN information_schema.constraint_column_usage ccu 
                    ON c.table_name = ccu.table_name 
                    AND c.column_name = ccu.column_name
                LEFT JOIN information_schema.table_constraints tc 
                    ON ccu.constraint_name = tc.constraint_name
                WHERE c.table_name = %s
                ORDER BY c.ordinal_position;
            """, [table])
            
            columns = []
            for row in cursor.fetchall():
                col_info = {
                    'name': row[0],
                    'type': row[1],
                    'nullable': row[2] == 'YES',
                    'default': row[3],
                    'max_length': row[4],
                    'constraint': row[5]
                }
                columns.append(col_info)
            
            schema[table] = columns
    
    return schema

def compare_schemas():
    """Compare Frankfurt and AWS schemas"""
    print("=" * 80)
    print("DATABASE SCHEMA COMPARISON")
    print("=" * 80)
    print()
    
    print("📊 Fetching Frankfurt schema...")
    frankfurt_schema = get_database_schema('frankfurt')
    print(f"   ✓ Found {len(frankfurt_schema)} tables")
    
    print("📊 Fetching AWS (default) schema...")
    aws_schema = get_database_schema('default')
    print(f"   ✓ Found {len(aws_schema)} tables")
    print()
    
    # Tables only in Frankfurt
    frankfurt_only = set(frankfurt_schema.keys()) - set(aws_schema.keys())
    if frankfurt_only:
        print(f"⚠️  TABLES ONLY IN FRANKFURT ({len(frankfurt_only)}):")
        for table in sorted(frankfurt_only):
            print(f"   - {table}")
        print()
    
    # Tables only in AWS
    aws_only = set(aws_schema.keys()) - set(frankfurt_schema.keys())
    if aws_only:
        print(f"✓ TABLES ONLY IN AWS ({len(aws_only)}):")
        for table in sorted(aws_only):
            print(f"   - {table}")
        print()
    
    # Common tables with different columns
    common_tables = set(frankfurt_schema.keys()) & set(aws_schema.keys())
    tables_with_differences = []
    
    for table in sorted(common_tables):
        frankfurt_cols = {col['name']: col for col in frankfurt_schema[table]}
        aws_cols = {col['name']: col for col in aws_schema[table]}
        
        frankfurt_col_names = set(frankfurt_cols.keys())
        aws_col_names = set(aws_cols.keys())
        
        # Columns only in Frankfurt
        missing_in_aws = frankfurt_col_names - aws_col_names
        # Columns only in AWS
        missing_in_frankfurt = aws_col_names - frankfurt_col_names
        
        if missing_in_aws or missing_in_frankfurt:
            tables_with_differences.append({
                'table': table,
                'missing_in_aws': missing_in_aws,
                'missing_in_frankfurt': missing_in_frankfurt,
                'frankfurt_cols': frankfurt_cols,
                'aws_cols': aws_cols
            })
    
    if tables_with_differences:
        print(f"⚠️  TABLES WITH COLUMN DIFFERENCES ({len(tables_with_differences)}):")
        print()
        for diff in tables_with_differences:
            print(f"   📋 Table: {diff['table']}")
            
            if diff['missing_in_aws']:
                print(f"      🔴 Columns in Frankfurt but NOT in AWS:")
                for col_name in sorted(diff['missing_in_aws']):
                    col = diff['frankfurt_cols'][col_name]
                    nullable = "NULL" if col['nullable'] else "NOT NULL"
                    print(f"         - {col_name}: {col['type']} {nullable}")
            
            if diff['missing_in_frankfurt']:
                print(f"      🟢 Columns in AWS but NOT in Frankfurt:")
                for col_name in sorted(diff['missing_in_frankfurt']):
                    col = diff['aws_cols'][col_name]
                    nullable = "NULL" if col['nullable'] else "NOT NULL"
                    print(f"         - {col_name}: {col['type']} {nullable}")
            print()
    
    # Check for UID consistency
    print("=" * 80)
    print("UID FIELD AUDIT")
    print("=" * 80)
    print()
    
    tables_without_uid = []
    tables_with_uid = []
    
    for table in sorted(set(aws_schema.keys())):
        cols = {col['name'] for col in aws_schema[table]}
        if 'uid' in cols:
            tables_with_uid.append(table)
        else:
            tables_without_uid.append(table)
    
    print(f"✓ Tables WITH uid field: {len(tables_with_uid)}")
    print(f"⚠️  Tables WITHOUT uid field: {len(tables_without_uid)}")
    print()
    
    if tables_without_uid:
        print("Tables missing UID field:")
        for table in tables_without_uid[:20]:  # Show first 20
            print(f"   - {table}")
        if len(tables_without_uid) > 20:
            print(f"   ... and {len(tables_without_uid) - 20} more")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Frankfurt-only tables: {len(frankfurt_only)}")
    print(f"AWS-only tables: {len(aws_only)}")
    print(f"Tables with column differences: {len(tables_with_differences)}")
    print(f"Tables without UID: {len(tables_without_uid)}")
    print("=" * 80)

if __name__ == "__main__":
    compare_schemas()
