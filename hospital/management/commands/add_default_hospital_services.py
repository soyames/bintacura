from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Participant
from hospital.models import HospitalData
from hospital.service_models import HospitalService


class Command(BaseCommand):
    help = 'Add default services (Appointments & Ambulance) to all hospitals'

    def handle(self, *args, **options):
        # Get default consultation fee from settings
        default_fee = getattr(settings, 'DEFAULT_CONSULTATION_FEE_XOF', 3500)
        
        # Get all hospitals
        hospitals = Participant.objects.filter(role='hospital', is_active=True)
        
        self.stdout.write(self.style.SUCCESS(f'Found {hospitals.count()} hospitals'))
        
        created_count = 0
        updated_count = 0
        
        for hospital in hospitals:
            # Ensure hospital has hospital_data
            hospital_data, _ = HospitalData.objects.get_or_create(
                participant=hospital,
                defaults={
                    'license_number': f'LIC-{hospital.uid}',
                    'consultation_fee': default_fee,
                }
            )
            
            # 1. Add Appointment/Consultation Service
            appointment_service, created = HospitalService.objects.get_or_create(
                hospital=hospital,
                name='Consultation Médicale',
                category='consultation_specialist',
                defaults={
                    'description': 'Consultation médicale générale avec un médecin',
                    'price': hospital_data.get_consultation_fee() * 100,  # Convert to cents
                    'currency': 'XOF',
                    'duration_minutes': 30,
                    'requires_appointment': True,
                    'is_available': True,
                    'is_active': True,
                    'notes': 'Service de consultation standard'
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'  ✓ Added Consultation service to {hospital.full_name}')
            else:
                # Update price if consultation fee changed
                if appointment_service.price != hospital_data.get_consultation_fee() * 100:
                    appointment_service.price = hospital_data.get_consultation_fee() * 100
                    appointment_service.save()
                    updated_count += 1
                    self.stdout.write(f'  ↻ Updated Consultation price for {hospital.full_name}')
            
            # 2. Add Ambulance/Emergency Transport Service
            ambulance_service, created = HospitalService.objects.get_or_create(
                hospital=hospital,
                name='Transport Ambulance',
                category='emergency',
                defaults={
                    'description': 'Service de transport ambulancier d\'urgence',
                    'price': default_fee * 100 * 2,  # Double consultation fee for ambulance
                    'currency': 'XOF',
                    'duration_minutes': None,  # Variable duration
                    'requires_appointment': False,  # Emergency service
                    'is_available': True,
                    'is_active': True,
                    'notes': 'Service d\'ambulance disponible 24/7'
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'  ✓ Added Ambulance service to {hospital.full_name}')
            
            # Update hospital_data to reflect ambulance availability
            if not hospital_data.has_ambulance:
                hospital_data.has_ambulance = True
                hospital_data.save(update_fields=['has_ambulance'])
                self.stdout.write(f'  ↻ Enabled ambulance flag for {hospital.full_name}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Completed! Created {created_count} services, Updated {updated_count} services'
            )
        )
