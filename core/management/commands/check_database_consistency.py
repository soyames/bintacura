from django.core.management.base import BaseCommand
from django.db import connections


class Command(BaseCommand):
    help = 'Compare database tables across all configured databases'

    def handle(self, *args, **options):
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('DATABASE CONSISTENCY CHECK'))
        self.stdout.write('='*70 + '\n')
        
        databases = {}
        
        # Check all configured databases
        for db_alias in connections:
            try:
                with connections[db_alias].cursor() as cursor:
                    cursor.execute("""
                        SELECT tablename 
                        FROM pg_tables 
                        WHERE schemaname = 'public' 
                        ORDER BY tablename
                    """)
                    databases[db_alias] = set([row[0] for row in cursor.fetchall()])
                    self.stdout.write(f"{db_alias.upper()}: {len(databases[db_alias])} tables")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"{db_alias.upper()}: ERROR - {str(e)}"))
                databases[db_alias] = set()
        
        if len(databases) < 2:
            self.stdout.write(self.style.WARNING('\nOnly one database configured, skipping comparison'))
            return
        
        # Find common tables and differences
        all_tables = set()
        for tables in databases.values():
            all_tables.update(tables)
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write('CONSISTENCY ANALYSIS:')
        self.stdout.write('='*70 + '\n')
        
        # Check each table
        missing_by_db = {db: [] for db in databases.keys()}
        
        for table in sorted(all_tables):
            present_in = []
            missing_in = []
            
            for db_alias, tables in databases.items():
                if table in tables:
                    present_in.append(db_alias)
                else:
                    missing_in.append(db_alias)
                    missing_by_db[db_alias].append(table)
            
            if missing_in:
                self.stdout.write(f"[MISSING] {table}")
                self.stdout.write(f"   Present in: {', '.join(present_in)}")
                self.stdout.write(f"   MISSING in: {', '.join(missing_in)}")
        
        # Summary
        self.stdout.write('\n' + '='*70)
        self.stdout.write('SUMMARY:')
        self.stdout.write('='*70 + '\n')
        
        all_consistent = True
        for db_alias, missing_tables in missing_by_db.items():
            if missing_tables:
                all_consistent = False
                self.stdout.write(self.style.ERROR(f"{db_alias.upper()}: Missing {len(missing_tables)} tables"))
        
        if all_consistent:
            self.stdout.write(self.style.SUCCESS('[OK] ALL DATABASES ARE CONSISTENT!'))
        else:
            self.stdout.write(self.style.ERROR('\n[WARNING] DATABASES ARE INCONSISTENT!'))
            self.stdout.write(self.style.WARNING('\nTo fix this, run migrations on all databases:'))
            self.stdout.write('  python manage.py migrate')
            self.stdout.write('\nOr run migrations per database:')
            for db_alias in databases.keys():
                if missing_by_db[db_alias]:
                    self.stdout.write(f'  python manage.py migrate --database={db_alias}')
        
        self.stdout.write('\n' + '='*70 + '\n')
