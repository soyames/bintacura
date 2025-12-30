from django.core.management.base import BaseCommand
from django.db.models import Count
from core.models import Participant, ProviderService, Wallet
from appointments.models import Appointment
from payments.models import HealthTransaction


class Command(BaseCommand):
    help = 'Verify database integrity and report critical data counts'

    def handle(self, *args, **options):
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('DATABASE INTEGRITY CHECK'))
        self.stdout.write('='*70 + '\n')
        
        # Participants by role
        self.stdout.write(self.style.WARNING('📊 PARTICIPANTS BY ROLE:'))
        roles = Participant.objects.values('role').annotate(count=Count('uid')).order_by('role')
        for role_data in roles:
            self.stdout.write(f"  • {role_data['role']}: {role_data['count']}")
        
        total_participants = Participant.objects.count()
        self.stdout.write(f"  TOTAL: {total_participants}\n")
        
        # Wallets
        wallet_count = Wallet.objects.count()
        active_wallets = Wallet.objects.filter(status='active').count()
        self.stdout.write(self.style.WARNING('💰 WALLETS:'))
        self.stdout.write(f"  • Total: {wallet_count}")
        self.stdout.write(f"  • Active: {active_wallets}\n")
        
        # Provider Services
        services_count = ProviderService.objects.count()
        active_services = ProviderService.objects.filter(is_active=True).count()
        self.stdout.write(self.style.WARNING('🏥 PROVIDER SERVICES:'))
        self.stdout.write(f"  • Total: {services_count}")
        self.stdout.write(f"  • Active: {active_services}\n")
        
        # Appointments
        appointments_count = Appointment.objects.count()
        pending_appointments = Appointment.objects.filter(status='pending').count()
        self.stdout.write(self.style.WARNING('📅 APPOINTMENTS:'))
        self.stdout.write(f"  • Total: {appointments_count}")
        self.stdout.write(f"  • Pending: {pending_appointments}\n")
        
        # Transactions
        try:
            transactions_count = HealthTransaction.objects.count()
            self.stdout.write(self.style.WARNING('💳 TRANSACTIONS:'))
            self.stdout.write(f"  • Total: {transactions_count}\n")
        except Exception as e:
            self.stdout.write(self.style.WARNING('💳 TRANSACTIONS:'))
            self.stdout.write(f"  • Error: Table may not exist yet\n")
        
        # WARNINGS
        self.stdout.write('='*70)
        if total_participants == 0:
            self.stdout.write(self.style.ERROR('⚠️  WARNING: NO PARTICIPANTS IN DATABASE!'))
        elif total_participants < 10:
            self.stdout.write(self.style.WARNING(f'⚠️  WARNING: Only {total_participants} participants (expected more)'))
        
        if services_count == 0:
            self.stdout.write(self.style.WARNING('⚠️  No provider services defined'))
        
        if appointments_count == 0:
            self.stdout.write(self.style.WARNING('⚠️  No appointments in system'))
        
        self.stdout.write('='*70 + '\n')
        
        if total_participants > 0:
            self.stdout.write(self.style.SUCCESS('✅ Database has data'))
        else:
            self.stdout.write(self.style.ERROR('❌ Database appears to be empty!'))
            self.stdout.write(self.style.WARNING('\n💡 This may indicate:'))
            self.stdout.write('  1. Fresh database initialization')
            self.stdout.write('  2. Data loss during migration/deployment')
            self.stdout.write('  3. Wrong database connection')
