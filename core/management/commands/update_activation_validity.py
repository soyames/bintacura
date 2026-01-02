from django.core.management.base import BaseCommand
from hospital.models import HospitalData
from pharmacy.models import PharmacyData
from core.models import InsuranceCompanyData
from core.subscription_identifier_utils import update_activation_code_validity


class Command(BaseCommand):
    help = 'Update activation code validity period for a specific entity'

    def add_arguments(self, parser):
        parser.add_argument(
            'identifier',
            type=str,
            help='Entity identifier (e.g., HOSP-YTHIYIXN)'
        )
        parser.add_argument(
            'validity_years',
            type=int,
            help='New validity period in years (1, 2, 5, etc.)'
        )

    def handle(self, *args, **options):
        identifier = options['identifier']
        validity_years = options['validity_years']
        
        if validity_years < 1:
            self.stdout.write(self.style.ERROR('Validity years must be at least 1'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Updating validity period for: {identifier}'))
        self.stdout.write(f'New validity: {validity_years} year(s)')
        self.stdout.write('')
        
        # Determine entity type from prefix
        model_class = None
        
        if identifier.startswith('HOSP-'):
            model_class = HospitalData
        elif identifier.startswith('PHRM-'):
            model_class = PharmacyData
        elif identifier.startswith('INSR-'):
            model_class = InsuranceCompanyData
        else:
            self.stdout.write(self.style.ERROR(
                f'Invalid identifier format. Must start with HOSP-, PHRM-, or INSR-'
            ))
            return
        
        try:
            instance = model_class.objects.select_related('participant').get(identifier=identifier)
            
            # Show current info
            self.stdout.write(f'Entity: {instance.participant.full_name}')
            self.stdout.write(f'Current Validity: {instance.activation_code_validity_years} year(s)')
            if instance.activation_code_expires_at:
                self.stdout.write(f'Current Expiry: {instance.activation_code_expires_at}')
            self.stdout.write('')
            
            # Update validity
            new_expires_at = update_activation_code_validity(instance, validity_years)
            
            # Show updated info
            self.stdout.write(self.style.SUCCESS('✓ Validity period updated successfully!'))
            self.stdout.write('')
            self.stdout.write(f'New Validity: {validity_years} year(s)')
            self.stdout.write(f'New Expiry Date: {new_expires_at}')
            self.stdout.write(f'Days Until Expiry: {instance.days_until_expiry()}')
            
        except model_class.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'No entity found with identifier: {identifier}'))
        except ValueError as e:
            self.stdout.write(self.style.ERROR(str(e)))
