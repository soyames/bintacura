from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Participant
from hospital.service_models import HospitalService


class Command(BaseCommand):
    help = 'Add default hospital services (Appointments & Ambulance)'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        hospitals = Participant.objects.filter(role='hospital', is_active=True)
        
        default_services = [
            {
                'name': 'Consultation Médicale',
                'category': 'consultation_specialist',
                'description': 'Consultation générale avec un médecin',
                'price': 500000,  # 5000 XOF in cents
                'duration_minutes': 30,
                'requires_appointment': True,
            },
            {
                'name': 'Service d\'Ambulance',
                'category': 'emergency',
                'description': 'Transport médical d\'urgence avec ambulance équipée',
                'price': 2000000,  # 20000 XOF in cents
                'duration_minutes': None,
                'requires_appointment': False,
            },
        ]
        
        created_count = 0
        for hospital in hospitals:
            for service_data in default_services:
                # Check if service already exists
                exists = HospitalService.objects.filter(
                    hospital=hospital,
                    name=service_data['name']
                ).exists()
                
                if not exists:
                    HospitalService.objects.create(
                        hospital=hospital,
                        **service_data
                    )
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Created "{service_data["name"]}" for {hospital.full_name}'
                        )
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} default services'
            )
        )
