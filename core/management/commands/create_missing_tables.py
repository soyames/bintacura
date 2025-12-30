from django.core.management.base import BaseCommand
from django.db import connections
from django.apps import apps


class Command(BaseCommand):
    help = 'Create all missing tables using Django schema editor'

    def add_arguments(self, parser):
        parser.add_argument(
            '--database',
            type=str,
            default='default',
            help='Target database (default: default)'
        )

    def handle(self, *args, **options):
        database = options['database']
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('CREATE MISSING TABLES'))
        self.stdout.write('='*70)
        self.stdout.write(f'\nTarget database: {database.upper()}\n')
        
        # Get existing tables
        with connections[database].cursor() as cursor:
            cursor.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
            """)
            existing_tables = set([row[0] for row in cursor.fetchall()])
        
        self.stdout.write(f'Existing tables: {len(existing_tables)}\n')
        
        #Get all models
        all_models = apps.get_models()
        
        created_count = 0
        skipped_count = 0
        error_count = 0
        
        for model in all_models:
            table_name = model._meta.db_table
            
            if table_name in existing_tables:
                skipped_count += 1
                continue
            
            try:
                # Use schema editor to create table (each in its own transaction)
                from django.db import transaction
                with transaction.atomic(using=database):
                    with connections[database].schema_editor() as schema_editor:
                        schema_editor.create_model(model)
                
                self.stdout.write(self.style.SUCCESS(f'  [CREATED] {table_name}'))
                created_count += 1
                
            except Exception as e:
                error_msg = str(e).split('\n')[0][:80]  # First line only, truncate
                self.stdout.write(self.style.ERROR(f'  [ERROR] {table_name}: {error_msg}'))
                error_count += 1
        
        # Summary
        self.stdout.write('\n' + '='*70)
        self.stdout.write('SUMMARY:')
        self.stdout.write('='*70)
        self.stdout.write(f'Total models: {len(all_models)}')
        self.stdout.write(f'Already existed: {skipped_count}')
        self.stdout.write(self.style.SUCCESS(f'Successfully created: {created_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'Failed: {error_count}'))
        self.stdout.write('='*70 + '\n')
        
        if created_count > 0:
            self.stdout.write(self.style.SUCCESS(f'\n{created_count} tables created successfully!'))
