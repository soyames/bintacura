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

    class Meta:  # Meta class implementation
        db_table = 'health_records'
        ordering = ['-date_of_record']
        indexes = [
            models.Index(fields=['assigned_to', 'type']),
            models.Index(fields=['created_by']),
            models.Index(fields=['date_of_record']),
        ]

class WearableDevice(SyncMixin):  # Manages patient wearable health devices and connections
    DEVICE_TYPE_CHOICES = [
        ('smartwatch', 'Smartwatch'),
        ('fitness_tracker', 'Fitness Tracker'),
        ('smart_ring', 'Smart Ring'),
        ('blood_pressure_monitor', 'Blood Pressure Monitor'),
        ('glucose_monitor', 'Glucose Monitor'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('disconnected', 'Disconnected'),
    ]

    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='wearable_devices')
    device_id = models.CharField(max_length=255, unique=True)
    device_name = models.CharField(max_length=255)
    device_type = models.CharField(max_length=50, choices=DEVICE_TYPE_CHOICES)
    manufacturer = models.CharField(max_length=255, blank=True)
    model = models.CharField(max_length=255, blank=True)
    firmware_version = models.CharField(max_length=50, blank=True)
    battery_level = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_connected = models.BooleanField(default=False)
    last_sync_time = models.DateTimeField(null=True, blank=True)
    paired_at = models.DateTimeField(default=timezone.now)

    class Meta:  # Meta class implementation
        db_table = 'wearable_devices'
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['device_id']),
        ]

class WearableData(SyncMixin):  # Stores health data collected from wearable devices
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='wearable_data')
    device = models.ForeignKey(WearableDevice, on_delete=models.CASCADE, related_name='data_points', null=True, blank=True)
    device_name = models.CharField(max_length=255)
    device_type = models.CharField(max_length=50)

    steps = models.IntegerField(null=True, blank=True)
    distance = models.FloatField(null=True, blank=True)
    calories = models.IntegerField(null=True, blank=True)
    heart_rate = models.IntegerField(null=True, blank=True)
    blood_oxygen = models.FloatField(null=True, blank=True)
    stress_level = models.IntegerField(null=True, blank=True)

    sleep_duration = models.IntegerField(null=True, blank=True)
    sleep_quality = models.CharField(max_length=50, blank=True)
    deep_sleep = models.IntegerField(null=True, blank=True)
    light_sleep = models.IntegerField(null=True, blank=True)
    rem_sleep = models.IntegerField(null=True, blank=True)

    timestamp = models.DateTimeField()
    synced_at = models.DateTimeField(default=timezone.now)

    class Meta:  # Meta class implementation
        db_table = 'wearable_data'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['patient', 'timestamp']),
            models.Index(fields=['device', 'timestamp']),
        ]

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

    class Meta:  # Meta class implementation
        db_table = 'document_uploads'
        ordering = ['-uploaded_at']

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
