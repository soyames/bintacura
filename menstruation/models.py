from django.db import models
from django.utils import timezone
from datetime import timedelta
import uuid
from core.models import Participant
from core.mixins import SyncMixin


class MenstrualCycle(SyncMixin):
    """
    Tracks menstrual cycle data and predictions for female patients
    """
    FLOW_INTENSITY_CHOICES = [
        ('light', 'Light'),
        ('medium', 'Medium'),
        ('heavy', 'Heavy'),
        ('spotting', 'Spotting'),
    ]
    
    MOOD_CHOICES = [
        ('happy', 'Happy'),
        ('normal', 'Normal'),
        ('irritable', 'Irritable'),
        ('sad', 'Sad'),
        ('anxious', 'Anxious'),
        ('tired', 'Tired'),
    ]
    
    patient = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='menstrual_cycles',
        limit_choices_to={'gender__in': ['female', 'feminin', 'f', 'F', 'Female']}
    )
    cycle_start_date = models.DateField(help_text="First day of menstruation")
    cycle_end_date = models.DateField(null=True, blank=True, help_text="Last day of cycle (first day of next period)")
    period_length = models.IntegerField(default=5, help_text="Number of days of active menstruation")
    cycle_length = models.IntegerField(default=28, help_text="Total cycle length in days")
    
    # Flow tracking
    flow_intensity = models.CharField(max_length=20, choices=FLOW_INTENSITY_CHOICES, blank=True)
    
    # Symptoms tracking
    symptoms = models.JSONField(
        default=list,
        blank=True,
        help_text="List of symptoms experienced (cramps, headache, bloating, etc.)"
    )
    
    # Mood tracking
    mood = models.CharField(max_length=50, choices=MOOD_CHOICES, blank=True)
    
    # Notes
    notes = models.TextField(blank=True, help_text="Personal notes about this cycle")
    
    # Predictions
    predicted_ovulation_date = models.DateField(null=True, blank=True)
    predicted_next_period_date = models.DateField(null=True, blank=True)
    predicted_fertile_window_start = models.DateField(null=True, blank=True)
    predicted_fertile_window_end = models.DateField(null=True, blank=True)
    
    # Tracking
    is_active_cycle = models.BooleanField(default=True, help_text="Whether this is the current cycle")
    
    class Meta:
        db_table = 'menstrual_cycles'
        ordering = ['-cycle_start_date']
        indexes = [
            models.Index(fields=['patient', 'cycle_start_date']),
            models.Index(fields=['patient', 'is_active_cycle']),
        ]
    
    def __str__(self):
        return f"{self.patient.full_name} - Cycle starting {self.cycle_start_date}"
    
    def save(self, *args, **kwargs):
        """Calculate predictions when saving"""
        if self.cycle_start_date and not self.predicted_ovulation_date:
            # Ovulation typically occurs 14 days before next period
            self.predicted_ovulation_date = self.cycle_start_date + timedelta(days=(self.cycle_length - 14))
        
        if self.cycle_start_date and not self.predicted_next_period_date:
            self.predicted_next_period_date = self.cycle_start_date + timedelta(days=self.cycle_length)
        
        if self.predicted_ovulation_date:
            # Fertile window is typically 5 days before ovulation + ovulation day
            self.predicted_fertile_window_start = self.predicted_ovulation_date - timedelta(days=5)
            self.predicted_fertile_window_end = self.predicted_ovulation_date + timedelta(days=1)
        
        super().save(*args, **kwargs)
    
    def get_cycle_day(self):
        """Get current day of cycle"""
        if self.cycle_start_date:
            days_since_start = (timezone.now().date() - self.cycle_start_date).days
            return days_since_start + 1
        return None
    
    def is_in_fertile_window(self):
        """Check if today is in fertile window"""
        today = timezone.now().date()
        if self.predicted_fertile_window_start and self.predicted_fertile_window_end:
            return self.predicted_fertile_window_start <= today <= self.predicted_fertile_window_end
        return False


class CycleSymptom(models.Model):
    """
    Daily symptom tracking within a cycle
    """
    SYMPTOM_TYPE_CHOICES = [
        ('cramps', 'Cramps'),
        ('headache', 'Headache'),
        ('bloating', 'Bloating'),
        ('breast_tenderness', 'Breast Tenderness'),
        ('acne', 'Acne'),
        ('back_pain', 'Back Pain'),
        ('fatigue', 'Fatigue'),
        ('nausea', 'Nausea'),
        ('diarrhea', 'Diarrhea'),
        ('constipation', 'Constipation'),
        ('food_cravings', 'Food Cravings'),
        ('mood_swings', 'Mood Swings'),
        ('insomnia', 'Insomnia'),
        ('other', 'Other'),
    ]
    
    SEVERITY_CHOICES = [
        (1, 'Mild'),
        (2, 'Moderate'),
        (3, 'Severe'),
    ]
    
    uid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cycle = models.ForeignKey(MenstrualCycle, on_delete=models.CASCADE, related_name='daily_symptoms')
    date = models.DateField()
    symptom_type = models.CharField(max_length=50, choices=SYMPTOM_TYPE_CHOICES)
    severity = models.IntegerField(choices=SEVERITY_CHOICES, default=1)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'cycle_symptoms'
        ordering = ['-date']
        unique_together = ['cycle', 'date', 'symptom_type']
    
    def __str__(self):
        return f"{self.symptom_type} - {self.date}"


class CycleReminder(SyncMixin):
    """
    Reminders for menstrual cycle events
    """
    REMINDER_TYPE_CHOICES = [
        ('period_starting', 'Period Starting Soon'),
        ('ovulation', 'Ovulation Day'),
        ('fertile_window', 'Fertile Window'),
        ('period_late', 'Period Late'),
        ('log_cycle', 'Log Your Cycle'),
    ]
    
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='cycle_reminders')
    reminder_type = models.CharField(max_length=50, choices=REMINDER_TYPE_CHOICES)
    reminder_date = models.DateField()
    reminder_time = models.TimeField(default='08:00:00')
    is_sent = models.BooleanField(default=False)
    is_enabled = models.BooleanField(default=True)
    message = models.TextField(blank=True)
    
    class Meta:
        db_table = 'cycle_reminders'
        ordering = ['reminder_date', 'reminder_time']
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.get_reminder_type_display()} on {self.reminder_date}"
