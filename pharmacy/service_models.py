from django.db import models
from django.utils import timezone
from core.models import Participant
from core.mixins import SyncMixin


class PharmacyService(SyncMixin):
    """
    Services offered by pharmacies with pricing in local currency.
    Examples: Medication Dispensing, Consultation, Health Screening, etc.
    """
    SERVICE_CATEGORY_CHOICES = [
        ('medication_dispensing', 'Dispensation de Médicaments'),
        ('pharmacist_consultation', 'Consultation Pharmaceutique'),
        ('health_screening', 'Dépistage Santé'),
        ('vaccination', 'Vaccination'),
        ('blood_pressure_check', 'Contrôle Tension Artérielle'),
        ('glucose_testing', 'Test de Glycémie'),
        ('medication_review', 'Révision de Médicaments'),
        ('home_delivery', 'Livraison à Domicile'),
        ('compounding', 'Préparation Magistrale'),
        ('medical_device', 'Dispositif Médical'),
        ('other', 'Autre'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    pharmacy = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='pharmacy_services',
        limit_choices_to={'role': 'pharmacy'}
    )
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=SERVICE_CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    price = models.IntegerField(default=0, help_text="Price in XOF cents")
    currency = models.CharField(max_length=3, default='XOF')
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    requires_appointment = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'pharmacy_services'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['pharmacy', 'is_active']),
            models.Index(fields=['category', 'is_available']),
        ]

    def __str__(self):
        return f"{self.name} - {self.pharmacy.full_name}"
