"""
Management command to sync schema across all regional databases
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings


class Command(BaseCommand):
    help = 'Sync database schema across all regional databases'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--region',
            type=str,
            help='Specific region to sync (default: all)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
        )
    
    def handle(self, *args, **options):
        region = options.get('region')
        dry_run = options.get('dry_run', False)
        
        # Get all database aliases
        if region:
            databases = [region] if region in settings.DATABASES else []
            if not databases:
                self.stdout.write(
                    self.style.ERROR(f'Region "{region}" not found in DATABASES')
                )
                return
        else:
            databases = [db for db in settings.DATABASES.keys() if db != 'default']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN - No changes will be made')
            )
            self.stdout.write(f'Would sync schema to: {", ".join(databases)}')
            return
        
        # Sync default database first
        self.stdout.write('Syncing default database...')
        call_command('migrate', database='default', verbosity=1)
        
        # Sync each regional database
        for db in databases:
            self.stdout.write(f'\nSyncing {db} database...')
            try:
                call_command('migrate', database=db, verbosity=1)
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully synced {db}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error syncing {db}: {str(e)}')
                )
        
        self.stdout.write(self.style.SUCCESS('\nSchema sync complete!'))
