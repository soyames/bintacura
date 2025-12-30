"""
Signals to automatically create default availability for new doctors and hospitals
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import Participant
from appointments.models import Availability
from datetime import time
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Participant)
def create_default_availability(sender, instance, created, **kwargs):
    """Create default 24/7 availability for newly registered hospitals and doctors"""
    
    # Only create for new participants who are doctors or hospitals
    if not created:
        return
    
    if instance.role not in ['doctor', 'hospital']:
        return
    
    # Check if they already have availability (shouldn't happen on create, but safety check)
    existing_count = Availability.objects.filter(participant=instance).count()
    if existing_count > 0:
        logger.info(f"Availability already exists for {instance.role} {instance.email}")
        return
    
    # Default availability settings
    if instance.role == 'hospital':
        # Hospitals are 24/7 by default
        start_time = time(0, 0)
        end_time = time(23, 59)
        slot_duration = 30
    else:  # doctor
        # Doctors have standard office hours by default (8am-6pm)
        start_time = time(8, 0)
        end_time = time(18, 0)
        slot_duration = 30
    
    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    created_slots = []
    for weekday in weekdays:
        availability = Availability.objects.create(
            participant=instance,
            weekday=weekday,
            start_time=start_time,
            end_time=end_time,
            slot_duration=slot_duration,
            is_active=True
        )
        created_slots.append(weekday)
    
    logger.info(
        f"Created default availability for {instance.role} {instance.email}: "
        f"{len(created_slots)} days, {start_time}-{end_time}, {slot_duration}min slots"
    )


def ensure_complete_availability(participant):
    """
    Ensure participant has availability for all 7 days.
    If some days exist, only create missing ones.
    Does not overwrite existing availability.
    """
    if participant.role not in ['doctor', 'hospital']:
        return
    
    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    existing_days = set(
        Availability.objects.filter(participant=participant).values_list('weekday', flat=True)
    )
    
    missing_days = set(weekdays) - existing_days
    
    if not missing_days:
        return  # All days covered
    
    # Default settings based on role
    if participant.role == 'hospital':
        start_time = time(0, 0)
        end_time = time(23, 59)
        slot_duration = 30
    else:  # doctor
        start_time = time(8, 0)
        end_time = time(18, 0)
        slot_duration = 30
    
    created_count = 0
    for weekday in missing_days:
        Availability.objects.create(
            participant=participant,
            weekday=weekday,
            start_time=start_time,
            end_time=end_time,
            slot_duration=slot_duration,
            is_active=True
        )
        created_count += 1
    
    logger.info(
        f"Added {created_count} missing availability days for {participant.role} {participant.email}"
    )
    
    return created_count
