from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def fetch_exchange_rates():
    """
    Celery task to fetch exchange rates daily.
    Runs automatically via celery beat schedule.
    Stores rates for 7 days to minimize API calls.
    """
    from currency_converter.services import CurrencyConverterService
    from currency_converter.models import ExchangeRate
    
    base_currency = 'XOF'
    logger.info(f"Starting scheduled exchange rate fetch for {base_currency}")
    
    # Check if we fetched rates in the last 24 hours
    recent_rate = ExchangeRate.objects.filter(
        from_currency=base_currency,
        fetched_at__gte=timezone.now() - timedelta(hours=24)
    ).first()
    
    if recent_rate:
        logger.info(f"Rates already fetched at {recent_rate.fetched_at}, skipping")
        return
    
    # Fetch rates
    supported_currencies = CurrencyConverterService.get_supported_currencies()
    success_count = 0
    
    for target_currency in supported_currencies:
        if target_currency == base_currency:
            continue
        
        try:
            rate = CurrencyConverterService._fetch_rate_from_api(
                base_currency,
                target_currency
            )
            if rate:
                success_count += 1
        except Exception as e:
            logger.error(f"Failed to fetch rate for {target_currency}: {e}")
    
    logger.info(f"Fetched {success_count} exchange rates successfully")


@shared_task
def cleanup_old_exchange_rates():
    """
    Celery task to clean up exchange rates older than 7 days.
    Runs daily to keep database size manageable.
    """
    from currency_converter.services import CurrencyConverterService
    
    logger.info("Starting cleanup of old exchange rates")
    CurrencyConverterService._cleanup_old_rates()
    logger.info("Cleanup completed")
