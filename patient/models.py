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
