from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from hospital.models import HospitalData
from pharmacy.models import PharmacyData
from core.models import InsuranceCompanyData


class Command(BaseCommand):
    help = 'Initialize expiry dates for existing activation codes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--entity-type',
            type=str,
            choices=['hospital', 'pharmacy', 'insurance', 'all'],
            default='all',
            help='Entity type to process (default: all)'
        )
        parser.add_argument(
            '--default-validity',
            type=int,
            default=1,
            help='Default validity in years for existing codes (default: 1 year)'
        )

    def handle(self, *args, **options):
        entity_type = options['entity_type']
        default_validity = options['default_validity']
        
        self.stdout.write(self.style.SUCCESS('Initializing expiry dates for existing activation codes...'))
        self.stdout.write(f'Default validity: {default_validity} year(s)')
        self.stdout.write('')
        
        total_updated = 0
        
        if entity_type in ['hospital', 'all']:
            self.stdout.write('Processing hospitals...')
            count = self.initialize_expiry_dates(HospitalData, default_validity)
            self.stdout.write(self.style.SUCCESS(f'  ✓ Updated {count} hospitals'))
            total_updated += count
        
        if entity_type in ['pharmacy', 'all']:
            self.stdout.write('Processing pharmacies...')
            count = self.initialize_expiry_dates(PharmacyData, default_validity)
            self.stdout.write(self.style.SUCCESS(f'  ✓ Updated {count} pharmacies'))
            total_updated += count
        
        if entity_type in ['insurance', 'all']:
            self.stdout.write('Processing insurance companies...')
            count = self.initialize_expiry_dates(InsuranceCompanyData, default_validity)
            self.stdout.write(self.style.SUCCESS(f'  ✓ Updated {count} insurance companies'))
            total_updated += count
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✓ COMPLETE: Initialized {total_updated} expiry dates'))

    @transaction.atomic
    def initialize_expiry_dates(self, model_class, default_validity):
        """Initialize expiry dates for entities with activation codes but no expiry date"""
        instances = model_class.objects.filter(
            activation_code__isnull=False,
            activation_code__gt='',
            activation_code_expires_at__isnull=True
        ).select_related('participant')
        
        updated_count = 0
        now = timezone.now()
        
        for instance in instances:
            # Set issued date to now (or could be participant creation date if preferred)
            issued_at = instance.participant.created_at or now
            expires_at = issued_at + relativedelta(years=default_validity)
            
            instance.activation_code_issued_at = issued_at
            instance.activation_code_expires_at = expires_at
            instance.activation_code_validity_years = default_validity
            
            instance.save(update_fields=[
                'activation_code_issued_at',
                'activation_code_expires_at',
                'activation_code_validity_years'
            ])
            
            self.stdout.write(
                f'    {instance.participant.full_name}: '
                f'Expires {expires_at.strftime("%Y-%m-%d")} '
                f'({instance.days_until_expiry()} days)'
            )
            updated_count += 1
        
        return updated_count
