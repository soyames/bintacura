from django.core.management.base import BaseCommand
from django.db import connections
from django.apps import apps
from django.conf import settings


class Command(BaseCommand):
    help = 'Sync database schema from Render (source of truth) to target database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--target',
            type=str,
            default='default',
            help='Target database to sync TO (default: default/AWS)'
        )
        parser.add_argument(
            '--source',
            type=str,
            default='frankfurt',
            help='Source database to sync FROM (default: frankfurt/Render)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )

    def handle(self, *args, **options):
        source_db = options['source']
        target_db = options['target']
        dry_run = options['dry_run']
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('SYNC DATABASE SCHEMA FROM RENDER'))
        self.stdout.write('='*70)
        self.stdout.write(f'\nSource: {source_db.upper()} (Render - Source of Truth)')
        self.stdout.write(f'Target: {target_db.upper()} (AWS - Will be synced)')
        if dry_run:
            self.stdout.write(self.style.WARNING('\n*** DRY RUN MODE - No changes will be made ***'))
        self.stdout.write('\n')
        
        # Check source database exists
        if source_db not in settings.DATABASES:
            self.stdout.write(self.style.ERROR(f'Error: Source database "{source_db}" not configured'))
            self.stdout.write(f'Available databases: {", ".join(settings.DATABASES.keys())}')
            return
        
        # Get tables from both databases
        source_tables = self._get_tables(source_db)
        target_tables = self._get_tables(target_db)
        
        self.stdout.write(f'Source ({source_db}): {len(source_tables)} tables')
        self.stdout.write(f'Target ({target_db}): {len(target_tables)} tables\n')
        
        # Find missing tables
        missing_tables = source_tables - target_tables
        extra_tables = target_tables - source_tables
        
        if missing_tables:
            self.stdout.write(self.style.WARNING(f'\n{len(missing_tables)} tables missing in target:'))
            for table in sorted(missing_tables):
                self.stdout.write(f'  - {table}')
        
        if extra_tables:
            self.stdout.write(self.style.NOTICE(f'\n{len(extra_tables)} extra tables in target (will be kept):'))
            for table in sorted(extra_tables)[:10]:
                self.stdout.write(f'  - {table}')
            if len(extra_tables) > 10:
                self.stdout.write(f'  ... and {len(extra_tables) - 10} more')
        
        if not missing_tables:
            self.stdout.write(self.style.SUCCESS('\n✅ Target database already has all tables from source!'))
            return
        
        # Create missing tables
        self.stdout.write('\n' + '='*70)
        self.stdout.write('CREATING MISSING TABLES')
        self.stdout.write('='*70 + '\n')
        
        created_count = 0
        failed_count = 0
        skipped_count = 0
        
        # Get all models and create missing tables
        all_models = apps.get_models()
        
        for model in all_models:
            table_name = model._meta.db_table
            
            if table_name not in missing_tables:
                continue
            
            if dry_run:
                self.stdout.write(f'  [DRY-RUN] Would create: {table_name}')
                skipped_count += 1
                continue
            
            try:
                with connections[target_db].schema_editor() as schema_editor:
                    schema_editor.create_model(model)
                
                self.stdout.write(self.style.SUCCESS(f'  [CREATED] {table_name}'))
                created_count += 1
                
            except Exception as e:
                error_msg = str(e).split('\n')[0][:100]
                self.stdout.write(self.style.ERROR(f'  [ERROR] {table_name}: {error_msg}'))
                failed_count += 1
        
        # Summary
        self.stdout.write('\n' + '='*70)
        self.stdout.write('SUMMARY')
        self.stdout.write('='*70)
        self.stdout.write(f'Missing tables found: {len(missing_tables)}')
        if dry_run:
            self.stdout.write(f'Would create: {skipped_count}')
        else:
            self.stdout.write(self.style.SUCCESS(f'Successfully created: {created_count}'))
            if failed_count > 0:
                self.stdout.write(self.style.ERROR(f'Failed: {failed_count}'))
        self.stdout.write('='*70 + '\n')
        
        if failed_count > 0 and not dry_run:
            self.stdout.write(self.style.WARNING(
                '\n⚠️  Some tables failed to create. Run this command again to retry.\n'
                '   Failed tables may have dependencies that need to be created first.'
            ))
    
    def _get_tables(self, database):
        """Get all table names from a database"""
        with connections[database].cursor() as cursor:
            cursor.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename
            """)
            return set([row[0] for row in cursor.fetchall()])
