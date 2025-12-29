from django.db import models
from django.utils import timezone
from core.models import Participant
from core.sync_mixin import SyncMixin
import uuid


class PlatformStatistics(SyncMixin):
    date = models.DateField(unique=True)

    total_users = models.IntegerField(default=0)
    total_patients = models.IntegerField(default=0)
    total_doctors = models.IntegerField(default=0)
    total_hospitals = models.IntegerField(default=0)
    total_pharmacies = models.IntegerField(default=0)
    total_insurance_companies = models.IntegerField(default=0)

    new_users_today = models.IntegerField(default=0)
    active_users_today = models.IntegerField(default=0)

    total_appointments = models.IntegerField(default=0)
    completed_appointments = models.IntegerField(default=0)
    cancelled_appointments = models.IntegerField(default=0)

    total_transactions = models.IntegerField(default=0)
    total_transaction_volume = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    total_platform_fees = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )

    total_prescriptions = models.IntegerField(default=0)
    fulfilled_prescriptions = models.IntegerField(default=0)

    total_insurance_claims = models.IntegerField(default=0)
    approved_claims = models.IntegerField(default=0)

    verified_providers = models.IntegerField(default=0)
    pending_verifications = models.IntegerField(default=0)

    total_refund_requests = models.IntegerField(default=0)
    pending_refunds = models.IntegerField(default=0)
    approved_refunds = models.IntegerField(default=0)
    region_code = models.CharField(max_length=50, default="global", db_index=True)

    class Meta:
        db_table = "platform_statistics"
        ordering = ["-date"]
        verbose_name_plural = "Platform Statistics"

    def __str__(self):
        return f"Statistics for {self.date}"


class UserGrowthMetrics(SyncMixin):
    date = models.DateField()
    user_role = models.CharField(max_length=50)
    new_registrations = models.IntegerField(default=0)
    active_users = models.IntegerField(default=0)
    total_users = models.IntegerField(default=0)
    region_code = models.CharField(max_length=50, default="global", db_index=True)

    class Meta:
        db_table = "user_growth_metrics"
        unique_together = [["date", "user_role"]]
        indexes = [
            models.Index(fields=["date", "user_role"]),
        ]

    def __str__(self):
        return f"{self.user_role} metrics for {self.date}"


class RevenueMetrics(SyncMixin):
    date = models.DateField()

    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    platform_fees = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    appointment_revenue = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    prescription_revenue = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    insurance_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    refunds_issued = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    transaction_count = models.IntegerField(default=0)
    average_transaction_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    region_code = models.CharField(max_length=50, default="global", db_index=True)

    class Meta:
        db_table = "revenue_metrics"
        unique_together = [["date"]]
        ordering = ["-date"]

    def __str__(self):
        return f"Revenue metrics for {self.date}"


class SurveyResponse(SyncMixin):
    SEX_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('PND', 'Prefer Not to Disclose'),
    ]

    email = models.EmailField(unique=True)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    profession = models.CharField(max_length=100)
    sex = models.CharField(max_length=4, choices=SEX_CHOICES)
    
    suggested_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10)
    
    feature_suggestion = models.TextField(blank=True)
    other_suggestion = models.TextField(blank=True)
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    
    submission_date = models.DateTimeField(auto_now_add=True)

    class Meta:  # Meta class implementation
        db_table = "survey_responses"
        ordering = ["-submission_date"]
        indexes = [
            models.Index(fields=["country"]),
            models.Index(fields=["profession"]),
            models.Index(fields=["sex"]),
            models.Index(fields=["submission_date"]),
        ]

    def __str__(self):  # Return string representation
        return f"Survey Response from {self.email}"
