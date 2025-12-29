"""
Universal Payment Views
=======================

QR-driven payment endpoints that work for ALL transaction types:
- Appointments
- Pharmacy orders
- Lab tests
- Insurance premiums
- Any other service

These endpoints use the UniversalPaymentService to provide
a consistent payment experience across the platform.
"""

import logging
from decimal import Decimal
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from payments.universal_payment_service import UniversalPaymentService
from qrcode_generator.models import QRCode
from currency_converter.services import CurrencyConverterService

logger = logging.getLogger(__name__)


@extend_schema(
    summary="Verify payment QR code for any service type",
    parameters=[
        OpenApiParameter('service_type', OpenApiTypes.STR, OpenApiParameter.PATH),
        OpenApiParameter('service_id', OpenApiTypes.STR, OpenApiParameter.PATH),
    ],
    responses={200: dict, 400: dict}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_payment_qr(request, service_type, service_id):
    """
    Universal endpoint to verify any service payment QR code.

    URL: /api/payments/verify/<service_type>/<service_id>/

    Supported service_types:
    - appointment
    - pharmacy_order
    - lab_test
    - insurance_premium
    etc.

    Returns:
        - Service details
        - Payment information
        - QR code URL
    """
    try:
        participant = request.user

        # Verify using UniversalPaymentService
        from payments.universal_payment_service import UniversalPaymentService

        # Create verification data
        qr_data = {
            'type': service_type,
            'service_id': service_id,
        }

        verification = UniversalPaymentService.verify_payment_qr(qr_data)

        if not verification['valid']:
            return Response(
                {'detail': verification['error']},
                status=status.HTTP_400_BAD_REQUEST
            )

        service_object = verification['service_object']
        patient_info = verification['patient']
        provider_info = verification.get('provider')

        # Get participant's currency for display
        viewer_currency = CurrencyConverterService.get_participant_currency(participant)
        order_currency = verification['currency']
        order_amount = Decimal(str(verification['amount']))

        # Convert amount if needed
        if viewer_currency != order_currency:
            display_amount = CurrencyConverterService.convert(
                order_amount,
                order_currency,
                viewer_currency
            )
        else:
            display_amount = order_amount

        # Get QR code
        qr_code = QRCode.objects.filter(
            content_type=service_type,
            object_id=str(service_id),
            is_active=True
        ).first()

        response_data = {
            'success': True,
            'service_type': service_type,
            'service': {
                'id': str(service_object.id),
                'reference': verification['reference'],
                'payment_status': verification['payment_status'],
                'amount': float(order_amount),
                'currency': order_currency,
                'display_amount': float(display_amount),
                'display_currency': viewer_currency,
            },
            'patient': patient_info,
            'provider': provider_info,
            'qr_code_url': request.build_absolute_uri(qr_code.qr_code_image.url) if qr_code and qr_code.qr_code_image else None,
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f'Error verifying payment QR: {str(e)}', exc_info=True)
        return Response(
            {'detail': f'Erreur lors de la vérification: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Pay for any service using QR code",
    parameters=[
        OpenApiParameter('service_type', OpenApiTypes.STR, OpenApiParameter.PATH),
        OpenApiParameter('service_id', OpenApiTypes.STR, OpenApiParameter.PATH),
    ],
    request={'application/json': dict},
    responses={200: dict, 400: dict}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def pay_service(request, service_type, service_id):
    """
    Universal endpoint to pay for any service (patient scans QR and pays).

    URL: /api/payments/pay/<service_type>/<service_id>/

    Request body:
        {
            "payment_method": "wallet|card|mobile_money|insurance|cash" (optional)
        }

    Returns:
        Payment result based on method
    """
    try:
        participant = request.user

        # Verify service
        qr_data = {
            'type': service_type,
            'service_id': service_id,
        }

        verification = UniversalPaymentService.verify_payment_qr(qr_data)

        if not verification['valid']:
            return Response(
                {'detail': verification['error']},
                status=status.HTTP_400_BAD_REQUEST
            )

        service_object = verification['service_object']
        patient_info = verification['patient']

        # Verify participant is the patient
        if participant.role != 'patient' or str(participant.uid) != patient_info['id']:
            return Response(
                {'detail': 'Seul le patient peut effectuer le paiement'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if already paid
        if verification['payment_status'] == 'paid':
            return Response(
                {'detail': 'Paiement déjà effectué'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get payment method (can override service's payment method)
        payment_method = request.data.get('payment_method')
        if not payment_method:
            # Try to get from service object
            payment_method = getattr(service_object, 'payment_method', 'wallet')

        # Process payment using UniversalPaymentService
        result = UniversalPaymentService.process_payment(
            service_type=service_type,
            service_object=service_object,
            payment_method=payment_method,
            patient=participant
        )

        return Response({
            'success': True,
            **result,
        }, status=status.HTTP_200_OK)

    except ValueError as e:
        return Response(
            {'detail': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f'Error processing payment: {str(e)}', exc_info=True)
        return Response(
            {'detail': f'Erreur lors du paiement: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Scan service QR code",
    request={'application/json': dict},
    responses={200: dict, 400: dict}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def scan_service_qr(request):
    """
    Universal endpoint for provider to scan patient QR and initiate mobile money push.

    URL: /api/payments/scan/

    Request body:
        {
            "qr_data": "..." (JSON string from QR code)
            OR
            "service_type": "appointment",
            "service_id": "uuid"
        }

    Returns:
        Mobile money push initiation result
    """
    try:
        scanner = request.user

        # Get service from QR data or direct parameters
        qr_data = request.data.get('qr_data')
        service_type = request.data.get('service_type')
        service_id = request.data.get('service_id')

        if qr_data:
            # Verify QR code
            verification = UniversalPaymentService.verify_payment_qr(qr_data)
            if not verification['valid']:
                return Response(
                    {'detail': verification['error']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            service_object = verification['service_object']
            service_type = verification['service_type']
        elif service_type and service_id:
            # Direct service reference
            verification_data = {
                'type': service_type,
                'service_id': service_id,
            }
            verification = UniversalPaymentService.verify_payment_qr(verification_data)
            if not verification['valid']:
                return Response(
                    {'detail': verification['error']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            service_object = verification['service_object']
        else:
            return Response(
                {'detail': 'qr_data ou (service_type et service_id) requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if already paid
        if verification['payment_status'] == 'paid':
            return Response(
                {'detail': 'Paiement déjà effectué'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Initiate mobile money push
        try:
            result = UniversalPaymentService.process_mobile_money_push(
                service_type=service_type,
                service_object=service_object,
                scanner_participant=scanner
            )

            return Response({
                'success': True,
                **result,
            }, status=status.HTTP_200_OK)

        except PermissionError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    except Exception as e:
        logger.error(f'Error scanning service QR: {str(e)}', exc_info=True)
        return Response(
            {'detail': f'Erreur lors du scan: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Payment callback endpoint for Fedapay",
    parameters=[
        OpenApiParameter('service_type', OpenApiTypes.STR, OpenApiParameter.PATH),
        OpenApiParameter('service_id', OpenApiTypes.STR, OpenApiParameter.PATH),
        OpenApiParameter('status', OpenApiTypes.STR, OpenApiParameter.QUERY),
    ],
    responses={200: dict, 400: dict}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_callback(request, service_type, service_id):
    """
    Universal Fedapay payment callback endpoint.

    URL: /api/payments/callback/<service_type>/<service_id>/

    Query params:
        - status: success|failed|cancelled
        - transaction_id: Gateway transaction ID
    """
    try:
        participant = request.user

        # Verify service
        qr_data = {
            'type': service_type,
            'service_id': service_id,
        }

        verification = UniversalPaymentService.verify_payment_qr(qr_data)

        if not verification['valid']:
            return Response(
                {'detail': verification['error']},
                status=status.HTTP_404_NOT_FOUND
            )

        service_object = verification['service_object']

        # Get payment status from query params
        payment_status = request.query_params.get('status')
        transaction_id = request.query_params.get('transaction_id')

        if payment_status == 'success':
            # Payment will be confirmed by webhook, just return success message
            return Response({
                'success': True,
                'message': 'Paiement en cours de vérification',
                'service_type': service_type,
                'service_id': service_id,
                'redirect_url': f'/patient/{service_type}s/{service_id}',
            }, status=status.HTTP_200_OK)

        elif payment_status in ['failed', 'cancelled']:
            return Response({
                'success': False,
                'message': f'Paiement {payment_status}',
                'service_type': service_type,
                'service_id': service_id,
                'redirect_url': f'/patient/{service_type}s/{service_id}',
            }, status=status.HTTP_200_OK)

        else:
            return Response({
                'success': False,
                'message': 'Statut de paiement inconnu',
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f'Error in payment callback: {str(e)}', exc_info=True)
        return Response(
            {'detail': f'Erreur: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
