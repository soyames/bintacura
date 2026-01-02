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

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        payment_request = self.get_object()
        if payment_request.to_participant != request.user:
            return Response(
                {"error": "Not authorized"}, status=status.HTTP_403_FORBIDDEN
            )

        if payment_request.status != "approved":
            return Response(
                {"error": "Request must be approved first"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment_request.status = "completed"
        payment_request.save()
        
        if payment_request.receipt:
            payment_request.receipt.payment_status = "paid"
            payment_request.receipt.save()

        return Response({"message": "Payment marked as completed"})


class LinkedVendorViewSet(viewsets.ModelViewSet):  # View for LinkedVendorSet operations
    serializer_class = LinkedVendorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return LinkedVendor.objects.none()
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
        if getattr(self, 'swagger_fake_view', False):
            return FinancialChat.objects.none()
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
@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
@csrf_exempt
def fedapay_webhook(request):
    """
    Handle FedaPay webhook events with ACID compliance and idempotency
    
    POST: Real webhook events from FedaPay (verified with signature)
    GET: User redirect callbacks (status=approved/declined/pending)
    """
    
    # Handle GET requests (user redirects from FedaPay payment page)
    if request.method == 'GET':
        status_param = request.GET.get('status', '')
        transaction_id = request.GET.get('id', '')
        
        logger.info(f"📥 FedaPay redirect callback: status={status_param}, transaction_id={transaction_id}")
        
        # Log the redirect for tracking
        if transaction_id:
            try:
                from .models import FedaPayWebhookEvent
                FedaPayWebhookEvent.objects.create(
                    event_id=f"redirect-{transaction_id}-{timezone.now().timestamp()}",
                    event_type=f'transaction.redirect.{status_param}',
                    payload={
                        'type': 'redirect_callback',
                        'status': status_param,
                        'transaction_id': transaction_id,
                        'timestamp': str(timezone.now())
                    },
                    processed=True,
                    processed_at=timezone.now()
                )
                logger.info(f"✅ Redirect callback logged for transaction {transaction_id}")
            except Exception as e:
                logger.warning(f"Failed to log redirect callback: {e}")
        
        # Return a simple HTML response thanking the user
        return HttpResponse(
            f"""
            <html>
                <head>
                    <title>Payment {status_param.title()}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                        .success {{ color: #28a745; }}
                        .pending {{ color: #ffc107; }}
                        .declined {{ color: #dc3545; }}
                    </style>
                </head>
                <body>
                    <h1 class="{status_param}">Payment {status_param.title()}</h1>
                    <p>Transaction ID: {transaction_id}</p>
                    <p>You can close this window and return to the application.</p>
                    <script>
                        setTimeout(function() {{ window.close(); }}, 3000);
                    </script>
                </body>
            </html>
            """,
            content_type='text/html'
        )
    
    # Handle POST requests (real webhooks from FedaPay)
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


@extend_schema(
    summary="Request cash payment for an invoice",
    request={'application/json': dict},
    responses={200: dict, 400: dict, 404: dict}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_cash_payment(request):
    """
    Patient requests to pay an invoice in cash (on-site).
    Creates a payment request that service provider must approve.
    """
    try:
        invoice_id = request.data.get('invoice_id')
        invoice_type = request.data.get('invoice_type', 'service')
        
        if not invoice_id:
            return Response(
                {"error": "invoice_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the receipt/invoice
        try:
            receipt = PaymentReceipt.objects.get(id=invoice_id)
        except PaymentReceipt.DoesNotExist:
            return Response(
                {"error": "Facture introuvable"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already paid
        if receipt.payment_status == 'paid':
            return Response(
                {"error": "Cette facture est déjà payée"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Determine service provider
        service_provider = receipt.issued_by if receipt.issued_by else receipt.issued_to
        
        # Check if payment request already exists
        existing_request = PaymentRequest.objects.filter(
            receipt=receipt,
            from_participant=request.user,
            status='pending'
        ).first()
        
        if existing_request:
            return Response(
                {"error": "Une demande de paiement est déjà en attente pour cette facture"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create payment request
        payment_request = PaymentRequest.objects.create(
            from_participant=request.user,
            to_participant=service_provider,
            amount=int(receipt.amount * 100) if hasattr(receipt, 'amount') else 0,
            currency=receipt.currency if hasattr(receipt, 'currency') else 'XOF',
            description=f"Paiement en espèces pour facture {receipt.invoice_number}",
            payment_method='cash',
            receipt=receipt,
            status='pending'
        )
        
        # Create notification for service provider
        from communication.models import Notification
        Notification.objects.create(
            participant=service_provider,
            title="Nouvelle demande de paiement en espèces",
            message=f"{request.user.get_full_name()} demande à payer la facture {receipt.invoice_number} en espèces",
            notification_type='payment_request',
            metadata={
                'payment_request_id': str(payment_request.id),
                'invoice_id': str(receipt.id),
                'amount': str(receipt.amount) if hasattr(receipt, 'amount') else '0',
                'patient_name': request.user.get_full_name()
            }
        )
        
        logger.info(f"Cash payment request created: {payment_request.id} for invoice {receipt.id}")
        
        return Response({
            'success': True,
            'message': 'Demande de paiement envoyée avec succès',
            'payment_request_id': str(payment_request.id)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error creating cash payment request: {str(e)}", exc_info=True)
        return Response(
            {"error": f"Erreur lors de la création de la demande: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Initiate online payment via FedaPay",
    request={'application/json': dict},
    responses={200: dict, 400: dict, 404: dict}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_online_payment(request):
    """
    Initiate an online payment via FedaPay for an invoice.
    Returns FedaPay payment URL for redirect.
    """
    try:
        invoice_id = request.data.get('invoice_id')
        invoice_type = request.data.get('invoice_type', 'service')
        
        if not invoice_id:
            return Response(
                {"error": "invoice_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the receipt/invoice
        try:
            receipt = PaymentReceipt.objects.get(id=invoice_id)
        except PaymentReceipt.DoesNotExist:
            return Response(
                {"error": "Facture introuvable"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already paid
        if receipt.payment_status == 'paid':
            return Response(
                {"error": "Cette facture est déjà payée"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get amount
        amount = receipt.amount if hasattr(receipt, 'amount') else 0
        currency = receipt.currency if hasattr(receipt, 'currency') else 'XOF'
        
        # Build callback URL
        callback_url = request.build_absolute_uri('/api/v1/payments/fedapay/webhook/')
        
        # Initiate FedaPay transaction
        result = fedapay_service.create_transaction(
            amount=amount,
            currency=currency,
            description=f"Paiement facture {receipt.invoice_number}",
            callback_url=callback_url,
            customer_email=request.user.email if request.user.email else None,
            customer_firstname=request.user.first_name if request.user.first_name else None,
            customer_lastname=request.user.last_name if request.user.last_name else None,
            custom_metadata={
                'invoice_id': str(receipt.id),
                'invoice_number': receipt.invoice_number,
                'patient_id': str(request.user.uid),
                'invoice_type': invoice_type
            }
        )
        
        if result['success']:
            # Create FedaPayTransaction record
            FedaPayTransaction.objects.create(
                participant=request.user,
                fedapay_transaction_id=result['transaction_id'],
                amount=amount,
                currency=currency,
                description=f"Paiement facture {receipt.invoice_number}",
                status='pending',
                metadata={
                    'invoice_id': str(receipt.id),
                    'invoice_number': receipt.invoice_number
                }
            )
            
            logger.info(f"Online payment initiated for invoice {receipt.id}: {result['transaction_id']}")
            
            return Response({
                'success': True,
                'payment_url': result['payment_url'],
                'transaction_id': result['transaction_id']
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": result.get('error', 'Erreur lors de l\'initialisation du paiement')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
    except Exception as e:
        logger.error(f"Error initiating online payment: {str(e)}", exc_info=True)
        return Response(
            {"error": f"Erreur lors de l\'initialisation: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Approve cash payment request (for service providers)",
    request={'application/json': dict},
    responses={200: dict, 400: dict, 403: dict, 404: dict}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_cash_payment(request):
    """
    Service provider approves a cash payment request.
    Marks invoice as paid and completes payment request.
    """
    try:
        payment_request_id = request.data.get('payment_request_id')
        
        if not payment_request_id:
            return Response(
                {"error": "payment_request_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get payment request
        try:
            payment_request = PaymentRequest.objects.get(id=payment_request_id)
        except PaymentRequest.DoesNotExist:
            return Response(
                {"error": "Demande de paiement introuvable"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check authorization
        if payment_request.to_participant != request.user:
            return Response(
                {"error": "Non autorisé"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if already processed
        if payment_request.status != 'pending':
            return Response(
                {"error": "Cette demande a déjà été traitée"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update payment request
        payment_request.status = 'approved'
        payment_request.responded_at = timezone.now()
        payment_request.save()
        
        # Update invoice/receipt to paid
        if payment_request.receipt:
            receipt = payment_request.receipt
            receipt.payment_status = 'paid'
            receipt.save()
            
            logger.info(f"Cash payment approved: {payment_request.id}, invoice {receipt.id} marked as paid")
        
        # Create notification for patient
        from communication.models import Notification
        Notification.objects.create(
            participant=payment_request.from_participant,
            title="Paiement approuvé",
            message=f"Votre paiement en espèces pour la facture {payment_request.receipt.invoice_number if payment_request.receipt else ''} a été approuvé",
            notification_type='payment_approved',
            metadata={
                'payment_request_id': str(payment_request.id),
                'invoice_id': str(payment_request.receipt.id) if payment_request.receipt else None
            }
        )
        
        return Response({
            'success': True,
            'message': 'Paiement approuvé avec succès'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error approving cash payment: {str(e)}", exc_info=True)
        return Response(
            {"error": f"Erreur lors de l\'approbation: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
