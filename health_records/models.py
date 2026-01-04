from django.db import models
from django.utils import timezone
import uuid
from core.models import Participant
from core.mixins import SyncMixin

class HealthRecord(SyncMixin):  # Stores patient health records and medical documents
    TYPE_CHOICES = [
        ('lab_result', 'Lab Result'),
        ('prescription', 'Prescription'),
        ('diagnosis', 'Diagnosis'),
        ('imaging', 'Imaging'),
        ('vaccination', 'Vaccination'),
        ('allergy', 'Allergy'),
        ('surgery', 'Surgery'),
        ('visit_summary', 'Visit Summary'),
        ('referral', 'Referral'),
        ('discharge_summary', 'Discharge Summary'),
    ]

    participants = models.JSONField(default=list)
    created_by = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, related_name='created_health_records')
    assigned_to = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='health_records')

    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    diagnosis = models.TextField(blank=True)
    symptoms = models.TextField(blank=True)
    treatment = models.TextField(blank=True)
    medications = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    file_url = models.URLField(blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    is_patient_uploaded = models.BooleanField(default=False)

    is_encrypted = models.BooleanField(default=False)
    encrypted_data = models.TextField(blank=True)

    date_of_record = models.DateField()
    
    # Vital signs entered by doctor during consultation
    blood_pressure_systolic = models.IntegerField(null=True, blank=True, help_text="Systolic BP in mmHg")
    blood_pressure_diastolic = models.IntegerField(null=True, blank=True, help_text="Diastolic BP in mmHg")
    heart_rate = models.IntegerField(null=True, blank=True, help_text="Heart rate in bpm")
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, help_text="Temperature in °C")
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Weight in kg")

    class Meta:  # Meta class implementation
        db_table = 'health_records'
        ordering = ['-date_of_record']
        indexes = [
            models.Index(fields=['assigned_to', 'type']),
            models.Index(fields=['created_by']),
            models.Index(fields=['date_of_record']),
        ]

# NOTE: Wearable device models have been moved to the wearable_devices app
# Import them from there if needed:
# from wearable_devices.models import WearableDevice, WearableData

# NOTE: MenstrualCycle model has been moved to the menstruation app
# Import it from there if needed: from menstruation.models import MenstrualCycle

class DocumentUpload(SyncMixin):  # Manages uploaded medical documents and verification status
    DOCUMENT_TYPE_CHOICES = [
        ('prescription', 'Prescription'),
        ('medical_record', 'Medical Record'),
        ('insurance_document', 'Insurance Document'),
        ('lab_result', 'Lab Result'),
        ('imaging', 'Imaging'),
        ('id_card', 'ID Card'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    uploaded_by = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='uploaded_documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    file_url = models.URLField()
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField()
    mime_type = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    description = models.TextField(blank=True)
    verified_by = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_documents')
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now)
    
    # Sharing and encryption
    is_shareable = models.BooleanField(default=True, help_text="Can this document be shared?")
    share_count = models.IntegerField(default=0, help_text="Number of times shared")

    class Meta:  # Meta class implementation
        db_table = 'document_uploads'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['uploaded_by', 'status']),
            models.Index(fields=['document_type']),
        ]


class DocumentShare(SyncMixin):
    """Tracks document sharing between participants"""
    PERMISSION_CHOICES = [
        ('view', 'View Only'),
        ('download', 'View & Download'),
        ('edit', 'View, Download & Edit'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('revoked', 'Revoked'),
        ('expired', 'Expired'),
    ]
    
    document = models.ForeignKey(DocumentUpload, on_delete=models.CASCADE, related_name='shares')
    shared_by = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='documents_shared')
    shared_with = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='documents_received')
    permission_level = models.CharField(max_length=20, choices=PERMISSION_CHOICES, default='view')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    message = models.TextField(blank=True, help_text="Optional message to recipient")
    expires_at = models.DateTimeField(null=True, blank=True, help_text="When this share expires")
    
    shared_at = models.DateTimeField(auto_now_add=True)
    accessed_at = models.DateTimeField(null=True, blank=True, help_text="When recipient first accessed")
    revoked_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'document_shares'
        ordering = ['-shared_at']
        unique_together = [['document', 'shared_with']]
        indexes = [
            models.Index(fields=['shared_by', 'status']),
            models.Index(fields=['shared_with', 'status']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.document.file_name} shared with {self.shared_with.full_name}"
    
    def is_active(self):
        """Check if share is still valid"""
        if self.status not in ['accepted', 'pending']:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            self.status = 'expired'
            self.save()
            return False
        return True
    
    def mark_accessed(self):
        """Record when recipient first accesses the document"""
        if not self.accessed_at:
            self.accessed_at = timezone.now()
            if self.status == 'pending':
                self.status = 'accepted'
            self.save()

class TelemedicineSession(SyncMixin):  # Manages video consultation sessions between doctors and patients
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
    ]

    appointment = models.OneToOneField('appointments.Appointment', on_delete=models.CASCADE, related_name='telemedicine_session', null=True, blank=True)
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='patient_sessions')
    doctor = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='doctor_sessions')
    session_id = models.CharField(max_length=255, unique=True)
    room_id = models.CharField(max_length=255)
    access_token = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    scheduled_start_time = models.DateTimeField()
    actual_start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=0)
    recording_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:  # Meta class implementation
        db_table = 'telemedicine_sessions'
        ordering = ['-scheduled_start_time']
