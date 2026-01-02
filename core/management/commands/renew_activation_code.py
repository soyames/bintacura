from django.core.management.base import BaseCommand
from django.db import transaction
from hospital.models import HospitalData
from pharmacy.models import PharmacyData
from core.models import InsuranceCompanyData
from core.subscription_identifier_utils import renew_activation_code


class Command(BaseCommand):
    help = 'Renew activation code for a specific entity using their identifier'

    def add_arguments(self, parser):
        parser.add_argument(
            'identifier',
            type=str,
            help='Entity identifier (e.g., HOSP-YTHIYIXN, PHRM-ABC123, INSR-XYZ789)'
        )
        parser.add_argument(
            '--validity-years',
            type=int,
            default=None,
            help='Number of years for new code validity (default: uses current setting)'
        )

    def handle(self, *args, **options):
        identifier = options['identifier']
        validity_years = options['validity_years']
        
        self.stdout.write(self.style.SUCCESS(f'Renewing activation code for: {identifier}'))
        self.stdout.write('')
        
        # Determine entity type from prefix
        entity_type = None
        model_class = None
        
        if identifier.startswith('HOSP-'):
            entity_type = 'hospital'
            model_class = HospitalData
        elif identifier.startswith('PHRM-'):
            entity_type = 'pharmacy'
            model_class = PharmacyData
        elif identifier.startswith('INSR-'):
            entity_type = 'insurance'
            model_class = InsuranceCompanyData
        else:
            self.stdout.write(self.style.ERROR(
                f'Invalid identifier format. Must start with HOSP-, PHRM-, or INSR-'
            ))
            return
        
        try:
            instance = model_class.objects.select_related('participant').get(identifier=identifier)
            
            # Show old code info
            self.stdout.write(f'Entity: {instance.participant.full_name}')
            self.stdout.write(f'Old Activation Code: {instance.activation_code}')
            if instance.activation_code_expires_at:
                self.stdout.write(f'Old Expiry Date: {instance.activation_code_expires_at}')
                self.stdout.write(f'Is Expired: {instance.is_activation_code_expired()}')
            self.stdout.write('')
            
            # Renew the code
            identifier, new_code, new_expires_at = renew_activation_code(
                instance, 
                entity_type, 
                validity_years
            )
            
            # Show new code info
            self.stdout.write(self.style.SUCCESS('✓ Activation code renewed successfully!'))
            self.stdout.write('')
            self.stdout.write(f'New Activation Code: {new_code}')
            self.stdout.write(f'Issued At: {instance.activation_code_issued_at}')
            self.stdout.write(f'Expires At: {new_expires_at}')
            self.stdout.write(f'Validity: {instance.activation_code_validity_years} year(s)')
            self.stdout.write(f'Days Until Expiry: {instance.days_until_expiry()}')
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(
                f'✓ Email notification should be sent to: {instance.participant.email}'
            ))
            
        except model_class.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'No entity found with identifier: {identifier}'))
