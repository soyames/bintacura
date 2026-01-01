"""
UID Database Migration Script
Purpose: Add uid column to all tables that don't have it
Strategy: Non-breaking, incremental approach
"""

import psycopg2
from psycopg2 import sql
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.conf import settings

# Get database configurations from Django settings
DATABASES = settings.DATABASES

# Tables already with uid - SKIP these
TABLES_WITH_UID = ['participants', 'participant_data']

# Critical tables to migrate FIRST
PRIORITY_TABLES = [
    'appointments',
    'payment_receipts',
    'core_transactions',
    'prescriptions',
    'health_records',
    'appointment_services',
    'availabilities',
]


def get_connection(db_key='default'):
    """Get database connection"""
    config = DATABASES[db_key]
    return psycopg2.connect(
        host=config['HOST'],
        port=config['PORT'],
        dbname=config['NAME'],
        user=config['USER'],
        password=config['PASSWORD'],
        **config.get('OPTIONS', {})
    )


def get_all_tables(conn):
    """Get all table names from database"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            AND table_name NOT LIKE 'django_%'
            AND table_name NOT LIKE 'auth_%'
            AND table_name NOT LIKE 'sessions_%'
            ORDER BY table_name;
        """)
        return [row[0] for row in cur.fetchall()]


def table_has_uid(conn, table_name):
    """Check if table already has uid column"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s 
            AND column_name = 'uid'
        """, (table_name,))
        return cur.fetchone() is not None


def add_uid_column(conn, table_name, dry_run=True):
    """
    Add uid column to table
    Strategy: Add column, populate, then add constraints
    """
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Processing table: {table_name}")
    
    try:
        with conn.cursor() as cur:
            # Step 1: Add uid column (nullable first)
            sql_add = f"""
            ALTER TABLE {table_name} 
            ADD COLUMN IF NOT EXISTS uid UUID;
            """
            print(f"  Step 1: Adding uid column...")
            if not dry_run:
                cur.execute(sql_add)
                conn.commit()
            print(f"   Column added")
            
            # Step 2: Populate existing rows with UUIDs
            sql_populate = f"""
            UPDATE {table_name} 
            SET uid = gen_random_uuid() 
            WHERE uid IS NULL;
            """
            print(f"  Step 2: Populating UIDs for existing rows...")
            if not dry_run:
                cur.execute(sql_populate)
                rows_updated = cur.rowcount
                conn.commit()
                print(f"   {rows_updated} rows updated")
            else:
                # In dry run, just count all rows (uid column was just added as null)
                cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cur.fetchone()[0]
                print(f"  [DRY RUN] Would update {count} rows")
            
            # Step 3: Make uid NOT NULL
            sql_not_null = f"""
            ALTER TABLE {table_name} 
            ALTER COLUMN uid SET NOT NULL;
            """
            print(f"  Step 3: Setting NOT NULL constraint...")
            if not dry_run:
                cur.execute(sql_not_null)
                conn.commit()
            print(f"   NOT NULL constraint added")
            
            # Step 4: Add unique constraint
            constraint_name = f"{table_name}_uid_unique"
            sql_unique = f"""
            ALTER TABLE {table_name} 
            ADD CONSTRAINT {constraint_name} UNIQUE (uid);
            """
            print(f"  Step 4: Adding UNIQUE constraint...")
            if not dry_run:
                cur.execute(sql_unique)
                conn.commit()
            print(f"   UNIQUE constraint added")
            
            # Step 5: Create index for performance
            index_name = f"idx_{table_name}_uid"
            sql_index = f"""
            CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}(uid);
            """
            print(f"  Step 5: Creating index...")
            if not dry_run:
                cur.execute(sql_index)
                conn.commit()
            print(f"   Index created")
            
            print(f"   SUCCESS: {table_name} migration complete")
            return True
            
    except Exception as e:
        print(f"   ERROR: {str(e)}")
        conn.rollback()
        return False


def migrate_database(db_key='default', dry_run=True, priority_only=False):
    """
    Migrate database to add uid to all tables
    """
    print(f"\n{'='*80}")
    print(f"UID MIGRATION - Database: {db_key.upper()}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE MIGRATION'}")
    print(f"Scope: {'Priority tables only' if priority_only else 'All tables'}")
    print(f"{'='*80}\n")
    
    conn = get_connection(db_key)
    
    try:
        # Get all tables
        all_tables = get_all_tables(conn)
        print(f" Found {len(all_tables)} tables in database")
        
        # Filter tables
        if priority_only:
            tables_to_process = [t for t in PRIORITY_TABLES if t in all_tables]
        else:
            tables_to_process = all_tables
        
        # Remove tables that already have uid
        tables_to_migrate = []
        tables_skipped = []
        
        for table in tables_to_process:
            if table in TABLES_WITH_UID or table_has_uid(conn, table):
                tables_skipped.append(table)
            else:
                tables_to_migrate.append(table)
        
        print(f" Tables with uid already: {len(tables_skipped)}")
        print(f"  Tables needing migration: {len(tables_to_migrate)}")
        
        if tables_skipped:
            print(f"\nSkipping (already have uid): {', '.join(tables_skipped[:5])}")
            if len(tables_skipped) > 5:
                print(f"  ... and {len(tables_skipped) - 5} more")
        
        # Confirm before proceeding
        if not dry_run:
            response = input(f"\n  LIVE MIGRATION: Proceed with {len(tables_to_migrate)} tables? (yes/no): ")
            if response.lower() != 'yes':
                print("Migration cancelled")
                return
        
        # Process tables
        success_count = 0
        failed_tables = []
        
        for i, table in enumerate(tables_to_migrate, 1):
            print(f"\n[{i}/{len(tables_to_migrate)}] ", end="")
            if add_uid_column(conn, table, dry_run):
                success_count += 1
            else:
                failed_tables.append(table)
        
        # Summary
        print(f"\n{'='*80}")
        print(f"MIGRATION SUMMARY")
        print(f"{'='*80}")
        print(f" Successful: {success_count}/{len(tables_to_migrate)}")
        if failed_tables:
            print(f" Failed: {len(failed_tables)}")
            print(f"   Tables: {', '.join(failed_tables)}")
        print(f"{'='*80}\n")
        
    finally:
        conn.close()


if __name__ == '__main__':
    import sys
    
    # Parse arguments
    dry_run = '--live' not in sys.argv
    priority_only = '--priority' in sys.argv
    db_key = 'frankfurt' if '--frankfurt' in sys.argv else 'default'
    
    print("""
    ========================================================================
                        UID DATABASE MIGRATION SCRIPT
    
      This script adds 'uid' UUID columns to all tables safely:
      1. Adds column (nullable)
      2. Populates with UUIDs
      3. Sets NOT NULL
      4. Adds UNIQUE constraint
      5. Creates index
    
      Usage:
        python scripts/add_uid_to_tables.py                 (dry run)
        python scripts/add_uid_to_tables.py --priority      (critical)
        python scripts/add_uid_to_tables.py --live          (execute)
        python scripts/add_uid_to_tables.py --frankfurt     (other DB)
    ========================================================================
    """)
    
    migrate_database(db_key=db_key, dry_run=dry_run, priority_only=priority_only)
