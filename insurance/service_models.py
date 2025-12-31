from django.db import models
from django.utils import timezone
from core.models import Participant
from core.mixins import SyncMixin


class InsuranceService(SyncMixin):
    """
    Services/products offered by insurance companies with pricing in local currency.
    Examples: Health Insurance Plans, Coverage Add-ons, etc.
    """
    SERVICE_CATEGORY_CHOICES = [
        ('health_insurance', 'Assurance Santé'),
        ('dental_insurance', 'Assurance Dentaire'),
        ('optical_insurance', 'Assurance Optique'),
        ('maternity_coverage', 'Couverture Maternité'),
        ('life_insurance', 'Assurance Vie'),
        ('disability_insurance', 'Assurance Invalidité'),
        ('critical_illness', 'Maladie Grave'),
        ('travel_insurance', 'Assurance Voyage'),
        ('add_on_coverage', 'Couverture Additionnelle'),
        ('consultation', 'Consultation Assurance'),
        ('other', 'Autre'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    insurance_company = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='insurance_services',
        limit_choices_to={'role': 'insurance_company'}
    )
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=SERVICE_CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    premium_amount = models.IntegerField(default=0, help_text="Premium in XOF cents")
    currency = models.CharField(max_length=3, default='XOF')
    payment_frequency = models.CharField(
        max_length=20,
        choices=[
            ('monthly', 'Mensuel'),
            ('quarterly', 'Trimestriel'),
            ('semi_annual', 'Semestriel'),
            ('annual', 'Annuel'),
        ],
        default='monthly'
    )
    coverage_limit = models.IntegerField(null=True, blank=True, help_text="Maximum coverage in XOF cents")
    is_available = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    minimum_age = models.IntegerField(null=True, blank=True)
    maximum_age = models.IntegerField(null=True, blank=True)
    waiting_period_days = models.IntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'insurance_services'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['insurance_company', 'is_active']),
            models.Index(fields=['category', 'is_available']),
        ]

    def __str__(self):
        return f"{self.name} - {self.insurance_company.full_name}"
