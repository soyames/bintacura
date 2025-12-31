from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse, FileResponse
from decimal import Decimal
import json
import logging
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from .models import *
from .serializers import *
from .fedapay_webhook_handler import FedaPayWebhookHandler, FedaPayWalletService
from .fedapay_service import fedapay_service
from .receipt_service import ReceiptPDFService
from .service_payment_service import ServicePaymentService
from core.models import Transaction as CoreTransaction, Participant
from core.view_mixins import SafeQuerysetMixin

logger = logging.getLogger(__name__)


class FeeLedgerViewSet(SafeQuerysetMixin, viewsets.ModelViewSet):  # View for FeeLedgerSet operations
    serializer_class = FeeLedgerSerializer
    permission_classes = [IsAuthenticated]
    queryset = FeeLedger.objects.none()

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return FeeLedger.objects.none()
        return FeeLedger.objects.filter(participant=self.request.user)


class PaymentRequestViewSet(SafeQuerysetMixin, viewsets.ModelViewSet):  # View for PaymentRequestSet operations
    serializer_class = PaymentRequestSerializer
    permission_classes = [IsAuthenticated]
    queryset = PaymentRequest.objects.none()

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return PaymentRequest.objects.none()
        return PaymentRequest.objects.filter(to_participant=self.request.user)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):  # Approve
        payment_request = self.get_object()
        if payment_request.to_participant != request.user:
            return Response(
                {"error": "Not authorized"}, status=status.HTTP_403_FORBIDDEN
            )

        if payment_request.status != "pending":
            return Response(
                {"error": "Request already processed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment_request.status = "approved"
        payment_request.responded_at = timezone.now()
        payment_request.save()

        return Response({"message": "Payment request approved"})

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):  # Reject
        payment_request = self.get_object()
        if payment_request.to_participant != request.user:
            return Response(
                {"error": "Not authorized"}, status=status.HTTP_403_FORBIDDEN
            )

        if payment_request.status != "pending":
            return Response(
                {"error": "Request already processed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment_request.status = "rejected"
        payment_request.rejection_reason = request.data.get("reason", "")
        payment_request.responded_at = timezone.now()
        payment_request.save()

        return Response({"message": "Payment request rejected"})


class LinkedVendorViewSet(viewsets.ModelViewSet):  # View for LinkedVendorSet operations
    serializer_class = LinkedVendorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        return LinkedVendor.objects.filter(participant=self.request.user)

    def perform_create(self, serializer):  # Perform create
        serializer.save(participant=self.request.user)

    @action(detail=True, methods=["post"])
    def charge(self, request, pk=None):  # Charge
        vendor = self.get_object()
        amount = request.data.get("amount")

        if not amount:
            return Response(
                {"error": "Amount required"}, status=status.HTTP_400_BAD_REQUEST
            )

        vendor.last_used_at = timezone.now()
        vendor.save()

        return Response({"message": "Payment method charged", "amount": amount})


class FinancialChatViewSet(viewsets.ModelViewSet):  # View for FinancialChatSet operations
    serializer_class = FinancialChatSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        return FinancialChat.objects.filter(participant=self.request.user)

    def perform_create(self, serializer):  # Perform create
        serializer.save(participant=self.request.user)

    @action(detail=True, methods=["post"])
    def add_message(self, request, pk=None):  # Add message
        chat = self.get_object()
        content = request.data.get("content")

        if not content:
            return Response(
                {"error": "Message content required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        message = FinancialChatMessage.objects.create(
            chat=chat, sender=request.user, message_type="user", content=content
        )

        chat.updated_at = timezone.now()
        chat.save()

        return Response(FinancialChatMessageSerializer(message).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):  # Close
        chat = self.get_object()
        if chat.participant != request.user:
            return Response(
                {"error": "Not authorized"}, status=status.HTTP_403_FORBIDDEN
            )

        chat.status = "closed"
        chat.resolved_at = timezone.now()
        chat.save()

        return Response({"message": "Chat closed"})


class FedaPayTransactionViewSet(SafeQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    """View FedaPay transactions"""
    serializer_class = FedaPayTransactionSerializer
    permission_classes = [IsAuthenticated]
    queryset = FedaPayTransaction.objects.none()

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return FedaPayTransaction.objects.none()
        return FedaPayTransaction.objects.filter(participant=self.request.user)

    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        """Get real-time status from FedaPay"""
        fedapay_txn = self.get_object()
        
        if not fedapay_txn.fedapay_transaction_id:
            return Response(
                {"error": "No FedaPay transaction ID"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            status_data = FedaPayWalletService.get_transaction_status(
                fedapay_txn.fedapay_transaction_id
            )
            return Response(status_data)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=["get"])
    def download_receipt(self, request, pk=None):
        """Download PDF receipt for transaction"""
        fedapay_txn = self.get_object()
        
        try:
            # Generate receipt number if not exists
            receipt_number = f"RCP-{fedapay_txn.id}"
            
            # Generate PDF
            pdf_buffer = ReceiptPDFService.generate_transaction_receipt(
                fedapay_txn,
                receipt_number
            )
            
            # Return PDF as response
            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="receipt_{receipt_number}.pdf"'
            return response
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class WalletTopupView(APIView):
    """Initiate wallet top-up via FedaPay"""
    permission_classes = [IsAuthenticated]

    def post(self, request):  # Post
        serializer = WalletTopupRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        amount = serializer.validated_data['amount']
        currency = serializer.validated_data.get('currency', 'XOF')
        
        # Build callback URL
        callback_url = request.build_absolute_uri('/api/payments/fedapay/webhook/')
        
        try:
            result = FedaPayWalletService.initiate_wallet_topup(
                participant=request.user,
                amount=amount,
                currency=currency,
                callback_url=callback_url
            )
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    summary="FedaPay webhook handler",
    request={'application/json': dict},
    responses={200: dict, 400: dict}
)
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def fedapay_webhook(request):
    """Handle FedaPay webhook events with ACID compliance and idempotency"""
    
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    # Get signature from headers
    signature = request.META.get('HTTP_X_FEDAPAY_SIGNATURE', '')
    
    # CRITICAL: Always verify signature
    if not signature:
        logger.error("Webhook rejected: Missing X-FedaPay-Signature header")
        return JsonResponse({"error": "Missing signature"}, status=401)
    
    # Verify signature before processing
    payload = request.body.decode('utf-8')
    if not fedapay_service.verify_webhook_signature(payload, signature):
        logger.error("Webhook rejected: Invalid signature")
        return JsonResponse({"error": "Invalid signature"}, status=401)
    
    try:
        event_data = json.loads(payload)
        
        # Validate required fields
        if 'entity' not in event_data or 'event' not in event_data:
            logger.error(f"Webhook rejected: Missing required fields in payload")
            return JsonResponse({"error": "Invalid payload structure"}, status=400)
        
        # Handle webhook with transaction safety
        success = FedaPayWebhookHandler.handle_webhook(event_data)
        
        if success:
            return JsonResponse({"status": "success"}, status=200)
        else:
            # Return 200 even on processing errors to prevent webhook disabling
            logger.warning(f"Webhook processing warning for event {event_data.get('event')}")
            return JsonResponse({"status": "acknowledged"}, status=200)
            
    except json.JSONDecodeError as e:
        logger.error(f"Webhook rejected: Invalid JSON - {str(e)}")
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}", exc_info=True)
        # Return 200 to acknowledge receipt, log for manual review
        return JsonResponse({"status": "error_logged"}, status=200)


@extend_schema(
    summary="Download transaction receipt as PDF",
    parameters=[OpenApiParameter('transaction_id', OpenApiTypes.STR, OpenApiParameter.PATH)],
    responses={200: bytes, 404: dict}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_transaction_receipt(request, transaction_id):
    """Download PDF receipt for a core transaction"""
    
    try:
        transaction = CoreTransaction.objects.get(
            id=transaction_id,
            wallet__participant=request.user
        )
        
        # Check if receipt already exists
        try:
            receipt = PaymentReceipt.objects.get(transaction=transaction)
            receipt_number = receipt.receipt_number
            
            if not receipt.invoice_number or not receipt.qr_code:
                from .invoice_number_service import InvoiceNumberService
                from .qr_service import QRCodeService
                
                if not receipt.invoice_number:
                    invoice_data = InvoiceNumberService.generate_invoice_number(
                        service_provider_role=transaction.recipient.role if transaction.recipient else 'doctor'
                    )
                    receipt.invoice_number = invoice_data['invoice_number']
                    receipt.invoice_sequence = invoice_data['sequence']
                
                if not receipt.qr_code:
                    QRCodeService.generate_invoice_qr_code(receipt)
                    
                receipt.save()
                
        except PaymentReceipt.DoesNotExist:
            from .invoice_number_service import InvoiceNumberService
            from .qr_service import QRCodeService
            
            receipt_number = f"RCP-{timezone.now().strftime('%Y%m%d')}-{transaction.id}"
            
            invoice_data = InvoiceNumberService.generate_invoice_number(
                service_provider_role=transaction.recipient.role if transaction.recipient else 'doctor'
            )
            
            receipt = PaymentReceipt.objects.create(
                transaction=transaction,
                receipt_number=receipt_number,
                invoice_number=invoice_data['invoice_number'],
                invoice_sequence=invoice_data['sequence'],
                issued_to=request.user,
                issued_by=request.user
            )
            
            QRCodeService.generate_invoice_qr_code(receipt)
        
        # Generate PDF
        pdf_buffer = ReceiptPDFService.generate_transaction_receipt(
            transaction,
            receipt_number
        )
        
        # Return PDF as response
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="receipt_{receipt_number}.pdf"'
        return response
        
    except CoreTransaction.DoesNotExist:
        return JsonResponse(
            {"error": "Transaction not found"},
            status=404
        )
    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=500
        )


class ServicePaymentView(APIView):
    """Process service payments (appointments, prescriptions, etc.) with 1% fee"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):  # Post
        serializer = ServicePaymentRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        
        try:
            # Get provider
            provider = Participant.objects.get(uid=data['provider_id'])
            
            # Check if provider is verified and can receive payments
            if provider.role in ['doctor', 'hospital', 'pharmacy', 'insurance_company']:
                if not provider.is_verified or not provider.can_receive_payments:
                    return Response(
                        {"error": "This provider is not yet verified to receive payments. Please contact support."},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Process payment based on method
            if data['payment_method'] == 'wallet':
                result = ServicePaymentService.process_wallet_payment(
                    patient=request.user,
                    provider=provider,
                    amount=data['amount'],
                    currency=data['currency'],
                    service_type=data['service_type'],
                    service_id=data['service_id'],
                    description=data['description']
                )
            else:  # onsite
                result = ServicePaymentService.record_onsite_payment(
                    patient=request.user,
                    provider=provider,
                    amount=data['amount'],
                    currency=data['currency'],
                    service_type=data['service_type'],
                    service_id=data['service_id'],
                    description=data['description']
                )
            
            # Generate receipt
            receipt = ServicePaymentService.generate_payment_receipt(
                result['patient_transaction'],
                service_provider_role=provider.role
            )
            
            return Response({
                'success': True,
                'message': f"Payment processed successfully via {data['payment_method']}",
                'patient_transaction_id': str(result['patient_transaction'].id),
                'provider_transaction_id': str(result['provider_transaction'].id),
                'receipt_number': receipt.receipt_number,
                'fee_details': {
                    'gross_amount': str(result['fee_calculation']['gross_amount']),
                    'platform_fee': str(result['fee_calculation']['platform_fee']),
                    'tax': str(result['fee_calculation']['tax']),
                    'total_fee': str(result['fee_calculation']['total_fee']),
                    'net_to_provider': str(result['fee_calculation']['net_amount']),
                    'fee_rate': '1% + 18% tax on fee'
                },
                'payment_method': data['payment_method'],
                'patient_new_balance': str(result.get('patient_new_balance', 'N/A')),
                'provider_new_balance': str(result.get('provider_new_balance', 'N/A'))
            }, status=status.HTTP_200_OK)
            
        except Participant.DoesNotExist:
            return Response(
                {"error": "Provider not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Payment processing failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
