from rest_framework import serializers
from .models import ExchangeRate, CurrencyPair


class ExchangeRateSerializer(serializers.ModelSerializer):  # Serializer for ExchangeRate data
    class Meta:  # Meta class implementation
        model = ExchangeRate
        fields = ['id', 'from_currency', 'to_currency', 'rate', 'source', 'fetched_at', 'is_active']
        read_only_fields = ['id', 'fetched_at']


class CurrencyPairSerializer(serializers.ModelSerializer):  # Serializer for CurrencyPair data
    class Meta:  # Meta class implementation
        model = CurrencyPair
        fields = ['id', 'base_currency', 'quote_currency', 'is_supported', 'last_updated']
        read_only_fields = ['id', 'last_updated']


class CurrencyConversionSerializer(serializers.Serializer):  # Serializer for CurrencyConversion data
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)
    from_currency = serializers.CharField(max_length=3, required=True)
    to_currency = serializers.CharField(max_length=3, required=True)
    converted_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    rate = serializers.DecimalField(max_digits=12, decimal_places=6, read_only=True)
    formatted = serializers.CharField(read_only=True)
