from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import TransportRequest, TransportProvider, RideShareQuote
from .serializers import TransportRequestSerializer, TransportProviderSerializer, RideShareQuoteSerializer
from core.models import Participant


class TransportRequestViewSet(viewsets.ModelViewSet):  # View for TransportRequestSet operations
    serializer_class = TransportRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        # Filter by current user (Participant model is the user model)
        return TransportRequest.objects.filter(patient=self.request.user)

    def perform_create(self, serializer):  # Perform create
        # Set scheduled_pickup_time to now for emergency transport
        serializer.save(
            patient=self.request.user,
            scheduled_pickup_time=timezone.now()
        )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):  # Cancel
        transport_request = self.get_object()
        if transport_request.status not in ['completed', 'cancelled']:
            transport_request.status = 'cancelled'
            transport_request.cancelled_at = timezone.now()
            transport_request.cancellation_reason = request.data.get('reason', '')
            transport_request.save()
            return Response({'status': 'cancelled'})
        return Response(
            {'error': 'Cannot cancel completed or already cancelled request'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):  # Rate
        transport_request = self.get_object()
        if transport_request.status == 'completed':
            transport_request.rating = request.data.get('rating')
            transport_request.feedback = request.data.get('feedback', '')
            transport_request.save()
            return Response({'status': 'rated'})
        return Response(
            {'error': 'Can only rate completed requests'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['get'])
    def quotes(self, request, pk=None):  # Get quotes for transport request
        transport_request = self.get_object()
        quotes = RideShareQuote.objects.filter(
            transport_request=transport_request,
            status__in=['active', 'pending']
        ).select_related('provider')
        serializer = RideShareQuoteSerializer(quotes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def accept_quote(self, request, pk=None):  # Accept a quote and process payment
        transport_request = self.get_object()
        quote_id = request.data.get('quote_id')
        payment_method = request.data.get('payment_method')

        if not quote_id or not payment_method:
            return Response(
                {'error': 'quote_id and payment_method are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            quote = RideShareQuote.objects.get(id=quote_id, transport_request=transport_request)

            # Update quote status
            quote.status = 'accepted'
            quote.save()

            # Convert quote fare to patient's local currency
            from currency_converter.services import CurrencyConverterService
            from decimal import Decimal

            # Get patient's currency
            patient_currency = CurrencyConverterService.get_participant_currency(transport_request.patient)

            # Quote fare is stored in USD
            quote_currency = 'USD'
            quote_amount = Decimal(str(quote.total_fare))

            # Convert to patient's currency
            if quote_currency != patient_currency:
                converted_amount = CurrencyConverterService.convert(
                    quote_amount,
                    quote_currency,
                    patient_currency
                )
            else:
                converted_amount = quote_amount

            # Update transport request with converted amount
            transport_request.status = 'driver_assigned'
            transport_request.driver_name = quote.driver_name
            transport_request.driver_phone = quote.driver_phone
            transport_request.final_cost = converted_amount
            transport_request.currency = patient_currency
            transport_request.save()

            # Create payment transaction
            from core.models import Transaction as CoreTransaction, Wallet
            from payments.models import HealthTransaction

            # Get patient's wallet for balance tracking
            patient_wallet, _ = Wallet.objects.get_or_create(
                participant=transport_request.patient,
                defaults={'balance': Decimal('0')}
            )

            # Get or create platform wallet as receiver (for now, until provider participant is linked)
            # In production, this should be the actual transport provider's participant
            platform_participant = Participant.objects.filter(role='admin').first()
            if not platform_participant:
                # Create a system participant for transport payments
                platform_participant, _ = Participant.objects.get_or_create(
                    email='transport@BINTACURA.system',
                    defaults={
                        'role': 'admin',
                        'full_name': 'BINTACURA Transport System'
                    }
                )

            # Map payment method to Transaction model choices
            payment_method_map = {
                'wallet': 'wallet',
                'cash': 'cash',
                'gateway': 'card'
            }
            mapped_payment = payment_method_map.get(payment_method, 'cash')

            # Create core transaction with converted amount
            core_transaction = CoreTransaction.objects.create(
                wallet=patient_wallet if mapped_payment == 'wallet' else None,
                sender=transport_request.patient,
                recipient=platform_participant,
                amount=converted_amount,
                currency=quote.currency,
                payment_method=mapped_payment,
                transaction_type='payment',
                description=f"Transport payment - {transport_request.transport_type} ({quote.provider.get_name_display()})",
                balance_before=patient_wallet.balance if mapped_payment == 'wallet' else Decimal('0'),
                balance_after=patient_wallet.balance - Decimal(str(quote.total_fare)) if mapped_payment == 'wallet' else Decimal('0'),
                status='pending',
                metadata={
                    'transport_request_id': str(transport_request.id),
                    'quote_id': str(quote.id),
                    'provider': quote.provider.get_name_display(),
                    'vehicle_type': quote.vehicle_type
                }
            )

            # If wallet payment, deduct from balance
            if mapped_payment == 'wallet':
                if patient_wallet.balance >= Decimal(str(quote.total_fare)):
                    patient_wallet.balance -= Decimal(str(quote.total_fare))
                    patient_wallet.save()
                    core_transaction.status = 'completed'
                    core_transaction.completed_at = timezone.now()
                    core_transaction.save()
                else:
                    core_transaction.status = 'failed'
                    core_transaction.save()
                    return Response(
                        {'error': 'Insufficient wallet balance'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Create health transaction
            health_transaction = HealthTransaction.objects.create(
                transaction=core_transaction,
                patient=transport_request.patient,
                provider=platform_participant,
                service_description=f"Transport Service - {transport_request.transport_type} from {transport_request.pickup_address[:50]} to {transport_request.dropoff_address[:50]}"
            )

            # Link payment to transport request
            transport_request.payment_id = core_transaction.id
            transport_request.payment_status = 'paid' if mapped_payment == 'wallet' else 'pending'
            transport_request.save()

            return Response({
                'status': 'accepted',
                'message': 'Quote accepted and payment initiated',
                'transaction_id': str(core_transaction.id),
                'payment_status': transport_request.payment_status
            })

        except RideShareQuote.DoesNotExist:
            return Response(
                {'error': 'Quote not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TransportProviderViewSet(viewsets.ModelViewSet):  # View for TransportProviderSet operations
    queryset = TransportProvider.objects.filter(status='active')
    serializer_class = TransportProviderSerializer
    permission_classes = [IsAuthenticated]


class TransportRequestView(LoginRequiredMixin, TemplateView):  # View for TransportRequest operations
    template_name = "patient/transport_request.html"

    def get_context_data(self, **kwargs):  # Get context data
        context = super().get_context_data(**kwargs)

        transport_providers = Participant.objects.filter(
            role="hospital", is_active=True
        ).select_related("provider_data")

        context["transport_providers"] = transport_providers

        return context


class TransportTrackingView(LoginRequiredMixin, TemplateView):  # View for tracking transport requests
    template_name = "patient/transport_tracking.html"

    def get_context_data(self, **kwargs):  # Get context data
        context = super().get_context_data(**kwargs)
        context["request_id"] = self.kwargs.get('request_id')
        return context


