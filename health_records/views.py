from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from django.utils import timezone
from datetime import timedelta
from .models import *
from .serializers import *
import logging
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from datetime import datetime

logger = logging.getLogger(__name__)


class HealthRecordViewSet(viewsets.ModelViewSet):  # View for HealthRecordSet operations
    serializer_class = HealthRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        participant = self.request.user
        if getattr(self, 'swagger_fake_view', False):
            return HealthRecord.objects.none()
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
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download a single health record as PDF"""
        record = self.get_object()
        
        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph(f"<b>Dossier Médical: {record.title}</b>", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 0.2*inch))
        
        # Patient info
        if record.assigned_to:
            patient_info = [
                ["Patient:", record.assigned_to.full_name],
                ["Date de naissance:", record.assigned_to.date_of_birth.strftime('%d/%m/%Y') if record.assigned_to.date_of_birth else "N/A"],
                ["Sexe:", record.assigned_to.gender or "N/A"],
            ]
            patient_table = Table(patient_info, colWidths=[2*inch, 4*inch])
            patient_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(patient_table)
            story.append(Spacer(1, 0.3*inch))
        
        # Record details
        record_info = [
            ["Type:", record.type],
            ["Date:", record.date_of_record.strftime('%d/%m/%Y')],
            ["Créé par:", record.created_by.full_name if record.created_by else "N/A"],
            ["Créé le:", record.created_at.strftime('%d/%m/%Y %H:%M')],
        ]
        record_table = Table(record_info, colWidths=[2*inch, 4*inch])
        record_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(record_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Diagnosis
        if record.diagnosis:
            story.append(Paragraph("<b>Diagnostic:</b>", styles['Heading2']))
            story.append(Paragraph(record.diagnosis, styles['BodyText']))
            story.append(Spacer(1, 0.2*inch))
        
        # Symptoms
        if record.symptoms:
            story.append(Paragraph("<b>Symptômes:</b>", styles['Heading2']))
            story.append(Paragraph(record.symptoms, styles['BodyText']))
            story.append(Spacer(1, 0.2*inch))
        
        # Treatment
        if record.treatment:
            story.append(Paragraph("<b>Traitement:</b>", styles['Heading2']))
            story.append(Paragraph(record.treatment, styles['BodyText']))
            story.append(Spacer(1, 0.2*inch))
        
        # Medications
        if record.medications:
            story.append(Paragraph("<b>Médicaments:</b>", styles['Heading2']))
            story.append(Paragraph(record.medications, styles['BodyText']))
            story.append(Spacer(1, 0.2*inch))
        
        # Notes
        if record.notes:
            story.append(Paragraph("<b>Notes:</b>", styles['Heading2']))
            story.append(Paragraph(record.notes, styles['BodyText']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Return PDF response
        response = FileResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="dossier_{record.id}_{datetime.now().strftime("%Y%m%d")}.pdf"'
        return response
    
    @action(detail=False, methods=['get'])
    def download_all(self, request):
        """Download all health records as a combined PDF"""
        records = self.get_queryset().order_by('-date_of_record')
        
        if not records.exists():
            return Response({"detail": "Aucun dossier à télécharger"}, status=status.HTTP_404_NOT_FOUND)
        
        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Main title
        title = Paragraph("<b>Carnet de Santé Complet</b>", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 0.2*inch))
        
        # Patient info (from first record)
        first_record = records.first()
        if first_record.assigned_to:
            patient_info = Paragraph(
                f"<b>Patient:</b> {first_record.assigned_to.full_name}<br/>"
                f"<b>Date de génération:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                styles['Normal']
            )
            story.append(patient_info)
            story.append(Spacer(1, 0.3*inch))
        
        # Add each record
        for i, record in enumerate(records, 1):
            # Record header
            story.append(Paragraph(f"<b>{i}. {record.title}</b>", styles['Heading2']))
            story.append(Spacer(1, 0.1*inch))
            
            # Record details
            details = f"""
                <b>Type:</b> {record.type}<br/>
                <b>Date:</b> {record.date_of_record.strftime('%d/%m/%Y')}<br/>
                <b>Créé par:</b> {record.created_by.full_name if record.created_by else 'N/A'}<br/>
            """
            if record.diagnosis:
                details += f"<b>Diagnostic:</b> {record.diagnosis}<br/>"
            if record.symptoms:
                details += f"<b>Symptômes:</b> {record.symptoms}<br/>"
            if record.treatment:
                details += f"<b>Traitement:</b> {record.treatment}<br/>"
            if record.medications:
                details += f"<b>Médicaments:</b> {record.medications}<br/>"
            if record.notes:
                details += f"<b>Notes:</b> {record.notes}"
            
            story.append(Paragraph(details, styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Return PDF response
        response = FileResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="carnet_sante_{datetime.now().strftime("%Y%m%d")}.pdf"'
        return response


# NOTE: Wearable device viewsets have been moved to the wearable_devices app
# Import them from there if needed:
# from wearable_devices.views import WearableDeviceViewSet, WearableDataViewSet


class DocumentUploadViewSet(viewsets.ModelViewSet):
    """ViewSet for document uploads"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return DocumentUpload.objects.none()
        return DocumentUpload.objects.filter(uploaded_by=self.request.user)
    
    def get_serializer_class(self):
        # You'll need to create a serializer for DocumentUpload
        from rest_framework import serializers
        
        class DocumentUploadSerializer(serializers.ModelSerializer):
            class Meta:
                model = DocumentUpload
                fields = '__all__'
                read_only_fields = ['uploaded_by', 'uploaded_at']
        
        return DocumentUploadSerializer
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download a document"""
        document = self.get_object()
        
        if document.file:
            response = FileResponse(document.file.open('rb'), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{document.file_name}"'
            return response
        
        return Response({"detail": "Fichier non trouvé"}, status=status.HTTP_404_NOT_FOUND)


class PersonalHealthNoteViewSet(viewsets.ModelViewSet):
    """ViewSet for personal health notes/journal entries"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return PersonalHealthNote.objects.none()
        # Only show notes belonging to the current user
        return PersonalHealthNote.objects.filter(patient=self.request.user).order_by('-note_date', '-created_at')
    
    def get_serializer_class(self):
        from rest_framework import serializers
        
        class PersonalHealthNoteSerializer(serializers.ModelSerializer):
            class Meta:
                model = PersonalHealthNote
                fields = ['id', 'title', 'content', 'category', 'note_date', 'tags', 'created_at', 'updated_at']
                read_only_fields = ['created_at', 'updated_at']
            
            def validate_tags(self, value):
                # Convert tags string to list if necessary
                if isinstance(value, str):
                    import json
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        # If it's a comma-separated string
                        return [tag.strip() for tag in value.split(',') if tag.strip()]
                return value
        
        return PersonalHealthNoteSerializer
    
    def perform_create(self, serializer):
        serializer.save(patient=self.request.user)
    
    def perform_update(self, serializer):
        # Only allow the owner to update their notes
        instance = self.get_object()
        if instance.patient != self.request.user:
            raise PermissionError('Vous ne pouvez modifier que vos propres notes')
        serializer.save()
    
    def destroy(self, request, *args, **kwargs):
        # Only allow the owner to delete their notes
        instance = self.get_object()
        if instance.patient != self.request.user:
            return Response(
                {'detail': 'Vous ne pouvez supprimer que vos propres notes'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)
