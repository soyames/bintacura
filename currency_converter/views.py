from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from decimal import Decimal
from .models import ExchangeRate, CurrencyPair
from .serializers import ExchangeRateSerializer, CurrencyPairSerializer, CurrencyConversionSerializer
from .services import CurrencyConverterService


class ExchangeRateViewSet(viewsets.ReadOnlyModelViewSet):  # View for ExchangeRateSet operations
    queryset = ExchangeRate.objects.filter(is_active=True)
    serializer_class = ExchangeRateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):  # Get queryset
        queryset = super().get_queryset()
        from_currency = self.request.query_params.get('from_currency')
        to_currency = self.request.query_params.get('to_currency')
        
        if from_currency:
            queryset = queryset.filter(from_currency=from_currency)
        if to_currency:
            queryset = queryset.filter(to_currency=to_currency)
        
        return queryset


class CurrencyPairViewSet(viewsets.ReadOnlyModelViewSet):  # View for CurrencyPairSet operations
    queryset = CurrencyPair.objects.filter(is_supported=True)
    serializer_class = CurrencyPairSerializer
    permission_classes = [IsAuthenticated]


class CurrencyConversionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CurrencyConversionSerializer
    
    @extend_schema(
        request=CurrencyConversionSerializer,
        responses={200: CurrencyConversionSerializer}
    )
    @action(detail=False, methods=['post'])
    def convert(self, request):
        serializer = CurrencyConversionSerializer(data=request.data)
        if serializer.is_valid():
            amount = serializer.validated_data['amount']
            from_currency = serializer.validated_data['from_currency']
            to_currency = serializer.validated_data['to_currency']
            
            try:
                rate = CurrencyConverterService.get_rate(from_currency, to_currency)
                converted_amount = CurrencyConverterService.convert(amount, from_currency, to_currency)
                formatted = CurrencyConverterService.format_amount(converted_amount, to_currency)
                
                return Response({
                    'amount': amount,
                    'from_currency': from_currency,
                    'to_currency': to_currency,
                    'rate': rate,
                    'converted_amount': converted_amount,
                    'formatted': formatted
                })
            except ValueError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def supported_currencies(self, request):  # Supported currencies
        currencies = CurrencyConverterService.get_supported_currencies()
        return Response({'currencies': currencies})
    
    @action(detail=False, methods=['get'])
    def my_currency(self, request):  # My currency
        participant = request.user
        currency = CurrencyConverterService.get_participant_currency(participant)
        return Response({
            'currency': currency,
            'symbol': CurrencyConverterService.CURRENCY_SYMBOLS.get(currency, currency)
        })
