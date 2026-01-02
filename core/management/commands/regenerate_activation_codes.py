from django.core.management.base import BaseCommand
from django.db import transaction
from hospital.models import HospitalData
from pharmacy.models import PharmacyData
from core.models import InsuranceCompanyData
from core.subscription_identifier_utils import generate_activation_code


class Command(BaseCommand):
    help = 'Regenerate activation codes with new alphanumeric format for existing entities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--entity-type',
            type=str,
            choices=['hospital', 'pharmacy', 'insurance', 'all'],
            default='all',
            help='Entity type to process (default: all)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration even if activation code already exists'
        )

    def handle(self, *args, **options):
        entity_type = options['entity_type']
        force = options['force']
        
        self.stdout.write(self.style.SUCCESS('Regenerating activation codes with new alphanumeric format...'))
        self.stdout.write('')
        
        total_updated = 0
        
        if entity_type in ['hospital', 'all']:
            self.stdout.write('Processing hospitals...')
            count = self.regenerate_codes(HospitalData, 'hospital', force)
            self.stdout.write(self.style.SUCCESS(f'  ✓ Updated {count} hospitals'))
            total_updated += count
        
        if entity_type in ['pharmacy', 'all']:
            self.stdout.write('Processing pharmacies...')
            count = self.regenerate_codes(PharmacyData, 'pharmacy', force)
            self.stdout.write(self.style.SUCCESS(f'  ✓ Updated {count} pharmacies'))
            total_updated += count
        
        if entity_type in ['insurance', 'all']:
            self.stdout.write('Processing insurance companies...')
            count = self.regenerate_codes(InsuranceCompanyData, 'insurance', force)
            self.stdout.write(self.style.SUCCESS(f'  ✓ Updated {count} insurance companies'))
            total_updated += count
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✓ COMPLETE: Regenerated {total_updated} activation codes'))

    @transaction.atomic
    def regenerate_codes(self, model_class, entity_type, force=False):
        """Regenerate activation codes for entities that have identifiers"""
        if force:
            # Update all entities with identifiers
            instances = model_class.objects.filter(identifier__isnull=False)
        else:
            # Only update entities with old digit-only codes or empty codes
            instances = model_class.objects.filter(
                identifier__isnull=False,
                activation_code__regex=r'^[0-9]{4}-[0-9]{4}-[0-9]{4}$|^$'
            )
        
        updated_count = 0
        
        for instance in instances:
            old_code = instance.activation_code
            new_code = generate_activation_code()
            
            instance.activation_code = new_code
            instance.save(update_fields=['activation_code'])
            
            self.stdout.write(
                f'    {instance.participant.full_name}: {old_code or "(empty)"} → {new_code}'
            )
            updated_count += 1
        
        return updated_count
