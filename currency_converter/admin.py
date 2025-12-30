from django.contrib import admin
from .models import ExchangeRate, CurrencyPair


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):  # Admin configuration for ExchangeRate model
    list_display = ['base_code', 'target_code', 'conversion_rate', 'source', 'fetched_at', 'is_active']
    list_filter = ['source', 'is_active', 'base_code', 'target_code']
    search_fields = ['base_code', 'target_code']
    ordering = ['-fetched_at']
    readonly_fields = ['fetched_at', 'time_last_update_utc']


@admin.register(CurrencyPair)
class CurrencyPairAdmin(admin.ModelAdmin):  # Admin configuration for CurrencyPair model
    list_display = ['base_currency', 'quote_currency', 'is_supported', 'last_updated']
    list_filter = ['is_supported']
    search_fields = ['base_currency', 'quote_currency']
    ordering = ['base_currency', 'quote_currency']
