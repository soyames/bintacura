from django.db import models
from decimal import Decimal
from core.sync_mixin import SyncMixin


class ExchangeRate(SyncMixin):
    """
    Stores exchange rates fetched from ExchangeRate-API.
    Rates are cached for 7 days to minimize API calls.
    API Response Structure: {base_code, time_last_update_utc, conversion_rates{...}}
    """
    SOURCE_CHOICES = [
        ('API', 'External API'),
        ('MANUAL', 'Manual Entry'),
        ('STATIC', 'Static Fallback'),
    ]
    
    # Base currency (e.g., 'XOF')
    base_code = models.CharField(max_length=3, db_index=True)
    
    # Target currency (e.g., 'USD', 'EUR', 'NGN')
    target_code = models.CharField(max_length=3, db_index=True)
    
    # Conversion rate (how much 1 unit of base_code equals in target_code)
    conversion_rate = models.DecimalField(max_digits=18, decimal_places=8)
    
    # When the rate was last updated by the API
    time_last_update_utc = models.DateTimeField(null=True, blank=True)
    
    # When we fetched this rate (for our 7-day retention)
    fetched_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Source of the rate
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='API', db_index=True)
    
    # Whether this rate is currently active
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Region (for multi-region support)
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    
    class Meta:
        db_table = 'currency_exchange_rates'
        ordering = ['-fetched_at']
        indexes = [
            models.Index(fields=['base_code', 'target_code', '-fetched_at']),
            models.Index(fields=['is_active', 'source', '-fetched_at']),
            models.Index(fields=['base_code', 'is_active']),
        ]
        # Ensure we don't store duplicate rates at same time
        unique_together = [['base_code', 'target_code', 'fetched_at']]
    
    def __str__(self):
        return f"{self.base_code}/{self.target_code}: {self.conversion_rate} ({self.source})"
    
    @classmethod
    def get_latest_rate(cls, base_code, target_code):
        """Get the most recent rate for a currency pair"""
        return cls.objects.filter(
            base_code=base_code,
            target_code=target_code,
            is_active=True
        ).first()
    
    @classmethod
    def get_rate_for_transaction(cls, base_code, target_code):
        """
        Get rate for a transaction with fallback logic.
        Returns: (rate, source, last_update_time)
        """
        # Try to get latest API rate (within last 7 days)
        from django.utils import timezone
        from datetime import timedelta
        
        recent_rate = cls.objects.filter(
            base_code=base_code,
            target_code=target_code,
            is_active=True,
            fetched_at__gte=timezone.now() - timedelta(days=7)
        ).first()
        
        if recent_rate:
            return (
                recent_rate.conversion_rate,
                recent_rate.source,
                recent_rate.time_last_update_utc or recent_rate.fetched_at
            )
        
        return (None, None, None)


class CurrencyPair(SyncMixin):
    """Supported currency pairs for the platform"""
    base_currency = models.CharField(max_length=3)
    quote_currency = models.CharField(max_length=3)
    is_supported = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    
    class Meta:
        db_table = 'currency_pairs'
        unique_together = ['base_currency', 'quote_currency']
    
    def __str__(self):
        return f"{self.base_currency}/{self.quote_currency}"


class CurrencyConversionLog(SyncMixin):
    """
    Audit log for all currency conversions performed in transactions.
    Provides traceability and compliance for multi-currency operations.
    """
    CONVERSION_TYPE_CHOICES = [
        ('transaction', 'Transaction Payment'),
        ('appointment', 'Appointment Booking'),
        ('prescription', 'Prescription Fulfillment'),
        ('service', 'Service Payment'),
        ('payout', 'Provider Payout'),
        ('refund', 'Refund Processing'),
        ('other', 'Other'),
    ]
    
    # Reference to the transaction/operation
    transaction_id = models.UUIDField(db_index=True, help_text="UUID of related transaction")
    conversion_type = models.CharField(max_length=20, choices=CONVERSION_TYPE_CHOICES, default='transaction')
    
    # Participant info
    participant = models.ForeignKey(
        'core.Participant',
        on_delete=models.CASCADE,
        related_name='currency_conversions',
        help_text="Participant whose currency was converted"
    )
    
    # Currency conversion details
    from_currency = models.CharField(max_length=3, db_index=True, help_text="Source currency code")
    to_currency = models.CharField(max_length=3, db_index=True, help_text="Target currency code")
    from_amount = models.DecimalField(max_digits=18, decimal_places=2, help_text="Amount in source currency")
    to_amount = models.DecimalField(max_digits=18, decimal_places=2, help_text="Amount in target currency")
    exchange_rate = models.DecimalField(max_digits=18, decimal_places=8, help_text="Exchange rate used")
    
    # Geo-location data used for currency determination
    participant_country = models.CharField(max_length=3, blank=True, help_text="ISO country code from phone/geo")
    participant_phone_country = models.CharField(max_length=3, blank=True, help_text="Country from phone number")
    resolved_via = models.CharField(
        max_length=20,
        choices=[('phone', 'Phone Number'), ('geo', 'Geolocation'), ('combined', 'Phone + Geo'), ('default', 'Default')],
        default='default',
        help_text="How currency was determined"
    )
    
    # Rate source tracking
    rate_source = models.CharField(
        max_length=20,
        choices=[('database', 'Database'), ('api', 'API'), ('static', 'Static Fallback')],
        default='database',
        help_text="Source of exchange rate"
    )
    rate_fetched_at = models.DateTimeField(null=True, blank=True, help_text="When rate was fetched")
    
    # Audit trail
    converted_at = models.DateTimeField(auto_now_add=True, db_index=True, help_text="When conversion happened")
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    
    class Meta:
        db_table = 'currency_conversion_logs'
        ordering = ['-converted_at']
        indexes = [
            models.Index(fields=['transaction_id', '-converted_at']),
            models.Index(fields=['participant', '-converted_at']),
            models.Index(fields=['from_currency', 'to_currency', '-converted_at']),
            models.Index(fields=['conversion_type', '-converted_at']),
            models.Index(fields=['resolved_via', '-converted_at']),
        ]
    
    def __str__(self):
        return f"{self.from_amount} {self.from_currency} → {self.to_amount} {self.to_currency} @ {self.exchange_rate}"

