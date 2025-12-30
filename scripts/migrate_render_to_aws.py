import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connections
from django.apps import apps

def migrate_data_from_render_to_aws():
    """Migrate all data from Render (frankfurt) to AWS (default)"""
    
    render_conn = connections['frankfurt']
    aws_conn = connections['default']
    
    with render_conn.cursor() as render_cursor:
        render_cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        render_tables = [row[0] for row in render_cursor.fetchall()]
    
    with aws_conn.cursor() as aws_cursor:
        aws_cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        aws_tables = [row[0] for row in aws_cursor.fetchall()]
    
    print(f"\n{'='*70}")
    print("DATABASE COMPARISON")
    print(f"{'='*70}")
    print(f"Render tables: {len(render_tables)}")
    print(f"AWS tables: {len(aws_tables)}")
    
    missing_in_aws = set(render_tables) - set(aws_tables)
    extra_in_aws = set(aws_tables) - set(render_tables)
    
    if missing_in_aws:
        print(f"\n⚠️  Missing in AWS ({len(missing_in_aws)}):")
        for table in sorted(missing_in_aws):
            print(f"  - {table}")
    
    if extra_in_aws:
        print(f"\n✓ Extra in AWS ({len(extra_in_aws)}):")
        for table in sorted(extra_in_aws):
            print(f"  - {table}")
    
    common_tables = sorted(set(render_tables) & set(aws_tables))
    print(f"\nCommon tables: {len(common_tables)}")
    
    # Migrate data
    print(f"\n{'='*70}")
    print("DATA MIGRATION: Render → AWS")
    print(f"{'='*70}\n")
    
    migrated = 0
    skipped = 0
    errors = []
    
    for table in common_tables:
        try:
            with render_conn.cursor() as render_cursor:
                render_cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                render_count = render_cursor.fetchone()[0]
            
            with aws_conn.cursor() as aws_cursor:
                aws_cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                aws_count = aws_cursor.fetchone()[0]
            
            if render_count == 0:
                print(f"  [SKIP] {table}: empty in Render")
                skipped += 1
                continue
            
            if aws_count > 0:
                print(f"  [SKIP] {table}: {aws_count} rows already in AWS (Render: {render_count})")
                skipped += 1
                continue
            
            # Copy data
            with render_conn.cursor() as render_cursor:
                render_cursor.execute(f'SELECT * FROM "{table}"')
                rows = render_cursor.fetchall()
                
                if rows:
                    columns = [desc[0] for desc in render_cursor.description]
                    placeholders = ','.join(['%s'] * len(columns))
                    column_names = ','.join([f'"{col}"' for col in columns])
                    
                    with aws_conn.cursor() as aws_cursor:
                        aws_cursor.executemany(
                            f'INSERT INTO "{table}" ({column_names}) VALUES ({placeholders})',
                            rows
                        )
                    
                    print(f"  [MIGRATED] {table}: {len(rows)} rows")
                    migrated += 1
        
        except Exception as e:
            error_msg = f"{table}: {str(e)}"
            errors.append(error_msg)
            print(f"  [ERROR] {error_msg}")
    
    print(f"\n{'='*70}")
    print("MIGRATION SUMMARY")
    print(f"{'='*70}")
    print(f"Tables processed: {len(common_tables)}")
    print(f"Migrated: {migrated}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {len(errors)}")
    
    if errors:
        print(f"\nErrors:")
        for error in errors:
            print(f"  - {error}")
    
    print(f"{'='*70}\n")

if __name__ == '__main__':
    migrate_data_from_render_to_aws()
