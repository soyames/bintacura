from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import render
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from decimal import Decimal
from doctor.models import DoctorData
from core.models import Participant, Transaction
from core.services import WalletService
from communication.services import NotificationService

from currency_converter.services import CurrencyConverterService
from .models import *
from .serializers import *


class AppointmentViewSet(viewsets.ModelViewSet):  # View for AppointmentSet operations
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        current_participant = self.request.user
        
        if current_participant.role == "patient":
            return Appointment.objects.filter(
                patient=current_participant
            ).select_related('doctor', 'hospital', 'service', 'beneficiary').order_by("-appointment_date", "-appointment_time")
        elif current_participant.role == "doctor":
            return Appointment.objects.filter(doctor=current_participant).select_related('patient', 'hospital', 'service').order_by(
                "-appointment_date", "-appointment_time"
            )
        elif current_participant.role == "hospital":
            return Appointment.objects.filter(
                hospital=current_participant
            ).select_related('patient', 'doctor', 'service').order_by("-appointment_date", "-appointment_time")
        elif current_participant.role in ["admin", "super_admin"]:
            return Appointment.objects.all().select_related('patient', 'doctor', 'hospital', 'service', 'beneficiary').order_by("-appointment_date", "-appointment_time")
        
        return Appointment.objects.none()

    @transaction.atomic
    @transaction.atomic
    def create(self, request, *args, **kwargs):  # Create
        try:
            if request.user.role != "patient":
                return Response(
                    {"error": "Seuls les patients peuvent créer des rendez-vous"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            
            patient = request.user
            doctor_id = request.data.get("doctor_id")
            appointment_date = request.data.get("appointment_date")
            appointment_time = request.data.get("appointment_time")

            if not doctor_id:
                return Response(
                    {"error": "L'identifiant du médecin est requis"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            if not appointment_date or not appointment_time:
                return Response(
                    {"error": "La date et l'heure du rendez-vous sont requises"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                doctor = Participant.objects.get(uid=doctor_id, role="doctor")
            except Participant.DoesNotExist:
                return Response(
                    {"error": "Médecin non trouvé"}, status=status.HTTP_404_NOT_FOUND,
                )
            
            # Prevent double booking - check if slot is already taken
            existing_appointment = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                status__in=['pending', 'confirmed', 'in_progress']
            ).exists()
            
            if existing_appointment:
                return Response(
                    {"error": "Ce créneau horaire n'est plus disponible. Veuillez en choisir un autre."},
                    status=status.HTTP_409_CONFLICT,
                )

            try:
                doctor_data = DoctorData.objects.get(participant=doctor)
                consultation_fee_xof = doctor_data.get_consultation_fee()
            except DoctorData.DoesNotExist:
                from django.conf import settings
                consultation_fee_xof = getattr(settings, 'DEFAULT_CONSULTATION_FEE_XOF', 3500)

            patient_currency = CurrencyConverterService.get_participant_currency(patient)
            consultation_fee = CurrencyConverterService.convert(
                Decimal(str(consultation_fee_xof)),
                'XOF',
                patient_currency
            )

            additional_services_total = Decimal('0.00')
            service_id = request.data.get("service_id")
            service = None
            if service_id:
                try:
                    from doctor.models import DoctorService

                    service = DoctorService.objects.get(
                        id=service_id,
                        doctor=doctor,
                        is_active=True,
                        is_available=True,
                    )
                    if service.price:
                        service_price_local = CurrencyConverterService.convert(
                            Decimal(str(service.price)),
                            'XOF',
                            patient_currency
                        )
                        additional_services_total = service_price_local
                        consultation_fee = consultation_fee + service_price_local
                except DoctorService.DoesNotExist:
                    pass

            subtotal = consultation_fee
            transaction_fee = subtotal * Decimal('0.01')
            total_amount = subtotal + transaction_fee

            # Get payment method from request (defaults to wallet if not specified)
            payment_method = request.data.get("payment_method", "wallet")

            appointment_data = {
                "patient": patient,
                "doctor": doctor,
                "service": service,
                "appointment_date": request.data.get("appointment_date"),
                "appointment_time": request.data.get("appointment_time"),
                "reason": request.data.get("reason", ""),
                "notes": request.data.get("notes", ""),
                "status": "pending",
                "type": "consultation",
                "consultation_fee": subtotal,
                "currency": patient_currency,
                "additional_services_total": additional_services_total,
                "original_price": subtotal,
                "final_price": total_amount,
                "payment_status": "pending",
                "payment_method": payment_method,  # Store payment method
            }

            appointment = Appointment.objects.create(**appointment_data)

            # Generate QR code for appointment payment
            try:
                from payments.universal_payment_service import UniversalPaymentService
                qr_code = UniversalPaymentService.generate_payment_qr('appointment', appointment, patient)
                if qr_code:
                    logger.info(f'QR code generated for appointment {appointment.id}')
            except Exception as qr_error:
                logger.warning(f'Failed to generate QR code for appointment: {str(qr_error)}')

            NotificationService.create_notification(
                {
                    "recipient": doctor,
                    "notification_type": "appointment",
                    "title": "Nouvelle demande de rendez-vous",
                    "message": f"{patient.full_name or patient.email} a demandé un rendez-vous pour le {appointment.appointment_date} à {appointment.appointment_time}",
                    "action_url": f"/doctor/appointments/{appointment.id}/",
                    "metadata": {
                        "appointment_id": str(appointment.id),
                        "patient_name": patient.full_name or patient.email,
                        "appointment_date": str(appointment.appointment_date),
                        "appointment_time": str(appointment.appointment_time),
                    },
                }
            )

            NotificationService.create_notification(
                {
                    "recipient": patient,
                    "notification_type": "appointment",
                    "title": "Rendez-vous pré-réservé",
                    "message": f"Votre rendez-vous avec Dr. {doctor.full_name or doctor.email} est pré-réservé. Veuillez effectuer le paiement pour confirmer.",
                    "action_url": f"/patient/my-appointments/{appointment.id}/",
                    "metadata": {
                        "appointment_id": str(appointment.id),
                        "doctor_name": doctor.full_name or doctor.email,
                        "consultation_fee": str(consultation_fee),
                    },
                }
            )

            serializer = self.get_serializer(appointment)
            return Response(
                {
                    "success": True,
                    "message": "Rendez-vous pré-réservé avec succès",
                    "appointment": serializer.data,
                    "requires_payment": total_amount > 0,
                    "subtotal": float(subtotal),
                    "transaction_fee": float(transaction_fee),
                    "total_amount": float(total_amount),
                    "currency": patient_currency,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):  # Pay
        appointment = self.get_object()

        if appointment.patient != request.user:
            return Response(
                {"error": "Seul le patient peut effectuer le paiement"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if appointment.payment_status == "paid":
            return Response(
                {"error": "Paiement déjà effectué"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment_method = request.data.get("payment_method", "wallet")

        if appointment.consultation_fee <= 0:
            appointment.payment_status = "paid"
            appointment.status = "confirmed"
            appointment.save()

            NotificationService.create_notification(
                {
                    "recipient": appointment.doctor,
                    "notification_type": "appointment",
                    "title": "Rendez-vous confirmé",
                    "message": f"Le rendez-vous avec {appointment.patient.full_name or appointment.patient.email} pour le {appointment.appointment_date} à {appointment.appointment_time} est confirmé.",
                    "action_url": f"/doctor/appointments/{appointment.id}/",
                    "metadata": {"appointment_id": str(appointment.id)},
                }
            )

            NotificationService.create_notification(
                {
                    "recipient": appointment.patient,
                    "notification_type": "appointment",
                    "title": "Rendez-vous confirmé",
                    "message": f"Votre rendez-vous avec Dr. {appointment.doctor.full_name or appointment.doctor.email} est confirmé pour le {appointment.appointment_date} à {appointment.appointment_time}.",
                    "action_url": f"/patient/my-appointments/{appointment.id}/",
                    "metadata": {"appointment_id": str(appointment.id)},
                }
            )

            return Response(
                {
                    "success": True,
                    "message": "Rendez-vous confirmé (aucun paiement requis)",
                    "appointment_id": str(appointment.id),
                }
            )

        try:
            payment_amount = appointment.final_price if appointment.final_price > 0 else appointment.consultation_fee
            
            payment_result = WalletService.make_payment(
                patient=appointment.patient,
                recipient=appointment.doctor,
                amount=payment_amount,
                description=f"Consultation fee - Appointment {appointment.id}",
                payment_method=payment_method,
                metadata={
                    "appointment_id": str(appointment.id),
                    "appointment_date": str(appointment.appointment_date),
                    "appointment_time": str(appointment.appointment_time),
                    "consultation_fee": str(appointment.consultation_fee),
                    "transaction_fee": str(payment_amount - appointment.consultation_fee),
                },
            )

            patient_txn = payment_result["patient_transaction"]
            is_cash_payment = payment_method in ['cash', 'onsite_cash', 'onsite']

            if is_cash_payment:
                appointment.payment_status = "pending"
                appointment.status = "pending"
            else:
                appointment.payment_status = "paid"
                appointment.status = "confirmed"

            appointment.payment_id = patient_txn.id
            appointment.payment_method = payment_method  # Store payment method
            appointment.payment_reference = str(patient_txn.id)  # Store payment reference
            appointment.save()

            if is_cash_payment:
                NotificationService.create_notification(
                    {
                        "recipient": appointment.doctor,
                        "notification_type": "appointment",
                        "title": "Nouveau rendez-vous - Paiement sur place",
                        "message": f"Rendez-vous avec {appointment.patient.full_name or appointment.patient.email} pour le {appointment.appointment_date} à {appointment.appointment_time}. Paiement sur place à confirmer.",
                        "action_url": f"/doctor/appointments/{appointment.id}/",
                        "metadata": {
                            "appointment_id": str(appointment.id),
                            "amount": str(appointment.consultation_fee),
                            "payment_method": payment_method,
                        },
                    }
                )

                NotificationService.create_notification(
                    {
                        "recipient": appointment.patient,
                        "notification_type": "appointment",
                        "title": "Rendez-vous enregistré",
                        "message": f"Votre rendez-vous avec Dr. {appointment.doctor.full_name or appointment.doctor.email} est enregistré pour le {appointment.appointment_date} à {appointment.appointment_time}. Veuillez effectuer le paiement sur place.",
                        "action_url": f"/patient/my-appointments/{appointment.id}/",
                        "metadata": {
                            "appointment_id": str(appointment.id),
                            "amount": str(appointment.consultation_fee),
                        },
                    }
                )
                
                return Response(
                    {
                        "success": True,
                        "message": "Rendez-vous enregistré. Veuillez effectuer le paiement sur place.",
                        "appointment_id": str(appointment.id),
                        "transaction_ref": str(patient_txn.transaction_ref),
                        "payment_status": "pending",
                    }
                )
            else:
                NotificationService.create_notification(
                    {
                        "recipient": appointment.doctor,
                        "notification_type": "payment",
                        "title": "Paiement reçu",
                        "message": f"Paiement de {appointment.consultation_fee} {appointment.currency} reçu de {appointment.patient.full_name or appointment.patient.email}. Rendez-vous confirmé pour le {appointment.appointment_date} à {appointment.appointment_time}.",
                        "action_url": f"/doctor/appointments/{appointment.id}/",
                        "metadata": {
                            "appointment_id": str(appointment.id),
                            "amount": str(appointment.consultation_fee),
                            "transaction_ref": str(patient_txn.transaction_ref),
                        },
                    }
                )

                NotificationService.create_notification(
                    {
                        "recipient": appointment.patient,
                        "notification_type": "payment",
                        "title": "Paiement confirmé",
                        "message": f"Votre paiement de {appointment.consultation_fee} {appointment.currency} a été effectué avec succès. Rendez-vous confirmé avec Dr. {appointment.doctor.full_name or appointment.doctor.email}.",
                        "action_url": f"/patient/my-appointments/{appointment.id}/",
                        "metadata": {
                            "appointment_id": str(appointment.id),
                            "amount": str(appointment.consultation_fee),
                            "transaction_ref": str(patient_txn.transaction_ref),
                        },
                    }
                )

                return Response(
                    {
                        "success": True,
                        "message": "Paiement réussi, rendez-vous confirmé",
                        "appointment_id": str(appointment.id),
                        "transaction_ref": str(patient_txn.transaction_ref),
                    }
                )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            print(f"Payment Error: {error_details}")
            return Response(
                {"error": f"Échec du traitement du paiement: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):  # Cancel
        appointment = self.get_object()

        if appointment.patient != request.user and appointment.doctor != request.user:
            return Response(
                {"success": False, "message": "Non autorisé"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if appointment.status in ["completed", "cancelled"]:
            return Response(
                {"success": False, "message": "Impossible d'annuler ce rendez-vous"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        previous_status = appointment.status
        appointment.status = "cancelled"
        appointment.cancelled_at = timezone.now()
        appointment.cancellation_reason = request.data.get(
            "reason", "Annulé par l'utilisateur"
        )
        appointment.save()

        if (
            appointment.payment_status == "paid"
            and appointment.payment_id
            and previous_status == "confirmed"
        ):
            try:
                WalletService.refund_payment(
                    original_transaction_ref=appointment.payment_id,
                    reason=f"Appointment cancelled: {appointment.cancellation_reason}",
                )
                appointment.payment_status = "refunded"
                appointment.save()
                return Response(
                    {
                        "success": True,
                        "message": "Rendez-vous annulé et paiement remboursé avec succès",
                    }
                )
            except Exception as e:
                return Response(
                    {
                        "success": True,
                        "message": "Rendez-vous annulé, mais erreur de remboursement. Contactez le support.",
                        "refund_error": str(e),
                    }
                )

        return Response({"success": True, "message": "Rendez-vous annulé avec succès"})

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):  # Confirm
        appointment = self.get_object()

        if appointment.doctor != request.user:
            return Response(
                {"success": False, "message": "Seul le médecin peut confirmer"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if appointment.status != "pending":
            return Response(
                {"success": False, "message": "Statut invalide"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        appointment.status = "confirmed"
        appointment.save()

        return Response({"success": True, "message": "Rendez-vous confirmé"})

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):  # Complete
        appointment = self.get_object()

        if appointment.doctor != request.user:
            return Response(
                {"success": False, "message": "Seul le médecin peut terminer"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if appointment.status not in ["confirmed", "in_progress"]:
            return Response(
                {"success": False, "message": "Statut invalide"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        appointment.status = "completed"
        appointment.completed_at = timezone.now()
        appointment.notes = request.data.get("notes", "")
        appointment.save()

        return Response({"success": True, "message": "Consultation terminée"})

    @action(detail=True, methods=["post"])
    def reschedule(self, request, pk=None):
        """Reschedule appointment with payment requirement"""
        from django.conf import settings

        appointment = self.get_object()

        if appointment.patient != request.user:
            return Response(
                {"error": "Only the patient can reschedule"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if appointment.status in ["completed", "cancelled"]:
            return Response(
                {"error": "Cannot reschedule completed or cancelled appointments"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_date = request.data.get("appointment_date")
        new_time = request.data.get("appointment_time")
        payment_method = request.data.get("payment_method", "wallet")

        if not new_date or not new_time:
            return Response(
                {"error": "New date and time are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reschedule_fee = getattr(settings, "RESCHEDULE_FEE", 1000)

        try:
            # Charge reschedule fee
            payment_result = WalletService.make_payment(
                patient=appointment.patient,
                recipient=None,  # Platform fee goes to platform
                amount=reschedule_fee,
                description=f"Reschedule fee - Appointment {appointment.id}",
                payment_method=payment_method,
                metadata={
                    "appointment_id": str(appointment.id),
                    "old_date": str(appointment.appointment_date),
                    "old_time": str(appointment.appointment_time),
                    "new_date": str(new_date),
                    "new_time": str(new_time),
                    "type": "reschedule_fee",
                },
            )

            # Update appointment
            appointment.appointment_date = new_date
            appointment.appointment_time = new_time
            appointment.save()

            return Response(
                {
                    "success": True,
                    "message": "Appointment rescheduled successfully",
                    "reschedule_fee": reschedule_fee,
                    "transaction_ref": str(
                        payment_result["patient_transaction"].transaction_ref
                    ),
                    "appointment": self.get_serializer(appointment).data,
                }
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": "Reschedule payment failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"])
    def download_receipt(self, request, pk=None):
        """Redirect to invoice page"""
        appointment = self.get_object()

        if appointment.patient != request.user and not request.user.is_staff:
            return Response(
                {"error": "Non autorisé"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if appointment.payment_id:
            from django.shortcuts import redirect
            return redirect(f'/patient/view-invoice/{appointment.payment_id}/')
        else:
            return Response(
                {"error": "Aucune facture disponible pour ce rendez-vous"},
                status=status.HTTP_404_NOT_FOUND,
            )


class AvailabilityViewSet(viewsets.ModelViewSet):  # View for AvailabilitySet operations
    queryset = Availability.objects.all()
    serializer_class = AvailabilitySerializer

    def get_permissions(self):  # Get permissions
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        current_participant = self.request.user
        participant_id = self.request.query_params.get("participant_id")
        date_param = self.request.query_params.get("date")

        if participant_id and date_param:
            from datetime import datetime
            selected_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            weekday_name = selected_date.strftime('%A').lower()
            
            return Availability.objects.filter(
                participant__uid=participant_id,
                weekday=weekday_name,
                is_active=True
            )

        if participant_id:
            return Availability.objects.filter(
                participant__uid=participant_id, is_active=True
            )

        if current_participant.role in ["doctor", "hospital", "pharmacy"]:
            return Availability.objects.filter(participant=current_participant)
        elif current_participant.role in ["admin", "super_admin"]:
            return Availability.objects.all()
        
        return Availability.objects.none()

    def perform_create(self, serializer):  # Perform create
        serializer.save()

    def list(self, request, *args, **kwargs):  # List
        participant_id = request.query_params.get("participant_id") or request.query_params.get("doctor_id") or request.query_params.get("hospital_id")
        date_param = request.query_params.get("date")

        if participant_id and date_param:
            return self.get_available_slots(request, participant_id, date_param)

        return super().list(request, *args, **kwargs)

    def get_available_slots(self, request, participant_id, date_str):  # Get available slots
        from datetime import datetime, timedelta, time as dt_time
        
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            today = timezone.now().date()

            if selected_date < today:
                return Response({
                    'available_slots': [],
                    'message': 'Cannot book appointments in the past'
                })

            weekday_name = selected_date.strftime('%A').lower()

            availabilities = Availability.objects.filter(
                participant__uid=participant_id,
                weekday=weekday_name,
                is_active=True
            )

            if not availabilities.exists():
                return Response({
                    'available_slots': [],
                    'message': f'No availability set for {weekday_name}'
                })

            existing_appointments = Appointment.objects.filter(
                Q(doctor__uid=participant_id) | Q(hospital__uid=participant_id),
                appointment_date=selected_date,
                status__in=['pending', 'confirmed', 'in_progress']
            ).values_list('appointment_time', flat=True)

            booked_times = set(existing_appointments)

            all_slots = []
            current_datetime = timezone.now()

            for availability in availabilities:
                start_time = availability.start_time
                end_time = availability.end_time
                slot_duration = availability.slot_duration

                current_slot_time = datetime.combine(selected_date, start_time)
                end_slot_time = datetime.combine(selected_date, end_time)

                while current_slot_time < end_slot_time:
                    slot_time = current_slot_time.time()
                    
                    slot_datetime = datetime.combine(selected_date, slot_time)
                    slot_datetime = timezone.make_aware(slot_datetime, timezone.get_current_timezone())

                    if slot_datetime > current_datetime and slot_time not in booked_times:
                        all_slots.append({
                            'time': slot_time.strftime('%H:%M'),
                            'available': True
                        })

                    current_slot_time += timedelta(minutes=slot_duration)

            all_slots.sort(key=lambda x: x['time'])

            return Response({
                'available_slots': all_slots,
                'date': date_str,
                'weekday': weekday_name,
                'participant_id': participant_id
            })

        except ValueError as e:
            return Response({
                'error': 'Invalid date format. Use YYYY-MM-DD'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AppointmentQueueViewSet(viewsets.ModelViewSet):  # View for AppointmentQueueSet operations
    queryset = AppointmentQueue.objects.all()
    serializer_class = AppointmentQueueSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        current_participant = self.request.user
        
        if current_participant.role == "doctor":
            return AppointmentQueue.objects.filter(
                Q(appointment__doctor=current_participant) |
                Q(provider=current_participant)
            )
        elif current_participant.role == "patient":
            return AppointmentQueue.objects.filter(appointment__patient=current_participant)
        elif current_participant.role == "hospital":
            # Hospitals can see queue for appointments at their hospital
            return AppointmentQueue.objects.filter(
                Q(appointment__facility=current_participant) |
                Q(provider=current_participant)
            )
        elif current_participant.role in ["admin", "super_admin"]:
            # Admins can see all queues
            return AppointmentQueue.objects.all()
        
        return AppointmentQueue.objects.none()
