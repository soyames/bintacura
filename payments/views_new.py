from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.http import HttpResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404, render
from django.conf import settings
from decimal import Decimal
from .models import (
    ParticipantPhone,
    ServiceCatalog,
    ParticipantGatewayAccount,
    ServiceTransaction,
    TransactionFee,
    GatewayTransaction,
    PayoutSchedule,
    PaymentReceipt,
)
from .serializers import (
    ParticipantPhoneSerializer,
    PhoneVerificationSerializer,
    PhoneVerifyCodeSerializer,
    ServiceCatalogSerializer,
    ServiceCatalogCreateSerializer,
    ParticipantGatewayAccountSerializer,
    GatewayAccountSetupSerializer,
    ServiceTransactionSerializer,
    ServicePaymentInitiateSerializer,
    FeeCalculationSerializer,
    PayoutScheduleSerializer,
    PaymentReceiptSerializer,
)
from .services.phone_verification_service import PhoneVerificationService
from .services.fedapay_gateway_service import FedaPayGatewayService
from .services.service_transaction_service import ServiceTransactionService
from .fee_service import FeeCalculationService
from .receipt_service import ReceiptPDFService
from .enhanced_receipt_service import EnhancedReceiptService
from core.models import Participant


class ParticipantPhoneViewSet(viewsets.ModelViewSet):  # View for ParticipantPhoneSet operations
    serializer_class = ParticipantPhoneSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return ParticipantPhone.objects.none()
        return ParticipantPhone.objects.filter(participant=self.request.user)

    def perform_create(self, serializer):  # Perform create
        serializer.save(participant=self.request.user)

    @action(detail=False, methods=['post'])
    def initiate_verification(self, request):  # Initiate verification
        serializer = PhoneVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        result = PhoneVerificationService.initiate_phone_verification(
            participant=request.user,
            phone_number=serializer.validated_data['phone_number'],
            country_code=serializer.validated_data['country_code'],
            is_primary=serializer.validated_data.get('is_primary', False)
        )

        return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):  # Verify
        phone = self.get_object()
        serializer = PhoneVerifyCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        result = PhoneVerificationService.verify_phone_code(
            phone_id=str(phone.id),
            verification_code=serializer.validated_data['verification_code']
        )

        return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def resend_code(self, request, pk=None):  # Resend code
        phone = self.get_object()

        result = PhoneVerificationService.initiate_phone_verification(
            participant=request.user,
            phone_number=phone.phone_number,
            country_code=phone.country_code,
            is_primary=phone.is_primary
        )

        return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):  # Set primary
        phone = self.get_object()

        result = PhoneVerificationService.set_primary_phone(
            participant=request.user,
            phone_id=str(phone.id)
        )

        return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)


class ServiceCatalogViewSet(viewsets.ModelViewSet):  # Service class for CatalogViewSet operations
    serializer_class = ServiceCatalogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        queryset = ServiceCatalog.objects.filter(is_active=True)

        service_category = self.request.query_params.get('service_category')
        provider_role = self.request.query_params.get('provider_role')
        provider_id = self.request.query_params.get('provider_id')
        region_code = self.request.query_params.get('region_code')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')

        if service_category:
            queryset = queryset.filter(service_category=service_category)
        if provider_role:
            queryset = queryset.filter(service_provider_role=provider_role)
        if provider_id:
            queryset = queryset.filter(service_provider_id=provider_id)
        if region_code:
            queryset = queryset.filter(region_code=region_code)
        if min_price:
            queryset = queryset.filter(price__gte=Decimal(min_price))
        if max_price:
            queryset = queryset.filter(price__lte=Decimal(max_price))

        return queryset.select_related('service_provider', 'created_by')

    def get_serializer_class(self):  # Get serializer class
        if self.action == 'create' or self.action == 'update':
            return ServiceCatalogCreateSerializer
        return ServiceCatalogSerializer

    def perform_create(self, serializer):  # Perform create
        serializer.save(
            service_provider=self.request.user,
            created_by=self.request.user
        )

    @action(detail=False, methods=['get'])
    def my_services(self, request):  # My services
        queryset = ServiceCatalog.objects.filter(service_provider=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def toggle_availability(self, request, pk=None):  # Toggle availability
        service = self.get_object()

        if service.service_provider != request.user:
            return Response(
                {'error': 'Not authorized'},
                status=status.HTTP_403_FORBIDDEN
            )

        service.is_available = not service.is_available
        service.save()

        return Response({
            'success': True,
            'is_available': service.is_available,
            'message': f'Service is now {"available" if service.is_available else "unavailable"}'
        })

    @action(detail=False, methods=['get'])
    def categories(self, request):  # Categories
        return Response([
            {'value': cat[0], 'label': cat[1]}
            for cat in ServiceCatalog.SERVICE_CATEGORY_CHOICES
        ])


class ParticipantGatewayAccountViewSet(viewsets.ModelViewSet):  # View for ParticipantGatewayAccountSet operations
    serializer_class = ParticipantGatewayAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return ParticipantGatewayAccount.objects.none()
        return ParticipantGatewayAccount.objects.filter(participant=self.request.user)

    @action(detail=False, methods=['post'])
    def setup(self, request):  # Setup
        serializer = GatewayAccountSetupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            phone = ParticipantPhone.objects.get(
                id=serializer.validated_data['phone_id'],
                participant=request.user
            )

            if not phone.is_verified:
                return Response(
                    {'error': 'Phone number must be verified before linking to payment gateway'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            gateway_account = FedaPayGatewayService.create_payment_gateway_account(
                participant=request.user,
                participant_phone=phone,
                gateway_provider=serializer.validated_data['gateway_provider'],
                payout_mode=serializer.validated_data.get('payout_mode')
            )

            return Response(
                ParticipantGatewayAccountSerializer(gateway_account).data,
                status=status.HTTP_201_CREATED
            )

        except ParticipantPhone.DoesNotExist:
            return Response(
                {'error': 'Phone not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):  # Set default
        gateway_account = self.get_object()

        ParticipantGatewayAccount.objects.filter(participant=request.user).update(is_default=False)
        gateway_account.is_default = True
        gateway_account.save()

        return Response({
            'success': True,
            'message': 'Default payment gateway updated'
        })


@extend_schema_view(
    post=extend_schema(
        request=ServicePaymentInitiateSerializer,
        responses={201: ServiceTransactionSerializer}
    )
)
class ServicePaymentView(APIView):  # Service class for PaymentView operations
    permission_classes = [IsAuthenticated]
    serializer_class = ServicePaymentInitiateSerializer

    def post(self, request):  # Post
        serializer = ServicePaymentInitiateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            service_provider = Participant.objects.get(id=serializer.validated_data['service_provider_id'])

            service_catalog_item = None
            amount = serializer.validated_data.get('amount')

            if serializer.validated_data.get('service_catalog_id'):
                service_catalog_item = ServiceCatalog.objects.get(
                    id=serializer.validated_data['service_catalog_id']
                )
                amount = service_catalog_item.price
                currency = service_catalog_item.currency
            else:
                if not amount:
                    return Response(
                        {'error': 'Amount is required when no service catalog item is provided'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                currency = serializer.validated_data.get('currency', 'XOF')

            payment_method = serializer.validated_data['payment_method']

            if payment_method == 'onsite_cash':
                result = ServiceTransactionService.process_onsite_payment(
                    patient=request.user,
                    service_provider=service_provider,
                    service_catalog_item=service_catalog_item,
                    service_type=serializer.validated_data['service_type'],
                    service_id=serializer.validated_data['service_id'],
                    service_description=serializer.validated_data['service_description'],
                    amount=amount,
                    currency=currency
                )

                return Response(result, status=status.HTTP_201_CREATED)

            else:
                callback_url = request.build_absolute_uri('/api/v1/payments/webhooks/fedapay/')

                result = ServiceTransactionService.initiate_gateway_payment(
                    patient=request.user,
                    service_provider=service_provider,
                    service_catalog_item=service_catalog_item,
                    service_type=serializer.validated_data['service_type'],
                    service_id=serializer.validated_data['service_id'],
                    service_description=serializer.validated_data['service_description'],
                    amount=amount,
                    currency=currency,
                    payment_method=payment_method,
                    patient_phone_id=serializer.validated_data.get('phone_id'),
                    callback_url=callback_url
                )

                return Response(result, status=status.HTTP_201_CREATED)

        except Participant.DoesNotExist:
            return Response(
                {'error': 'Service provider not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ServiceCatalog.DoesNotExist:
            return Response(
                {'error': 'Service not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ServiceTransactionViewSet(viewsets.ReadOnlyModelViewSet):  # Service class for TransactionViewSet operations
    serializer_class = ServiceTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return ServiceTransaction.objects.none()
        return ServiceTransactionService.get_participant_transactions(
            participant=self.request.user,
            status=self.request.query_params.get('status')
        )

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):  # Status
        service_txn = self.get_object()

        if service_txn.gateway_transaction:
            status_data = FedaPayGatewayService.get_transaction_status(
                gateway_transaction_id=str(service_txn.gateway_transaction.id)
            )
            return Response(status_data)
        else:
            return Response({
                'status': service_txn.status,
                'message': 'No gateway transaction associated'
            })

    @action(detail=True, methods=['get'])
    def receipt(self, request, pk=None):  # Receipt
        service_txn = self.get_object()

        if service_txn.status != 'completed':
            return Response(
                {'error': 'Receipt only available for completed transactions'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            receipt_number = f"RCP-{timezone.now().strftime('%Y%m%d')}-{service_txn.id}"

            pdf_buffer = ReceiptPDFService.generate_service_transaction_receipt(
                service_txn,
                receipt_number
            )

            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="receipt_{receipt_number}.pdf"'
            return response

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def stats(self, request):  # Stats
        queryset = self.get_queryset()

        total_transactions = queryset.count()
        completed_transactions = queryset.filter(status='completed').count()
        pending_transactions = queryset.filter(status='pending').count()
        total_amount = sum(txn.amount for txn in queryset.filter(status='completed'))

        return Response({
            'total_transactions': total_transactions,
            'completed_transactions': completed_transactions,
            'pending_transactions': pending_transactions,
            'total_amount': total_amount,
        })


@extend_schema_view(
    post=extend_schema(
        request=FeeCalculationSerializer,
        responses={200: FeeCalculationSerializer}
    )
)
class FeeCalculationView(APIView):  # View for FeeCalculation operations
    permission_classes = [IsAuthenticated]
    serializer_class = FeeCalculationSerializer

    def post(self, request):  # Post
        serializer = FeeCalculationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        amount = serializer.validated_data['amount']
        currency = serializer.validated_data.get('currency', 'XOF')

        fee_calculation = FeeCalculationService.calculate_service_payment_fees(amount)

        return Response(fee_calculation)


class PayoutScheduleViewSet(viewsets.ReadOnlyModelViewSet):  # View for PayoutScheduleSet operations
    serializer_class = PayoutScheduleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return PayoutSchedule.objects.none()
        if self.request.user.role in ['doctor', 'hospital', 'pharmacy', 'insurance_company']:
            return PayoutSchedule.objects.filter(participant=self.request.user)
        return PayoutSchedule.objects.none()

    @action(detail=False, methods=['get'])
    def earnings(self, request):  # Earnings
        queryset = self.get_queryset()

        total_earnings = sum(ps.total_net_amount for ps in queryset.filter(payout_status='completed'))
        pending_earnings = sum(ps.total_net_amount for ps in queryset.filter(payout_status='scheduled'))

        return Response({
            'total_earnings': total_earnings,
            'pending_earnings': pending_earnings,
            'payout_count': queryset.filter(payout_status='completed').count(),
        })


class PaymentReceiptViewSet(viewsets.ReadOnlyModelViewSet):
    """View for payment receipts"""
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentReceiptSerializer
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return PaymentReceipt.objects.none()
        return PaymentReceipt.objects.filter(issued_to=self.request.user).order_by('-issued_at')
    
    def retrieve(self, request, pk=None):
        """Display receipt in HTML"""
        receipt = get_object_or_404(PaymentReceipt, id=pk, issued_to=request.user)
        
        context = {
            'receipt': receipt,
            'company_ifu': getattr(settings, 'COMPANY_IFU', 'N/A'),
            'company_phone': getattr(settings, 'COMPANY_PHONE', '+229 XX XX XX XX'),
            'company_address': getattr(settings, 'COMPANY_ADDRESS', 'Cotonou, BENIN'),
        }
        
        return render(request, 'payments/receipt_detail.html', context)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download receipt as PDF"""
        receipt = get_object_or_404(PaymentReceipt, id=pk, issued_to=request.user)
        
        try:
            pdf_buffer = EnhancedReceiptService.generate_invoice_receipt(
                receipt,
                receipt.service_transaction
            )
            
            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            filename = f"facture_{receipt.invoice_number or receipt.receipt_number}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
