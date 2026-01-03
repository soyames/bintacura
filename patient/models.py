from django.db import models
from django.utils import timezone
from core.models import Participant
from core.mixins import SyncMixin
import uuid


class PatientData(models.Model):  # Stores medical and personal information specific to patients
    MARITAL_STATUS_CHOICES = [
        ("single", "Single"),
        ("married", "Married"),
        ("divorced", "Divorced"),
        ("widowed", "Widowed"),
        ("other", "Other"),
    ]
    
    SMOKING_STATUS_CHOICES = [
        ("never", "Jamais"),
        ("former", "Ancien fumeur"),
        ("current", "Fumeur actuel"),
    ]
    
    ALCOHOL_CONSUMPTION_CHOICES = [
        ("none", "Aucun"),
        ("occasional", "Occasionnel"),
        ("moderate", "Modéré"),
        ("heavy", "Important"),
    ]
    
    PHYSICAL_ACTIVITY_CHOICES = [
        ("sedentary", "Sédentaire"),
        ("light", "Léger"),
        ("moderate", "Modéré"),
        ("active", "Actif"),
    ]

    participant = models.OneToOneField(
        Participant, on_delete=models.CASCADE, related_name="patient_data"
    )
    blood_type = models.CharField(max_length=5, blank=True)
    allergies = models.JSONField(default=list, blank=True)
    chronic_conditions = models.JSONField(default=list, blank=True)
    current_medications = models.JSONField(default=list, blank=True)
    medical_history = models.TextField(blank=True)
    height = models.FloatField(null=True, blank=True)
    weight = models.FloatField(null=True, blank=True)
    primary_doctor_id = models.UUIDField(null=True, blank=True)
    insurance_provider = models.CharField(max_length=255, blank=True)
    insurance_policy_number = models.CharField(max_length=100, blank=True)
    marital_status = models.CharField(
        max_length=20, choices=MARITAL_STATUS_CHOICES, blank=True
    )
    number_of_children = models.IntegerField(null=True, blank=True, default=0)
    profession = models.CharField(max_length=255, blank=True)
    home_doctor_id = models.UUIDField(null=True, blank=True)
    
    # Lifestyle fields
    smoking_status = models.CharField(
        max_length=20, choices=SMOKING_STATUS_CHOICES, blank=True
    )
    alcohol_consumption = models.CharField(
        max_length=20, choices=ALCOHOL_CONSUMPTION_CHOICES, blank=True
    )
    physical_activity = models.CharField(
        max_length=20, choices=PHYSICAL_ACTIVITY_CHOICES, blank=True
    )
    
    # Preventive care tracking
    last_checkup_date = models.DateField(null=True, blank=True)
    last_dental_visit = models.DateField(null=True, blank=True)
    last_eye_exam = models.DateField(null=True, blank=True)
    last_gynecological_exam = models.DateField(null=True, blank=True)
    last_mammogram = models.DateField(null=True, blank=True)
    
    # Vaccination records
    vaccination_records = models.JSONField(default=list, blank=True)

    class Meta:  # Meta class implementation
        db_table = "patient_data"

    def __str__(self):  # Return string representation
        return f"Patient Data for {self.participant.email}"


class DependentProfile(SyncMixin):  # Represents family members or dependents linked to a patient account
    RELATIONSHIP_CHOICES = [
        ("spouse", "Spouse"),
        ("child", "Child"),
        ("parent", "Parent"),
        ("sibling", "Sibling"),
        ("guardian", "Guardian"),
        ("other", "Other"),
    ]

    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    patient = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="dependents",
        limit_choices_to={"role": "patient"},
    )
    full_name = models.CharField(max_length=255)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES)
    relationship = models.CharField(max_length=50, choices=RELATIONSHIP_CHOICES)
    blood_type = models.CharField(max_length=5, blank=True)
    allergies = models.JSONField(default=list, blank=True)
    chronic_conditions = models.JSONField(default=list, blank=True)
    photo_url = models.URLField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    medical_notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:  # Meta class implementation
        db_table = "dependent_profiles"
        ordering = ["-created_at"]

    def __str__(self):  # Return string representation
        return f"{self.full_name} ({self.relationship} of {self.patient.email})"


class PreventiveCareReminder(SyncMixin):
    """Automated reminders for preventive healthcare"""
    
    REMINDER_TYPE_CHOICES = [
        ('vaccination', 'Vaccination'),
        ('screening', 'Dépistage'),
        ('checkup', 'Bilan annuel'),
        ('dental', 'Contrôle dentaire'),
        ('eye_exam', 'Examen de la vue'),
        ('mammogram', 'Mammographie'),
        ('cervical_screening', 'Dépistage du cancer du col'),
        ('blood_pressure', 'Tension artérielle'),
        ('diabetes_screening', 'Dépistage du diabète'),
        ('malaria_prophylaxis', 'Prophylaxie antipaludique'),
        ('cholera_vaccination', 'Vaccination contre le choléra'),
        ('tb_screening', 'Dépistage de la tuberculose'),
    ]
    
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    patient = models.ForeignKey(
        Participant, 
        on_delete=models.CASCADE, 
        related_name='preventive_reminders',
        limit_choices_to={"role": "patient"}
    )
    reminder_type = models.CharField(max_length=30, choices=REMINDER_TYPE_CHOICES)
    due_date = models.DateField()
    description = models.TextField()
    is_completed = models.BooleanField(default=False)
    completed_date = models.DateField(null=True, blank=True)
    
    # Notification tracking
    reminder_sent = models.BooleanField(default=False)
    last_reminder_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'preventive_care_reminders'
        ordering = ['due_date']
        indexes = [
            models.Index(fields=['patient', 'due_date']),
            models.Index(fields=['is_completed', 'due_date']),
        ]
    
    def __str__(self):
        return f"{self.get_reminder_type_display()} - {self.patient.email}"


class PersonalHealthNote(SyncMixin):
    """Patient's personal health diary"""
    
    CATEGORY_CHOICES = [
        ('symptom', 'Symptôme'),
        ('medication', 'Médicament'),
        ('side_effect', 'Effet secondaire'),
        ('mood', 'Humeur'),
        ('diet', 'Alimentation'),
        ('exercise', 'Exercice'),
        ('sleep', 'Sommeil'),
        ('general', 'Général'),
    ]
    
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    patient = models.ForeignKey(
        Participant, 
        on_delete=models.CASCADE, 
        related_name='health_notes',
        limit_choices_to={"role": "patient"}
    )
    
    title = models.CharField(max_length=255)
    content = models.TextField()
    note_date = models.DateField(default=timezone.now)
    
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default='general'
    )
    
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = 'personal_health_notes'
        ordering = ['-note_date', '-created_at']
        indexes = [
            models.Index(fields=['patient', '-note_date']),
            models.Index(fields=['category', '-note_date']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.patient.email}"
