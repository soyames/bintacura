from django.db import models
from django.utils import timezone
import uuid
from core.models import Participant
from core.mixins import SyncMixin


class Appointment(SyncMixin):  # Represents scheduled medical appointments between patients and providers
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("rejected", "Rejected"),
        ("in_progress", "In Progress"),
        ("no_show", "No Show"),
    ]

    TYPE_CHOICES = [
        ("consultation", "Consultation"),
        ("follow_up", "Follow Up"),
        ("emergency", "Emergency"),
        ("telemedicine", "Telemedicine"),
        ("checkup", "Checkup"),
        ("procedure", "Procedure"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("refunded", "Refunded"),
        ("failed", "Failed"),
    ]

    PAYMENT_METHOD_CHOICES = [
        # NO WALLET - BINTACURA does not store money
        ('cash', 'Cash'),
        ('onsite', 'On-site Cash'),
        ('onsite_cash', 'On-site Cash'),
        ('online', 'Online Payment'),
        ('fedapay', 'FedaPay'),
        ('card', 'Card'),
        ('mobile_money', 'Mobile Money'),
        ('insurance', 'Insurance'),
    ]

    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, null=False, db_index=True)
    region_code = models.CharField(max_length=50, default="global", null=False, db_index=True)
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Client-provided unique key to prevent duplicate appointment creation"
    )
    participants = models.JSONField(default=list, null=False)
    patient = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="patient_appointments",
        null=True,
    )
    doctor = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="doctor_appointments",
        null=True,
        blank=True,
    )
    hospital = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="hospital_appointments",
        null=True,
        blank=True,
    )
    service = models.ForeignKey(
        "core.ParticipantService",
        on_delete=models.SET_NULL,
        related_name="appointments",
        to_field="uid",
        db_column="service_id",
        null=True,
        blank=True,
    )

    appointment_date = models.DateField(null=False)
    appointment_time = models.TimeField(null=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", null=False)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default="consultation", null=False)
    appointment_type = models.CharField(max_length=50, default='', blank=True, null=False)

    is_hospital_appointment = models.BooleanField(default=False, null=False)
    beneficiary = models.ForeignKey(
        "patient.DependentProfile",
        on_delete=models.SET_NULL,
        related_name="appointments",
        null=True,
        blank=True,
    )

    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=False, help_text="Base consultation fee in XOF")
    currency = models.CharField(max_length=3, default='XOF', null=False, help_text="Currency code for all fees")
    additional_services_total = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        null=False,
        help_text="Total cost of additional services selected"
    )
    original_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=False, help_text="consultation_fee + additional_services_total")
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=False, help_text="Total after discounts")
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=False)
    insurance_package_id = models.UUIDField(null=True, blank=True)

    queue_number = models.IntegerField(null=True, blank=True)
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending", null=False
    )
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES, default="cash",
        null=False, help_text="Payment method selected by patient"
    )
    payment_reference = models.CharField(max_length=100, default='', blank=True, help_text="Payment transaction reference number")
    payment_id = models.UUIDField(null=True, blank=True)

    reason = models.TextField(default='', blank=True, null=False)
    notes = models.TextField(default='', blank=True, null=False)
    symptoms = models.TextField(default='', blank=True, null=False)

    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(default='', blank=True, null=False)

    reminder_sent = models.BooleanField(default=False, null=False)
    rating = models.IntegerField(null=True, blank=True)
    review = models.TextField(default='', blank=True, null=False)

    class Meta:  # Meta class implementation
        db_table = "appointments"
        ordering = ["-appointment_date", "-appointment_time"]
        indexes = [
            models.Index(fields=["patient", "appointment_date"]),
            models.Index(fields=["doctor", "appointment_date"]),
            models.Index(fields=["hospital", "appointment_date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["appointment_date", "appointment_time"]),
        ]


class Availability(SyncMixin):  # Defines participant availability schedules for appointment booking
    WEEKDAY_CHOICES = [
        ("monday", "Monday"),
        ("tuesday", "Tuesday"),
        ("wednesday", "Wednesday"),
        ("thursday", "Thursday"),
        ("friday", "Friday"),
        ("saturday", "Saturday"),
        ("sunday", "Sunday"),
    ]

    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="availabilities"
    )
    weekday = models.CharField(max_length=20, choices=WEEKDAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration = models.IntegerField(default=30)
    is_active = models.BooleanField(default=True)

    class Meta:  # Meta class implementation
        db_table = "availabilities"
        indexes = [
            models.Index(fields=["participant", "weekday"]),
        ]


class AppointmentQueue(SyncMixin):  # Manages appointment queues and wait times for participants
    appointment = models.OneToOneField(
        Appointment, on_delete=models.CASCADE, related_name="queue_entry", null=False
    )
    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="queue_entries"
    )
    queue_number = models.IntegerField(null=False)
    estimated_wait_time = models.IntegerField(default=0, null=False)
    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default="waiting", null=False)

    class Meta:  # Meta class implementation
        db_table = "appointment_queues"
        ordering = ["queue_number"]
        indexes = [
            models.Index(fields=["participant", "status"]),
            models.Index(fields=["queue_number"]),
        ]


class AppointmentHistory(SyncMixin):  # Tracks changes made to appointments for audit purposes
    appointment = models.ForeignKey(
        Appointment, on_delete=models.CASCADE, related_name="history"
    )
    changed_by = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True)
    field_name = models.CharField(max_length=100)
    old_value = models.TextField()
    new_value = models.TextField()
    change_reason = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:  # Meta class implementation
        db_table = "appointment_history"
        ordering = ["-timestamp"]


class StaffTask(SyncMixin):  # Manages tasks assigned to staff related to appointments
    TASK_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    assigned_to = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="assigned_tasks"
    )
    assigned_by = models.ForeignKey(
        Participant, on_delete=models.SET_NULL, null=True, related_name="created_tasks"
    )
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="tasks",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default="medium"
    )
    status = models.CharField(
        max_length=20, choices=TASK_STATUS_CHOICES, default="pending"
    )
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:  # Meta class implementation
        db_table = "staff_tasks"
        ordering = ["-priority", "due_date"]


# Additional services model
from .appointment_service_model import AppointmentService


