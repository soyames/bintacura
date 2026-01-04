"""
Management command to ensure all hospitals have default services:
- Appointment Booking
- Ambulance Transport
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Participant
from hospital.service_models import HospitalService


class Command(BaseCommand):
    help = 'Setup default services for all hospitals (Appointment Booking & Ambulance Transport)'

    def handle(self, *args, **options):
        default_fee_xof = getattr(settings, 'DEFAULT_CONSULTATION_FEE_XOF', 3500)
        
        # Get all hospitals
        hospitals = Participant.objects.filter(role='hospital', is_active=True)
        
        self.stdout.write(f"Found {hospitals.count()} active hospitals")
        
        created_count = 0
        updated_count = 0
        
        for hospital in hospitals:
            # 1. Appointment Booking Service
            appointment_service, created = HospitalService.objects.get_or_create(
                hospital=hospital,
                name='Prise de Rendez-vous',
                category='consultation_specialist',
                defaults={
                    'description': 'Service de prise de rendez-vous médical standard',
                    'price': default_fee_xof,  # Price in XOF cents
                    'currency': 'XOF',
                    'duration_minutes': 30,
                    'requires_appointment': True,
                    'is_available': True,
                    'is_active': True,
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created appointment booking service for {hospital.full_name}')
                )
            else:
                # Update price if different
                if appointment_service.price != default_fee_xof:
                    appointment_service.price = default_fee_xof
                    appointment_service.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'⟳ Updated appointment booking price for {hospital.full_name}')
                    )
            
            # 2. Ambulance Transport Service
            ambulance_service, created = HospitalService.objects.get_or_create(
                hospital=hospital,
                name='Transport Ambulance',
                category='emergency',
                defaults={
                    'description': 'Service de transport médical d\'urgence par ambulance. Disponible 24/7 pour les urgences médicales.',
                    'price': default_fee_xof * 2,  # Double the consultation fee for ambulance
                    'currency': 'XOF',
                    'duration_minutes': None,  # Variable duration
                    'requires_appointment': False,  # No appointment needed for ambulance
                    'is_available': True,
                    'is_active': True,
                    'notes': 'Service disponible 24h/24 et 7j/7. Le coût final peut varier selon la distance et l\'urgence.'
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created ambulance service for {hospital.full_name}')
                )
            else:
                # Update to ensure it's properly configured
                if ambulance_service.price != default_fee_xof * 2:
                    ambulance_service.price = default_fee_xof * 2
                    ambulance_service.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'⟳ Updated ambulance service price for {hospital.full_name}')
                    )
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS(f'✓ SUMMARY'))
        self.stdout.write(f'  - Hospitals processed: {hospitals.count()}')
        self.stdout.write(f'  - Services created: {created_count}')
        self.stdout.write(f'  - Services updated: {updated_count}')
        self.stdout.write('='*70 + '\n')
