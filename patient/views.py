from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.db import models
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from .models import PatientData, DependentProfile, PreventiveCareReminder, PersonalHealthNote
from .serializers import PatientDataSerializer, DependentProfileSerializer, PreventiveCareReminderSerializer, PersonalHealthNoteSerializer
from prescriptions.models import Prescription
from prescriptions.serializers import PrescriptionSerializer
from appointments.models import Appointment


class PatientDataViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for PatientData
    Authenticated users can only access their own patient data
    """
    queryset = PatientData.objects.all()
    serializer_class = PatientDataSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        # Users can only see their own patient data
        if getattr(self, 'swagger_fake_view', False):
            return PatientData.objects.none()
        if self.request.user.role == "patient":
            return PatientData.objects.filter(participant=self.request.user)
        # Staff/admin can see all
        elif self.request.user.is_staff:
            return PatientData.objects.all()
        return PatientData.objects.none()


class DependentProfileViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for DependentProfile
    Patients can manage their own dependents
    """
    queryset = DependentProfile.objects.all()
    serializer_class = DependentProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        # Users can only see their own dependents
        if getattr(self, 'swagger_fake_view', False):
            return DependentProfile.objects.none()
        if self.request.user.role == "patient":
            return DependentProfile.objects.filter(
                patient=self.request.user, is_active=True
            )
        # Staff/admin can see all
        elif self.request.user.is_staff:
            return DependentProfile.objects.all()
        return DependentProfile.objects.none()

    def perform_create(self, serializer):  # Perform create
        # Automatically set the patient to the current user
        serializer.save(patient=self.request.user)


@extend_schema(tags=["Patient Prescriptions"])
class PrescriptionsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PrescriptionSerializer

    @extend_schema(
        summary="Get patient prescriptions",
        responses={200: PrescriptionSerializer}
    )
    def get(self, request):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"PrescriptionsAPIView called for user: {request.user.email}")
        logger.info(f"User role: {request.user.role}")

        if request.user.role != 'patient':
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

        prescriptions = Prescription.objects.filter(patient=request.user).prefetch_related('items', 'items__medication', 'doctor')
        logger.info(f"Found {prescriptions.count()} prescriptions")

        serializer = PrescriptionSerializer(prescriptions, many=True, context={'request': request})
        return Response({'results': serializer.data}, status=status.HTTP_200_OK)


@method_decorator(login_required, name='dispatch')
class MyAppointmentsView(TemplateView):
    """
    View for displaying patient's appointments
    """
    template_name = 'patient/my_appointments.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get appointments for the current patient
        appointments = Appointment.objects.filter(
            patient=self.request.user
        ).select_related(
            'doctor', 'hospital'
        ).order_by('-appointment_date', '-appointment_time')
        
        context['appointments'] = appointments
        context['upcoming_appointments'] = appointments.filter(
            status__in=['scheduled', 'confirmed']
        )
        context['past_appointments'] = appointments.filter(
            status__in=['completed', 'cancelled']
        )
        
        return context


class PreventiveCareReminderViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for Preventive Care Reminders
    Patients can manage their preventive care reminders
    """
    queryset = PreventiveCareReminder.objects.all()
    serializer_class = PreventiveCareReminderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return PreventiveCareReminder.objects.none()
        if self.request.user.role == "patient":
            return PreventiveCareReminder.objects.filter(patient=self.request.user)
        elif self.request.user.is_staff:
            return PreventiveCareReminder.objects.all()
        return PreventiveCareReminder.objects.none()

    def perform_create(self, serializer):
        serializer.save(patient=self.request.user)


class PersonalHealthNoteViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for Personal Health Notes
    Patients can manage their personal health journal
    """
    queryset = PersonalHealthNote.objects.all()
    serializer_class = PersonalHealthNoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return PersonalHealthNote.objects.none()
        if self.request.user.role == "patient":
            queryset = PersonalHealthNote.objects.filter(patient=self.request.user)
            # Filter by category if provided
            category = self.request.query_params.get('category', None)
            if category:
                queryset = queryset.filter(category=category)
            # Search by title/content if provided
            search = self.request.query_params.get('search', None)
            if search:
                queryset = queryset.filter(
                    models.Q(title__icontains=search) | models.Q(content__icontains=search)
                )
            return queryset
        elif self.request.user.is_staff:
            return PersonalHealthNote.objects.all()
        return PersonalHealthNote.objects.none()

    def perform_create(self, serializer):
        serializer.save(patient=self.request.user)


@method_decorator(login_required, name='dispatch')
class PreventiveRemindersView(TemplateView):
    """View for displaying preventive care reminders"""
    template_name = 'patient/preventive_reminders.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.role == 'patient':
            reminders = PreventiveCareReminder.objects.filter(patient=self.request.user)
            context['upcoming_reminders'] = reminders.filter(is_completed=False)
            context['completed_reminders'] = reminders.filter(is_completed=True)
        return context


@method_decorator(login_required, name='dispatch')
class HealthJournalView(TemplateView):
    """View for displaying personal health notes"""
    template_name = 'patient/health_journal.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.role == 'patient':
            notes = PersonalHealthNote.objects.filter(patient=self.request.user)
            context['notes'] = notes
            context['categories'] = PersonalHealthNote.CATEGORY_CHOICES
        return context


@method_decorator(login_required, name='dispatch')
class WearableDevicesView(TemplateView):
    """View for managing wearable devices"""
    template_name = 'health_records/wearable_devices.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


