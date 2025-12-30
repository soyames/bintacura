from django.core.management.base import BaseCommand
from django.db import connections, transaction


class Command(BaseCommand):
    help = 'Sync database schema from source to target database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--from-db',
            type=str,
            default='frankfurt',
            help='Source database (default: frankfurt)'
        )
        parser.add_argument(
            '--to-db',
            type=str,
            default='default',
            help='Target database (default: default)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )

    def handle(self, *args, **options):
        from_db = options['from_db']
        to_db = options['to_db']
        dry_run = options['dry_run']
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('DATABASE SCHEMA SYNC'))
        self.stdout.write('='*70)
        self.stdout.write(f'\nFrom: {from_db.upper()}')
        self.stdout.write(f'To: {to_db.upper()}')
        if dry_run:
            self.stdout.write(self.style.WARNING('Mode: DRY RUN (no changes will be made)'))
        self.stdout.write('\n' + '='*70 + '\n')
        
        # Get tables from both databases
        with connections[from_db].cursor() as cursor:
            cursor.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                ORDER BY tablename
            """)
            from_tables = set([row[0] for row in cursor.fetchall()])
        
        with connections[to_db].cursor() as cursor:
            cursor.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                ORDER BY tablename
            """)
            to_tables = set([row[0] for row in cursor.fetchall()])
        
        missing_tables = from_tables - to_tables
        
        self.stdout.write(f'{from_db.upper()} has: {len(from_tables)} tables')
        self.stdout.write(f'{to_db.upper()} has: {len(to_tables)} tables')
        self.stdout.write(f'Missing in {to_db.upper()}: {len(missing_tables)} tables\n')
        
        if not missing_tables:
            self.stdout.write(self.style.SUCCESS('No missing tables! Databases are in sync.'))
            return
        
        self.stdout.write('Missing tables:')
        for table in sorted(missing_tables):
            self.stdout.write(f'  - {table}')
        
        if dry_run:
            self.stdout.write('\n' + '='*70)
            self.stdout.write(self.style.WARNING('DRY RUN: No changes made.'))
            self.stdout.write('Run without --dry-run to actually sync schemas.')
            return
        
        # Copy table structures
        self.stdout.write('\n' + '='*70)
        self.stdout.write('Copying table structures...\n')
        
        success_count = 0
        error_count = 0
        
        for table in sorted(missing_tables):
            try:
                # Get CREATE TABLE statement from source
                with connections[from_db].cursor() as cursor:
                    cursor.execute(f"""
                        SELECT 
                            'CREATE TABLE ' || quote_ident(tablename) || ' (' ||
                            string_agg(
                                quote_ident(attname) || ' ' || 
                                format_type(atttypid, atttypmod) ||
                                CASE WHEN attnotnull THEN ' NOT NULL' ELSE '' END ||
                                CASE WHEN atthasdef THEN ' DEFAULT ' || pg_get_expr(adbin, adrelid) ELSE '' END,
                                ', '
                            ) || ');'
                        FROM pg_attribute a
                        JOIN pg_class c ON a.attrelid = c.oid
                        JOIN pg_namespace n ON c.relnamespace = n.oid
                        LEFT JOIN pg_attrdef d ON a.attrelid = d.adrelid AND a.attnum = d.adnum
                        WHERE c.relname = '{table}'
                        AND n.nspname = 'public'
                        AND a.attnum > 0
                        AND NOT a.attisdropped
                        GROUP BY tablename;
                    """)
                    result = cursor.fetchone()
                    
                    if result:
                        create_sql = result[0]
                        
                        # Create table in target
                        with connections[to_db].cursor() as target_cursor:
                            with transaction.atomic(using=to_db):
                                target_cursor.execute(create_sql)
                        
                        self.stdout.write(self.style.SUCCESS(f'  [OK] {table}'))
                        success_count += 1
                    else:
                        self.stdout.write(self.style.WARNING(f'  [SKIP] {table} - Could not get structure'))
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  [ERROR] {table}: {str(e)}'))
                error_count += 1
        
        # Summary
        self.stdout.write('\n' + '='*70)
        self.stdout.write('SUMMARY:')
        self.stdout.write('='*70)
        self.stdout.write(f'Total missing tables: {len(missing_tables)}')
        self.stdout.write(self.style.SUCCESS(f'Successfully created: {success_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'Failed: {error_count}'))
        self.stdout.write('='*70 + '\n')
        
        if error_count == 0:
            self.stdout.write(self.style.SUCCESS('Schema sync completed successfully!'))
            self.stdout.write('\nIMPORTANT: Run migrations to add indexes and constraints:')
            self.stdout.write(f'  python manage.py migrate --database={to_db}')
        else:
            self.stdout.write(self.style.WARNING('Schema sync completed with errors.'))
            self.stdout.write('Check errors above and try again.')
