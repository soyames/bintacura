from .models import Advertisement
from django.db import OperationalError, DatabaseError


def active_ads(request):
    """
    Context processor to add active advertisements to all templates
    """
    try:
        ads = Advertisement.objects.filter(status='active')
        active_ads_list = [ad for ad in ads if ad.is_active()]
        return {
            'carousel_ads': active_ads_list
        }
    except (OperationalError, DatabaseError):
        # If database is not available (e.g., during initial deployment),
        # return empty list instead of crashing
        return {
            'carousel_ads': []
        }
