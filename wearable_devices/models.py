from django.db import models
from django.contrib.postgres.fields import JSONField
from core.mixins import SyncMixin
from core.models import Participant
from cryptography.fernet import Fernet
from django.conf import settings
import base64


class WearableDevice(SyncMixin):
    """Model to store connected wearable devices"""
    
    DEVICE_TYPES = [
        ('google_fit', 'Google Fit'),
        ('apple_health', 'Apple Health'),
        ('fitbit', 'Fitbit'),
        ('garmin', 'Garmin'),
        ('samsung_health', 'Samsung Health'),
        ('whoop', 'Whoop'),
        ('oura', 'Oura Ring'),
        ('polar', 'Polar'),
        ('suunto', 'Suunto'),
        ('strava', 'Strava'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('pending', 'Pending'),
        ('paused', 'Paused'),
        ('disconnected', 'Disconnected'),
        ('error', 'Error'),
    ]
    
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='wearable_devices')
    device_type = models.CharField(max_length=50, choices=DEVICE_TYPES)
    device_name = models.CharField(max_length=200)
    device_id = models.CharField(max_length=200, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # OAuth tokens (encrypted)
    access_token_encrypted = models.TextField(null=True, blank=True)
    refresh_token_encrypted = models.TextField(null=True, blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Device metadata
    last_sync = models.DateTimeField(null=True, blank=True)
    sync_frequency = models.IntegerField(default=60, help_text="Sync frequency in minutes")
    
    # Settings
    auto_sync_enabled = models.BooleanField(default=True)
    data_types_enabled = models.JSONField(default=dict, help_text="Which data types to sync")
    
    class Meta:
        db_table = 'wearable_devices'
        constraints = [
            models.UniqueConstraint(
                fields=['patient', 'device_type'],
                condition=models.Q(status='active'),
                name='unique_active_device_per_patient'
            )
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.get_device_type_display()}"
    
    @property
    def access_token(self):
        """Decrypt and return access token"""
        if not self.access_token_encrypted:
            return None
        cipher = Fernet(settings.ENCRYPTION_KEY.encode())
        return cipher.decrypt(self.access_token_encrypted.encode()).decode()
    
    @access_token.setter
    def access_token(self, value):
        """Encrypt and store access token"""
        if value:
            cipher = Fernet(settings.ENCRYPTION_KEY.encode())
            self.access_token_encrypted = cipher.encrypt(value.encode()).decode()
        else:
            self.access_token_encrypted = None
    
    @property
    def refresh_token(self):
        """Decrypt and return refresh token"""
        if not self.refresh_token_encrypted:
            return None
        cipher = Fernet(settings.ENCRYPTION_KEY.encode())
        return cipher.decrypt(self.refresh_token_encrypted.encode()).decode()
    
    @refresh_token.setter
    def refresh_token(self, value):
        """Encrypt and store refresh token"""
        if value:
            cipher = Fernet(settings.ENCRYPTION_KEY.encode())
            self.refresh_token_encrypted = cipher.encrypt(value.encode()).decode()
        else:
            self.refresh_token_encrypted = None


class WearableData(SyncMixin):
    """Model to store wearable device data"""
    
    DATA_TYPES = [
        ('heart_rate', 'Heart Rate'),
        ('steps', 'Steps'),
        ('distance', 'Distance'),
        ('calories', 'Calories'),
        ('sleep', 'Sleep'),
        ('blood_pressure', 'Blood Pressure'),
        ('blood_oxygen', 'Blood Oxygen (SpO2)'),
        ('body_temperature', 'Body Temperature'),
        ('weight', 'Weight'),
        ('bmi', 'BMI'),
        ('body_fat', 'Body Fat Percentage'),
        ('exercise', 'Exercise/Activity'),
        ('stress', 'Stress Level'),
        ('hydration', 'Hydration'),
        ('nutrition', 'Nutrition'),
        ('menstruation', 'Menstruation'),
        ('respiratory_rate', 'Respiratory Rate'),
        ('vo2_max', 'VO2 Max'),
        ('hrv', 'Heart Rate Variability'),
    ]
    
    device = models.ForeignKey(WearableDevice, on_delete=models.CASCADE, related_name='data_points')
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='wearable_data')
    
    data_type = models.CharField(max_length=50, choices=DATA_TYPES)
    timestamp = models.DateTimeField()
    value = models.FloatField(null=True, blank=True)
    unit = models.CharField(max_length=50, null=True, blank=True)
    
    # Additional metadata
    metadata = models.JSONField(default=dict, help_text="Additional data points and context")
    source_id = models.CharField(max_length=200, null=True, blank=True, help_text="Original ID from source")
    
    class Meta:
        db_table = 'wearable_data'
        indexes = [
            models.Index(fields=['patient', 'data_type', 'timestamp']),
            models.Index(fields=['device', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.get_data_type_display()} - {self.timestamp}"


class WearableSyncLog(SyncMixin):
    """Model to track sync history and errors"""
    
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('partial', 'Partial Success'),
        ('failed', 'Failed'),
    ]
    
    device = models.ForeignKey(WearableDevice, on_delete=models.CASCADE, related_name='sync_logs')
    sync_started_at = models.DateTimeField(auto_now_add=True)
    sync_completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    records_fetched = models.IntegerField(default=0)
    records_stored = models.IntegerField(default=0)
    errors = models.JSONField(default=list, help_text="List of errors encountered")
    
    class Meta:
        db_table = 'wearable_sync_logs'
        ordering = ['-sync_started_at']
    
    def __str__(self):
        return f"{self.device} - {self.status} - {self.sync_started_at}"
