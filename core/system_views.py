"""
API Views for System Configuration and Currency
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from decimal import Decimal

from core.system_config import SystemConfiguration
from currency_converter.services import CurrencyConverterService

from core.models import Participant


class GetConsultationFeeView(APIView):
    """
    Get the default consultation fee in patient's local currency
    
    GET /api/system/consultation-fee/
    
    Response:
    {
        "fee_usd": "5.00",
        "fee_local": "3012.50",
        "currency": "XOF",
        "formatted": "CFA 3013"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            from django.conf import settings
            
            # Get system config
            system_config = SystemConfiguration.get_active_config()
            base_currency = system_config.default_consultation_currency
            
            # Get the default fee based on currency from settings
            default_currency = getattr(settings, 'DEFAULT_CURRENCY', 'XOF')
            if base_currency == default_currency:
                # Use setting name dynamically: DEFAULT_CONSULTATION_FEE_XOF
                setting_name = f'DEFAULT_CONSULTATION_FEE_{default_currency}'
                default_fee = getattr(settings, setting_name, 3500)
                base_fee_amount = Decimal(str(default_fee))
            else:
                base_fee_amount = Decimal(str(system_config.default_consultation_fee))
            
            # Get patient's currency
            patient_currency = CurrencyConverterService.get_participant_currency(request.user)
            
            # Convert to patient's currency if different
            if patient_currency == base_currency:
                fee_in_local_currency = base_fee_amount
            else:
                fee_in_local_currency = CurrencyConverterService.convert(
                    base_fee_amount,
                    base_currency,
                    patient_currency
                )
            
            # Format the amount
            formatted = CurrencyConverterService.format_amount(fee_in_local_currency, patient_currency)
            
            return Response({
                'success': True,
                'fee_eur': str(fee_in_local_currency),  # Keep for backwards compatibility
                'fee_local': str(fee_in_local_currency),
                'currency': patient_currency,
                'currency_symbol': formatted.split()[0] if formatted else patient_currency,
                'formatted': formatted,
                'base_currency': base_currency,
                'base_fee': str(base_fee_amount)
            })
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetParticipantServicesView(APIView):
    """
    Get additional services offered by a participant (doctor or hospital)
    
    GET /api/v1/core/participants/{participant_id}/services/
    
    Query params:
    - category (optional): Filter by category
    - is_available (optional): Filter by availability (default: true)
    
    Response:
    {
        "success": true,
        "participant_id": "uuid",
        "participant_name": "Dr. John Smith",
        "role": "doctor",
        "services": [
            {
                "id": "uuid",
                "name": "X-Ray",
                "description": "Chest X-Ray",
                "category": "diagnostic",
                "price": "10.00",
                "currency": "EUR",
                "is_available": true
            }
        ],
        "total_services": 5
    }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, participant_id):
        try:
            participant = Participant.objects.get(uid=participant_id)
            
            if participant.role not in ['doctor', 'hospital']:
                return Response({
                    'success': False,
                    'error': 'Participant must be a doctor or hospital'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            category = request.query_params.get('category', None)
            is_available = request.query_params.get('is_available', 'true').lower() == 'true'
            
            services_data = []
            
            if participant.role == 'doctor':
                from doctor.models import DoctorService
                services = DoctorService.objects.filter(
                    doctor=participant,
                    is_active=True
                )
                
                if category:
                    services = services.filter(category=category)
                
                if is_available:
                    services = services.filter(is_available=True)
                
                patient_currency = CurrencyConverterService.get_participant_currency(request.user)
                for service in services:
                    price_in_patient_currency = CurrencyConverterService.convert(
                        Decimal(str(service.price)),
                        'XOF',
                        patient_currency
                    )
                    services_data.append({
                        'id': str(service.id),
                        'name': service.name,
                        'description': service.description or '',
                        'category': service.category,
                        'price': str(price_in_patient_currency),
                        'currency': patient_currency,
                        'duration_minutes': service.duration_minutes,
                        'is_available': service.is_available,
                        'requires_appointment': True
                    })
            
            return Response({
                'success': True,
                'participant_id': str(participant.uid),
                'participant_name': participant.full_name,
                'role': participant.role,
                'services': services_data,
                'total_services': len(services_data)
            })
        
        except Participant.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Participant not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConvertCurrencyView(APIView):
    """
    Convert amount from one currency to another
    
    POST /api/system/convert-currency/
    
    Body:
    {
        "amount": "10.00",
        "from_currency": "EUR",
        "to_currency": "XOF"
    }
    
    Response:
    {
        "success": true,
        "original_amount": "10.00",
        "original_currency": "EUR",
        "converted_amount": "6559.60",
        "converted_currency": "XOF",
        "exchange_rate": "655.96",
        "formatted": "CFA 6560"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            amount = Decimal(str(request.data.get('amount', 0)))
            from_currency = request.data.get('from_currency', 'USD')
            to_currency = request.data.get('to_currency', 'USD')
            
            # Get exchange rate
            rate = CurrencyConverter.get_exchange_rate(from_currency, to_currency)
            
            # Convert
            converted = CurrencyConverter.convert(amount, from_currency, to_currency)
            
            # Format
            formatted = CurrencyConverter.format_amount(converted, to_currency)
            
            return Response({
                'success': True,
                'original_amount': str(amount),
                'original_currency': from_currency,
                'converted_amount': str(converted),
                'converted_currency': to_currency,
                'exchange_rate': str(rate),
                'formatted': formatted
            })
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
