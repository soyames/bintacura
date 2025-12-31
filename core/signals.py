from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from django.db.models import Avg
from core.models import Participant


@receiver(pre_save, sender=Participant)
def set_preferred_currency(sender, instance, **kwargs):  # Automatically set participant's preferred currency based on country before saving
    if not instance.preferred_currency and instance.country:
        from currency_converter.services import CurrencyConverterService
        instance.preferred_currency = CurrencyConverterService.get_currency_from_country(instance.country)
    elif not instance.preferred_currency:
        from currency_converter.services import CurrencyConverterService
        instance.preferred_currency = CurrencyConverterService.BASE_CURRENCY


@receiver(post_save, sender=Participant)
def create_participant_preferences(sender, instance, created, **kwargs):
    if created:
        from .preferences_utils import create_default_preferences
        create_default_preferences(instance)
        
        if instance.role in ['doctor', 'hospital']:
            from appointments.utils import create_default_availability_slots
            create_default_availability_slots(instance)


@receiver([post_save, post_delete], sender='core.Review')
@transaction.atomic
def update_rating_cache(sender, instance, **kwargs):
    """
    Update cached rating when a review is created, updated, or deleted.
    
    ACID Compliance:
    - Wrapped in @transaction.atomic
    - Uses select_for_update() to prevent race conditions
    - Calculates rating from approved reviews only
    """
    if not instance.is_approved:
        return
    
    from core.models import Review
    reviewed_type = instance.reviewed_type
    reviewed_id = instance.reviewed_id
    
    # Calculate current rating from approved reviews
    approved_reviews = Review.objects.filter(
        reviewed_type=reviewed_type,
        reviewed_id=reviewed_id,
        is_approved=True
    )
    
    avg_rating = approved_reviews.aggregate(Avg('rating'))['rating__avg']
    total_reviews = approved_reviews.count()
    
    # Round to 1 decimal place
    avg_rating = round(avg_rating, 1) if avg_rating else 0.0
    
    # Update appropriate model based on reviewed_type
    if reviewed_type == 'hospital':
        from hospital.models import HospitalData
        try:
            hospital_data = HospitalData.objects.select_for_update().get(
                participant__uid=reviewed_id
            )
            hospital_data.rating = avg_rating
            hospital_data.total_reviews = total_reviews
            hospital_data.save(update_fields=['rating', 'total_reviews'])
        except HospitalData.DoesNotExist:
            pass
    
    elif reviewed_type == 'doctor':
        from doctor.models import DoctorData
        try:
            doctor_data = DoctorData.objects.select_for_update().get(
                participant__uid=reviewed_id
            )
            doctor_data.rating = avg_rating
            doctor_data.total_reviews = total_reviews
            doctor_data.save(update_fields=['rating', 'total_reviews'])
        except DoctorData.DoesNotExist:
            pass
    
    elif reviewed_type == 'pharmacy':
        try:
            # Pharmacies store rating directly in Participant model
            pharmacy = Participant.objects.select_for_update().get(uid=reviewed_id)
            pharmacy.rating = avg_rating
            pharmacy.total_reviews = total_reviews
            pharmacy.save(update_fields=['rating', 'total_reviews'])
        except Participant.DoesNotExist:
            pass
    
    elif reviewed_type == 'insurance':
        try:
            # Insurance companies store rating directly in Participant model
            insurance = Participant.objects.select_for_update().get(uid=reviewed_id)
            insurance.rating = avg_rating
            insurance.total_reviews = total_reviews
            insurance.save(update_fields=['rating', 'total_reviews'])
        except Participant.DoesNotExist:
            pass

