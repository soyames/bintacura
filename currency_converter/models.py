from django.db import models
from decimal import Decimal
from core.sync_mixin import SyncMixin


class ExchangeRate(SyncMixin):
    SOURCE_CHOICES = [
        ('API', 'External API'),
        ('MANUAL', 'Manual Entry'),
        ('STATIC', 'Static Fallback'),
    ]
    
    from_currency = models.CharField(max_length=3)
    to_currency = models.CharField(max_length=3)
    rate = models.DecimalField(max_digits=12, decimal_places=6)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='STATIC')
    fetched_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    
    class Meta:
        db_table = 'currency_exchange_rates'
        ordering = ['-fetched_at']
        indexes = [
            models.Index(fields=['from_currency', 'to_currency', '-fetched_at']),
            models.Index(fields=['is_active', '-fetched_at']),
        ]
    
    def __str__(self):
        return f"{self.from_currency}/{self.to_currency}: {self.rate} ({self.source})"
    
    @classmethod
    def get_latest_rate(cls, from_currency, to_currency):
        return cls.objects.filter(
            from_currency=from_currency,
            to_currency=to_currency,
            is_active=True
        ).first()


class CurrencyPair(SyncMixin):
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
