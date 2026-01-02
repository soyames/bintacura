from django.core.management.base import BaseCommand
from core.subscription_identifier_utils import bulk_assign_identifiers_to_existing
from hospital.models import HospitalData
from pharmacy.models import PharmacyData
from core.models import InsuranceCompanyData


class Command(BaseCommand):
    help = 'Assign identifiers and activation codes to existing verified hospitals, pharmacies, and insurance companies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--entity-type',
            type=str,
            choices=['hospital', 'pharmacy', 'insurance', 'all'],
            default='all',
            help='Entity type to process (default: all)'
        )

    def handle(self, *args, **options):
        entity_type = options['entity_type']
        
        self.stdout.write(self.style.SUCCESS('Starting identifier assignment process...'))
        self.stdout.write('')
        
        total_updated = 0
        
        if entity_type in ['hospital', 'all']:
            self.stdout.write('Processing hospitals...')
            count = bulk_assign_identifiers_to_existing(HospitalData, 'hospital')
            self.stdout.write(self.style.SUCCESS(f'  ✓ Updated {count} hospitals'))
            total_updated += count
        
        if entity_type in ['pharmacy', 'all']:
            self.stdout.write('Processing pharmacies...')
            count = bulk_assign_identifiers_to_existing(PharmacyData, 'pharmacy')
            self.stdout.write(self.style.SUCCESS(f'  ✓ Updated {count} pharmacies'))
            total_updated += count
        
        if entity_type in ['insurance', 'all']:
            self.stdout.write('Processing insurance companies...')
            count = bulk_assign_identifiers_to_existing(InsuranceCompanyData, 'insurance')
            self.stdout.write(self.style.SUCCESS(f'  ✓ Updated {count} insurance companies'))
            total_updated += count
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✓ COMPLETE: Assigned identifiers to {total_updated} entities'))
