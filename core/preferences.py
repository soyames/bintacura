from django.db import models
from django.utils import timezone
import uuid


class ParticipantPreferences(models.Model):
    """
    Universal participant preferences that affect platform behavior.
    Each participant has their own preferences regardless of role.
    Settings are stored in database and consistent across all devices.
    """
    
    # Appearance preferences
    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('auto', 'Auto'),
    ]
    
    FONT_SIZE_CHOICES = [
        ('small', 'Small'),
        ('medium', 'Medium'),
        ('large', 'Large'),
    ]
    
    LANGUAGE_CHOICES = [
        ('fr', 'Français'),
        ('en', 'English'),
        ('es', 'Español'),
        ('ar', 'العربية'),
    ]
    
    # Notification timing choices
    REMINDER_TIME_CHOICES = [
        (0, 'Disabled'),
        (15, '15 minutes before'),
        (30, '30 minutes before'),
        (60, '1 hour before'),
        (120, '2 hours before'),
        (1440, '1 day before'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participant = models.OneToOneField(
        'Participant',
        on_delete=models.CASCADE,
        related_name='preferences'
    )
    
    # Appearance Settings
    theme = models.CharField(
        max_length=10,
        choices=THEME_CHOICES,
        default='light',
        help_text='Display theme preference'
    )
    font_size = models.CharField(
        max_length=10,
        choices=FONT_SIZE_CHOICES,
        default='medium',
        help_text='Text size preference'
    )
    language = models.CharField(
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default='fr',
        help_text='Preferred language'
    )
    
    # Notification Settings - Control actual platform behavior
    enable_push_notifications = models.BooleanField(
        default=True,
        help_text='Receive push notifications for appointments and updates'
    )
    enable_email_notifications = models.BooleanField(
        default=True,
        help_text='Receive email notifications - affects actual emails sent'
    )
    enable_sms_notifications = models.BooleanField(
        default=False,
        help_text='Receive SMS notifications - affects actual SMS sent'
    )
    
    # Specific notification types
    notify_appointment_confirmed = models.BooleanField(default=True)
    notify_appointment_cancelled = models.BooleanField(default=True)
    notify_appointment_reminder = models.BooleanField(default=True)
    notify_prescription_ready = models.BooleanField(default=True)
    notify_test_results = models.BooleanField(default=True)
    notify_payment_received = models.BooleanField(default=True)
    notify_payment_due = models.BooleanField(default=True)
    notify_new_message = models.BooleanField(default=True)
    notify_marketing = models.BooleanField(default=False)
    
    # Reminder preferences
    appointment_reminder_time = models.IntegerField(
        choices=REMINDER_TIME_CHOICES,
        default=60,
        help_text='Time before appointment to send reminder'
    )
    
    # Privacy & Security Settings
    enable_two_factor_auth = models.BooleanField(
        default=False,
        help_text='Require 2FA for login'
    )
    profile_visible_to_providers = models.BooleanField(
        default=True,
        help_text='Allow healthcare providers to see profile'
    )
    allow_anonymous_data_sharing = models.BooleanField(
        default=False,
        help_text='Share anonymized data for medical research'
    )
    
    # Data & Storage Settings
    enable_auto_backup = models.BooleanField(
        default=True,
        help_text='Automatically backup documents and health records'
    )
    
    # Medical Preferences
    blood_type = models.CharField(
        max_length=5,
        blank=True,
        choices=[
            ('A+', 'A+'),
            ('A-', 'A-'),
            ('B+', 'B+'),
            ('B-', 'B-'),
            ('AB+', 'AB+'),
            ('AB-', 'AB-'),
            ('O+', 'O+'),
            ('O-', 'O-'),
        ],
        help_text='Blood type for emergency information'
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'participant_preferences'
        indexes = [
            models.Index(fields=['participant']),
        ]
        verbose_name = 'Participant Preference'
        verbose_name_plural = 'Participant Preferences'
    
    def __str__(self):
        return f"Preferences for {self.participant.email}"
    
    def should_send_email_notification(self, notification_type):
        """
        Check if email notification should be sent based on preferences.
        This method is used by notification system to respect participant preferences.
        """
        if not self.enable_email_notifications:
            return False
        
        notification_flags = {
            'appointment_confirmed': self.notify_appointment_confirmed,
            'appointment_cancelled': self.notify_appointment_cancelled,
            'appointment_reminder': self.notify_appointment_reminder,
            'prescription_ready': self.notify_prescription_ready,
            'test_results': self.notify_test_results,
            'payment_received': self.notify_payment_received,
            'payment_due': self.notify_payment_due,
            'new_message': self.notify_new_message,
            'marketing': self.notify_marketing,
        }
        
        return notification_flags.get(notification_type, True)
    
    def should_send_sms_notification(self, notification_type):
        """
        Check if SMS notification should be sent based on preferences.
        """
        if not self.enable_sms_notifications:
            return False
        
        # SMS typically for critical notifications only
        critical_notifications = [
            'appointment_confirmed',
            'appointment_cancelled',
            'appointment_reminder',
            'test_results',
        ]
        
        return notification_type in critical_notifications
    
    def should_send_push_notification(self, notification_type):
        """
        Check if push notification should be sent based on preferences.
        """
        if not self.enable_push_notifications:
            return False
        
        # Exclude marketing from push unless explicitly enabled
        if notification_type == 'marketing' and not self.notify_marketing:
            return False
        
        return True


class EmergencyContact(models.Model):
    """Emergency contact information for participants."""
    
    RELATIONSHIP_CHOICES = [
        ('spouse', 'Spouse'),
        ('parent', 'Parent'),
        ('child', 'Child'),
        ('sibling', 'Sibling'),
        ('friend', 'Friend'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participant = models.ForeignKey(
        'Participant',
        on_delete=models.CASCADE,
        related_name='emergency_contacts'
    )
    
    full_name = models.CharField(max_length=255)
    relationship = models.CharField(max_length=50, choices=RELATIONSHIP_CHOICES)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    is_primary = models.BooleanField(
        default=False,
        help_text='Primary emergency contact'
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'emergency_contacts'
        ordering = ['-is_primary', 'full_name']
        indexes = [
            models.Index(fields=['participant', '-is_primary']),
        ]
    
    def __str__(self):
        return f"{self.full_name} ({self.relationship}) for {self.participant.email}"
