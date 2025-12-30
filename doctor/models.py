from django.db import models
from django.utils import timezone
from core.models import Participant
from core.mixins import SyncMixin


class DoctorAffiliation(SyncMixin):  # Manages doctor-hospital affiliations and employment relationships
    """
    Manages doctor-hospital affiliations.
    Independent doctors can affiliate with multiple hospitals.
    Hospital staff doctors have a locked affiliation.
    """
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    doctor = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='hospital_affiliations',
        limit_choices_to={'role': 'doctor'}
    )
    hospital = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='affiliated_doctors',
        limit_choices_to={'role': 'hospital'}
    )
    is_primary = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)  # True if created by hospital as staff
    affiliation_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    department_id = models.CharField(max_length=100, blank=True)

    class Meta:  # Meta class implementation
        db_table = 'doctor_affiliations'
        unique_together = ['doctor', 'hospital']
        indexes = [
            models.Index(fields=['doctor', 'is_active']),
            models.Index(fields=['hospital', 'is_active']),
        ]

    def __str__(self):  # Return string representation
        return f"Dr. {self.doctor.full_name} @ {self.hospital.full_name}"


class DoctorData(models.Model):  # Stores detailed doctor profile information including specialization and qualifications
    """
    Doctor profile data - OneToOne extension of Participant.
    Does not use SyncMixin as it syncs with the parent Participant.
    """
    SPECIALIZATION_CHOICES = [
        ("general_practice", "General Practice"),
        ("cardiology", "Cardiology"),
        ("dermatology", "Dermatology"),
        ("pediatrics", "Pediatrics"),
        ("psychiatry", "Psychiatry"),
        ("orthopedics", "Orthopedics"),
        ("neurology", "Neurology"),
        ("oncology", "Oncology"),
    ]

    participant = models.OneToOneField(
        Participant, on_delete=models.CASCADE, related_name="doctor_data"
    )
    specialization = models.CharField(max_length=100, choices=SPECIALIZATION_CHOICES)
    license_number = models.CharField(max_length=100, unique=True)
    years_of_experience = models.IntegerField(default=0)
    qualifications = models.JSONField(default=list)
    consultation_fee = models.IntegerField(default=0)  # Stored in XOF cents
    bio = models.TextField(blank=True)
    languages_spoken = models.JSONField(default=list)
    rating = models.FloatField(default=0.0)
    total_reviews = models.IntegerField(default=0)
    total_consultations = models.IntegerField(default=0)
    is_available_for_telemedicine = models.BooleanField(default=False)

    class Meta:  # Meta class implementation
        db_table = "doctor_data"

    def __str__(self):  # Return string representation
        return f"Dr. {self.participant.full_name} - {self.get_specialization_display()}"

    def get_actual_rating(self):
        """Calculate real-time average rating from Review model"""
        from core.models import Review
        from django.db.models import Avg

        reviews = Review.objects.filter(
            reviewed_type='doctor',
            reviewed_id=self.participant.uid,
            is_approved=True
        )

        if not reviews.exists():
            return 0.0

        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
        return round(avg_rating, 1) if avg_rating else 0.0

    def get_actual_total_reviews(self):
        """Get real-time count of approved reviews"""
        from core.models import Review

        return Review.objects.filter(
            reviewed_type='doctor',
            reviewed_id=self.participant.uid,
            is_approved=True
        ).count()

    def update_rating_cache(self):
        """Update cached rating and total_reviews fields from actual reviews"""
        self.rating = self.get_actual_rating()
        self.total_reviews = self.get_actual_total_reviews()
        self.save(update_fields=['rating', 'total_reviews'])
    
    def get_consultation_fee(self):
        """Get consultation fee, using settings default if not set"""
        from django.conf import settings
        if self.consultation_fee and self.consultation_fee > 0:
            return self.consultation_fee
        return getattr(settings, 'DEFAULT_CONSULTATION_FEE_XOF', 3500)


class DoctorService(SyncMixin):  # Represents services offered by doctors with pricing and duration
    SERVICE_CATEGORY_CHOICES = [
        ('consultation', 'Consultation'),
        ('diagnostic', 'Examen Diagnostique'),
        ('therapy', 'Thérapie'),
        ('vaccination', 'Vaccination'),
        ('other', 'Autre'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    doctor = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='doctor_services',
        limit_choices_to={'role': 'doctor'}
    )
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=SERVICE_CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    price = models.IntegerField(default=0)  # Stored in XOF cents
    duration_minutes = models.PositiveIntegerField()
    is_available = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:  # Meta class implementation
        db_table = 'doctor_services'
        ordering = ['-created_at']

    def __str__(self):  # Return string representation
        return f"{self.name} - Dr. {self.doctor.full_name}"

