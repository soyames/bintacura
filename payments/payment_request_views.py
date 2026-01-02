from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.contrib import messages
from django.db import transaction as db_transaction
from django.conf import settings
from decimal import Decimal

from .models import PaymentReceipt, PaymentRequest
from appointments.models import Appointment
from core.models import Participant
from communication.services import NotificationService


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_cash_payment_request(request):
    """Create a cash payment request from patient to service provider"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Payment request data: {request.data}")
    
    # Extract IDs - check all possible fields
    invoice_id = request.data.get('invoice_id')
    receipt_id = request.data.get('receipt_id')
    appointment_id = request.data.get('appointment_id')
    invoice_type = request.data.get('invoice_type', 'receipt')
    
    # Use invoice_id as receipt_id if provided and not empty
    if invoice_id and str(invoice_id).strip():
        receipt_id = invoice_id
        logger.info(f"Using invoice_id {invoice_id} as receipt_id")
    
    # Validate that we have at least one valid ID
    if not receipt_id or str(receipt_id).strip() == '':
        if not appointment_id or str(appointment_id).strip() == '':
            logger.error(f"No valid ID found! Received: invoice_id={invoice_id}, receipt_id={receipt_id}, appointment_id={appointment_id}")
            logger.error(f"Request keys: {list(request.data.keys())}")
            logger.error(f"Full request data: {request.data}")
            return Response(
                {'error': 'invoice_id, receipt_id ou appointment_id est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    participant = request.user
    
    # Get receipt or create temporary one from appointment
    receipt = None
    if receipt_id:
        try:
            receipt = PaymentReceipt.objects.select_related(
                'issued_to', 'issued_by', 'service_transaction'
            ).get(id=receipt_id)
        except PaymentReceipt.DoesNotExist:
            logger.error(f"Receipt not found with id: {receipt_id}")
            return Response(
                {'error': 'Facture introuvable'},
                status=status.HTTP_404_NOT_FOUND
            )
    elif appointment_id:
        appointment = get_object_or_404(Appointment, id=appointment_id, patient=participant)
        
        # Check if payment request already exists
        existing_request = PaymentRequest.objects.filter(
            appointment=appointment,
            from_participant=participant,
            status='pending'
        ).first()
        
        if existing_request:
            return Response(
                {'success': True, 'message': 'Une demande de paiement existe déjà pour ce rendez-vous'},
                status=status.HTTP_200_OK
            )
        
        # Get or create receipt
        receipt = PaymentReceipt.objects.filter(
            appointment=appointment
        ).first()
        
        if not receipt:
            # Create temporary receipt
            receipt = PaymentReceipt.objects.create(
                issued_to=participant,
                issued_by=appointment.doctor if appointment.doctor else appointment.hospital,
                amount=appointment.service_cost or Decimal('0.00'),
                currency=getattr(settings, 'DEFAULT_CURRENCY', 'XOF'),
                payment_method='cash',
                payment_status='PENDING'
            )
            receipt.ensure_invoice_data()
            receipt.save()
    
    if not receipt:
        return Response(
            {'error': 'Impossible de trouver ou créer la facture'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if payment request already exists for this receipt
    existing_request = PaymentRequest.objects.filter(
        receipt=receipt,
        from_participant=participant,
        status='pending'
    ).first()
    
    if existing_request:
        return Response(
            {'success': True, 'message': 'Une demande de paiement existe déjà pour cette facture'},
            status=status.HTTP_200_OK
        )
    
    # Determine recipient (service provider)
    recipient = None
    
    # First try to get from receipt
    if receipt.issued_by:
        recipient = receipt.issued_by
    elif hasattr(receipt, 'service_transaction') and receipt.service_transaction:
        recipient = receipt.service_transaction.service_provider
    
    if not recipient:
        logger.error(f"Cannot determine recipient for receipt {receipt.id}")
        return Response(
            {'error': 'Impossible de déterminer le destinataire du paiement'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create payment request
    amount_decimal = receipt.total_amount or receipt.amount or Decimal('0.00')
    amount_cents = int(amount_decimal * 100)  # Convert to cents
    
    description = f'Demande de paiement en espèces pour {receipt.receipt_number or receipt.invoice_number}'
    if hasattr(receipt, 'service_transaction') and receipt.service_transaction:
        service_type = receipt.service_transaction.service_type or 'service'
        description = f'Paiement {service_type} - {receipt.receipt_number or receipt.invoice_number}'
    
    payment_request = PaymentRequest.objects.create(
        from_participant=participant,
        to_participant=recipient,
        receipt=receipt,
        amount=amount_cents,
        currency=receipt.currency or 'XOF',
        description=description,
        payment_method='cash',
        status='pending',
        metadata={
            'receipt_id': str(receipt.id),
            'invoice_number': receipt.invoice_number or receipt.receipt_number,
            'invoice_type': invoice_type,
        }
    )
    
    # Create notification for the recipient (service provider)
    from communication.models import Notification
    try:
        # Check if recipient has notifications enabled
        if recipient.has_notifications_enabled():
            recipient_role = recipient.role or 'service provider'
            amount_display = f"{amount_cents / 100:.0f} {receipt.currency or 'XOF'}"
            
            Notification.objects.create(
                recipient=recipient,
                notification_type='payment',
                title='Nouvelle Demande de Paiement',
                message=f'{participant.full_name} a envoyé une demande de paiement en espèces de {amount_display}. Facture: {receipt.invoice_number or receipt.receipt_number}',
                action_url=f'/{recipient_role}/payment-requests/',
                metadata={
                    'payment_request_id': str(payment_request.id),
                    'amount': amount_cents,
                    'currency': receipt.currency or 'XOF',
                    'from_participant': str(participant.uid),
                }
            )
            logger.info(f"Notification created for recipient {recipient.uid}")
    except Exception as notif_error:
        logger.error(f"Failed to create notification: {str(notif_error)}")
    
    logger.info(f"Payment request created: {payment_request.id} for receipt {receipt.id}")
    
    return Response({
        'success': True,
        'message': 'Demande de paiement envoyée avec succès',
        'payment_request_id': str(payment_request.id),
        'status': 'pending'
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pending_payment_requests(request):
    """Get all pending payment requests for the current participant"""
    participant = request.user
    
    # Get requests where participant is the recipient
    requests = PaymentRequest.objects.filter(
        to_participant=participant,
        status='pending'
    ).select_related('from_participant', 'receipt', 'appointment').order_by('-created_at')
    
    data = []
    for req in requests:
        data.append({
            'id': str(req.id),
            'from_participant': {
                'uid': str(req.from_participant.uid),
                'name': req.from_participant.get_full_name()
            },
            'amount': str(req.amount),
            'currency': req.currency,
            'payment_method': req.payment_method,
            'receipt_number': req.receipt.receipt_number if req.receipt else None,
            'appointment_id': str(req.appointment.id) if req.appointment else None,
            'notes': req.notes,
            'created_at': req.created_at.isoformat()
        })
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_cash_payment(request, payment_request_id):
    """Mark a cash payment request as completed"""
    participant = request.user
    payment_request = get_object_or_404(PaymentRequest, id=payment_request_id, to_participant=participant)
    
    if payment_request.status != 'pending':
        return Response(
            {'error': 'Cette demande a déjà été traitée'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Mark as approved and completed
    payment_request.status = 'completed'
    payment_request.responded_at = timezone.now()
    payment_request.save()
    
    # Update receipt status
    if payment_request.receipt:
        payment_request.receipt.status = 'paid'
        payment_request.receipt.paid_at = timezone.now()
        payment_request.receipt.save()
    
    # Create notification for the patient
    from communication.models import Notification
    try:
        # Check if patient has notifications enabled
        if payment_request.from_participant.has_notifications_enabled():
            amount_display = f"{payment_request.amount / 100:.0f} {payment_request.currency}"
            
            Notification.objects.create(
                recipient=payment_request.from_participant,
                notification_type='payment',
                title='Paiement Confirmé',
                message=f'Votre paiement de {amount_display} a été confirmé par {participant.full_name}. Facture: {payment_request.receipt.invoice_number or payment_request.receipt.receipt_number}',
                action_url=f'/patient/invoices/',
                metadata={
                    'payment_request_id': str(payment_request.id),
                    'amount': payment_request.amount,
                    'currency': payment_request.currency,
                }
            )
    except Exception as notif_error:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create notification: {str(notif_error)}")
    
    return Response({
        'message': 'Paiement confirmé avec succès',
        'status': 'completed'
    }, status=status.HTTP_200_OK)


# Web Views for Provider Interface

class ProviderPaymentRequestsView(LoginRequiredMixin, View):
    """View for service providers to see and process payment requests"""
    
    def get(self, request):
        participant = request.user
        
        if participant.role not in ['doctor', 'hospital', 'pharmacy', 'insurance_company']:
            messages.error(request, "Accès non autorisé")
            return redirect('patient:dashboard')
        
        pending_requests = PaymentRequest.objects.filter(
            to_participant=participant,
            status='pending'
        ).select_related('from_participant', 'receipt').order_by('-created_at')
        
        completed_requests = PaymentRequest.objects.filter(
            to_participant=participant,
            status__in=['completed', 'cancelled']
        ).select_related('from_participant', 'receipt').order_by('-updated_at')[:20]
        
        context = {
            'pending_requests': pending_requests,
            'completed_requests': completed_requests,
        }
        
        template_map = {
            'doctor': 'doctor/payment_requests.html',
            'hospital': 'hospital/payment_requests.html',
            'pharmacy': 'pharmacy/payment_requests.html',
            'insurance_company': 'insurance/payment_requests.html',
        }
        
        template = template_map.get(participant.role, 'payments/payment_requests.html')
        return render(request, template, context)


class ProcessPaymentRequestView(LoginRequiredMixin, View):
    """Process a cash payment request"""
    
    @db_transaction.atomic
    def post(self, request, request_id):
        participant = request.user
        
        if participant.role not in ['doctor', 'hospital', 'pharmacy', 'insurance_company']:
            messages.error(request, "Accès non autorisé")
            return redirect('patient:dashboard')
        
        payment_request = get_object_or_404(
            PaymentRequest.objects.select_for_update(),
            id=request_id,
            to_participant=participant,
            status='pending'
        )
        
        action = request.POST.get('action')
        
        if action == 'confirm':
            payment_request.status = 'completed'
            payment_request.responded_at = timezone.now()
            payment_request.metadata['notes'] = request.POST.get('notes', '')
            payment_request.save()
            
            if payment_request.receipt:
                payment_request.receipt.payment_status = 'PAID'
                payment_request.receipt.paid_at = timezone.now()
                payment_request.receipt.save()
            
            # Send notification to patient
            try:
                NotificationService.send_notification(
                    recipient=payment_request.from_participant,
                    title="Paiement confirmé",
                    message=f"Votre paiement de {payment_request.amount_display} a été confirmé.",
                    notification_type='payment'
                )
            except:
                pass
            
            messages.success(request, "Paiement confirmé avec succès")
            
        elif action == 'cancel':
            payment_request.status = 'cancelled'
            payment_request.responded_at = timezone.now()
            payment_request.metadata['notes'] = request.POST.get('notes', '')
            payment_request.save()
            
            # Send notification to patient
            try:
                NotificationService.send_notification(
                    recipient=payment_request.from_participant,
                    title="Demande de paiement annulée",
                    message=f"Votre demande de paiement de {payment_request.amount_display} a été annulée.",
                    notification_type='payment'
                )
            except:
                pass
            
            messages.info(request, "Demande annulée")
        
        # Redirect based on portal
        portal = request.path.split('/')[1]
        return redirect(f'/{portal}/payment-requests/')
