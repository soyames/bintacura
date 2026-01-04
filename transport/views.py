from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.utils import timezone
from django.db.models import Q, Count
from datetime import datetime, timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import TransportRequest, TransportProvider, RideShareQuote
from .serializers import TransportRequestSerializer, TransportProviderSerializer, RideShareQuoteSerializer
from core.models import Participant
from communication.models import Notification


# Patient Transport Requests List View
class PatientTransportRequestsView(LoginRequiredMixin, TemplateView):
    template_name = 'patient/transport_requests_list.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Only allow patients to access
        if request.user.role != 'patient':
            from django.contrib import messages
            messages.error(request, "Accès réservé aux patients.")
            from django.shortcuts import redirect
            return redirect('patient:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        from django.conf import settings
        context = super().get_context_data(**kwargs)
        
        # Pass platform fee rate to template
        context['platform_fee_rate'] = settings.PLATFORM_FEE_RATE
        
        # Get all transport requests for this patient
        requests = TransportRequest.objects.filter(
            patient=self.request.user
        ).order_by('-created_at')
        
        # Calculate stats
        stats = {
            'pending': requests.filter(status='pending').count(),
            'accepted': requests.filter(status='accepted').count(),
            'in_transit': requests.filter(status__in=['driver_assigned', 'en_route', 'arrived', 'in_transit']).count(),
            'completed': requests.filter(status='completed').count(),
        }
        
        context['requests'] = requests
        context['stats'] = stats
        
        return context


# Hospital Transport Dashboard View
class HospitalTransportDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'transport/hospital_dashboard.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Only allow hospital staff to access
        if request.user.role not in ['hospital_admin', 'hospital_staff', 'admin', 'super_admin']:
            from django.contrib import messages
            messages.error(request, "Vous n'avez pas accès à ce tableau de bord.")
            from django.shortcuts import redirect
            return redirect('patient:dashboard')
        return super().dispatch(request, *args, **kwargs)


class TransportRequestViewSet(viewsets.ModelViewSet):  # View for TransportRequestSet operations
    serializer_class = TransportRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return TransportRequest.objects.none()
        # Filter by current user (Participant model is the user model)
        return TransportRequest.objects.filter(patient=self.request.user)

    def perform_create(self, serializer):  # Perform create
        from communication.models import Notification
        from core.models import Participant
        
        # Set scheduled_pickup_time to now for emergency transport
        transport_request = serializer.save(
            patient=self.request.user,
            scheduled_pickup_time=timezone.now()
        )
        
        # Notify all active hospitals about the new transport request
        hospitals = Participant.objects.filter(
            role='hospital',
            is_active=True
        )
        
        for hospital in hospitals:
            Notification.objects.create(
                recipient=hospital,
                notification_type='system',
                title='Nouvelle Demande de Transport',
                message=f'Nouvelle demande de transport ambulancier de {self.request.user.first_name} {self.request.user.last_name}. Urgence: {transport_request.get_urgency_display()}',
                action_url=f'/hospital/transport/dashboard/',
                metadata={
                    'transport_request_id': str(transport_request.id),
                    'urgency': transport_request.urgency,
                    'transport_type': transport_request.transport_type
                }
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
    def pay(self, request, pk=None):  # Pay for transport
        from core.models import Wallet, Transaction
        from payments.models import Invoice, InvoiceItem
        from decimal import Decimal
        from django.conf import settings
        
        transport_request = self.get_object()
        payment_method = request.data.get('payment_method', 'wallet')
        
        # Check if transport is accepted
        if transport_request.status != 'accepted':
            return Response(
                {'success': False, 'message': 'Le transport doit être accepté avant le paiement'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already paid
        if transport_request.payment_status == 'paid':
            return Response(
                {'success': False, 'message': 'Ce transport a déjà été payé'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get amount
        amount = transport_request.final_cost
        if amount <= 0:
            return Response(
                {'success': False, 'message': 'Montant invalide'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate platform fee using settings (1%)
        platform_fee_rate = Decimal(str(settings.PLATFORM_FEE_RATE))
        platform_fee = amount * platform_fee_rate
        total_amount = amount + platform_fee
        
        # Get hospital
        if not transport_request.assigned_hospital:
            return Response(
                {'success': False, 'message': 'Aucun hôpital assigné'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create invoice
        invoice = Invoice.objects.create(
            participant=self.request.user,
            invoice_type='transport',
            total_amount=int(total_amount),
            currency='XOF',
            status='pending' if payment_method == 'cash' else 'paid',
            payment_method=payment_method,
            metadata={
                'transport_request_id': str(transport_request.id),
                'request_number': transport_request.request_number,
                'transport_type': transport_request.transport_type,
                'base_amount': float(amount),
                'platform_fee': float(platform_fee)
            }
        )
        
        # Add invoice item
        InvoiceItem.objects.create(
            invoice=invoice,
            description=f'Transport {transport_request.get_transport_type_display()} - {transport_request.request_number}',
            quantity=1,
            unit_price=int(amount),
            total_price=int(amount)
        )
        
        # Handle different payment methods
        if payment_method == 'cash':
            # Cash payment - mark as pending, driver confirms later
            transport_request.payment_status = 'pending'
            transport_request.save()
            
            # Notify hospital
            Notification.objects.create(
                recipient=transport_request.assigned_hospital,
                notification_type='payment',
                title='Paiement en Espèces - Transport',
                message=f'Le patient paiera {total_amount} XOF en espèces au chauffeur pour #{transport_request.request_number}',
                action_url='/hospital/transport/dashboard/',
                metadata={'transport_request_id': str(transport_request.id), 'invoice_id': str(invoice.id)}
            )
            
            return Response({
                'success': True,
                'message': 'Paiement en espèces confirmé. Facture créée.',
                'invoice_id': str(invoice.id),
                'amount': float(total_amount),
                'platform_fee': float(platform_fee),
                'platform_fee_rate': float(platform_fee_rate),
                'payment_method': 'cash'
            })
            
        elif payment_method == 'online':
            # Online payment via FedaPay
            try:
                from payments.fedapay_service import FedaPayService
                fedapay_service = FedaPayService()
                
                # Create FedaPay transaction
                fedapay_transaction = fedapay_service.create_transaction(
                    amount=int(total_amount),
                    description=f'Transport {transport_request.request_number}',
                    customer_email=self.request.user.email,
                    customer_firstname=self.request.user.first_name,
                    customer_lastname=self.request.user.last_name,
                    callback_url=f'/api/v1/transport/payment-callback/{transport_request.id}/',
                    metadata={
                        'transport_request_id': str(transport_request.id),
                        'invoice_id': str(invoice.id),
                        'patient_id': str(self.request.user.uid),
                        'hospital_id': str(transport_request.assigned_hospital.uid)
                    }
                )
                
                # Update invoice with FedaPay transaction ID
                invoice.fedapay_transaction_id = fedapay_transaction['id']
                invoice.save()
                
                return Response({
                    'success': True,
                    'message': 'Redirection vers FedaPay...',
                    'payment_url': fedapay_transaction['url'],
                    'invoice_id': str(invoice.id),
                    'platform_fee': float(platform_fee),
                    'platform_fee_rate': float(platform_fee_rate),
                    'payment_method': 'online'
                })
                
            except Exception as e:
                invoice.status = 'failed'
                invoice.save()
                return Response(
                    {'success': False, 'message': f'Erreur FedaPay: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        else:
            return Response(
                {'success': False, 'message': 'Méthode de paiement non supportée'},
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


# Hospital Transport Management Views
class HospitalTransportDashboardView(LoginRequiredMixin, TemplateView):
    """View for hospital to manage transport requests"""
    template_name = "hospital/transport_requests.html"
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.role != 'hospital':
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Accès réservé aux hôpitaux")
        return super().dispatch(request, *args, **kwargs)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hospital_transport_requests(request):
    """API endpoint for hospitals to view transport requests in their region"""
    if request.user.role != 'hospital':
        return Response({'error': 'Accès refusé'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get hospital's location/region
    hospital_region = getattr(request.user, 'region_code', 'global')
    
    # Get all pending and active transport requests in the region
    requests = TransportRequest.objects.filter(
        Q(status__in=['pending', 'driver_assigned', 'en_route', 'arrived', 'in_transit']) &
        Q(region_code=hospital_region)
    ).select_related('patient').order_by('-created_at')
    
    # Serialize the data
    data = []
    for req in requests:
        data.append({
            'id': str(req.id),
            'request_number': req.request_number,
            'patient_name': req.patient.get_full_name() if hasattr(req.patient, 'get_full_name') else str(req.patient),
            'contact_phone': req.contact_phone,
            'transport_type': req.transport_type,
            'urgency': req.urgency,
            'status': req.status,
            'pickup_address': req.pickup_address,
            'pickup_latitude': req.pickup_latitude,
            'pickup_longitude': req.pickup_longitude,
            'destination_address': req.dropoff_address,
            'destination_latitude': req.dropoff_latitude,
            'destination_longitude': req.dropoff_longitude,
            'special_requirements': req.special_requirements,
            'scheduled_pickup_time': req.scheduled_pickup_time.isoformat() if req.scheduled_pickup_time else None,
            'created_at': req.created_at.isoformat(),
            'completed_at': req.completed_at.isoformat() if req.completed_at else None
        })
    
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_transport_request(request, request_id):
    """Hospital accepts a transport request"""
    if request.user.role != 'hospital':
        return Response({'error': 'Accès refusé'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        transport_request = TransportRequest.objects.get(id=request_id, status='pending')
        
        # Update status
        transport_request.status = 'driver_assigned'
        transport_request.assigned_hospital = request.user
        transport_request.save()
        
        # Send notification to patient
        Notification.objects.create(
            user=transport_request.patient,
            type='transport_update',
            title='Transport Accepté',
            message=f'Votre demande de transport d\'urgence a été acceptée. L\'ambulance arrivera dans environ {request.data.get("estimated_arrival", 15)} minutes.',
            priority='high'
        )
        
        return Response({
            'status': 'accepted',
            'message': 'Demande de transport acceptée'
        })
    except TransportRequest.DoesNotExist:
        return Response({'error': 'Demande non trouvée'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_transport_status(request, request_id):
    """Update transport request status"""
    if request.user.role != 'hospital':
        return Response({'error': 'Accès refusé'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        transport_request = TransportRequest.objects.get(id=request_id)
        new_status = request.data.get('status')
        
        if new_status not in dict(TransportRequest.STATUS_CHOICES).keys():
            return Response({'error': 'Statut invalide'}, status=status.HTTP_400_BAD_REQUEST)
        
        transport_request.status = new_status
        
        if new_status == 'completed':
            transport_request.completed_at = timezone.now()
        
        transport_request.save()
        
        # Send notification to patient
        status_messages = {
            'en_route': 'L\'ambulance est en route vers vous',
            'arrived': 'L\'ambulance est arrivée à votre emplacement',
            'in_transit': 'Vous êtes en route vers l\'hôpital',
            'completed': 'Transport terminé. Merci d\'avoir utilisé nos services'
        }
        
        if new_status in status_messages:
            Notification.objects.create(
                user=transport_request.patient,
                type='transport_update',
                title='Mise à jour du Transport',
                message=status_messages[new_status],
                priority='normal'
            )
        
        return Response({
            'status': 'updated',
            'new_status': new_status
        })
    except TransportRequest.DoesNotExist:
        return Response({'error': 'Demande non trouvée'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def decline_transport_request(request, request_id):
    """Hospital declines a transport request"""
    if request.user.role != 'hospital':
        return Response({'error': 'Accès refusé'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        transport_request = TransportRequest.objects.get(id=request_id, status='pending')
        
        reason = request.data.get('reason', 'Non disponible')
        
        # Note: We don't cancel the request, just decline it so other hospitals can accept
        # Add a declined_by field to track which hospitals declined
        
        # Send notification to patient
        Notification.objects.create(
            user=transport_request.patient,
            type='transport_update',
            title='Recherche en cours',
            message='Nous recherchons un transport disponible pour vous. Veuillez patienter.',
            priority='high'
        )
        
        return Response({
            'status': 'declined',
            'message': 'Demande déclinée'
        })
    except TransportRequest.DoesNotExist:
        return Response({'error': 'Demande non trouvée'}, status=status.HTTP_404_NOT_FOUND)




# Hospital-specific ViewSet for Transport Management
class HospitalTransportViewSet(viewsets.ReadOnlyModelViewSet):
    """Hospital ViewSet for managing transport requests"""
    serializer_class = TransportRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get transport requests for hospital's region"""
        if getattr(self, 'swagger_fake_view', False):
            return TransportRequest.objects.none()
        
        user = self.request.user
        
        # Only allow hospital staff
        if user.role not in ['hospital_admin', 'hospital_staff', 'admin', 'super_admin']:
            return TransportRequest.objects.none()
        
        # Get requests in hospital's region
        # For now, show all pending and assigned requests
        # In production, filter by hospital's region_code
        queryset = TransportRequest.objects.filter(
            status__in=['pending', 'driver_assigned', 'en_route', 'arrived', 'in_transit']
        ).select_related('patient').order_by('-created_at')
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        
        # Filter by urgency if provided
        urgency_filter = self.request.query_params.get('urgency')
        if urgency_filter and urgency_filter != 'all':
            queryset = queryset.filter(urgency=urgency_filter)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Hospital accepts a transport request"""
        transport_request = self.get_object()
        
        if transport_request.status != 'pending':
            return Response(
                {'success': False, 'error': 'Cette demande n\'est plus disponible'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Assign hospital to request
        transport_request.assigned_hospital = request.user
        transport_request.status = 'accepted'
        transport_request.save()
        
        # Send notification to patient
        Notification.objects.create(
            user=transport_request.patient,
            type='transport_update',
            title='Transport Accepté',
            message=f'Votre demande de transport a été acceptée par {request.user.name}. Un chauffeur vous sera assigné sous peu.',
            priority='high',
            metadata={'transport_request_id': str(transport_request.id)}
        )
        
        return Response({
            'success': True,
            'status': 'accepted',
            'message': 'Demande acceptée avec succès'
        })
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Hospital rejects a transport request"""
        transport_request = self.get_object()
        
        if transport_request.status != 'pending':
            return Response(
                {'success': False, 'error': 'Cette demande n\'est plus disponible'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Mark as cancelled
        transport_request.status = 'cancelled'
        transport_request.cancellation_reason = 'Refusé par l\'hôpital'
        transport_request.cancelled_at = timezone.now()
        transport_request.save()
        
        # Send notification to patient
        Notification.objects.create(
            user=transport_request.patient,
            type='transport_update',
            title='Transport Refusé',
            message=f'Votre demande de transport a été refusée. Veuillez essayer un autre établissement ou service.',
            priority='high',
            metadata={'transport_request_id': str(transport_request.id)}
        )
        
        return Response({
            'success': True,
            'status': 'rejected',
            'message': 'Demande refusée'
        })
    
    @action(detail=True, methods=['post'])
    def assign_driver(self, request, pk=None):
        """Assign a driver to the transport request"""
        transport_request = self.get_object()
        
        driver_name = request.data.get('driver_name')
        driver_phone = request.data.get('driver_phone')
        vehicle_number = request.data.get('vehicle_number')
        
        if not all([driver_name, driver_phone, vehicle_number]):
            return Response(
                {'error': 'Tous les champs sont requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        transport_request.driver_name = driver_name
        transport_request.driver_phone = driver_phone
        transport_request.vehicle_number = vehicle_number
        transport_request.status = 'driver_assigned'
        transport_request.save()
        
        # Send notification to patient
        Notification.objects.create(
            user=transport_request.patient,
            type='transport_update',
            title='Chauffeur Assigné',
            message=f'Le chauffeur {driver_name} a été assigné à votre transport. Véhicule: {vehicle_number}. Contact: {driver_phone}',
            priority='high',
            metadata={
                'transport_request_id': str(transport_request.id),
                'driver_name': driver_name,
                'driver_phone': driver_phone,
                'vehicle_number': vehicle_number
            }
        )
        
        return Response({
            'status': 'assigned',
            'message': 'Chauffeur assigné avec succès'
        })
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update transport request status"""
        transport_request = self.get_object()
        
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')
        
        if new_status not in dict(TransportRequest.STATUS_CHOICES).keys():
            return Response(
                {'error': 'Statut invalide'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_status = transport_request.status
        transport_request.status = new_status
        
        # Update timestamps based on status
        if new_status == 'arrived':
            transport_request.actual_pickup_time = timezone.now()
        elif new_status == 'completed':
            transport_request.actual_dropoff_time = timezone.now()
        
        transport_request.save()
        
        # Send appropriate notification to patient
        status_messages = {
            'en_route': 'L\'ambulance est en route vers vous',
            'arrived': 'L\'ambulance est arrivée à votre emplacement',
            'in_transit': 'Vous êtes en route vers l\'hôpital',
            'completed': 'Transport terminé avec succès'
        }
        
        if new_status in status_messages:
            Notification.objects.create(
                user=transport_request.patient,
                type='transport_update',
                title='Mise à Jour du Transport',
                message=status_messages[new_status],
                priority='high',
                metadata={
                    'transport_request_id': str(transport_request.id),
                    'old_status': old_status,
                    'new_status': new_status,
                    'notes': notes
                }
            )
        
        return Response({
            'success': True,
            'status': 'updated',
            'message': 'Statut mis à jour avec succès'
        })
