from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from core.models import Participant
from hospital.models import HospitalData
from hospital.service_models import HospitalService
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=HospitalData)
def add_default_hospital_services(sender, instance, created, **kwargs):
    """
    Automatically add default services when a hospital is created or updated.
    Default services: Consultation and Ambulance Transport
    """
    if not created:
        return  # Only run for new hospitals
    
    hospital = instance.participant
    default_fee = getattr(settings, 'DEFAULT_CONSULTATION_FEE_XOF', 3500)
    
    try:
        # 1. Add Consultation Service
        consultation_service, created_consult = HospitalService.objects.get_or_create(
            hospital=hospital,
            name='Consultation Médicale',
            category='consultation_specialist',
            defaults={
                'description': 'Consultation médicale générale avec un médecin',
                'price': instance.get_consultation_fee() * 100,  # Convert to cents
                'currency': 'XOF',
                'duration_minutes': 30,
                'requires_appointment': True,
                'is_available': True,
                'is_active': True,
                'notes': 'Service de consultation standard'
            }
        )
        
        if created_consult:
            logger.info(f"✓ Added Consultation service to {hospital.full_name}")
        
        # 2. Add Ambulance Service
        ambulance_service, created_amb = HospitalService.objects.get_or_create(
            hospital=hospital,
            name='Transport Ambulance',
            category='emergency',
            defaults={
                'description': 'Service de transport ambulancier d\'urgence 24/7',
                'price': default_fee * 100 * 2,  # Double consultation fee
                'currency': 'XOF',
                'duration_minutes': None,
                'requires_appointment': False,
                'is_available': True,
                'is_active': True,
                'notes': 'Service d\'ambulance disponible 24/7 pour les urgences'
            }
        )
        
        if created_amb:
            logger.info(f"✓ Added Ambulance service to {hospital.full_name}")
            # Enable ambulance flag
            if not instance.has_ambulance:
                instance.has_ambulance = True
                instance.save(update_fields=['has_ambulance'])
        
    except Exception as e:
        logger.error(f"Error adding default services to {hospital.full_name}: {str(e)}")
