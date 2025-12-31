from django.db import models
from django.utils import timezone
import uuid
from core.models import Participant
from core.mixins import SyncMixin
from qrcode_generator.services import QRCodeService

class Medication(SyncMixin):  # Stores medication information and drug details
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    name = models.CharField(max_length=255)
    generic_name = models.CharField(max_length=255, blank=True)
    brand_name = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    manufacturer = models.CharField(max_length=255, blank=True)
    is_controlled_substance = models.BooleanField(default=False)
    requires_prescription = models.BooleanField(default=True)
    side_effects = models.TextField(blank=True)
    contraindications = models.TextField(blank=True)
    dosage_forms = models.JSONField(default=list)
    strengths = models.JSONField(default=list)

    class Meta:  # Meta class implementation
        db_table = 'medications'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['generic_name']),
        ]

class Prescription(SyncMixin):  # Represents medical prescriptions issued by doctors to patients
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('pendingRenewal', 'Pending Renewal'),
        ('renewed', 'Renewed'),
        ('used', 'Used'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
        ('ordered', 'Ordered'),
        ('fulfilled', 'Fulfilled'),
        ('partiallyFulfilled', 'Partially Fulfilled'),
        ('verified', 'Verified'),
        ('transferred', 'Transferred'),
        ('suspended', 'Suspended'),
    ]

    TYPE_CHOICES = [
        ('regular', 'Regular'),
        ('controlled', 'Controlled'),
        ('emergency', 'Emergency'),
        ('repeat', 'Repeat'),
        ('acute', 'Acute'),
        ('chronic', 'Chronic'),
        ('telemedicine', 'Telemedicine'),
    ]

    REFILL_STATUS_CHOICES = [
        ('none', 'None'),
        ('available', 'Available'),
        ('exhausted', 'Exhausted'),
        ('pending_approval', 'Pending Approval'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Client-provided unique key to prevent duplicate prescription creation"
    )
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='prescriptions')
    doctor = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='prescribed_prescriptions')
    preferred_pharmacy = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True, related_name='preferred_prescriptions')
    issue_date = models.DateField()
    valid_until = models.DateField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='active')
    type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='regular')

    diagnosis = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    special_instructions = models.TextField(blank=True)

    max_refills = models.IntegerField(default=0)
    refills_used = models.IntegerField(default=0)
    refill_status = models.CharField(max_length=30, choices=REFILL_STATUS_CHOICES, default='none')

    is_controlled_substance = models.BooleanField(default=False)
    requires_pharmacist_verification = models.BooleanField(default=False)
    drug_interaction_warnings = models.JSONField(default=list, blank=True)
    allergy_warnings = models.JSONField(default=list, blank=True)

    class Meta:  # Meta class implementation
        db_table = 'prescriptions'
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['doctor']),
            models.Index(fields=['issue_date']),
            models.Index(fields=['valid_until']),
            models.Index(fields=['region_code', 'status']),
        ]

class PrescriptionItem(SyncMixin):  # Represents individual medications within a prescription
    FREQUENCY_CHOICES = [
        ('once_daily', 'Once Daily'),
        ('twice_daily', 'Twice Daily'),
        ('three_times_daily', 'Three Times Daily'),
        ('four_times_daily', 'Four Times Daily'),
        ('every_6_hours', 'Every 6 Hours'),
        ('every_8_hours', 'Every 8 Hours'),
        ('every_12_hours', 'Every 12 Hours'),
        ('as_needed', 'As Needed'),
    ]

    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    medication = models.ForeignKey(Medication, on_delete=models.PROTECT, null=True, blank=True)
    medication_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100)
    dosage_form = models.CharField(max_length=50)
    strength = models.CharField(max_length=50)
    quantity = models.IntegerField()
    frequency = models.CharField(max_length=50, choices=FREQUENCY_CHOICES)
    duration_days = models.IntegerField()
    instructions = models.TextField(blank=True)
    route = models.CharField(max_length=50, blank=True)
    timing = models.CharField(max_length=100, blank=True)

    class Meta:  # Meta class implementation
        db_table = 'prescription_items'

class PrescriptionFulfillment(SyncMixin):  # Tracks pharmacy fulfillment of prescriptions
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('partially_completed', 'Partially Completed'),
        ('cancelled', 'Cancelled'),
    ]

    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='fulfillments')
    pharmacy = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='fulfillments')
    pharmacist = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, related_name='verified_fulfillments')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    fulfillment_date = models.DateTimeField(null=True, blank=True)
    total_cost = models.IntegerField(default=0)
    patient_paid = models.IntegerField(default=0)
    insurance_covered = models.IntegerField(default=0)
    pharmacist_signature = models.CharField(max_length=255, blank=True)
    patient_signature = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    class Meta:  # Meta class implementation
        db_table = 'prescription_fulfillments'
        ordering = ['-fulfillment_date']

class FulfillmentItem(SyncMixin):  # Represents individual medications dispensed in a fulfillment
    fulfillment = models.ForeignKey(PrescriptionFulfillment, on_delete=models.CASCADE, related_name='items')
    prescription_item = models.ForeignKey(PrescriptionItem, on_delete=models.CASCADE, related_name='fulfillment_items')
    quantity_fulfilled = models.IntegerField()
    quantity_remaining = models.IntegerField(default=0)
    batch_number = models.CharField(max_length=100, blank=True)
    manufacturer = models.CharField(max_length=255, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    unit_price = models.IntegerField(default=0)
    total_price = models.IntegerField(default=0)

    class Meta:  # Meta class implementation
        db_table = 'fulfillment_items'

class PrescriptionRenewalRequest(SyncMixin):  # Tracks patient requests to renew prescriptions
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]

    original_prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='renewal_requests')
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='prescription_renewal_requests')
    doctor = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='doctor_renewal_requests')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    patient_notes = models.TextField(blank=True, help_text="Patient's reason for renewal request")
    doctor_notes = models.TextField(blank=True, help_text="Doctor's response or notes")
    renewed_prescription = models.ForeignKey(Prescription, on_delete=models.SET_NULL, null=True, blank=True, related_name='renewed_from_request')
    requested_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:  # Meta class implementation
        db_table = 'prescription_renewal_requests'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['doctor', 'status']),
            models.Index(fields=['original_prescription']),
        ]
