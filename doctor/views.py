from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta, date
from django.db.models import Count, Q
import json
from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import DoctorData, DoctorAffiliation
from .serializers import DoctorDataSerializer, DoctorAffiliationSerializer
from core.models import Participant
from core.mixins import DoctorRequiredMixin


class DoctorAnalyticsView(DoctorRequiredMixin, TemplateView):
    template_name = "doctor/analytics.html"


class DoctorQueueView(LoginRequiredMixin, TemplateView):  # View for DoctorQueue operations
    template_name = 'doctor/queue.html'
    
    def get_context_data(self, **kwargs):  # Get context data
        context = super().get_context_data(**kwargs)
        context['page_title'] = "File d'attente"
        return context


@login_required
@require_http_methods(["GET"])
def doctor_patients_api(request):
    """API endpoint to get doctor's patients list"""
    from appointments.models import Appointment
    from django.db.models import Count, Max
    
    try:
        doctor = request.user
        
        # Get all appointments for this doctor
        appointments = Appointment.objects.filter(
            doctor=doctor
        ).select_related('patient').order_by('patient', '-appointment_date')
        
        # Build patient list with stats
        patient_data = {}
        for apt in appointments:
            if apt.patient:
                patient_uid = str(apt.patient.uid)
                if patient_uid not in patient_data:
                    patient_data[patient_uid] = {
                        'uid': patient_uid,
                        'full_name': apt.patient.full_name,
                        'email': apt.patient.email,
                        'phone_number': apt.patient.phone_number or '',
                        'age': calculate_age(apt.patient.date_of_birth) if hasattr(apt.patient, 'date_of_birth') and apt.patient.date_of_birth else None,
                        'gender_display': apt.patient.gender if apt.patient.gender else 'N/A',
                        'total_appointments': 0,
                        'last_visit_date': None,
                        'last_visit': 'Jamais',
                        'has_active_prescription': False
                    }
                
                patient_data[patient_uid]['total_appointments'] += 1
                
                # Update last visit
                if apt.appointment_date:
                    if not patient_data[patient_uid]['last_visit_date'] or apt.appointment_date > patient_data[patient_uid]['last_visit_date']:
                        patient_data[patient_uid]['last_visit_date'] = apt.appointment_date
                        days_ago = (date.today() - apt.appointment_date).days
                        if days_ago == 0:
                            patient_data[patient_uid]['last_visit'] = "Aujourd'hui"
                        elif days_ago == 1:
                            patient_data[patient_uid]['last_visit'] = "Hier"
                        elif days_ago < 30:
                            patient_data[patient_uid]['last_visit'] = f"Il y a {days_ago}j"
                        else:
                            patient_data[patient_uid]['last_visit'] = apt.appointment_date.strftime("%d/%m/%Y")
        
        # Check for active prescriptions
        from prescriptions.models import Prescription
        active_prescriptions = Prescription.objects.filter(
            doctor=doctor,
            patient__uid__in=patient_data.keys(),
            status='active'
        ).values_list('patient__uid', flat=True)
        
        for patient_uid in active_prescriptions:
            if str(patient_uid) in patient_data:
                patient_data[str(patient_uid)]['has_active_prescription'] = True
        
        patients_list = sorted(
            patient_data.values(),
            key=lambda x: x['last_visit_date'] if x['last_visit_date'] else date.min,
            reverse=True
        )
        
        # Calculate stats
        thirty_days_ago = date.today() - timedelta(days=30)
        active_patients = sum(1 for p in patients_list if p['last_visit_date'] and p['last_visit_date'] >= thirty_days_ago)
        total_consultations = sum(p['total_appointments'] for p in patients_list)
        avg_consultations = total_consultations / len(patients_list) if patients_list else 0
        
        return JsonResponse({
            'success': True,
            'patients': patients_list,
            'stats': {
                'total': len(patients_list),
                'active': active_patients,
                'consultations': total_consultations,
                'average': round(avg_consultations, 1)
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def doctor_consultations_api(request):
    """API endpoint to get doctor's consultations with filtering"""
    from appointments.models import Appointment, AppointmentQueue
    
    try:
        doctor = request.user
        today = date.today()
        
        # Get waiting consultations (in queue)
        waiting_queue = AppointmentQueue.objects.filter(
            provider=doctor,
            status='waiting'
        ).select_related('appointment__patient').order_by('queue_number')
        
        waiting_consultations = []
        for queue_entry in waiting_queue:
            if queue_entry.appointment and queue_entry.appointment.patient:
                waiting_consultations.append({
                    'id': str(queue_entry.appointment.id),
                    'patient_uid': str(queue_entry.appointment.patient.uid),
                    'patient_name': queue_entry.appointment.patient.full_name,
                    'date': queue_entry.appointment.appointment_date.strftime('%d/%m/%Y'),
                    'time': queue_entry.appointment.appointment_time.strftime('%H:%M'),
                    'duration': 30,
                    'type': queue_entry.appointment.get_type_display(),
                    'reason': queue_entry.appointment.reason or '',
                    'status': 'waiting',
                    'queue_position': queue_entry.queue_number
                })
        
        # Get scheduled consultations
        scheduled_appointments = Appointment.objects.filter(
            doctor=doctor,
            status='confirmed',
            appointment_date__gte=today
        ).select_related('patient').order_by('appointment_date', 'appointment_time')
        
        scheduled_consultations = []
        for apt in scheduled_appointments:
            if apt.patient:
                scheduled_consultations.append({
                    'id': str(apt.id),
                    'patient_uid': str(apt.patient.uid),
                    'patient_name': apt.patient.full_name,
                    'date': apt.appointment_date.strftime('%d/%m/%Y'),
                    'time': apt.appointment_time.strftime('%H:%M') if apt.appointment_time else '',
                    'duration': 30,
                    'type': apt.get_type_display(),
                    'reason': apt.reason or '',
                    'status': 'scheduled'
                })
        
        # Get in-progress consultations
        in_progress_appointments = Appointment.objects.filter(
            doctor=doctor,
            status='in_progress'
        ).select_related('patient').order_by('appointment_date', 'appointment_time')
        
        in_progress_consultations = []
        for apt in in_progress_appointments:
            if apt.patient:
                in_progress_consultations.append({
                    'id': str(apt.id),
                    'patient_uid': str(apt.patient.uid),
                    'patient_name': apt.patient.full_name,
                    'date': apt.appointment_date.strftime('%d/%m/%Y'),
                    'time': apt.appointment_time.strftime('%H:%M') if apt.appointment_time else '',
                    'duration': 30,
                    'type': apt.get_type_display(),
                    'reason': apt.reason or '',
                    'status': 'in-progress'
                })
        
        # Get completed consultations (last 20)
        completed_appointments = Appointment.objects.filter(
            doctor=doctor,
            status='completed'
        ).select_related('patient').order_by('-appointment_date', '-appointment_time')[:20]
        
        completed_consultations = []
        for apt in completed_appointments:
            if apt.patient:
                completed_consultations.append({
                    'id': str(apt.id),
                    'patient_uid': str(apt.patient.uid),
                    'patient_name': apt.patient.full_name,
                    'date': apt.appointment_date.strftime('%d/%m/%Y'),
                    'time': apt.appointment_time.strftime('%H:%M') if apt.appointment_time else '',
                    'duration': 30,
                    'type': apt.get_type_display(),
                    'reason': apt.reason or '',
                    'status': 'completed'
                })
        
        # Combine all consultations
        all_consultations = (
            waiting_consultations +
            scheduled_consultations +
            in_progress_consultations +
            completed_consultations
        )
        
        return JsonResponse({
            'success': True,
            'consultations': all_consultations,
            'counts': {
                'waiting': len(waiting_consultations),
                'scheduled': len(scheduled_consultations),
                'in_progress': len(in_progress_consultations),
                'completed': len(completed_consultations)
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def call_patient_api(request):
    """API endpoint to call a patient (send notification)"""
    from appointments.models import Appointment
    from communication.models import Notification
    
    try:
        data = json.loads(request.body)
        consultation_id = data.get('consultation_id')
        
        if not consultation_id:
            return JsonResponse({
                'success': False,
                'message': 'ID de consultation requis'
            }, status=400)
        
        appointment = Appointment.objects.select_related('patient').get(
            id=consultation_id,
            doctor=request.user
        )
        
        # Update appointment status to in_progress
        appointment.status = 'in_progress'
        appointment.save()
        
        # Send notification to patient
        if appointment.patient:
            Notification.objects.create(
                participant=appointment.patient,
                title="Le docteur vous appelle",
                message=f"Dr. {request.user.full_name} vous demande de venir pour votre consultation.",
                notification_type='appointment',
                priority='high'
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Notification envoyée au patient'
        })
    except Appointment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Consultation non trouvée'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def complete_consultation_api(request):
    """API endpoint to mark consultation as completed"""
    from appointments.models import Appointment
    
    try:
        data = json.loads(request.body)
        consultation_id = data.get('consultation_id')
        
        if not consultation_id:
            return JsonResponse({
                'success': False,
                'message': 'ID de consultation requis'
            }, status=400)
        
        appointment = Appointment.objects.get(
            id=consultation_id,
            doctor=request.user
        )
        
        appointment.status = 'completed'
        appointment.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Consultation terminée'
        })
    except Appointment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Consultation non trouvée'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


def calculate_age(birth_date):
    """Calculate age from birth date"""
    if not birth_date:
        return None
    today = date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age


class DoctorDataViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for DoctorData
    Provides list, retrieve, create, update, and delete operations for doctors
    """
    serializer_class = DoctorDataSerializer
    permission_classes = [AllowAny]  # Public endpoint for listing doctors

    def get_queryset(self):  # Get queryset
        # Show all active doctors for public listing
        queryset = DoctorData.objects.select_related("participant").filter(
            participant__is_active=True
        )

        # Filter by specialty
        specialty = self.request.query_params.get("specialty")
        if specialty:
            queryset = queryset.filter(specialization=specialty)

        # Filter by telemedicine availability
        telemedicine = self.request.query_params.get("telemedicine")
        if telemedicine == "true":
            queryset = queryset.filter(is_available_for_telemedicine=True)

        # Show verified doctors first, then by rating
        return queryset.order_by("-participant__is_verified", "-rating", "consultation_fee")


class DoctorAffiliationViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for managing doctor-hospital affiliations
    """
    serializer_class = DoctorAffiliationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        user = self.request.user
        if user.role == 'doctor':
            return DoctorAffiliation.objects.filter(doctor=user, is_active=True).select_related('hospital')
        elif user.role == 'hospital':
            return DoctorAffiliation.objects.filter(hospital=user, is_active=True).select_related('doctor')
        return DoctorAffiliation.objects.none()

    def perform_create(self, serializer):  # Perform create
        user = self.request.user

        # Only independent doctors can create affiliations
        if user.affiliated_provider_id:
            raise serializers.ValidationError({
                'detail': 'Hospital staff doctors cannot manage their own affiliations'
            })

        hospital_id = self.request.data.get('hospital_id')
        if not hospital_id:
            raise serializers.ValidationError({'hospital_id': 'Hospital ID is required'})

        try:
            hospital = Participant.objects.get(uid=hospital_id, role='hospital')
        except Participant.DoesNotExist:
            raise serializers.ValidationError({'hospital_id': 'Hospital not found'})

        # Check if affiliation already exists
        existing = DoctorAffiliation.objects.filter(
            doctor=user,
            hospital=hospital,
            is_active=True
        ).exists()

        if existing:
            raise serializers.ValidationError({
                'detail': 'You are already affiliated with this hospital'
            })

        # If this is being set as primary, remove primary from others
        if self.request.data.get('is_primary'):
            DoctorAffiliation.objects.filter(doctor=user, is_primary=True).update(is_primary=False)

        serializer.save(doctor=user, hospital=hospital, is_locked=False)

    def perform_destroy(self, instance):  # Perform destroy
        # Prevent deletion of locked affiliations
        if instance.is_locked:
            raise serializers.ValidationError({
                'detail': 'Cannot remove locked affiliations'
            })

        # Soft delete
        instance.is_active = False
        instance.end_date = timezone.now()
        instance.save()

    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        """Set this affiliation as primary"""
        affiliation = self.get_object()

        if affiliation.is_locked:
            return Response(
                {'detail': 'Cannot modify locked affiliations'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Remove primary from all other affiliations
        DoctorAffiliation.objects.filter(
            doctor=request.user,
            is_primary=True
        ).update(is_primary=False)

        # Set this one as primary
        affiliation.is_primary = True
        affiliation.save()

        return Response({'message': 'Primary affiliation updated successfully'})

