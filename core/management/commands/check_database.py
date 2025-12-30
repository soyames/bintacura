"""
Management command to check database health and fix common issues
"""
from django.core.management.base import BaseCommand
from django.db import connections, connection
from django.conf import settings
import sys


class Command(BaseCommand):
    help = 'Check database health and identify missing tables or sync issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Attempt to fix issues by running migrations',
        )
        parser.add_argument(
            '--database',
            type=str,
            default='default',
            help='Database to check (default, frankfurt)',
        )

    def handle(self, *args, **options):
        database = options['database']
        should_fix = options['fix']
        
        self.stdout.write(self.style.SUCCESS(f'\n{"="*70}'))
        self.stdout.write(self.style.SUCCESS(f'DATABASE HEALTH CHECK: {database}'))
        self.stdout.write(self.style.SUCCESS(f'{"="*70}\n'))
        
        # Check database connection
        if not self.check_connection(database):
            return
        
        # Check for critical tables
        missing_tables = self.check_critical_tables(database)
        
        # Check for participants
        self.check_participants(database)
        
        # Check for doctor data
        self.check_doctor_fees(database)
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n{"="*70}'))
        if missing_tables:
            self.stdout.write(self.style.ERROR(f'❌ ISSUES FOUND: {len(missing_tables)} missing tables'))
            if should_fix:
                self.stdout.write(self.style.WARNING('\nAttempting to fix by running migrations...'))
                self.run_migrations(database)
            else:
                self.stdout.write(self.style.WARNING('\nRun with --fix to attempt automatic repair'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ DATABASE HEALTH: GOOD'))
        self.stdout.write(self.style.SUCCESS(f'{"="*70}\n'))

    def check_connection(self, database):
        """Check if database is accessible"""
        try:
            conn = connections[database]
            conn.ensure_connection()
            self.stdout.write(self.style.SUCCESS(f'✅ Database connection: OK'))
            
            # Show database info
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            self.stdout.write(self.style.SUCCESS(f'   PostgreSQL Version: {version.split(",")[0]}'))
            return True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Database connection failed: {str(e)}'))
            return False

    def check_critical_tables(self, database):
        """Check if critical tables exist"""
        critical_tables = [
            'core_participants',
            'participant_phones',
            'doctor_data',
            'patient_data',
            'core_wallets',
            'appointments',
        ]
        
        self.stdout.write(self.style.SUCCESS(f'\n📊 Checking critical tables...'))
        
        missing = []
        conn = connections[database]
        cursor = conn.cursor()
        
        for table in critical_tables:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                );
            """, [table])
            exists = cursor.fetchone()[0]
            
            if exists:
                # Count rows
                cursor.execute(f'SELECT COUNT(*) FROM {table};')
                count = cursor.fetchone()[0]
                self.stdout.write(self.style.SUCCESS(f'   ✅ {table}: {count} rows'))
            else:
                self.stdout.write(self.style.ERROR(f'   ❌ {table}: MISSING'))
                missing.append(table)
        
        return missing

    def check_participants(self, database):
        """Check participant data"""
        self.stdout.write(self.style.SUCCESS(f'\n👥 Checking participants...'))
        
        try:
            from core.models import Participant
            
            # Use specific database
            participants = Participant.objects.using(database).all()
            total = participants.count()
            
            if total == 0:
                self.stdout.write(self.style.WARNING(f'   ⚠️  No participants found'))
                return
            
            # Count by role
            roles = participants.values('role').distinct()
            self.stdout.write(self.style.SUCCESS(f'   Total participants: {total}'))
            
            for role_dict in roles:
                role = role_dict['role']
                count = participants.filter(role=role).count()
                self.stdout.write(self.style.SUCCESS(f'   - {role}: {count}'))
            
            # Check for superadmin
            superadmins = participants.filter(role='super_admin')
            if superadmins.exists():
                for admin in superadmins:
                    status = 'Active' if admin.is_active else 'Inactive'
                    self.stdout.write(self.style.SUCCESS(f'   - Superadmin: {admin.email} ({status})'))
            else:
                self.stdout.write(self.style.WARNING(f'   ⚠️  No superadmin found'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Error checking participants: {str(e)}'))

    def check_doctor_fees(self, database):
        """Check doctor consultation fees"""
        self.stdout.write(self.style.SUCCESS(f'\n💰 Checking doctor consultation fees...'))
        
        try:
            from doctor.models import DoctorData
            
            doctors = DoctorData.objects.using(database).all()
            total = doctors.count()
            
            if total == 0:
                self.stdout.write(self.style.WARNING(f'   ⚠️  No doctors found'))
                return
            
            # Check for doctors with 0 fee
            zero_fee = doctors.filter(consultation_fee__lte=0).count()
            has_fee = doctors.filter(consultation_fee__gt=0).count()
            
            self.stdout.write(self.style.SUCCESS(f'   Total doctors: {total}'))
            self.stdout.write(self.style.SUCCESS(f'   - With valid fee: {has_fee}'))
            
            if zero_fee > 0:
                self.stdout.write(self.style.WARNING(f'   ⚠️  With zero/negative fee: {zero_fee}'))
                self.stdout.write(self.style.WARNING(f'   Run migration: python manage.py migrate doctor --database={database}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'   ✅ All doctors have valid fees'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Error checking doctors: {str(e)}'))

    def run_migrations(self, database):
        """Run migrations to fix issues"""
        from django.core.management import call_command
        
        try:
            self.stdout.write(self.style.WARNING(f'\nRunning migrations on {database}...'))
            call_command('migrate', database=database, interactive=False)
            self.stdout.write(self.style.SUCCESS('✅ Migrations completed'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Migration failed: {str(e)}'))
