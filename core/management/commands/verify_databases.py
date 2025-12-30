from django.core.management.base import BaseCommand
from django.db import connections
from django.conf import settings


class Command(BaseCommand):
    help = 'Verify all database tables across all configured databases'

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*70)
        self.stdout.write("DATABASE VERIFICATION")
        self.stdout.write("="*70 + "\n")

        databases = settings.DATABASES.keys()
        table_counts = {}
        all_tables = {}

        for db_alias in databases:
            try:
                with connections[db_alias].cursor() as cursor:
                    cursor.execute("""
                        SELECT tablename 
                        FROM pg_tables 
                        WHERE schemaname = 'public' 
                        ORDER BY tablename;
                    """)
                    tables = [row[0] for row in cursor.fetchall()]
                    table_counts[db_alias] = len(tables)
                    all_tables[db_alias] = set(tables)
                    
                    self.stdout.write(f"\n📊 Database: {db_alias.upper()}")
                    self.stdout.write(f"   Total tables: {len(tables)}")
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"\n❌ Error accessing {db_alias}: {str(e)}"))
                continue

        if len(all_tables) > 1:
            self.stdout.write("\n" + "-"*70)
            self.stdout.write("TABLE COMPARISON")
            self.stdout.write("-"*70)
            
            db_list = list(all_tables.keys())
            reference_db = db_list[0]
            reference_tables = all_tables[reference_db]
            
            for db_alias in db_list[1:]:
                current_tables = all_tables[db_alias]
                
                missing_in_current = reference_tables - current_tables
                extra_in_current = current_tables - reference_tables
                
                if missing_in_current:
                    self.stdout.write(self.style.WARNING(
                        f"\n⚠️  Tables in {reference_db} but NOT in {db_alias} ({len(missing_in_current)}):"
                    ))
                    for table in sorted(missing_in_current):
                        self.stdout.write(f"   - {table}")
                
                if extra_in_current:
                    self.stdout.write(self.style.WARNING(
                        f"\n⚠️  Tables in {db_alias} but NOT in {reference_db} ({len(extra_in_current)}):"
                    ))
                    for table in sorted(extra_in_current):
                        self.stdout.write(f"   - {table}")
                
                if not missing_in_current and not extra_in_current:
                    self.stdout.write(self.style.SUCCESS(
                        f"\n✅ {reference_db} and {db_alias} have identical tables!"
                    ))

        self.stdout.write("\n" + "="*70)
        self.stdout.write("SUMMARY")
        self.stdout.write("="*70)
        for db_alias, count in table_counts.items():
            self.stdout.write(f"{db_alias.upper()}: {count} tables")
        self.stdout.write("="*70 + "\n")
