from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.utils import timezone
import uuid
import json


class ParticipantManager(BaseUserManager):
    def create_participant(self, email, password=None, **extra_fields):  # Creates a new participant with email and password
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        participant = self.model(email=email, **extra_fields)
        participant.set_password(password)
        participant.save(using=self._db)
        return participant

    def create_superuser(self, email, password=None, **extra_fields):  # Creates a superuser with admin privileges
        from django.conf import settings
        from django.core.exceptions import PermissionDenied

        instance_type = getattr(settings, 'INSTANCE_TYPE', 'CLOUD')
        if instance_type != 'CLOUD':
            raise PermissionDenied(
                "\n\n"
                "========================================================\n"
                "ACCÈS REFUSÉ / ACCESS DENIED\n"
                "========================================================\n\n"
                "La création de super-administrateurs n'est pas autorisée\n"
                "sur les instances locales pour des raisons de sécurité.\n\n"
                "Superuser creation is not allowed on local instances\n"
                "for security reasons.\n\n"
                "Pour obtenir un accès administrateur :\n"
                "To request admin access:\n\n"
                "1. Contactez le support BintaCura\n"
                "   Contact BintaCura support\n"
                "   Email: support@bintacura.com\n\n"
                "2. Fournissez votre email et informations d'instance\n"
                "   Provide your email and instance information\n\n"
                "3. Un administrateur sera créé pour vous par notre équipe\n"
                "   An administrator will be created for you by our team\n\n"
                "========================================================\n"
            )

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "super_admin")
        return self.create_participant(email, password, **extra_fields)


class Participant(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("patient", "Patient"),
        ("doctor", "Doctor"),
        ("hospital", "Hospital"),
        ("hospital_staff", "Hospital Staff"),
        ("pharmacy", "Pharmacy"),
        ("pharmacy_staff", "Pharmacy Staff"),
        ("insurance_company", "Insurance Company"),
        ("insurance_company_staff", "Insurance Company Staff"),
        ("admin", "Admin"),
        ("super_admin", "Super Admin"),
    ]

    ADMIN_LEVEL_CHOICES = [
        ("superAdmin", "Super Admin"),
        ("admin", "Admin"),
        ("moderator", "Moderator"),
        ("analyst", "Analyst"),
        ("viewer", "Viewer"),
    ]

    STAFF_ROLE_CHOICES = [
        # Hospital staff roles
        ("doctor", "Doctor"),
        ("nurse", "Nurse"),
        ("receptionist", "Receptionist"),
        ("lab_technician", "Lab Technician"),
        ("administrator", "Administrator"),
        # Pharmacy staff roles
        ("pharmacist", "Pharmacist"),
        ("cashier", "Cashier"),
        ("inventory_clerk", "Inventory Clerk"),
        ("delivery_person", "Delivery Person"),
        ("manager", "Manager"),
        # Insurance company staff roles
        ("claims_processor", "Claims Processor"),
        ("underwriter", "Underwriter"),
        ("customer_service", "Customer Service"),
    ]

    uid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    has_blue_checkmark = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    full_name = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    profile_picture_url = models.URLField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Latitude for location on Leaflet map")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Longitude for location on Leaflet map")
    preferred_currency = models.CharField(max_length=3, default="EUR", blank=True)
    preferred_language = models.CharField(max_length=2, default="fr", choices=[("fr", "Français"), ("en", "English")], blank=True)
    
    # Multi-region support
    region_code = models.CharField(max_length=50, default="global", db_index=True, help_text="Region code for multi-tenant deployment")

    affiliated_provider_id = models.UUIDField(null=True, blank=True)
    staff_role = models.CharField(max_length=50, choices=STAFF_ROLE_CHOICES, blank=True)
    department_id = models.CharField(max_length=100, blank=True)
    supervisor_id = models.UUIDField(null=True, blank=True)
    employee_id = models.CharField(max_length=100, blank=True)

    admin_level = models.CharField(
        max_length=20, choices=ADMIN_LEVEL_CHOICES, blank=True
    )
    department = models.CharField(max_length=100, blank=True)

    is_staff = models.BooleanField(default=False)

    activation_code = models.CharField(max_length=6, blank=True)
    activation_code_created_at = models.DateTimeField(null=True, blank=True)

    terms_accepted = models.BooleanField(default=False)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)

    objects = ParticipantManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["role"]

    class Meta:
        db_table = "participants"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["role"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["role", "is_active"]),
            models.Index(fields=["affiliated_provider_id"]),
            models.Index(fields=["region_code", "role"]),
            models.Index(fields=["region_code", "created_at"]),
        ]

    @property
    def first_name(self):
        if self.full_name:
            return self.full_name.split()[0] if self.full_name.split() else ""
        return ""

    @property
    def last_name(self):
        if self.full_name:
            parts = self.full_name.split()
            return " ".join(parts[1:]) if len(parts) > 1 else ""
        return ""

    def get_initials(self):
        if self.full_name:
            parts = self.full_name.split()
            if len(parts) >= 2:
                return f"{parts[0][0]}{parts[-1][0]}".upper()
            elif len(parts) == 1:
                return parts[0][:2].upper()
        return "?"


# Import SyncMixin after Participant to avoid circular import
from .sync_mixin import SyncMixin


class ParticipantProfile(models.Model):
    participant = models.OneToOneField(
        Participant, on_delete=models.CASCADE, related_name="profile"
    )
    full_name = models.CharField(max_length=255)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20)
    profile_picture_url = models.URLField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = "participant_profiles"


# PatientData and DoctorData models moved to patient and doctor apps respectively


class ProviderData(models.Model):
    PROVIDER_TYPE_CHOICES = [
        ("hospital", "Hospital"),
        ("clinic", "Clinic"),
        ("pharmacy", "Pharmacy"),
        ("laboratory", "Laboratory"),
        ("diagnostic_center", "Diagnostic Center"),
    ]

    participant = models.OneToOneField(
        Participant, on_delete=models.CASCADE, related_name="provider_data"
    )
    provider_name = models.CharField(max_length=255)
    provider_type = models.CharField(max_length=50, choices=PROVIDER_TYPE_CHOICES)
    license_number = models.CharField(max_length=100, unique=True)
    registration_number = models.CharField(max_length=100, blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    website = models.URLField(blank=True)
    services_offered = models.JSONField(default=list)
    operating_hours = models.JSONField(default=dict)
    emergency_services = models.BooleanField(default=False)
    bed_capacity = models.IntegerField(null=True, blank=True)
    rating = models.FloatField(default=0.0)
    total_reviews = models.IntegerField(default=0)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = "participant_provider_data"  # Renamed from provider_data to use participant namespace


class InsuranceCompanyData(models.Model):
    participant = models.OneToOneField(
        Participant, on_delete=models.CASCADE, related_name="insurance_company_data"
    )
    company_name = models.CharField(max_length=255)
    license_number = models.CharField(max_length=100, unique=True)
    registration_number = models.CharField(max_length=100)
    address = models.TextField()
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    website = models.URLField(blank=True)
    coverage_types = models.JSONField(default=list)
    network_providers = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "insurance_company_data"


class AdminPermissions(models.Model):
    participant = models.OneToOneField(
        Participant, on_delete=models.CASCADE, related_name="admin_permissions"
    )
    full_system_access = models.BooleanField(default=False)
    payment_system_access = models.BooleanField(default=False)
    participant_management = models.BooleanField(default=False)
    analytics_access = models.BooleanField(default=False)
    audit_access = models.BooleanField(default=False)
    provider_verification = models.BooleanField(default=False)
    insurance_management = models.BooleanField(default=False)
    content_moderation = models.BooleanField(default=False)
    system_configuration = models.BooleanField(default=False)
    api_management = models.BooleanField(default=False)
    database_access = models.BooleanField(default=False)
    compliance_monitoring = models.BooleanField(default=False)
    financial_reports = models.BooleanField(default=False)
    emergency_access = models.BooleanField(default=False)

    class Meta:
        db_table = "admin_permissions"


# DependentProfile model moved to patient app


class StaffPermissions(models.Model):
    participant = models.OneToOneField(
        Participant, on_delete=models.CASCADE, related_name="staff_permissions"
    )
    can_manage_appointments = models.BooleanField(default=False)
    can_view_patient_records = models.BooleanField(default=False)
    can_edit_patient_records = models.BooleanField(default=False)
    can_prescribe_medication = models.BooleanField(default=False)
    can_manage_inventory = models.BooleanField(default=False)
    can_process_payments = models.BooleanField(default=False)
    can_manage_staff = models.BooleanField(default=False)
    can_view_reports = models.BooleanField(default=False)
    can_manage_schedules = models.BooleanField(default=False)

    class Meta:
        db_table = "staff_permissions"


class AuditLogEntry(models.Model):
    ACTION_TYPE_CHOICES = [
        ("create", "Create"),
        ("read", "Read"),
        ("update", "Update"),
        ("delete", "Delete"),
        ("login", "Login"),
        ("logout", "Logout"),
        ("payment", "Payment"),
        ("access_denied", "Access Denied"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participant = models.ForeignKey(
        Participant, on_delete=models.SET_NULL, null=True, related_name="audit_logs"
    )
    action_type = models.CharField(max_length=50, choices=ACTION_TYPE_CHOICES)
    resource_type = models.CharField(max_length=100)
    resource_id = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    details = models.JSONField(default=dict)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "audit_logs"
        indexes = [
            models.Index(fields=["participant", "timestamp"]),
            models.Index(fields=["action_type"]),
            models.Index(fields=["resource_type"]),
        ]


class ParticipantActivityLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="activity_logs"
    )
    activity_type = models.CharField(max_length=100)
    description = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict)

    class Meta:
        db_table = "participant_activity_logs"
        indexes = [
            models.Index(fields=["participant", "timestamp"]),
            models.Index(fields=["activity_type"]),
        ]


class RefundRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    REQUEST_TYPE_CHOICES = [
        ("cancelled_appointment", "Cancelled Appointment"),
        ("service_issue", "Service Issue"),
        ("billing_error", "Billing Error"),
        ("duplicate_payment", "Duplicate Payment"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="refund_requests"
    )
    transaction = models.ForeignKey(
        "Transaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="refund_requests",
    )
    request_type = models.CharField(max_length=50, choices=REQUEST_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="XAF")
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    admin_reviewer = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_refunds",
    )
    admin_notes = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    refund_transaction = models.ForeignKey(
        "Transaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="refund_for_requests",
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "refund_requests"
        indexes = [
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["admin_reviewer"]),
        ]

    def __str__(self):  # Returns string representation of refund request
        return f"Refund Request {self.id} - {self.provider.full_name} - {self.amount} {self.currency}"


class Wallet(SyncMixin):
    CURRENCY_CHOICES = [
        ("XOF", "Franc CFA UEMOA"),
        ("XAF", "Franc CFA CEMAC"),
        ("NGN", "Nigerian Naira"),
        ("GHS", "Ghanaian Cedi"),
        ("ZAR", "South African Rand"),
        ("KES", "Kenyan Shilling"),
        ("EGP", "Egyptian Pound"),
        ("MAD", "Moroccan Dirham"),
        ("TZS", "Tanzanian Shilling"),
        ("UGX", "Ugandan Shilling"),
        ("DZD", "Algerian Dinar"),
        ("TND", "Tunisian Dinar"),
        ("EUR", "Euro"),
        ("USD", "US Dollar"),
        ("GBP", "British Pound"),
        ("JPY", "Japanese Yen"),
        ("CNY", "Chinese Yuan"),
        ("CAD", "Canadian Dollar"),
        ("AUD", "Australian Dollar"),
        ("CHF", "Swiss Franc"),
        ("INR", "Indian Rupee"),
        ("KRW", "South Korean Won"),
        ("BRL", "Brazilian Real"),
        ("RUB", "Russian Ruble"),
        ("MXN", "Mexican Peso"),
        ("SEK", "Swedish Krona"),
        ("NOK", "Norwegian Krone"),
        ("DKK", "Danish Krone"),
        ("PLN", "Polish Zloty"),
        ("TRY", "Turkish Lira"),
        ("SAR", "Saudi Riyal"),
        ("AED", "UAE Dirham"),
        ("SGD", "Singapore Dollar"),
        ("HKD", "Hong Kong Dollar"),
        ("NZD", "New Zealand Dollar"),
        ("THB", "Thai Baht"),
        ("MYR", "Malaysian Ringgit"),
        ("IDR", "Indonesian Rupiah"),
        ("PHP", "Philippine Peso"),
        ("VND", "Vietnamese Dong"),
        ("ARS", "Argentine Peso"),
        ("CLP", "Chilean Peso"),
        ("COP", "Colombian Peso"),
        ("PEN", "Peruvian Sol"),
        ("ILS", "Israeli Shekel"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("suspended", "Suspended"),
        ("frozen", "Frozen"),
        ("closed", "Closed"),
    ]

    participant = models.OneToOneField(
        Participant, on_delete=models.CASCADE, related_name="core_wallet"
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, null=True, blank=True, help_text="DEPRECATED: Use computed ledger balance instead")
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="EUR")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    last_transaction_date = models.DateTimeField(null=True, blank=True)
    region_code = models.CharField(max_length=50, default="global", db_index=True)

    class Meta:
        db_table = "core_wallets"
        indexes = [
            models.Index(fields=["participant"]),
            models.Index(fields=["status"]),
        ]

    def get_ledger_balance(self):
        """Compute balance from Transaction ledger (Final Payment Model)"""
        from django.db.models import Sum, Q
        received = self.core_transactions.filter(
            Q(recipient=self.participant) & Q(status="completed")
        ).aggregate(total=Sum('amount_local'))['total'] or 0
        
        sent = self.core_transactions.filter(
            Q(sender=self.participant) & Q(status="completed")
        ).aggregate(total=Sum('amount_local'))['total'] or 0
        
        return received - sent

    def __str__(self):  # Returns string representation of wallet with balance
        ledger_balance = self.get_ledger_balance()
        return f"Wallet {self.participant.email} - {ledger_balance} {self.currency} (Ledger)"


class PaymentMethod(SyncMixin):
    PAYMENT_METHOD_TYPE_CHOICES = [
        ("fedapay", "FedaPay"),
        ("mobile_money", "Mobile Money"),
        ("card", "Credit/Debit Card"),
        ("bank_account", "Bank Account"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("expired", "Expired"),
        ("suspended", "Suspended"),
    ]

    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="payment_methods"
    )
    method_type = models.CharField(max_length=20, choices=PAYMENT_METHOD_TYPE_CHOICES)
    provider_name = models.CharField(max_length=100)
    account_identifier = models.CharField(max_length=255)
    is_default = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    external_token = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    region_code = models.CharField(max_length=50, default="global", db_index=True)

    class Meta:
        db_table = "payment_methods"
        indexes = [
            models.Index(fields=["participant", "is_default"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):  # Returns string representation of payment method
        return f"{self.participant.email} - {self.method_type} - {self.provider_name}"


class Transaction(SyncMixin):
    TRANSACTION_TYPE_CHOICES = [
        ("deposit", "Deposit"),
        ("withdrawal", "Withdrawal"),
        ("payment", "Payment"),
        ("refund", "Refund"),
        ("transfer", "Transfer"),
        ("commission", "Commission"),
        ("fee", "Fee"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
        ("reversed", "Reversed"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("card", "Credit/Debit Card"),
        ("bank_transfer", "Bank Transfer"),
        ("mobile_money", "Mobile Money"),
        ("cash", "Cash"),
        ("wallet", "Wallet Balance"),
        ("insurance", "Insurance"),
    ]

    PAYMENT_CONTEXT_CHOICES = [
        ("patient_service", "Patient Service Payment"),
        ("b2b_supplier", "B2B Supplier Payment"),
        ("payroll", "Payroll/Staff Payment"),
        ("other", "Other"),
    ]

    transaction_ref = models.CharField(max_length=50, unique=True)
    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, related_name="core_transactions",
        null=True, blank=True
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    
    # Dual currency fields (Final Payment Model)
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Reference amount in USD")
    amount_local = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Amount in participant local currency")
    currency_code = models.CharField(max_length=3, default="USD", help_text="Local currency code used for payment")
    exchange_rate_used = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True, help_text="Exchange rate at time of transaction")
    conversion_timestamp = models.DateTimeField(null=True, blank=True, help_text="When currency conversion was applied")
    
    # Commission tracking (1% BintaCura fee)
    commission_amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="BintaCura 1% commission in USD")
    commission_amount_local = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="BintaCura 1% commission in local currency")
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Tax amount (18% where applicable)")
    
    # Gateway integration
    gateway_transaction_id = models.CharField(max_length=255, null=True, blank=True, help_text="External gateway transaction ID")
    gateway_reference = models.CharField(max_length=255, null=True, blank=True, help_text="External gateway reference number")
    gateway_name = models.CharField(max_length=50, null=True, blank=True, help_text="Payment gateway used (FedaPay, etc)")
    
    # Currency resolution audit trail
    resolved_country = models.CharField(max_length=3, null=True, blank=True, help_text="Country resolved from phone + geolocation")
    resolution_method = models.CharField(max_length=20, null=True, blank=True, help_text="How currency was resolved: phone/geo/combined")
    
    # Payment context
    payment_context = models.CharField(max_length=30, choices=PAYMENT_CONTEXT_CHOICES, default="patient_service", help_text="Type of payment transaction")
    
    # Webhook data (source of truth)
    webhook_payload = models.JSONField(default=dict, blank=True, help_text="Full webhook payload from gateway")
    webhook_received_at = models.DateTimeField(null=True, blank=True, help_text="When webhook was received")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True
    )
    description = models.TextField()
    reference_id = models.CharField(max_length=255, null=True, blank=True)
    recipient = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="core_received_transactions",
    )
    sender = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="core_sent_transactions",
    )
    balance_before = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    completed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    region_code = models.CharField(max_length=50, default="global", db_index=True)

    class Meta:
        db_table = "core_transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["wallet", "-created_at"]),
            models.Index(fields=["transaction_ref"]),
            models.Index(fields=["status"], name="core_txn_status_idx"),
            models.Index(fields=["transaction_type"]),
            models.Index(fields=["gateway_transaction_id"], name="core_txn_gateway_idx"),
            models.Index(fields=["payment_context"], name="core_txn_context_idx"),
        ]

    def __str__(self):  # Returns string representation of transaction
        return (
            f"{self.transaction_type} - {self.amount} {self.currency} - {self.status}"
        )

    def save(self, *args, **kwargs):  # Generates transaction reference before saving
        if not self.transaction_ref:
            self.transaction_ref = f"TXN-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)



class Department(SyncMixin):
    hospital = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="departments"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    head_of_department = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_departments",
    )
    total_beds = models.IntegerField(default=0)
    occupied_beds = models.IntegerField(default=0)
    total_staff = models.IntegerField(default=0)
    phone_number = models.CharField(max_length=20, blank=True)
    floor_number = models.CharField(max_length=10, blank=True)
    is_active = models.BooleanField(default=True)
    region_code = models.CharField(max_length=50, default="global", db_index=True)

    class Meta:
        db_table = "departments"
        unique_together = [["hospital", "name"]]

    def __str__(self):  # Returns department name with hospital
        return f"{self.name} - {self.hospital.full_name}"


class MedicalEquipment(SyncMixin):
    STATUS_CHOICES = [
        ("available", "Available"),
        ("in_use", "In Use"),
        ("maintenance", "Maintenance"),
        ("out_of_order", "Out of Order"),
    ]

    CATEGORY_CHOICES = [
        ("diagnostic", "Diagnostic"),
        ("surgical", "Surgical"),
        ("life_support", "Life Support"),
        ("monitoring", "Monitoring"),
        ("therapeutic", "Therapeutic"),
        ("laboratory", "Laboratory"),
        ("other", "Other"),
    ]

    equipment_id = models.CharField(max_length=50, unique=True, blank=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    manufacturer = models.CharField(max_length=255, blank=True)
    model_number = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)

    hospital = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="equipment",
        limit_choices_to={"role": "hospital"},
    )

    location = models.CharField(max_length=255)
    department = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="available"
    )

    purchase_date = models.DateField(null=True, blank=True)
    purchase_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    warranty_expiry = models.DateField(null=True, blank=True)

    last_maintenance_date = models.DateField(null=True, blank=True)
    next_maintenance_date = models.DateField(null=True, blank=True)
    maintenance_interval_days = models.IntegerField(default=90)

    assigned_to_patient = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_equipment",
        limit_choices_to={"role": "patient"},
    )
    assigned_date = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)
    problem_description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    region_code = models.CharField(max_length=50, default="global", db_index=True)

    def save(self, *args, **kwargs):  # Auto-generates unique equipment ID before saving
        if not self.equipment_id:
            import random
            import string

            category_prefix = self.category[:3].upper() if self.category else "EQP"
            random_suffix = "".join(random.choices(string.digits, k=6))
            self.equipment_id = f"EQ-{category_prefix}-{random_suffix}"

            while MedicalEquipment.objects.filter(
                equipment_id=self.equipment_id
            ).exists():
                random_suffix = "".join(random.choices(string.digits, k=6))
                self.equipment_id = f"EQ-{category_prefix}-{random_suffix}"

        super().save(*args, **kwargs)

    class Meta:
        db_table = "medical_equipment"
        indexes = [
            models.Index(fields=["hospital", "status"]),
            models.Index(fields=["equipment_id"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):  # Returns equipment ID and name
        return f"{self.equipment_id} - {self.name}"


class ProviderService(SyncMixin):
    SERVICE_CATEGORY_CHOICES = [
        ("consultation", "Consultation"),
        ("surgery", "Surgery"),
        ("diagnostic", "Diagnostic"),
        ("laboratory", "Laboratory"),
        ("imaging", "Imaging"),
        ("therapy", "Therapy"),
        ("pharmacy", "Pharmacy"),
        ("emergency", "Emergency"),
        ("vaccination", "Vaccination"),
        ("dental", "Dental"),
        ("maternity", "Maternity"),
        ("pediatric", "Pediatric"),
        ("other", "Other"),
    ]

    provider = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="services"
    )
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=SERVICE_CATEGORY_CHOICES)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    duration_minutes = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    region_code = models.CharField(max_length=50, default="global", db_index=True)

    class Meta:
        db_table = "participant_services"
        indexes = [
            models.Index(fields=["provider", "category"]),
            models.Index(fields=["is_active", "is_available"]),
        ]
        ordering = ["category", "name"]

    def __str__(self):  # Returns service name with provider
        return f"{self.name} - {self.provider.full_name}"


class FeatureFlagConfig(models.Model):
    """
    Feature flag configuration for multi-region deployment.
    Enables dynamic feature control per region without code deployment.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    flag_name = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(help_text="What this feature flag controls")
    is_enabled = models.BooleanField(default=False)
    enabled_regions = models.TextField(
        blank=True,
        help_text="Comma-separated region codes (e.g., 'mali,benin') or 'all'"
    )
    rollout_percentage = models.IntegerField(
        default=100,
        help_text="Percentage of users to enable for (0-100)"
    )
    allowed_roles = models.TextField(
        blank=True,
        help_text="Comma-separated roles that can use this feature"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Set to False to disable this configuration"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "Participant",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_feature_flags"
    )
    
    class Meta:
        db_table = "feature_flag_configs"
        ordering = ["flag_name"]
        indexes = [
            models.Index(fields=["flag_name", "is_active"]),
            models.Index(fields=["is_enabled", "is_active"]),
        ]
    
    def __str__(self):  # Returns feature flag name with enabled status
        return f"{self.flag_name} ({'enabled' if self.is_enabled else 'disabled'})"


class RegionalConfiguration(models.Model):
    """
    Regional-specific configuration for multi-tenant deployment.
    Stores payment providers, API keys, and settings per region.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    region_code = models.CharField(max_length=50, unique=True, db_index=True)
    region_name = models.CharField(max_length=200)
    domain = models.CharField(max_length=255, help_text="e.g., ml.BINTACURA.com")
    country_code = models.CharField(max_length=2, help_text="ISO country code")
    region_timezone = models.CharField(max_length=50, default="UTC")
    language_code = models.CharField(max_length=10, default="fr")
    currency_code = models.CharField(max_length=3, default="XOF")
    
    # Payment configuration
    payment_provider = models.CharField(
        max_length=50,
        choices=[
            ("fedapay", "FedaPay"),
            ("stripe", "Stripe"),
            ("mtn_momo", "MTN Mobile Money"),
            ("orange_money", "Orange Money"),
        ]
    )
    payment_api_key_encrypted = models.TextField(blank=True)
    payment_webhook_secret = models.TextField(blank=True)
    
    # Regional limits
    max_appointment_distance_km = models.IntegerField(default=50)
    max_delivery_distance_km = models.IntegerField(default=20)
    
    # Status
    is_active = models.BooleanField(default=True)
    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(blank=True)
    
    # Database connection info (reference only, actual connection in settings)
    database_host = models.CharField(max_length=255, blank=True)
    database_name = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "regional_configurations"
        ordering = ["region_name"]
    
    def __str__(self):  # Returns region name with code
        return f"{self.region_name} ({self.region_code})"


class Review(SyncMixin):
    """
    Unified review system for doctors, hospitals, pharmacies, and insurance companies
    Tracks patient satisfaction and service quality across all providers
    """
    REVIEWED_TYPE_CHOICES = [
        ('doctor', 'Doctor'),
        ('hospital', 'Hospital'),
        ('pharmacy', 'Pharmacy'),
        ('insurance', 'Insurance Company'),
    ]

    SERVICE_TYPE_CHOICES = [
        ('consultation', 'Consultation'),
        ('telemedicine', 'Telemedicine'),
        ('prescription', 'Prescription'),
        ('pharmacy_service', 'Pharmacy Service'),
        ('insurance_claim', 'Insurance Claim'),
        ('hospital_service', 'Hospital Service'),
        ('emergency', 'Emergency Service'),
        ('surgery', 'Surgery'),
        ('diagnostic', 'Diagnostic Service'),
        ('other', 'Other'),
    ]

    # Reviewer information
    reviewer = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='reviews_given')

    # Reviewed entity (polymorphic relationship)
    reviewed_type = models.CharField(max_length=20, choices=REVIEWED_TYPE_CHOICES)
    reviewed_id = models.UUIDField(help_text="UUID of the doctor, hospital, pharmacy, or insurance company")

    # Rating and review details
    rating = models.IntegerField(choices=[(1, '1 Star'), (2, '2 Stars'), (3, '3 Stars'), (4, '4 Stars'), (5, '5 Stars')])
    service_type = models.CharField(max_length=30, choices=SERVICE_TYPE_CHOICES)
    review_text = models.TextField(blank=True, help_text="Optional review comments")

    # Service quality ratings (optional, 1-5)
    professionalism_rating = models.IntegerField(null=True, blank=True, help_text="Professionalism and courtesy")
    communication_rating = models.IntegerField(null=True, blank=True, help_text="Communication quality")
    facility_rating = models.IntegerField(null=True, blank=True, help_text="Facility cleanliness and quality")
    wait_time_rating = models.IntegerField(null=True, blank=True, help_text="Wait time satisfaction")
    value_rating = models.IntegerField(null=True, blank=True, help_text="Value for money")

    # Reference to appointment or service (if applicable)
    appointment_id = models.UUIDField(null=True, blank=True, help_text="Related appointment ID")

    # Verification and moderation
    is_verified = models.BooleanField(default=False, help_text="Verified by system as genuine review")
    is_approved = models.BooleanField(default=True, help_text="Approved for display")
    is_featured = models.BooleanField(default=False, help_text="Featured review")

    # Response from provider
    provider_response = models.TextField(blank=True, help_text="Response from service provider")
    provider_responded_at = models.DateTimeField(null=True, blank=True)
    region_code = models.CharField(max_length=50, default="global", db_index=True)

    class Meta:
        db_table = 'reviews'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reviewed_type', 'reviewed_id', '-created_at']),
            models.Index(fields=['reviewer', '-created_at']),
            models.Index(fields=['reviewed_type', 'reviewed_id', 'rating']),
            models.Index(fields=['appointment_id']),
            models.Index(fields=['is_approved', '-created_at']),
        ]
        unique_together = [['reviewer', 'appointment_id']]  # One review per appointment

    def __str__(self):
        return f"{self.rating}★ Review by {self.reviewer.full_name} for {self.reviewed_type}"

    @property
    def average_detailed_rating(self):
        """Calculate average of detailed ratings if provided"""
        ratings = [
            r for r in [
                self.professionalism_rating,
                self.communication_rating,
                self.facility_rating,
                self.wait_time_rating,
                self.value_rating
            ] if r is not None
        ]
        return sum(ratings) / len(ratings) if ratings else self.rating


# Import SystemConfiguration and Preferences
from .system_config import SystemConfiguration
from .preferences import ParticipantPreferences, EmergencyContact
from .legal_representative import LegalRepresentative


# Import hospital staff affiliation models
from .hospital_staff_models import HospitalStaffAffiliation, StaffPermission, get_doctor_payment_recipient, can_doctor_link_payment_account, can_doctor_affiliate_to_hospital

