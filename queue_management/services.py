"""
Queue Management Service for BINTACURA
Handles appointment queues, waiting lists, and real-time notifications

This is the SINGLE source for queue management logic.
Import from here: from queue_management.services import QueueManagementService
"""
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db.models import Max, Count, Q, Sum
from datetime import datetime, timedelta
from appointments.models import Appointment, AppointmentQueue
from appointments.appointment_service_model import AppointmentService
from core.models import Participant
from core.system_config import SystemConfiguration
from currency_converter.services import CurrencyConverterService
from payments.service_payment_service import ServicePaymentService

from communication.notification_service import NotificationService

logger = logging.getLogger(__name__)


class QueueManagementService:
    """Comprehensive queue management for appointments"""
    
    @staticmethod
    @transaction.atomic
    def book_appointment_with_payment(
        patient: Participant,
        appointment_data: dict,
        payment_method: str = 'wallet'
    ) -> dict:
        """
        Complete appointment booking flow:
        1. Calculate total: default consultation fee + additional services
        2. Create appointment
        3. Process payment
        4. Assign queue number
        5. Generate receipt
        6. Send notifications
        
        Args:
            patient: Patient booking the appointment
            appointment_data: Appointment details (doctor/hospital, date, time, services, etc.)
            payment_method: 'wallet' or 'onsite'
            
        Returns:
            dict with appointment, payment, queue info, and receipt
        """
        # Extract data
        service_participant = appointment_data.get('doctor') or appointment_data.get('hospital')  # Doctor or Hospital
        additional_services = appointment_data.get('additional_services', [])  # List of service IDs
        appointment_date = appointment_data.get('appointment_date')
        appointment_time = appointment_data.get('appointment_time')
        appointment_type = appointment_data.get('type', 'consultation')
        reason = appointment_data.get('reason', '')
        symptoms = appointment_data.get('symptoms', '')
        
        # Get system default consultation fee (cannot be changed)
        system_config = SystemConfiguration.get_active_config()
        default_consultation_fee_usd = Decimal(str(system_config.default_consultation_fee))
        
        # Get patient's local currency
        patient_currency = CurrencyConverterService.get_participant_currency(patient)
        
        # Convert consultation fee to patient's local currency
        default_consultation_fee = CurrencyConverterService.get_consultation_fee_in_currency(
            default_consultation_fee_usd,
            patient_currency
        )
        
        logger.info(f"Consultation fee: {default_consultation_fee_usd} USD = {default_consultation_fee} {patient_currency}")
        
        # Calculate additional services total
        additional_services_total = Decimal('0.00')
        services_details = []
        
        if additional_services:
            from core.models import ProviderService
            for service_id in additional_services:
                try:
                    service = ProviderService.objects.get(
                        id=service_id,
                        participant=service_participant,
                        is_active=True,
                        is_available=True
                    )
                    additional_services_total += Decimal(str(service.price))
                    services_details.append({
                        'service': service,
                        'price': Decimal(str(service.price))
                    })
                except ProviderService.DoesNotExist:
                    logger.warning(f"Service {service_id} not found or unavailable")
        
        # Total amount = default consultation + additional services
        subtotal = default_consultation_fee + additional_services_total
        
        # Add 1% transaction fee to patient's total (not deducted from provider)
        transaction_fee = subtotal * Decimal('0.01')
        total_amount_with_fee = subtotal + transaction_fee
        
        # Create appointment (pending until payment)
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=service_participant if service_participant.role == 'doctor' else None,
            hospital=service_participant if service_participant.role == 'hospital' else None,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            type=appointment_type,
            reason=reason,
            symptoms=symptoms,
            consultation_fee=int(default_consultation_fee),
            additional_services_total=additional_services_total,
            original_price=int(subtotal),
            final_price=int(total_amount_with_fee),
            status='pending',
            payment_status='pending',
            is_hospital_appointment=service_participant.role == 'hospital',
            currency=patient_currency
        )
        
        # Create appointment service records for additional services
        for service_detail in services_details:
            AppointmentService.objects.create(
                appointment=appointment,
                service=service_detail['service'],
                service_price=service_detail['price'],
                quantity=1,
                subtotal=service_detail['price']
            )
        
        # Process payment
        payment_result = None
        payment_url = None
        if total_amount_with_fee > 0:
            try:
                # Normalize payment method names
                is_online_payment = payment_method in ['wallet', 'online', 'fedapay', 'card', 'mobile_money']
                is_onsite_payment = payment_method in ['onsite', 'cash', 'onsite_cash']
                
                if is_online_payment:
                    # For online payments, initiate FedaPay transaction
                    # This returns a payment URL for the user to complete payment
                    payment_result = ServicePaymentService.initiate_online_payment(
                        patient=patient,
                        provider=service_participant,
                        amount=subtotal,
                        currency=patient_currency,
                        service_type='appointment',
                        service_id=str(appointment.id),
                        description=f"Appointment booking - {appointment_type} with {service_participant.full_name}" + 
                                  (f" + {len(services_details)} additional service(s)" if services_details else "")
                    )
                    # Online payment starts as pending until FedaPay confirms
                    appointment.payment_status = 'pending'
                    appointment.payment_method = 'online'
                    payment_url = payment_result.get('payment_url')
                    
                elif is_onsite_payment:
                    # For onsite payments, create a pending payment record
                    payment_result = ServicePaymentService.record_onsite_payment(
                        patient=patient,
                        provider=service_participant,
                        amount=subtotal,
                        currency=patient_currency,
                        service_type='appointment',
                        service_id=str(appointment.id),
                        description=f"Appointment booking - {appointment_type} with {service_participant.full_name} (Pay on-site)" +
                                  (f" + {len(services_details)} additional service(s)" if services_details else "")
                    )
                    appointment.payment_status = 'pending'
                    appointment.payment_method = 'onsite'
                else:
                    raise ValueError(f"Unsupported payment method: {payment_method}")
                
                # Update appointment with payment info
                appointment.payment_id = payment_result['patient_transaction'].id
                appointment.payment_reference = str(payment_result['patient_transaction'].transaction_ref)
                appointment.status = 'confirmed'
                appointment.save()
                
            except Exception as e:
                logger.error(f"Payment failed for appointment {appointment.id}: {str(e)}")
                appointment.delete()
                raise ValueError(f"Payment failed: {str(e)}")
        else:
            # Free appointment
            appointment.payment_status = 'paid'
            appointment.status = 'confirmed'
            appointment.save()
        
        # Assign queue number
        queue_entry = QueueManagementService._assign_queue_number(appointment, service_participant)
        
        # Generate receipt
        receipt = None
        if payment_result:
            receipt = ServicePaymentService.generate_payment_receipt(
                payment_result['patient_transaction'],
                service_provider_role=service_participant.role
            )
            
            # Add queue info and services to receipt metadata
            from payments.models import PaymentReceipt
            receipt_obj = PaymentReceipt.objects.get(receipt_number=receipt.receipt_number)
            if receipt_obj.transaction.metadata is None:
                receipt_obj.transaction.metadata = {}
            
            receipt_obj.transaction.metadata.update({
                'appointment_id': str(appointment.id),
                'queue_number': queue_entry.queue_number,
                'appointment_date': str(appointment_date),
                'appointment_time': str(appointment_time),
                'service_participant_name': service_participant.full_name,
                'consultation_fee_usd': str(default_consultation_fee_usd),
                'consultation_fee': str(default_consultation_fee),
                'currency': patient_currency,
                'additional_services_total': str(additional_services_total),
                'subtotal': str(subtotal),
                'transaction_fee': str(transaction_fee),
                'transaction_fee_percentage': '1%',
                'total_amount': str(total_amount_with_fee),
                'services_count': len(services_details),
                'services': [
                    {
                        'name': sd['service'].name,
                        'price': str(sd['price'])
                    } for sd in services_details
                ]
            })
            receipt_obj.transaction.save()
        
        # Send notifications
        QueueManagementService._send_booking_notifications(
            appointment=appointment,
            queue_entry=queue_entry,
            payment_method=payment_method
        )
        
        return {
            'success': True,
            'appointment': appointment,
            'queue_number': queue_entry.queue_number,
            'estimated_wait_time': queue_entry.estimated_wait_time,
            'payment_result': payment_result,
            'payment_url': payment_url,  # FedaPay payment URL for online payments
            'transaction_id': str(payment_result['patient_transaction'].id) if payment_result else None,
            'queue_position': QueueManagementService.get_queue_position(queue_entry.id)
        }
    
    @staticmethod
    def _assign_queue_number(appointment: Appointment, provider: Participant) -> 'AppointmentQueue':
        """Assign queue number to appointment"""
        # Get next queue number for this participant on this date
        max_queue = AppointmentQueue.objects.filter(
            participant=provider,
            appointment__appointment_date=appointment.appointment_date,
            status__in=['waiting', 'in_progress']
        ).aggregate(Max('queue_number'))['queue_number__max']
        
        next_queue_number = (max_queue or 0) + 1
        
        # Calculate estimated wait time (15 min per person ahead)
        estimated_wait = (next_queue_number - 1) * 15
        
        # Create queue entry
        queue_entry = AppointmentQueue.objects.create(
            appointment=appointment,
            participant=provider,
            queue_number=next_queue_number,
            estimated_wait_time=estimated_wait,
            status='waiting'
        )
        
        # Update appointment queue number
        appointment.queue_number = next_queue_number
        appointment.save()
        
        return queue_entry
    
    @staticmethod
    def _send_booking_notifications(appointment: Appointment, queue_entry: 'AppointmentQueue', payment_method: str):
        """Send notifications to patient and service participant"""
        try:
            service_participant_name = (appointment.doctor or appointment.hospital).full_name
            appointment_datetime = f"{appointment.appointment_date} at {appointment.appointment_time}"
            
            # Notify patient
            NotificationService.send_notification(
                user=appointment.patient,
                title="Appointment Confirmed",
                message=f"Your appointment with {service_participant_name} on {appointment_datetime} is confirmed. "
                        f"Queue number: {queue_entry.queue_number}. "
                        f"Estimated wait time: {queue_entry.estimated_wait_time} minutes. "
                        f"Payment: {payment_method}",
                notification_type='appointment',
                priority='high',
                metadata={
                    'appointment_id': str(appointment.id),
                    'queue_number': queue_entry.queue_number,
                    'payment_method': payment_method
                }
            )
            
            # Notify provider (doctor/hospital)
            NotificationService.send_notification(
                user=appointment.provider,
                title="New Appointment Booked",
                message=f"New appointment from {appointment.patient.full_name} "
                        f"on {appointment_datetime}. "
                        f"Queue number: {queue_entry.queue_number}. "
                        f"Reason: {appointment.reason}",
                notification_type='appointment',
                priority='normal',
                metadata={
                    'appointment_id': str(appointment.id),
                    'patient_id': str(appointment.patient.uid),
                    'queue_number': queue_entry.queue_number
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to send booking notifications: {str(e)}")
    
    @staticmethod
    def get_queue_position(queue_entry_id: str) -> dict:
        """Get detailed queue position information"""
        try:
            queue_entry = AppointmentQueue.objects.get(id=queue_entry_id)
            
            # Count people ahead in queue
            ahead = AppointmentQueue.objects.filter(
                participant=queue_entry.participant,
                appointment__appointment_date=queue_entry.appointment.appointment_date,
                queue_number__lt=queue_entry.queue_number,
                status='waiting'
            ).count()
            
            # Total in queue
            total_waiting = AppointmentQueue.objects.filter(
                participant=queue_entry.participant,
                appointment__appointment_date=queue_entry.appointment.appointment_date,
                status='waiting'
            ).count()
            
            return {
                'queue_number': queue_entry.queue_number,
                'people_ahead': ahead,
                'total_waiting': total_waiting,
                'estimated_wait_time': ahead * 15,  # 15 min per person
                'status': queue_entry.status,
                'appointment_date': str(queue_entry.appointment.appointment_date),
                'appointment_time': str(queue_entry.appointment.appointment_time)
            }
        except AppointmentQueue.DoesNotExist:
            return None
    
    @staticmethod
    @transaction.atomic
    def call_next_patient(service_participant: Participant, appointment_date=None) -> dict:
        """
        Call the next patient in queue
        Sends notifications to patient
        """
        if appointment_date is None:
            appointment_date = timezone.now().date()
        
        # Get next waiting patient
        next_in_queue = AppointmentQueue.objects.filter(
            participant=service_participant,
            appointment__appointment_date=appointment_date,
            status='waiting'
        ).order_by('queue_number').first()
        
        if not next_in_queue:
            return {
                'success': False,
                'message': 'No patients waiting in queue'
            }
        
        # Update queue status
        next_in_queue.status = 'in_progress'
        next_in_queue.actual_start_time = timezone.now()
        next_in_queue.save()
        
        # Update appointment status
        appointment = next_in_queue.appointment
        appointment.status = 'in_progress'
        appointment.save()
        
        # Send notification to patient (mobile + screen)
        NotificationService.send_notification(
            user=appointment.patient,
            title="It's Your Turn!",
            message=f"The doctor is ready to see you now. "
                    f"Queue number: {next_in_queue.queue_number}. "
                    f"Please proceed to consultation room.",
            notification_type='queue_call',
            priority='urgent',
            metadata={
                'appointment_id': str(appointment.id),
                'queue_number': next_in_queue.queue_number,
                'participant_id': str(service_participant.uid),
                'call_time': str(timezone.now())
            },
            send_push=True,  # Mobile notification
            send_sms=True    # Optional SMS
        )
        
        # Update wait times for remaining patients
        QueueManagementService._update_waiting_estimates(service_participant, appointment_date)
        
        return {
            'success': True,
            'appointment': appointment,
            'queue_entry': next_in_queue,
            'patient': appointment.patient,
            'message': f"Called patient {appointment.patient.full_name}, Queue #{next_in_queue.queue_number}"
        }
    
    @staticmethod
    def _update_waiting_estimates(provider: Participant, appointment_date):
        """Update estimated wait times for remaining patients"""
        waiting_patients = AppointmentQueue.objects.filter(
            participant=provider,
            appointment__appointment_date=appointment_date,
            status='waiting'
        ).order_by('queue_number')
        
        for index, queue_entry in enumerate(waiting_patients):
            queue_entry.estimated_wait_time = index * 15  # 15 min each
            queue_entry.save()
    
    @staticmethod
    @transaction.atomic
    def complete_appointment(appointment_id: str) -> dict:
        """Mark appointment as completed"""
        try:
            appointment = Appointment.objects.get(id=appointment_id)
            queue_entry = appointment.queue_entry
            
            # Update statuses
            appointment.status = 'completed'
            appointment.completed_at = timezone.now()
            appointment.save()
            
            queue_entry.status = 'completed'
            queue_entry.actual_end_time = timezone.now()
            queue_entry.save()
            
            # Calculate actual duration
            if queue_entry.actual_start_time:
                duration = (queue_entry.actual_end_time - queue_entry.actual_start_time).total_minutes()
            else:
                duration = 0
            
            # Send completion notification
            NotificationService.send_notification(
                user=appointment.patient,
                title="Appointment Completed",
                message=f"Your appointment with {(appointment.doctor or appointment.hospital).full_name} is complete. "
                        f"Thank you for choosing BINTACURA!",
                notification_type='appointment',
                priority='normal',
                metadata={
                    'appointment_id': str(appointment.id),
                    'duration_minutes': duration
                }
            )
            
            return {
                'success': True,
                'appointment': appointment,
                'duration_minutes': duration
            }
            
        except Appointment.DoesNotExist:
            return {
                'success': False,
                'error': 'Appointment not found'
            }
    
    @staticmethod
    def send_appointment_reminder(appointment_id: str):
        """Send reminder notification before appointment"""
        try:
            appointment = Appointment.objects.get(id=appointment_id)
            
            if appointment.reminder_sent:
                return {'success': False, 'message': 'Reminder already sent'}
            
            appointment_datetime = f"{appointment.appointment_date} at {appointment.appointment_time}"
            
            NotificationService.send_notification(
                user=appointment.patient,
                title="Appointment Reminder",
                message=f"Reminder: You have an appointment with {(appointment.doctor or appointment.hospital).full_name} "
                        f"tomorrow at {appointment.appointment_time}. "
                        f"Your queue number is {appointment.queue_number}.",
                notification_type='reminder',
                priority='normal',
                metadata={
                    'appointment_id': str(appointment.id),
                    'queue_number': appointment.queue_number
                },
                send_push=True,
                send_email=True
            )
            
            appointment.reminder_sent = True
            appointment.save()
            
            return {'success': True}
            
        except Appointment.DoesNotExist:
            return {'success': False, 'error': 'Appointment not found'}
    
    @staticmethod
    def get_participant_queue_status(participant_id: str, date=None) -> dict:
        """Get queue status for a participant (doctor/hospital)"""
        if date is None:
            date = timezone.now().date()
        
        participant = Participant.objects.get(uid=participant_id)
        
        queue_entries = AppointmentQueue.objects.filter(
            participant=participant,
            appointment__appointment_date=date
        ).select_related('appointment', 'appointment__patient')
        
        waiting = queue_entries.filter(status='waiting').order_by('queue_number')
        in_progress = queue_entries.filter(status='in_progress').first()
        completed = queue_entries.filter(status='completed').count()
        
        return {
            'participant': participant,
            'date': str(date),
            'total_appointments': queue_entries.count(),
            'waiting_count': waiting.count(),
            'completed_count': completed,
            'current_patient': in_progress.appointment if in_progress else None,
            'waiting_list': [
                {
                    'queue_number': qe.queue_number,
                    'patient_name': qe.appointment.patient.full_name,
                    'appointment_time': str(qe.appointment.appointment_time),
                    'estimated_wait': qe.estimated_wait_time,
                    'reason': qe.appointment.reason
                }
                for qe in waiting
            ]
        }

