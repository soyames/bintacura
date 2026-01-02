from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
import uuid
import secrets
import string
from .models import (
    PharmacyCounter, OrderQueue, DeliveryTracking, PickupVerification,
    PharmacyOrder, PharmacyStaff, PharmacySale, PharmacySaleItem
)
from .serializers import (
    PharmacyCounterSerializer, OrderQueueSerializer,
    DeliveryTrackingSerializer, PickupVerificationSerializer,
    PharmacyOrderSerializer
)
from core.models import Participant
from currency_converter.services import CurrencyConverterService


def get_pharmacy_id_for_user(user):
    """
    Get the pharmacy ID for a user.
    - If user is pharmacy staff: returns affiliated_provider_id
    - If user is pharmacy owner: returns user.uid
    - Otherwise: returns None
    """
    if user.role == 'pharmacy':
        if user.staff_role and user.affiliated_provider_id:
            return user.affiliated_provider_id
        return user.uid
    return None


class PharmacyCounterViewSet(viewsets.ModelViewSet):
    serializer_class = PharmacyCounterSerializer
    permission_classes = [IsAuthenticated]
    queryset = PharmacyCounter.objects.none()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return PharmacyCounter.objects.none()
        pharmacy_id = get_pharmacy_id_for_user(self.request.user)
        if pharmacy_id:
            return PharmacyCounter.objects.filter(
                pharmacy_id=pharmacy_id
            ).select_related('current_staff', 'cash_register')
        return PharmacyCounter.objects.none()

    def perform_create(self, serializer):
        serializer.save(pharmacy=self.request.user)

    @action(detail=True, methods=['post'])
    def start_session(self, request, pk=None):
        """Staff member starts session at a counter"""
        counter = self.get_object()
        
        if counter.current_staff:
            return Response({
                'success': False,
                'message': f'Counter already occupied by {counter.current_staff.full_name}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        counter.current_staff = request.user
        counter.current_session_started = timezone.now()
        counter.save()
        
        return Response({
            'success': True,
            'message': f'Session started at {counter.counter_name}',
            'counter': self.get_serializer(counter).data
        })

    @action(detail=True, methods=['post'])
    def end_session(self, request, pk=None):
        """Staff member ends session at counter"""
        counter = self.get_object()
        
        if counter.current_staff != request.user:
            return Response({
                'success': False,
                'message': 'You are not currently using this counter'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        counter.current_staff = None
        counter.current_session_started = None
        counter.save()
        
        return Response({
            'success': True,
            'message': 'Session ended successfully'
        })


class OrderQueueViewSet(viewsets.ModelViewSet):
    serializer_class = OrderQueueSerializer
    permission_classes = [IsAuthenticated]
    queryset = OrderQueue.objects.none()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return OrderQueue.objects.none()
        pharmacy_id = get_pharmacy_id_for_user(self.request.user)
        if pharmacy_id:
            return OrderQueue.objects.filter(
                pharmacy_id=pharmacy_id
            ).select_related('order', 'claimed_by', 'counter').prefetch_related('order__items')
        return OrderQueue.objects.none()

    @action(detail=False, methods=['get'])
    def pending_orders(self, request):
        """Get all pending orders visible to all staff"""
        pending = self.get_queryset().filter(status='pending')
        serializer = self.get_serializer(pending, many=True)
        return Response({
            'success': True,
            'pending_orders': serializer.data,
            'count': pending.count()
        })

    @action(detail=True, methods=['post'])
    def claim_order(self, request, pk=None):
        """Staff member claims an order to process"""
        queue_item = self.get_object()
        
        if queue_item.status != 'pending':
            return Response({
                'success': False,
                'message': 'Order is no longer available'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        counter_id = request.data.get('counter_id')
        if not counter_id:
            return Response({
                'success': False,
                'message': 'Counter ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        counter = get_object_or_404(PharmacyCounter, id=counter_id, pharmacy=request.user)
        
        queue_item.status = 'claimed'
        queue_item.claimed_by = request.user
        queue_item.claimed_at = timezone.now()
        queue_item.counter = counter
        queue_item.save()
        
        return Response({
            'success': True,
            'message': 'Order claimed successfully',
            'queue_item': self.get_serializer(queue_item).data
        })

    @action(detail=True, methods=['post'])
    def start_preparing(self, request, pk=None):
        """Mark order as being prepared"""
        queue_item = self.get_object()
        
        if queue_item.claimed_by != request.user:
            return Response({
                'success': False,
                'message': 'You have not claimed this order'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        queue_item.status = 'preparing'
        queue_item.save()
        
        return Response({
            'success': True,
            'message': 'Order preparation started',
            'queue_item': self.get_serializer(queue_item).data
        })

    @action(detail=True, methods=['post'])
    def mark_ready(self, request, pk=None):
        """Mark order as ready for pickup/delivery"""
        queue_item = self.get_object()
        
        if queue_item.claimed_by != request.user:
            return Response({
                'success': False,
                'message': 'You have not claimed this order'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        queue_item.status = 'ready'
        queue_item.actual_ready_time = timezone.now()
        queue_item.order.status = 'ready'
        queue_item.order.ready_date = timezone.now()
        queue_item.order.save()
        queue_item.save()
        
        return Response({
            'success': True,
            'message': 'Order is ready',
            'queue_item': self.get_serializer(queue_item).data
        })

    @action(detail=True, methods=['post'])
    def scan_qr_code(self, request, pk=None):
        """Scan QR code for pickup verification"""
        qr_code = request.data.get('qr_code')
        
        if not qr_code:
            return Response({
                'success': False,
                'message': 'QR code is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            queue_item = OrderQueue.objects.get(qr_code=qr_code, pharmacy=request.user)
            
            if queue_item.status != 'ready':
                return Response({
                    'success': False,
                    'message': f'Order is not ready for pickup. Current status: {queue_item.get_status_display()}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = self.get_serializer(queue_item)
            return Response({
                'success': True,
                'message': 'QR code verified successfully',
                'order': serializer.data
            })
            
        except OrderQueue.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Invalid QR code or order not found'
            }, status=status.HTTP_404_NOT_FOUND)


class DeliveryTrackingViewSet(viewsets.ModelViewSet):
    serializer_class = DeliveryTrackingSerializer
    permission_classes = [IsAuthenticated]
    queryset = DeliveryTracking.objects.none()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return DeliveryTracking.objects.none()
        user = self.request.user
        pharmacy_id = get_pharmacy_id_for_user(user)
        
        if pharmacy_id:
            return DeliveryTracking.objects.filter(
                pharmacy_id=pharmacy_id
            ).select_related('order', 'delivery_person')
        elif user.role == 'patient':
            return DeliveryTracking.objects.filter(order__patient=user).select_related('pharmacy', 'delivery_person')
        return DeliveryTracking.objects.none()

    def generate_tracking_number(self):
        """Generate unique tracking number"""
        return f"TRK-{timezone.now().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"

    def generate_confirmation_code(self):
        """Generate 6-digit confirmation code"""
        return ''.join(secrets.choice(string.digits) for _ in range(6))

    def perform_create(self, serializer):
        tracking_number = self.generate_tracking_number()
        confirmation_code = self.generate_confirmation_code()
        serializer.save(
            pharmacy=self.request.user,
            tracking_number=tracking_number,
            patient_confirmation_code=confirmation_code
        )

    @action(detail=True, methods=['post'])
    def assign_delivery_person(self, request, pk=None):
        """Assign delivery person to order"""
        delivery = self.get_object()
        delivery_person_id = request.data.get('delivery_person_id')
        
        if not delivery_person_id:
            return Response({
                'success': False,
                'message': 'Delivery person ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        delivery_person = get_object_or_404(Participant, id=delivery_person_id)
        
        delivery.delivery_person = delivery_person
        delivery.status = 'assigned'
        delivery.assigned_at = timezone.now()
        delivery.save()
        
        return Response({
            'success': True,
            'message': f'Delivery assigned to {delivery_person.full_name}',
            'delivery': self.get_serializer(delivery).data
        })

    @action(detail=True, methods=['post'])
    def update_location(self, request, pk=None):
        """Update delivery person's current location"""
        delivery = self.get_object()
        
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        
        if not latitude or not longitude:
            return Response({
                'success': False,
                'message': 'Latitude and longitude are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        delivery.current_latitude = latitude
        delivery.current_longitude = longitude
        delivery.last_location_update = timezone.now()
        delivery.save()
        
        return Response({
            'success': True,
            'message': 'Location updated successfully'
        })

    @action(detail=True, methods=['post'])
    def confirm_delivery(self, request, pk=None):
        """Patient confirms delivery with confirmation code"""
        delivery = self.get_object()
        confirmation_code = request.data.get('confirmation_code')
        
        if not confirmation_code:
            return Response({
                'success': False,
                'message': 'Confirmation code is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if confirmation_code != delivery.patient_confirmation_code:
            return Response({
                'success': False,
                'message': 'Invalid confirmation code'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        delivery.status = 'delivered'
        delivery.confirmed_by_patient = True
        delivery.confirmation_time = timezone.now()
        delivery.delivered_at = timezone.now()
        
        delivery.order.status = 'delivered'
        delivery.order.delivered_date = timezone.now()
        delivery.order.save()
        
        delivery.save()
        
        return Response({
            'success': True,
            'message': 'Delivery confirmed successfully',
            'delivery': self.get_serializer(delivery).data
        })


class PickupVerificationViewSet(viewsets.ModelViewSet):
    serializer_class = PickupVerificationSerializer
    permission_classes = [IsAuthenticated]
    queryset = PickupVerification.objects.none()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return PickupVerification.objects.none()
        pharmacy_id = get_pharmacy_id_for_user(self.request.user)
        if pharmacy_id:
            return PickupVerification.objects.filter(
                pharmacy_id=pharmacy_id
            ).select_related('order', 'scanned_by', 'counter')
        return PickupVerification.objects.none()

    def generate_qr_code(self):
        """Generate unique QR code"""
        return f"PCK-{uuid.uuid4().hex[:12].upper()}"

    def generate_verification_code(self):
        """Generate 6-digit verification code"""
        return ''.join(secrets.choice(string.digits) for _ in range(6))

    def perform_create(self, serializer):
        qr_code = self.generate_qr_code()
        verification_code = self.generate_verification_code()
        serializer.save(
            pharmacy=self.request.user,
            qr_code=qr_code,
            verification_code=verification_code
        )

    @action(detail=False, methods=['post'])
    def verify_pickup(self, request):
        """Verify pickup using QR code or verification code"""
        qr_code = request.data.get('qr_code')
        verification_code = request.data.get('verification_code')
        counter_id = request.data.get('counter_id')
        
        if not (qr_code or verification_code):
            return Response({
                'success': False,
                'message': 'QR code or verification code is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            if qr_code:
                pickup = PickupVerification.objects.get(qr_code=qr_code, pharmacy=request.user)
            else:
                pickup = PickupVerification.objects.get(verification_code=verification_code, pharmacy=request.user)
            
            if pickup.scanned_by:
                return Response({
                    'success': False,
                    'message': 'This order has already been picked up'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            counter = None
            if counter_id:
                counter = get_object_or_404(PharmacyCounter, id=counter_id, pharmacy=request.user)
            
            pickup.scanned_by = request.user
            pickup.scanned_at = timezone.now()
            pickup.counter = counter
            pickup.save()
            
            return Response({
                'success': True,
                'message': 'Pickup verified successfully',
                'pickup': self.get_serializer(pickup).data
            })
            
        except PickupVerification.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Invalid QR code or verification code'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def complete_payment(self, request, pk=None):
        """Complete payment for pickup order"""
        pickup = self.get_object()
        
        if pickup.payment_completed:
            return Response({
                'success': False,
                'message': 'Payment already completed'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        payment_method = request.data.get('payment_method')
        transaction_ref = request.data.get('transaction_ref', '')
        
        if not payment_method:
            return Response({
                'success': False,
                'message': 'Payment method is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            pickup.payment_completed = True
            pickup.payment_transaction_ref = transaction_ref
            pickup.save()
            
            order = pickup.order
            order.payment_status = 'paid'
            order.payment_method = payment_method
            order.payment_reference = transaction_ref
            order.status = 'delivered'
            order.delivered_date = timezone.now()
            order.save()
            
            queue_item = OrderQueue.objects.filter(order=order).first()
            if queue_item:
                queue_item.status = 'completed'
                queue_item.completed_at = timezone.now()
                queue_item.save()
        
        return Response({
            'success': True,
            'message': 'Payment completed successfully',
            'pickup': self.get_serializer(pickup).data
        })
