"""
Pharmacy Payment Views
QR-driven payment endpoints for pharmacy orders
"""
import logging
import json
from decimal import Decimal
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from pharmacy.models import PharmacyOrder
from pharmacy.payment_service import PharmacyPaymentService
from qrcode_generator.models import QRCode
from currency_converter.services import CurrencyConverterService

logger = logging.getLogger(__name__)


@extend_schema(
    summary="Verify pharmacy order QR code",
    parameters=[OpenApiParameter('order_id', OpenApiTypes.STR, OpenApiParameter.PATH)],
    responses={200: dict, 400: dict}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_order_qr(request, order_id):
    """
    Verify pharmacy order QR code and return order details.
    Called when patient scans QR code to view order and payment options.

    Returns:
        - Order details
        - Payment options based on order.payment_method
        - Outstanding amount in patient's currency
    """
    try:
        participant = request.user

        order = PharmacyOrder.objects.select_related('patient', 'pharmacy').filter(id=order_id).first()

        if not order:
            return Response(
                {'detail': 'Commande introuvable'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verify participant has access (patient or pharmacy)
        if participant.uid not in [order.patient.uid, order.pharmacy.uid]:
            # Check if participant is pharmacy staff
            from pharmacy.models import PharmacyStaff
            is_staff = PharmacyStaff.objects.filter(
                pharmacy=order.pharmacy,
                staff_participant=participant,
                is_active=True
            ).exists()

            if not is_staff:
                return Response(
                    {'detail': 'Accès non autorisé'},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Get participant's currency
        viewer_currency = CurrencyConverterService.get_participant_currency(participant)

        # Convert amount if needed
        order_amount = Decimal(str(order.total_amount)) / 100  # Convert from minor units

        if viewer_currency != order.currency:
            display_amount = CurrencyConverterService.convert(
                order_amount,
                order.currency,
                viewer_currency
            )
        else:
            display_amount = order_amount

        # Get order items
        items = []
        for item in order.items.all():
            items.append({
                'medication_name': item.medication.name if item.medication else 'N/A',
                'quantity': item.quantity,
                'unit_price': float(item.unit_price / 100),
                'total_price': float(item.total_price / 100),
            })

        # Get QR code
        qr_code = QRCode.objects.filter(
            content_type='pharmacy_order',
            object_id=str(order.id),
            is_active=True
        ).first()

        response_data = {
            'success': True,
            'order': {
                'id': str(order.id),
                'order_number': order.order_number,
                'status': order.status,
                'payment_status': order.payment_status,
                'payment_method': order.payment_method,
                'total_amount': float(order_amount),
                'currency': order.currency,
                'display_amount': float(display_amount),
                'display_currency': viewer_currency,
                'created_at': order.order_date.isoformat(),
                'items': items,
            },
            'patient': {
                'id': str(order.patient.uid),
                'name': order.patient.full_name,
                'phone': order.patient.phone_number or order.patient.phone,
            },
            'pharmacy': {
                'id': str(order.pharmacy.uid),
                'name': order.pharmacy.full_name,
                'address': order.pharmacy.address,
            },
            'qr_code_url': request.build_absolute_uri(qr_code.qr_code_image.url) if qr_code and qr_code.qr_code_image else None,
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f'Error verifying order QR: {str(e)}', exc_info=True)
        return Response(
            {'detail': f'Erreur lors de la vérification: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Pay for pharmacy order",
    parameters=[OpenApiParameter('order_id', OpenApiTypes.STR, OpenApiParameter.PATH)],
    request={'application/json': dict},
    responses={200: dict, 400: dict}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def pay_order(request, order_id):
    """
    Process payment for pharmacy order (patient scans QR and pays).
    Supports multiple payment methods:
    - wallet: Deduct from patient wallet
    - card/mobile_money: Initiate gateway payment
    - insurance: Process insurance claim
    - cash: Mark as pending (pay on pickup)

    Request body:
        {
            "payment_method": "wallet|card|mobile_money|insurance|cash"  (optional, uses order.payment_method if not provided)
        }
    """
    try:
        participant = request.user

        order = PharmacyOrder.objects.select_for_update().select_related('patient', 'pharmacy').filter(id=order_id).first()

        if not order:
            return Response(
                {'detail': 'Commande introuvable'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verify participant is the patient
        if participant.role != 'patient' or participant.uid != order.patient.uid:
            return Response(
                {'detail': 'Seul le patient peut effectuer le paiement'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if already paid
        if order.payment_status == 'paid':
            return Response(
                {'detail': 'Cette commande a déjà été payée'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get payment method (can override order's payment method)
        payment_method = request.data.get('payment_method', order.payment_method)

        # Process based on payment method
        if payment_method == 'wallet':
            # Wallet payment
            from core.services import WalletService
            from core.models import Wallet

            patient_wallet = Wallet.objects.filter(participant=participant).first()
            if not patient_wallet:
                return Response(
                    {'detail': 'Portefeuille non trouvé'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            order_amount = Decimal(str(order.total_amount)) / 100

            if patient_wallet.balance < order_amount:
                return Response(
                    {'detail': f'Solde insuffisant. Solde: {patient_wallet.balance} {order.currency}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Deduct from wallet
            WalletService.deduct_funds(
                participant=participant,
                amount=order_amount,
                description=f'Paiement commande pharmacie {order.order_number}',
                reference_id=str(order.id)
            )

            # Update order
            order.payment_status = 'paid'
            order.amount_paid = order.total_amount
            order.payment_reference = f'WALLET-{order.order_number}'
            order.save()

            # Create receipt
            receipt = PharmacyPaymentService.create_payment_receipt(order)

            return Response({
                'success': True,
                'message': 'Paiement effectué avec succès',
                'payment_method': 'wallet',
                'receipt_number': receipt.receipt_number,
                'order_status': order.payment_status,
            }, status=status.HTTP_200_OK)

        elif payment_method in ['card', 'mobile_money']:
            # Gateway payment
            result = PharmacyPaymentService.initiate_gateway_payment(order)

            return Response({
                'success': True,
                'message': 'Paiement en cours de traitement',
                'payment_method': payment_method,
                'payment_url': result['payment_url'],
                'payment_token': result.get('payment_token'),
                'amount': result['amount'],
                'currency': result['currency'],
            }, status=status.HTTP_200_OK)

        elif payment_method == 'insurance':
            # Insurance already handled in order creation
            return Response({
                'success': True,
                'message': 'Réclamation d\'assurance en cours de traitement',
                'payment_method': 'insurance',
                'payment_reference': order.payment_reference,
            }, status=status.HTTP_200_OK)

        else:  # cash or cash_on_delivery
            return Response({
                'success': True,
                'message': 'Paiement en espèces à la livraison/retrait',
                'payment_method': payment_method,
            }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f'Error processing payment: {str(e)}', exc_info=True)
        return Response(
            {'detail': f'Erreur lors du paiement: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Pharmacy staff scans order QR code",
    request={'application/json': dict},
    responses={200: dict, 400: dict}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def scan_order_qr(request):
    """
    Provider (pharmacy staff) scans patient's order QR code to initiate mobile money push.

    Request body:
        {
            "qr_data": "..." (JSON string from QR code)
            OR
            "order_id": "..."
        }

    Returns:
        - Payment initiation details
        - Mobile money push status
    """
    try:
        scanner = request.user

        # Get order from QR data or order_id
        qr_data = request.data.get('qr_data')
        order_id = request.data.get('order_id')

        if qr_data:
            # Verify QR code
            verification = PharmacyPaymentService.verify_order_qr(qr_data)
            if not verification['valid']:
                return Response(
                    {'detail': verification['error']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            order = verification['order']
        elif order_id:
            order = PharmacyOrder.objects.select_related('patient', 'pharmacy').filter(id=order_id).first()
            if not order:
                return Response(
                    {'detail': 'Commande introuvable'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            return Response(
                {'detail': 'qr_data ou order_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if already paid
        if order.payment_status == 'paid':
            return Response(
                {'detail': 'Cette commande a déjà été payée'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Initiate mobile money push
        try:
            result = PharmacyPaymentService.process_mobile_money_push(order, scanner)

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
        logger.error(f'Error scanning order QR: {str(e)}', exc_info=True)
        return Response(
            {'detail': f'Erreur lors du scan: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Payment callback for pharmacy orders",
    parameters=[
        OpenApiParameter('order_id', OpenApiTypes.STR, OpenApiParameter.PATH),
        OpenApiParameter('status', OpenApiTypes.STR, OpenApiParameter.QUERY),
    ],
    responses={200: dict, 400: dict}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_callback(request, order_id):
    """
    Fedapay payment callback endpoint.
    Called after payment gateway completes (success or failure).

    Query params:
        - status: success|failed|cancelled
        - transaction_id: Gateway transaction ID
    """
    try:
        participant = request.user

        order = PharmacyOrder.objects.select_related('patient', 'pharmacy').filter(id=order_id).first()

        if not order:
            return Response(
                {'detail': 'Commande introuvable'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get payment status from query params
        payment_status = request.query_params.get('status')
        transaction_id = request.query_params.get('transaction_id')

        if payment_status == 'success':
            # Payment will be confirmed by webhook, just return success message
            return Response({
                'success': True,
                'message': 'Paiement en cours de vérification',
                'order_number': order.order_number,
                'redirect_url': f'/patient/orders/{order.id}',
            }, status=status.HTTP_200_OK)

        elif payment_status in ['failed', 'cancelled']:
            return Response({
                'success': False,
                'message': f'Paiement {payment_status}',
                'order_number': order.order_number,
                'redirect_url': f'/patient/orders/{order.id}',
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
