"""
Migration script to sync all Frankfurt data to AWS and disable Frankfurt database.
This is a ONE-TIME migration - do not run multiple times.
"""
import os
import sys
import django
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connections
from django.core.management import call_command

def migrate_data():
    """Migrate all data from Frankfurt to AWS"""
    
    print("\n" + "="*80)
    print("FRANKFURT TO AWS DATA MIGRATION")
    print("="*80 + "\n")
    
    # Get connections
    frankfurt_conn = connections['frankfurt']
    aws_conn = connections['default']
    
    frankfurt_cursor = frankfurt_conn.cursor()
    aws_cursor = aws_conn.cursor()
    
    # Tables to migrate (all tables that exist in both databases)
    print("📊 Fetching table list...")
    frankfurt_cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    
    all_tables = [row[0] for row in frankfurt_cursor.fetchall()]
    
    # Exclude Django system tables and tables we don't want to migrate
    exclude_tables = [
        'django_migrations',
        'django_session',
        'django_admin_log',
        'django_content_type',
        'auth_permission',
        'provider_data',  # AWS-only
        'provider_services',  # AWS-only
    ]
    
    tables_to_migrate = [t for t in all_tables if t not in exclude_tables]
    
    print(f"✓ Found {len(tables_to_migrate)} tables to migrate\n")
    
    migrated_count = 0
    skipped_count = 0
    error_count = 0
    
    for table_name in tables_to_migrate:
        try:
            # Check if table exists in AWS
            aws_cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """, [table_name])
            
            if not aws_cursor.fetchone()[0]:
                print(f"   ⚠️  Skipping {table_name} - doesn't exist in AWS")
                skipped_count += 1
                continue
            
            # Get row count in Frankfurt
            frankfurt_cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            frankfurt_count = frankfurt_cursor.fetchone()[0]
            
            # Get row count in AWS
            aws_cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            aws_count = aws_cursor.fetchone()[0]
            
            if frankfurt_count == 0:
                print(f"   ⏭️  Skipping {table_name} - no data in Frankfurt")
                skipped_count += 1
                continue
            
            if aws_count >= frankfurt_count:
                print(f"   ✓ Skipping {table_name} - AWS already has {aws_count} rows (Frankfurt: {frankfurt_count})")
                skipped_count += 1
                continue
            
            print(f"   🔄 Migrating {table_name} ({frankfurt_count} rows)...")
            
            # Get column names that exist in both databases
            frankfurt_cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position;
            """, [table_name])
            frankfurt_columns = set(row[0] for row in frankfurt_cursor.fetchall())
            
            aws_cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position;
            """, [table_name])
            aws_columns = set(row[0] for row in aws_cursor.fetchall())
            
            # Common columns
            common_columns = frankfurt_columns & aws_columns
            
            if not common_columns:
                print(f"      ⚠️  No common columns found!")
                error_count += 1
                continue
            
            columns_str = ', '.join(f'"{col}"' for col in sorted(common_columns))
            
            # Fetch data from Frankfurt
            frankfurt_cursor.execute(f'SELECT {columns_str} FROM "{table_name}"')
            rows = frankfurt_cursor.fetchall()
            
            if rows:
                # Insert into AWS (with conflict handling)
                placeholders = ', '.join(['%s'] * len(common_columns))
                insert_query = f'''
                    INSERT INTO "{table_name}" ({columns_str})
                    VALUES ({placeholders})
                    ON CONFLICT DO NOTHING
                '''
                
                aws_cursor.executemany(insert_query, rows)
                aws_conn.commit()
                
                print(f"      ✅ Migrated {len(rows)} rows")
                migrated_count += 1
            
        except Exception as e:
            print(f"      ❌ Error migrating {table_name}: {str(e)[:100]}")
            error_count += 1
            aws_conn.rollback()
            continue
    
    print("\n" + "="*80)
    print("MIGRATION SUMMARY")
    print("="*80)
    print(f"   ✅ Successfully migrated: {migrated_count} tables")
    print(f"   ⏭️  Skipped: {skipped_count} tables")
    print(f"   ❌ Errors: {error_count} tables")
    print("="*80 + "\n")
    
    # Close cursors
    frankfurt_cursor.close()
    aws_cursor.close()

if __name__ == '__main__':
    migrate_data()
    print("\n✨ Migration complete! You can now comment out Frankfurt database in settings.py\n")
