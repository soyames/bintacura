from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render
from .models import *
from .serializers import *
import logging

logger = logging.getLogger(__name__)


class HealthRecordViewSet(viewsets.ModelViewSet):  # View for HealthRecordSet operations
    serializer_class = HealthRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        participant = self.request.user
        if participant.role == 'patient':
            return HealthRecord.objects.filter(assigned_to=participant)
        elif participant.role == 'doctor' or participant.role == 'hospital':
            from appointments.models import Appointment
            from django.db.models import Q

            # Get records for patients the doctor/hospital has appointments with
            patient_ids = Appointment.objects.filter(doctor=participant).values_list('patient_id', flat=True).distinct()

            # Build query: records created by this user OR where they are in participants list
            queryset = HealthRecord.objects.filter(
                Q(assigned_to_id__in=patient_ids) |
                Q(participants__contains=[str(participant.uid)])
            )

            assigned_to_param = self.request.query_params.get('assigned_to')
            if assigned_to_param:
                queryset = queryset.filter(assigned_to__uid=assigned_to_param)

            return queryset
        return HealthRecord.objects.none()

    def get_serializer_context(self):  # Pass request context to serializer
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):  # Control access to record details
        instance = self.get_object()
        participant = request.user

        # Check if participant is in participants list (for referrals)
        participant_in_list = str(participant.uid) in instance.participants if instance.participants else False

        # If doctor/hospital is NOT the creator AND NOT in participants list, show limited info
        if (participant.role == 'doctor' or participant.role == 'hospital') and instance.created_by_id != participant.uid and not participant_in_list:
            return Response({
                'id': instance.id,
                'title': instance.title,
                'type': instance.type,
                'date_of_record': instance.date_of_record,
                'created_by_name': instance.created_by.full_name if instance.created_by else 'Unknown',
                'created_by_contact': {
                    'email': instance.created_by.email if instance.created_by else '',
                    'phone': instance.created_by.phone_number if instance.created_by else ''
                },
                'can_view_details': False,
                'message': 'Contactez le médecin qui a créé ce dossier pour plus de détails'
            })
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):  # Override create to add error logging
        try:
            logger.info(f"Creating health record - User: {request.user.uid}, Role: {request.user.role}")
            logger.info(f"Request data: {request.data}")
            return super().create(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error creating health record: {str(e)}", exc_info=True)
            return Response(
                {'detail': f'Error creating record: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):  # Set created_by when creating record
        participant = self.request.user
        assigned_to_participant = serializer.validated_data.get('assigned_to')

        logger.info(f"Performing create - Doctor: {participant.uid}, Patient: {assigned_to_participant.uid if assigned_to_participant else 'None'}")

        # Doctors and hospitals can create records for their patients
        if participant.role in ['doctor', 'hospital']:
            from appointments.models import Appointment

            # Check if doctor/hospital has at least one appointment with this patient
            has_appointment = Appointment.objects.filter(
                doctor=participant,
                patient=assigned_to_participant
            ).exists()

            if not has_appointment:
                logger.warning(f"Doctor {participant.uid} creating record for patient {assigned_to_participant.uid} without appointment history")
                # Allow creation anyway - doctor may be receiving referral or creating initial record
                pass

        try:
            instance = serializer.save(created_by=participant)
            logger.info(f"Successfully created health record: {instance.id}")
        except Exception as e:
            logger.error(f"Error saving health record: {str(e)}", exc_info=True)
            raise

    def perform_update(self, serializer):  # Only allow creator to update
        instance = self.get_object()
        if self.request.user.uid != instance.created_by_id:
            raise PermissionError('Seul le médecin créateur peut modifier ce dossier')
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        return Response({'detail': 'Les dossiers médicaux ne peuvent pas être supprimés'}, status=status.HTTP_403_FORBIDDEN)


class WearableDataViewSet(viewsets.ModelViewSet):  # View for WearableDataSet operations
    serializer_class = WearableDataSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        return WearableData.objects.filter(patient=self.request.user)
