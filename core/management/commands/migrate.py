"""
Custom migrate command that applies migrations to ALL configured databases automatically.
This ensures all database instances (AWS RDS, Render, future regions) stay in sync.
"""
from django.core.management.commands.migrate import Command as MigrateCommand
from django.core.management import call_command
from django.conf import settings


class Command(MigrateCommand):
    help = 'Applies migrations to ALL configured databases automatically'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--single-database',
            action='store_true',
            help='Run on single database only (use --database flag)',
        )

    def handle(self, *args, **options):
        """Apply migrations to all databases unless --single-database is specified"""
        
        # If user specifically wants single database, use original behavior
        if options.get('single_database'):
            return super().handle(*args, **options)
        
        # Check if database was explicitly specified by user (not just default)
        if options.get('database') and options.get('database') != 'default':
            return super().handle(*args, **options)
        
        # Get all configured databases
        databases = list(settings.DATABASES.keys())
        
        self.stdout.write(self.style.SUCCESS(
            f'\n{"=" * 70}\n'
            f'  MULTI-DATABASE MIGRATION\n'
            f'  Applying to: {", ".join(databases)}\n'
            f'{"=" * 70}\n'
        ))
        
        results = {}
        errors = {}
        
        # Apply migrations to each database
        for db_alias in databases:
            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f'\n>>> Migrating database: {db_alias.upper()}'
                )
            )
            
            try:
                # Create a copy of options for this database
                db_options = options.copy()
                db_options['database'] = db_alias
                
                # Run migration on this database
                super().handle(*args, **db_options)
                
                results[db_alias] = 'SUCCESS'
                self.stdout.write(
                    self.style.SUCCESS(f'[OK] {db_alias} migrated successfully')
                )
                
            except Exception as e:
                errors[db_alias] = str(e)
                self.stdout.write(
                    self.style.ERROR(f'[ERROR] {db_alias} migration failed: {e}')
                )
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{"=" * 70}\n'
                f'  MIGRATION SUMMARY\n'
                f'{"=" * 70}'
            )
        )
        
        for db_alias in databases:
            if db_alias in results:
                self.stdout.write(
                    self.style.SUCCESS(f'  [OK] {db_alias}: SUCCESS')
                )
            elif db_alias in errors:
                self.stdout.write(
                    self.style.ERROR(f'  [ERROR] {db_alias}: FAILED - {errors[db_alias][:50]}...')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{"=" * 70}\n'
                f'  Total databases: {len(databases)}\n'
                f'  Successful: {len(results)}\n'
                f'  Failed: {len(errors)}\n'
                f'{"=" * 70}\n'
            )
        )
        
        # If any failed, show warning
        if errors:
            self.stdout.write(
                self.style.WARNING(
                    '\n[WARNING] Some databases failed to migrate. Check errors above.'
                )
            )
