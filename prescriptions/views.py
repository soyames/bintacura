from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render
from django.db import transaction
from .models import *
from .serializers import *
from core.models import Participant
from communication.models import Notification
from currency_converter.services import CurrencyConverterService
import logging

logger = logging.getLogger(__name__)


class PrescriptionViewSet(viewsets.ModelViewSet):
    serializer_class = PrescriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Prescription.objects.none()
        
        participant = self.request.user
        print(f"DEBUG PrescriptionViewSet: User={participant.email}, Role={participant.role}, UID={participant.uid}")
        
        # Patients see their own prescriptions
        if participant.role == 'patient':
            queryset = Prescription.objects.filter(patient=participant).prefetch_related('items', 'items__medication')
            count = queryset.count()
            print(f"DEBUG: Found {count} prescriptions for patient")
            if count > 0:
                for p in queryset:
                    print(f"  - Prescription {p.id}: issued {p.issue_date}, status={p.status}")
            return queryset
        # Doctors see prescriptions they've written
        elif participant.role == 'doctor':
            return Prescription.objects.filter(doctor=participant).prefetch_related('items', 'items__medication')
        # Pharmacies see prescriptions for their pharmacy
        elif participant.role == 'pharmacy':
            return Prescription.objects.filter(preferred_pharmacy=participant).prefetch_related('items', 'items__medication')
        
        print(f"DEBUG: No matching role for {participant.role}, returning empty queryset")
        return Prescription.objects.none()

    @action(detail=False, methods=['post'])
    def create_prescription(self, request):
        """Create a prescription with items - Custom endpoint for doctor workflow"""
        try:
            doctor = request.user

            # Validate doctor role
            if doctor.role != 'doctor':
                return Response(
                    {'detail': 'Seuls les médecins peuvent créer des ordonnances'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Get patient
            patient_id = request.data.get('patient_id')
            if not patient_id:
                return Response(
                    {'detail': 'patient_id est requis'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                patient = Participant.objects.get(uid=patient_id, role='patient')
            except Participant.DoesNotExist:
                return Response(
                    {'detail': 'Patient non trouvé'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get medications array
            medications = request.data.get('medications', [])
            if not medications:
                return Response(
                    {'detail': 'Au moins un médicament est requis'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create prescription with all items in a transaction
            with transaction.atomic():
                # Create prescription
                prescription = Prescription.objects.create(
                    patient=patient,
                    doctor=doctor,
                    issue_date=request.data.get('issue_date'),
                    valid_until=request.data.get('valid_until'),
                    status=request.data.get('status', 'active'),
                    type=request.data.get('type', 'regular'),
                    diagnosis=request.data.get('diagnosis', ''),
                    notes=request.data.get('notes', ''),
                    special_instructions=request.data.get('special_instructions', '')
                )

                # Create prescription items
                for med_data in medications:
                    PrescriptionItem.objects.create(
                        prescription=prescription,
                        medication_name=med_data.get('medication_name', ''),
                        dosage=med_data.get('dosage', ''),
                        dosage_form=med_data.get('dosage_form', 'Comprimé'),
                        strength=med_data.get('dosage', ''),
                        quantity=med_data.get('quantity', 0),
                        frequency=med_data.get('frequency', 'once_daily'),
                        duration_days=med_data.get('duration_days', 0),
                        instructions=med_data.get('instructions', '')
                    )

                # Send in-app notification to patient
                Notification.objects.create(
                    recipient=patient,
                    title='Nouvelle Ordonnance',
                    message=f'Dr. {doctor.full_name} vous a prescrit une nouvelle ordonnance. Diagnostic: {prescription.diagnosis[:100]}',
                    notification_type='prescription',
                    action_url=f'/patient/prescriptions/{prescription.id}/'
                )

                # Send SMS notification to patient
                try:
                    from communication.sms_service import SMSService
                    sms_service = SMSService()
                    if patient.phone_number:
                        sms_message = f'BINTACURA: Dr. {doctor.full_name} vous a prescrit une nouvelle ordonnance. Consultez votre application pour les détails.'
                        sms_service.send_sms(patient.phone_number, sms_message)
                except Exception as sms_error:
                    logger.warning(f'Failed to send SMS to patient: {str(sms_error)}')

                # Send email notification to patient using AWS SES
                try:
                    from communication.email_service import EmailService
                    if patient.email:
                        medications_list = [
                            {'name': item.medication_name, 'dosage': item.dosage, 'frequency': item.frequency}
                            for item in prescription.items.all()
                        ]
                        context = {
                            'patient_name': patient.full_name,
                            'doctor_name': doctor.full_name,
                            'diagnosis': prescription.diagnosis,
                            'medications': medications_list,
                            'special_instructions': prescription.special_instructions,
                            'prescription_id': str(prescription.id)[:8]
                        }
                        EmailService.send_email(
                            to_email=patient.email,
                            subject='Nouvelle Ordonnance - BINTACURA',
                            template_name='emails/prescription_created.html',
                            context=context,
                            participant=patient,
                            notification_type='prescription'
                        )
                except Exception as email_error:
                    logger.warning(f'Failed to send email to patient: {str(email_error)}')

                # Send notification to preferred pharmacy if specified
                if prescription.preferred_pharmacy:
                    try:
                        Notification.objects.create(
                            participant=prescription.preferred_pharmacy,
                            title='Nouvelle Ordonnance',
                            message=f'Dr. {doctor.full_name} a prescrit une ordonnance pour {patient.full_name}. ID: {str(prescription.id)[:8]}',
                            notification_type='prescription',
                            priority='high'
                        )
                    except Exception as pharmacy_notif_error:
                        logger.warning(f'Failed to send pharmacy notification: {str(pharmacy_notif_error)}')

                logger.info(f'Prescription created: {prescription.id} by doctor {doctor.uid} for patient {patient.uid}')

                return Response({
                    'success': True,
                    'message': 'Ordonnance créée avec succès',
                    'prescription_id': str(prescription.id)
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f'Error creating prescription: {str(e)}', exc_info=True)
            return Response(
                {'detail': f'Erreur lors de la création: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def medication_prices(self, request, pk=None):
        """Get medication prices from available pharmacies with comparison"""
        try:
            prescription = self.get_object()
            participant = request.user

            # Get participant's currency using phone number and geolocation
            currency_code = CurrencyConverterService.get_participant_currency(participant)

            # Get all prescription items
            items = prescription.items.select_related('medication').all()

            # Get available pharmacies with inventory
            from pharmacy.models import PharmacyInventory

            medication_data = []
            total_cost_all = 0

            for item in items:
                # Find pharmacies that have this medication
                inventory_items = PharmacyInventory.objects.filter(
                    medication__name__icontains=item.medication_name,
                    quantity_in_stock__gte=item.quantity,
                    is_publicly_available=True
                ).select_related('pharmacy', 'medication').order_by('selling_price')[:5]

                pharmacy_options = []
                lowest_price = None

                for inv in inventory_items:
                    # Determine pharmacy's currency based on their location
                    pharmacy_currency = CurrencyConverterService.get_participant_currency(inv.pharmacy)

                    # Convert price from pharmacy currency to patient currency
                    try:
                        from decimal import Decimal
                        unit_price_in_pharmacy_currency = Decimal(str(inv.selling_price))

                        if pharmacy_currency != currency_code:
                            unit_price_converted = CurrencyConverterService.convert(
                                unit_price_in_pharmacy_currency,
                                pharmacy_currency,
                                currency_code
                            )
                        else:
                            unit_price_converted = unit_price_in_pharmacy_currency
                    except Exception as e:
                        logger.warning(f'Currency conversion error for pharmacy {inv.pharmacy.uid}: {str(e)}')
                        unit_price_converted = Decimal(str(inv.selling_price))

                    total_price = unit_price_converted * item.quantity

                    if lowest_price is None or unit_price_converted < lowest_price:
                        lowest_price = unit_price_converted

                    pharmacy_options.append({
                        'pharmacy_id': str(inv.pharmacy.uid),
                        'pharmacy_name': inv.pharmacy.full_name,
                        'pharmacy_currency': pharmacy_currency,
                        'original_unit_price': float(inv.selling_price),
                        'unit_price': float(round(unit_price_converted, 2)),
                        'total_price': float(round(total_price, 2)),
                        'in_stock': inv.quantity_in_stock,
                        'batch_number': inv.batch_number,
                        'expiry_date': str(inv.expiry_date) if inv.expiry_date else None
                    })

                # Calculate total for this medication using lowest price
                if lowest_price:
                    total_cost_all += lowest_price * item.quantity

                medication_data.append({
                    'item_id': str(item.id),
                    'medication_name': item.medication_name,
                    'dosage': item.dosage,
                    'strength': item.strength,
                    'quantity': item.quantity,
                    'frequency': item.frequency,
                    'instructions': item.instructions,
                    'pharmacies': pharmacy_options,
                    'lowest_price': float(round(lowest_price, 2)) if lowest_price else 0.0,
                    'available': len(pharmacy_options) > 0
                })

            # Convert Decimal to float for JSON serialization
            from decimal import Decimal
            total_cost_float = float(total_cost_all) if isinstance(total_cost_all, Decimal) else total_cost_all

            return Response({
                'success': True,
                'prescription_id': str(prescription.id),
                'medications': medication_data,
                'currency': currency_code,
                'currency_symbol': CurrencyConverterService.format_amount(Decimal('1'), currency_code).replace('1.00', '').strip(),
                'estimated_total': round(total_cost_float, 2),
                'pharmacies_count': len(set([
                    p['pharmacy_id']
                    for med in medication_data
                    for p in med['pharmacies']
                ]))
            })

        except Exception as e:
            logger.error(f'Error getting medication prices: {str(e)}', exc_info=True)
            return Response(
                {'detail': f'Erreur lors du chargement des prix: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def order_medications(self, request, pk=None):
        """Submit medication order to selected pharmacy"""
        try:
            prescription = self.get_object()
            participant = request.user

            if participant.role != 'patient':
                return Response(
                    {'detail': 'Seuls les patients peuvent commander des médicaments'},
                    status=status.HTTP_403_FORBIDDEN
                )

            pharmacy_id = request.data.get('pharmacy_id')
            medication_items = request.data.get('medication_items', [])
            delivery_method = request.data.get('delivery_method', 'pickup')
            delivery_address = request.data.get('delivery_address', '')
            payment_method = request.data.get('payment_method', 'cash_on_delivery')

            # Get patient's currency for this order
            patient_currency = CurrencyConverterService.get_participant_currency(participant)

            if not medication_items:
                return Response(
                    {'detail': 'Veuillez sélectionner au moins un médicament'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get selected pharmacy or find nearest one
            if pharmacy_id:
                try:
                    pharmacy = Participant.objects.get(uid=pharmacy_id, role='pharmacy', is_active=True)
                except Participant.DoesNotExist:
                    return Response(
                        {'detail': 'Pharmacie non trouvée'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                # Find any available pharmacy
                pharmacy = Participant.objects.filter(role='pharmacy', is_active=True).first()
                if not pharmacy:
                    return Response(
                        {'detail': 'Aucune pharmacie disponible pour le moment'},
                        status=status.HTTP_404_NOT_FOUND
                    )

            # Create pharmacy order
            from pharmacy.models import PharmacyOrder, PharmacyOrderItem, PharmacyInventory
            import random

            order_number = f"ORD-{random.randint(100000, 999999)}"

            with transaction.atomic():
                order = PharmacyOrder.objects.create(
                    order_number=order_number,
                    pharmacy=pharmacy,
                    patient=participant,
                    prescription=prescription,
                    status='pending',
                    payment_status='unpaid',
                    payment_method=payment_method,
                    currency=patient_currency,
                    delivery_method=delivery_method,
                    delivery_address=delivery_address
                )

                total_amount = 0

                # Create order items
                for med_item in medication_items:
                    item_id = med_item.get('item_id')
                    quantity = med_item.get('quantity', 0)

                    # Get prescription item
                    try:
                        prescription_item = prescription.items.get(id=item_id)
                    except:
                        continue

                    # Find inventory item
                    inventory_item = PharmacyInventory.objects.filter(
                        pharmacy=pharmacy,
                        medication__name__icontains=prescription_item.medication_name,
                        quantity_in_stock__gte=quantity,
                        is_publicly_available=True
                    ).first()

                    if inventory_item:
                        # Get pharmacy's currency and convert price to patient's currency
                        pharmacy_currency = CurrencyConverterService.get_participant_currency(pharmacy)
                        from decimal import Decimal

                        unit_price_pharmacy = Decimal(str(inventory_item.selling_price))

                        # Convert to patient currency if different
                        if pharmacy_currency != patient_currency:
                            unit_price = CurrencyConverterService.convert(
                                unit_price_pharmacy,
                                pharmacy_currency,
                                patient_currency
                            )
                        else:
                            unit_price = unit_price_pharmacy

                        # Convert to integer for database (storing as cents/minor units)
                        unit_price_int = int(unit_price * 100)
                        total_price = unit_price_int * quantity

                        PharmacyOrderItem.objects.create(
                            order=order,
                            medication=inventory_item.medication,
                            inventory_item=inventory_item,
                            quantity=quantity,
                            unit_price=unit_price_int,
                            total_price=total_price,
                            dosage_form=prescription_item.dosage_form,
                            strength=prescription_item.strength,
                            instructions=prescription_item.instructions
                        )

                        total_amount += total_price

                # Update order total
                order.total_amount = total_amount
                order.save()

                # Process payment based on payment method
                payment_result = None
                if payment_method == 'wallet':
                    # Deduct from wallet immediately
                    try:
                        from core.services import WalletService
                        from core.models import Wallet

                        patient_wallet = Wallet.objects.filter(participant=participant).first()
                        if not patient_wallet:
                            raise Exception('Portefeuille non trouvé')

                        # Convert total_amount from minor units to major units
                        amount_decimal = Decimal(str(total_amount)) / 100

                        if patient_wallet.balance < amount_decimal:
                            raise Exception('Solde insuffisant dans le portefeuille')

                        # Deduct from wallet
                        WalletService.deduct_funds(
                            participant=participant,
                            amount=amount_decimal,
                            description=f'Paiement pour commande {order_number}',
                            reference_id=str(order.id)
                        )

                        order.payment_status = 'paid'
                        order.amount_paid = total_amount
                        order.payment_reference = f'WALLET-{order_number}'
                        order.save()

                        payment_result = {
                            'status': 'success',
                            'message': 'Paiement par portefeuille effectué avec succès'
                        }

                    except Exception as wallet_error:
                        logger.error(f'Wallet payment failed: {str(wallet_error)}')
                        # Cancel the order
                        order.status = 'cancelled'
                        order.notes = f'Paiement échoué: {str(wallet_error)}'
                        order.save()
                        return Response(
                            {'detail': f'Erreur de paiement: {str(wallet_error)}'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                elif payment_method == 'insurance':
                    # Create insurance claim
                    try:
                        from insurance.models import InsuranceClaim

                        # Check if patient has active insurance
                        from insurance.models import InsuranceSubscription
                        active_subscription = InsuranceSubscription.objects.filter(
                            participant=participant,
                            status='active'
                        ).first()

                        if not active_subscription:
                            raise Exception('Aucune assurance active trouvée')

                        # Create insurance claim
                        claim = InsuranceClaim.objects.create(
                            participant=participant,
                            insurance_company=active_subscription.insurance_company,
                            subscription=active_subscription,
                            claim_type='medication',
                            service_date=timezone.now(),
                            total_amount=total_amount,
                            status='pending'
                        )

                        order.payment_status = 'pending'
                        order.payment_reference = f'INSURANCE-CLAIM-{claim.id}'
                        order.notes = f'En attente d\'approbation de l\'assurance (Réclamation #{claim.id})'
                        order.save()

                        payment_result = {
                            'status': 'pending',
                            'message': 'Réclamation d\'assurance créée. En attente d\'approbation.',
                            'claim_id': str(claim.id)
                        }

                    except Exception as insurance_error:
                        logger.error(f'Insurance claim failed: {str(insurance_error)}')
                        order.notes = f'Assurance non disponible: {str(insurance_error)}. Paiement requis.'
                        order.save()
                        payment_result = {
                            'status': 'warning',
                            'message': f'Assurance non disponible: {str(insurance_error)}. Veuillez choisir une autre méthode de paiement.'
                        }

                elif payment_method in ['card', 'mobile_money']:
                    # For card and mobile money, we'll return payment instructions
                    # The actual payment will be processed through payment gateway
                    order.payment_status = 'unpaid'
                    order.notes = f'En attente de paiement par {payment_method}'
                    order.save()

                    payment_result = {
                        'status': 'pending',
                        'message': f'Commande créée. Veuillez procéder au paiement.',
                        'payment_required': True,
                        'payment_amount': total_amount,
                        'currency': patient_currency
                    }

                else:  # cash or cash_on_delivery
                    # No immediate payment processing
                    order.notes = 'Paiement à la livraison/retrait'
                    order.save()

                    payment_result = {
                        'status': 'success',
                        'message': 'Commande créée. Paiement à la livraison/retrait.'
                    }

                # Update prescription status
                prescription.status = 'ordered'
                prescription.save()

                # Notify pharmacy
                try:
                    Notification.objects.create(
                        participant=pharmacy,
                        title='Nouvelle Commande de Médicaments',
                        message=f'{participant.full_name} a commandé des médicaments. Commande: {order_number}',
                        notification_type='prescription',
                        priority='high'
                    )
                except Exception as notif_error:
                    logger.warning(f'Failed to notify pharmacy: {str(notif_error)}')

                # Notify patient
                try:
                    Notification.objects.create(
                        participant=participant,
                        title='Commande Envoyée',
                        message=f'Votre commande {order_number} a été envoyée à {pharmacy.full_name}',
                        notification_type='prescription',
                        priority='medium'
                    )
                except Exception as notif_error:
                    logger.warning(f'Failed to notify patient: {str(notif_error)}')

                logger.info(f'Pharmacy order created: {order.id} for prescription {prescription.id}')

                # Generate QR code for order payment
                try:
                    from pharmacy.payment_service import PharmacyPaymentService
                    qr_code = PharmacyPaymentService.generate_order_qr_code(order)
                    if qr_code:
                        logger.info(f'QR code generated for order {order.order_number}')
                except Exception as qr_error:
                    logger.warning(f'Failed to generate QR code: {str(qr_error)}')

                # Prepare response with payment information
                response_data = {
                    'success': True,
                    'message': payment_result.get('message', 'Commande envoyée avec succès') if payment_result else 'Commande envoyée avec succès',
                    'order_id': str(order.id),
                    'order_number': order_number,
                    'pharmacy_name': pharmacy.full_name,
                    'total_amount': total_amount,
                    'currency': patient_currency,
                    'payment_method': payment_method,
                    'payment_status': order.payment_status
                }

                # Add payment-specific information
                if payment_result:
                    response_data['payment_info'] = payment_result

                return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f'Error creating prescription order: {str(e)}', exc_info=True)
            return Response(
                {'detail': f'Erreur lors de la commande: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def request_renewal(self, request, pk=None):
        """Request prescription renewal from doctor"""
        try:
            prescription = self.get_object()
            participant = request.user

            if participant.role != 'patient':
                return Response(
                    {'detail': 'Seuls les patients peuvent demander un renouvellement'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Check if prescription belongs to patient
            if prescription.patient != participant:
                return Response(
                    {'detail': 'Cette ordonnance ne vous appartient pas'},
                    status=status.HTTP_403_FORBIDDEN
                )

            patient_notes = request.data.get('patient_notes', '')

            # Check if there's already a pending renewal request
            from prescriptions.models import PrescriptionRenewalRequest
            existing_request = PrescriptionRenewalRequest.objects.filter(
                original_prescription=prescription,
                patient=participant,
                status='pending'
            ).first()

            if existing_request:
                return Response(
                    {'detail': 'Vous avez déjà une demande de renouvellement en attente'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create renewal request
            renewal_request = PrescriptionRenewalRequest.objects.create(
                original_prescription=prescription,
                patient=participant,
                doctor=prescription.doctor,
                patient_notes=patient_notes,
                status='pending'
            )

            # Notify doctor
            try:
                Notification.objects.create(
                    participant=prescription.doctor,
                    title='Demande de Renouvellement d\'Ordonnance',
                    message=f'{participant.full_name} demande le renouvellement d\'une ordonnance. Note: {patient_notes[:100]}',
                    notification_type='prescription',
                    priority='medium'
                )
            except Exception as notif_error:
                logger.warning(f'Failed to notify doctor: {str(notif_error)}')

            # Notify patient
            try:
                Notification.objects.create(
                    participant=participant,
                    title='Demande Envoyée',
                    message=f'Votre demande de renouvellement a été envoyée à Dr. {prescription.doctor.full_name}',
                    notification_type='prescription',
                    priority='low'
                )
            except Exception as notif_error:
                logger.warning(f'Failed to notify patient: {str(notif_error)}')

            logger.info(f'Prescription renewal request created: {renewal_request.id} for prescription {prescription.id}')

            return Response({
                'success': True,
                'message': 'Demande de renouvellement envoyée avec succès',
                'request_id': str(renewal_request.id),
                'doctor_name': prescription.doctor.full_name
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f'Error creating renewal request: {str(e)}', exc_info=True)
            return Response(
                {'detail': f'Erreur lors de la demande: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PrescriptionItemViewSet(viewsets.ModelViewSet):  # View for PrescriptionItemSet operations
    serializer_class = PrescriptionItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return PrescriptionItem.objects.none()
        return PrescriptionItem.objects.filter(prescription__patient=self.request.user)


class MedicationViewSet(viewsets.ModelViewSet):  # View for MedicationSet operations
    queryset = Medication.objects.all()
    serializer_class = MedicationSerializer
    permission_classes = [IsAuthenticated]

