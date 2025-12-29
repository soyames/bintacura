from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from core.models import Participant
from currency_converter.services import CurrencyConverterService



@receiver(pre_save, sender=Participant)
def set_preferred_currency(sender, instance, **kwargs):  # Automatically set participant's preferred currency based on country before saving
    if not instance.preferred_currency and instance.country:
        instance.preferred_currency = CurrencyConverterService.get_currency_from_country(instance.country)
    elif not instance.preferred_currency:
        instance.preferred_currency = CurrencyConverterService.BASE_CURRENCY


@receiver(post_save, sender=Participant)
def create_participant_preferences(sender, instance, created, **kwargs):
    if created:
        from .preferences_utils import create_default_preferences
        create_default_preferences(instance)
        
        if instance.role in ['doctor', 'hospital']:
            from appointments.utils import create_default_availability_slots
            create_default_availability_slots(instance)
