"""
Signal handlers for transport requests
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from .models import TransportRequest, HospitalTransportNotification
from core.models import Participant
from communication.models import Notification
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=TransportRequest)
def notify_hospitals_on_ambulance_request(sender, instance, created, **kwargs):
    """
    When a patient requests ambulance transport, notify all hospitals in their region
    so they can accept and provide the ambulance service.
    """
    if not created:
        return  # Only notify on new requests
    
    if instance.transport_type != 'ambulance':
        return  # Only for ambulance requests
    
    try:
        # Get all active hospitals in the same region
        hospitals = Participant.objects.filter(
            role='hospital',
            is_active=True,
            region_code=instance.region_code
        )
        
        logger.info(f"Notifying {hospitals.count()} hospitals about transport request {instance.request_number}")
        
        for hospital in hospitals:
            # Create hospital notification
            HospitalTransportNotification.objects.create(
                transport_request=instance,
                hospital=hospital,
                status='pending'
            )
            
            # Create system notification for hospital staff
            Notification.objects.create(
                user=hospital,
                notification_type='transport_request',
                title=f'Nouvelle demande de transport ambulance',
                message=(
                    f"Demande d'ambulance urgente ({instance.get_urgency_display()})\n"
                    f"Lieu de prise en charge: {instance.pickup_address}\n"
                    f"Destination: {instance.dropoff_address}\n"
                    f"Heure prévue: {instance.scheduled_pickup_time.strftime('%d/%m/%Y %H:%M')}"
                ),
                link=f'/hospital/transport-requests/{instance.id}/',
                priority='high' if instance.urgency == 'emergency' else 'normal'
            )
        
        logger.info(f"Successfully notified {hospitals.count()} hospitals")
        
    except Exception as e:
        logger.error(f"Error notifying hospitals about transport request: {str(e)}")
