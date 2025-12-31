from django.db import models
from django.utils import timezone
from core.models import Participant
from core.mixins import SyncMixin


class HospitalService(SyncMixin):
    """
    Services offered by hospitals with pricing in local currency.
    Examples: X-Ray, MRI, Surgery, Lab Tests, etc.
    """
    SERVICE_CATEGORY_CHOICES = [
        ('imaging', 'Imagerie Médicale'),
        ('surgery', 'Chirurgie'),
        ('laboratory', 'Laboratoire'),
        ('emergency', 'Urgence'),
        ('consultation_specialist', 'Consultation Spécialiste'),
        ('hospitalization', 'Hospitalisation'),
        ('maternity', 'Maternité'),
        ('icu', 'Soins Intensifs'),
        ('physiotherapy', 'Physiothérapie'),
        ('dental', 'Dentaire'),
        ('optical', 'Optique'),
        ('other', 'Autre'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    hospital = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='hospital_services',
        limit_choices_to={'role': 'hospital'}
    )
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=SERVICE_CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    price = models.IntegerField(default=0, help_text="Price in XOF cents")
    currency = models.CharField(max_length=3, default='XOF')
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    requires_appointment = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'hospital_services'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['hospital', 'is_active']),
            models.Index(fields=['category', 'is_available']),
        ]

    def __str__(self):
        return f"{self.name} - {self.hospital.full_name}"
