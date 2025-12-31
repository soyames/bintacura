from django.db import models
from django.utils import timezone
import uuid
from core.models import Participant
from core.mixins import SyncMixin


class InsurancePackage(SyncMixin):  # Defines insurance coverage plans and premium details
    PACKAGE_TYPE_CHOICES = [
        ("individual", "Individual"),
        ("family", "Family"),
    ]

    PAYMENT_FREQUENCY_CHOICES = [
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("semi_annual", "Semi-Annual"),
        ("annual", "Annual"),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    company = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="insurance_packages"
    )
    name = models.CharField(max_length=255)
    description = models.TextField()
    package_type = models.CharField(
        max_length=20, choices=PACKAGE_TYPE_CHOICES, default="individual"
    )
    payment_frequency = models.CharField(
        max_length=20, choices=PAYMENT_FREQUENCY_CHOICES, default="monthly"
    )
    is_active = models.BooleanField(default=True)
    consultation_discount_percentage = models.FloatField(default=0.0)
    is_consultation_free = models.BooleanField(default=False)
    coverage_details = models.JSONField(default=dict, blank=True)
    premium_amount = models.IntegerField(default=0)
    max_coverage_amount = models.IntegerField(null=True, blank=True)

    class Meta:  # Meta class implementation
        db_table = "insurance_packages"
        indexes = [
            models.Index(fields=["company", "is_active"]),
        ]


class PatientInsuranceCard(SyncMixin):  # Represents patient insurance cards with policy information
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("expired", "Expired"),
        ("suspended", "Suspended"),
    ]

    patient = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="insurance_cards"
    )
    insurance_package = models.ForeignKey(
        InsurancePackage, on_delete=models.CASCADE, related_name="patient_cards"
    )
    card_number = models.CharField(max_length=100, unique=True)
    policy_number = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    issue_date = models.DateField()
    expiry_date = models.DateField()
    coverage_start_date = models.DateField()
    coverage_end_date = models.DateField()
    beneficiaries = models.JSONField(default=list, blank=True)
    card_image_url = models.URLField(blank=True)

    class Meta:  # Meta class implementation
        db_table = "patient_insurance_cards"
        indexes = [
            models.Index(fields=["patient", "status"]),
            models.Index(fields=["card_number"]),
        ]


class InsuranceClaim(SyncMixin):  # Tracks insurance claims submitted by patients for medical services
    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("underReview", "Under Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("paid", "Paid"),
    ]

    SERVICE_TYPE_CHOICES = [
        ("consultation", "Consultation"),
        ("prescription", "Prescription"),
        ("lab_test", "Lab Test"),
        ("hospitalization", "Hospitalization"),
        ("surgery", "Surgery"),
        ("emergency", "Emergency"),
    ]

    claim_number = models.CharField(max_length=100, unique=True)
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Client-provided unique key to prevent duplicate claim submission"
    )
    patient = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="insurance_claims"
    )
    insurance_card = models.ForeignKey(
        PatientInsuranceCard, on_delete=models.CASCADE, related_name="claims"
    )
    insurance_package = models.ForeignKey(
        InsurancePackage, on_delete=models.CASCADE, related_name="claims"
    )

    service_type = models.CharField(max_length=50, choices=SERVICE_TYPE_CHOICES)
    healthcare_provider = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_insurance_claims",
        help_text="Hospital, doctor, pharmacy, or other healthcare provider"
    )
    service_date = models.DateField()

    claimed_amount = models.IntegerField()
    approved_amount = models.IntegerField(default=0)
    paid_amount = models.IntegerField(default=0)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="submitted"
    )
    submission_date = models.DateTimeField(default=timezone.now)
    review_date = models.DateTimeField(null=True, blank=True)
    approval_date = models.DateTimeField(null=True, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)

    diagnosis = models.TextField(blank=True)
    treatment_details = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    reviewer_notes = models.TextField(blank=True)

    attachment_urls = models.JSONField(default=list, blank=True)

    class Meta:  # Meta class implementation
        db_table = "insurance_claims"
        ordering = ["-submission_date"]
        indexes = [
            models.Index(fields=["patient", "status"]),
            models.Index(fields=["claim_number"]),
        ]


class EnrollmentRequest(SyncMixin):  # Manages patient requests to enroll in insurance packages
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("under_review", "Under Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    patient = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="enrollment_requests"
    )
    insurance_package = models.ForeignKey(
        InsurancePackage, on_delete=models.CASCADE, related_name="enrollment_requests"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    requested_coverage_start = models.DateField()
    applicant_details = models.JSONField(default=dict)
    dependents_details = models.JSONField(default=list, blank=True)
    medical_history = models.JSONField(default=dict, blank=True)
    supporting_documents = models.JSONField(default=list, blank=True)
    rejection_reason = models.TextField(blank=True)
    reviewer_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_enrollments",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:  # Meta class implementation
        db_table = "enrollment_requests"
        ordering = ["-created_at"]


class InsuranceSubscription(SyncMixin):
    """Manages patient's active insurance subscriptions with recurring payments"""

    STATUS_CHOICES = [
        ("pending_approval", "En Attente d'Approbation"),
        ("active", "Active"),
        ("suspended", "Suspended"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    patient = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="insurance_subscriptions"
    )
    insurance_package = models.ForeignKey(
        InsurancePackage, on_delete=models.CASCADE, related_name="subscriptions"
    )
    insurance_card = models.OneToOneField(
        PatientInsuranceCard,
        on_delete=models.CASCADE,
        related_name="subscription",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending_approval")

    # Subscription dates
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    next_payment_date = models.DateField()
    last_payment_date = models.DateField(null=True, blank=True)

    # Payment details (in XOF cents)
    premium_amount = models.IntegerField(help_text="Premium amount in XOF cents")
    payment_frequency = models.CharField(max_length=20)
    total_paid = models.IntegerField(default=0, help_text="Total paid in XOF cents")
    payment_count = models.IntegerField(default=0)

    # Auto-renewal
    auto_renew = models.BooleanField(default=True)
    payment_method = models.CharField(max_length=50, default="fedapay_mobile", help_text="Payment method: fedapay_mobile, fedapay_card, mtn_momo, moov_money, orange_money")

    # Approval tracking
    approved_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_subscriptions"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_subscriptions"
    )

    # Metadata
    cancellation_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:  # Meta class implementation
        db_table = "insurance_subscriptions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["patient", "status"]),
            models.Index(fields=["next_payment_date", "status"]),
        ]

    def __str__(self):  # Return string representation
        return f"{self.patient.full_name} - {self.insurance_package.name}"


class InsuranceInvoice(SyncMixin):
    """Tracks insurance premium invoices and payments"""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("overdue", "Overdue"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    invoice_number = models.CharField(max_length=100, unique=True)
    subscription = models.ForeignKey(
        InsuranceSubscription, on_delete=models.CASCADE, related_name="invoices"
    )
    patient = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="insurance_invoices"
    )
    insurance_package = models.ForeignKey(
        InsurancePackage, on_delete=models.CASCADE, related_name="invoices"
    )

    # Invoice details
    amount = models.IntegerField(help_text="Amount in XOF cents")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Dates
    issue_date = models.DateField()
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)

    # Payment tracking
    transaction_ref = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(max_length=30, blank=True)

    # Period covered
    period_start = models.DateField()
    period_end = models.DateField()

    # Metadata
    notes = models.TextField(blank=True)

    class Meta:  # Meta class implementation
        db_table = "insurance_invoices"
        ordering = ["-issue_date"]
        indexes = [
            models.Index(fields=["patient", "status"]),
            models.Index(fields=["subscription"]),
            models.Index(fields=["invoice_number"]),
            models.Index(fields=["due_date", "status"]),
        ]

    def __str__(self):  # Return string representation
        return f"Invoice {self.invoice_number} - {self.patient.full_name}"


class ClaimAttachment(SyncMixin):  # Stores supporting documents attached to insurance claims
    DOCUMENT_TYPE_CHOICES = [
        ("medical_report", "Medical Report"),
        ("prescription", "Prescription"),
        ("invoice", "Invoice"),
        ("lab_result", "Lab Result"),
        ("xray", "X-Ray"),
        ("receipt", "Receipt"),
        ("referral_letter", "Referral Letter"),
        ("diagnosis_certificate", "Diagnosis Certificate"),
        ("other", "Other"),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    claim = models.ForeignKey(
        InsuranceClaim, on_delete=models.CASCADE, related_name="attachments"
    )
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPE_CHOICES)
    file_url = models.URLField()
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField()
    mime_type = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_claim_attachments",
    )
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_claim_attachments",
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:  # Meta class implementation
        db_table = "claim_attachments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["claim", "document_type"]),
            models.Index(fields=["is_verified"]),
        ]

    def __str__(self):  # Return string representation
        return f"{self.document_type} - {self.file_name}"


class HealthcarePartnerNetwork(SyncMixin):  # Defines partnerships between insurance companies and healthcare providers
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("suspended", "Suspended"),
        ("pending", "Pending Approval"),
    ]

    TIER_CHOICES = [
        ("premium", "Premium"),
        ("standard", "Standard"),
        ("basic", "Basic"),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    insurance_company = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="healthcare_networks"
    )
    healthcare_partner = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="network_memberships"
    )
    insurance_package = models.ForeignKey(
        InsurancePackage,
        on_delete=models.CASCADE,
        related_name="network_partners",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default="standard")
    discount_percentage = models.FloatField(default=0.0)
    contracted_rate = models.JSONField(default=dict, blank=True)
    services_covered = models.JSONField(default=list, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    contract_number = models.CharField(max_length=100, blank=True)
    terms_conditions = models.TextField(blank=True)
    is_preferred = models.BooleanField(default=False)
    patient_copay_percentage = models.FloatField(default=0.0)

    class Meta:  # Meta class implementation
        db_table = "healthcare_partner_networks"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["insurance_company", "status"]),
            models.Index(fields=["healthcare_partner", "status"]),
            models.Index(fields=["insurance_package"]),
        ]
        unique_together = [["insurance_company", "healthcare_partner", "insurance_package"]]

    def __str__(self):  # Return string representation
        package_name = (
            self.insurance_package.name if self.insurance_package else "All Packages"
        )
        return f"{self.healthcare_partner.full_name} - {package_name}"


class InsuranceCoverageEnquiry(SyncMixin):  # Handles patient inquiries about insurance coverage for specific services
    SERVICE_TYPE_CHOICES = [
        ("consultation", "Consultation"),
        ("prescription", "Prescription"),
        ("lab_test", "Laboratory Test"),
        ("imaging", "Medical Imaging"),
        ("surgery", "Surgery"),
        ("hospitalization", "Hospitalization"),
        ("emergency", "Emergency"),
        ("dental", "Dental"),
        ("optical", "Optical"),
        ("maternity", "Maternity"),
        ("physiotherapy", "Physiotherapy"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("under_review", "Under Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("expired", "Expired"),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    enquiry_number = models.CharField(max_length=100, unique=True)

    patient = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="coverage_enquiries"
    )
    insurance_card = models.ForeignKey(
        PatientInsuranceCard, on_delete=models.CASCADE, related_name="enquiries"
    )
    insurance_package = models.ForeignKey(
        InsurancePackage, on_delete=models.CASCADE, related_name="enquiries"
    )

    service_type = models.CharField(max_length=50, choices=SERVICE_TYPE_CHOICES)
    service_name = models.CharField(max_length=255)
    service_description = models.TextField()
    estimated_cost = models.IntegerField(help_text="Estimated cost in XOF cents")

    healthcare_provider = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_coverage_enquiries",
        help_text="Hospital, doctor, pharmacy, or other healthcare provider"
    )
    planned_date = models.DateField()

    medical_necessity = models.TextField()
    doctor_recommendation = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    insurance_coverage_percentage = models.FloatField(null=True, blank=True)
    insurance_covers_amount = models.IntegerField(null=True, blank=True, help_text="Amount covered in XOF cents")
    patient_pays_amount = models.IntegerField(null=True, blank=True, help_text="Patient payment in XOF cents")

    approval_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    conditions = models.TextField(blank=True)

    reviewed_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_enquiries",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    attachment_urls = models.JSONField(default=list, blank=True)

    class Meta:  # Meta class implementation
        db_table = "insurance_coverage_enquiries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["patient", "status"]),
            models.Index(fields=["insurance_package", "status"]),
            models.Index(fields=["enquiry_number"]),
        ]

    def __str__(self):  # Return string representation
        return f"{self.enquiry_number} - {self.service_name}"


class InsuranceStaff(SyncMixin):  # Manages insurance company staff members and their permissions
    """Manages insurance company staff members and their permissions"""

    STAFF_ROLE_CHOICES = [
        ("claims_processor", "Claims Processor"),
        ("underwriter", "Underwriter"),
        ("customer_service", "Customer Service"),
        ("manager", "Manager"),
        ("administrator", "Administrator"),
    ]

    PERMISSION_CHOICES = [
        ("view_claims", "View Claims"),
        ("process_claims", "Process Claims"),
        ("approve_claims", "Approve Claims"),
        ("view_subscriptions", "View Subscriptions"),
        ("approve_subscriptions", "Approve Subscriptions"),
        ("manage_packages", "Manage Packages"),
        ("view_reports", "View Reports"),
        ("manage_staff", "Manage Staff"),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    staff_participant = models.OneToOneField(
        Participant,
        on_delete=models.CASCADE,
        related_name="insurance_staff_profile"
    )
    insurance_company = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="insurance_staff_members"
    )
    staff_role = models.CharField(max_length=50, choices=STAFF_ROLE_CHOICES)
    department = models.CharField(max_length=100, blank=True)
    employee_id = models.CharField(max_length=100, blank=True)

    # Permissions as JSON field for flexibility
    permissions = models.JSONField(default=list, blank=True)

    # Status
    is_active = models.BooleanField(default=True)

    # Manager/supervisor relationship
    supervisor = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supervised_staff"
    )

    # Metadata
    hire_date = models.DateField(default=timezone.now)
    termination_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:  # Meta class implementation
        db_table = "insurance_staff"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["insurance_company", "is_active"]),
            models.Index(fields=["staff_role"]),
        ]
        verbose_name = "Insurance Staff"
        verbose_name_plural = "Insurance Staff"

    def __str__(self):
        return f"{self.staff_participant.full_name} - {self.get_staff_role_display()}"


# COVERAGE CONFIGURATION MODELS - ISSUE-INS-007, INS-008

class ServiceCategory(SyncMixin):
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    insurance_company = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='service_categories')
    category_name = models.CharField(max_length=255)
    category_code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    parent_category = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subcategories')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'service_categories'
        indexes = [
            models.Index(fields=['insurance_company', 'is_active']),
            models.Index(fields=['category_code']),
        ]

    def __str__(self):
        return f"{self.category_name} ({self.category_code})"


class CoverageRule(SyncMixin):
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    insurance_package = models.ForeignKey(InsurancePackage, on_delete=models.CASCADE, related_name='coverage_rules')
    service_category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='coverage_rules')
    coverage_percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentage covered by insurance")
    max_coverage_per_service = models.IntegerField(null=True, blank=True, help_text="Max amount per service in XOF cents")
    max_coverage_per_year = models.IntegerField(null=True, blank=True, help_text="Annual limit for this category")
    waiting_period_days = models.IntegerField(default=0, help_text="Days before coverage starts")
    requires_pre_authorization = models.BooleanField(default=False)
    is_excluded = models.BooleanField(default=False, help_text="Service excluded from coverage")
    exclusion_reason = models.TextField(blank=True)
    conditions = models.TextField(blank=True, help_text="Special conditions or restrictions")
    is_active = models.BooleanField(default=True)
    effective_date = models.DateField(default=timezone.now)
    expiration_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'coverage_rules'
        indexes = [
            models.Index(fields=['insurance_package', 'is_active']),
            models.Index(fields=['service_category']),
        ]

    def __str__(self):
        return f"{self.insurance_package.name} - {self.service_category.category_name}: {self.coverage_percentage}%"


class CopayDeductibleConfig(SyncMixin):
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    insurance_package = models.ForeignKey(InsurancePackage, on_delete=models.CASCADE, related_name='copay_configs')
    annual_deductible = models.IntegerField(default=0, help_text="Annual deductible in XOF cents")
    out_of_pocket_maximum = models.IntegerField(null=True, blank=True, help_text="Annual OOP max in XOF cents")
    copay_consultation = models.IntegerField(default=0, help_text="Fixed copay for consultations")
    copay_specialist = models.IntegerField(default=0, help_text="Fixed copay for specialists")
    copay_emergency = models.IntegerField(default=0, help_text="Fixed copay for emergency")
    copay_prescription_generic = models.IntegerField(default=0)
    copay_prescription_brand = models.IntegerField(default=0)
    copay_lab_test = models.IntegerField(default=0)
    copay_imaging = models.IntegerField(default=0)
    coinsurance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Patient's share after deductible")
    deductible_applies_to_prescriptions = models.BooleanField(default=True)
    deductible_applies_to_preventive = models.BooleanField(default=False, help_text="Preventive care exempt from deductible")
    family_deductible_multiplier = models.DecimalField(max_digits=3, decimal_places=1, default=2.0)
    effective_date = models.DateField(default=timezone.now)
    expiration_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'copay_deductible_configs'
        indexes = [
            models.Index(fields=['insurance_package']),
            models.Index(fields=['effective_date']),
        ]

    def __str__(self):
        # Amount stored in XOF cents - display formatted
        return f"{self.insurance_package.name} - Deductible: ${self.annual_deductible/100:.2f}"


# CLAIMS ADJUDICATION MODELS - ISSUE-INS-027, INS-028, INS-029, INS-030

class FeeSchedule(SyncMixin):
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    insurance_company = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='fee_schedules')
    service_category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='fee_schedules')
    service_code = models.CharField(max_length=50, help_text="CPT, ICD, or internal code")
    service_description = models.CharField(max_length=255)
    usual_and_customary_rate = models.IntegerField(help_text="Typical market rate in XOF cents")
    maximum_allowed_amount = models.IntegerField(help_text="Max amount insurance will consider in XOF cents")
    contracted_rate = models.IntegerField(null=True, blank=True, help_text="Negotiated rate with providers in XOF cents")
    geographic_modifier = models.DecimalField(max_digits=4, decimal_places=2, default=1.0, help_text="Regional cost adjustment")
    effective_date = models.DateField(default=timezone.now)
    expiration_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'fee_schedules'
        indexes = [
            models.Index(fields=['insurance_company', 'is_active']),
            models.Index(fields=['service_code']),
            models.Index(fields=['service_category']),
        ]

    def __str__(self):
        # Amount stored in XOF cents - display formatted
        return f"{self.service_code} - {self.service_description}: ${self.maximum_allowed_amount/100:.2f}"


class ClaimAdjudicationRule(SyncMixin):
    RULE_TYPE_CHOICES = [
        ('coverage_check', 'Coverage Verification'),
        ('eligibility_check', 'Eligibility Check'),
        ('deductible_calculation', 'Deductible Calculation'),
        ('copay_calculation', 'Copay Calculation'),
        ('coinsurance_calculation', 'Coinsurance Calculation'),
        ('maximum_benefit_check', 'Maximum Benefit Check'),
        ('pre_authorization_check', 'Pre-Authorization Required'),
        ('duplicate_check', 'Duplicate Claim Check'),
        ('timely_filing', 'Timely Filing Check'),
        ('pricing_verification', 'Pricing Reasonableness'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    insurance_company = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='adjudication_rules')
    rule_name = models.CharField(max_length=255)
    rule_type = models.CharField(max_length=50, choices=RULE_TYPE_CHOICES)
    rule_code = models.CharField(max_length=50, unique=True)
    priority_order = models.IntegerField(default=100, help_text="Lower numbers execute first")
    applies_to_service_category = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='adjudication_rules')
    rule_logic = models.JSONField(default=dict, help_text="Rule conditions and calculations")
    auto_approve_threshold = models.IntegerField(null=True, blank=True, help_text="Auto-approve claims below this amount")
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    error_message = models.TextField(blank=True, help_text="Message when rule fails")

    class Meta:
        db_table = 'claim_adjudication_rules'
        ordering = ['priority_order']
        indexes = [
            models.Index(fields=['insurance_company', 'is_active']),
            models.Index(fields=['rule_type']),
            models.Index(fields=['priority_order']),
        ]

    def __str__(self):
        return f"{self.rule_code} - {self.rule_name}"


class ClaimAdjudicationResult(SyncMixin):
    STATUS_CHOICES = [
        ('auto_approved', 'Auto-Approved'),
        ('auto_denied', 'Auto-Denied'),
        ('requires_review', 'Requires Manual Review'),
        ('pended', 'Pended for Information'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    claim = models.OneToOneField(InsuranceClaim, on_delete=models.CASCADE, related_name='adjudication_result')
    adjudication_date = models.DateTimeField(default=timezone.now)
    adjudication_status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    total_billed_amount = models.IntegerField()
    allowed_amount = models.IntegerField(help_text="Amount allowed per fee schedule")
    deductible_applied = models.IntegerField(default=0)
    copay_applied = models.IntegerField(default=0)
    coinsurance_applied = models.IntegerField(default=0)
    insurance_pays = models.IntegerField(help_text="Final amount insurance will pay")
    patient_responsibility = models.IntegerField(help_text="Patient owes this amount")
    reduction_reason = models.TextField(blank=True, help_text="Why billed amount was reduced")
    rules_applied = models.JSONField(default=list, help_text="List of rules that were applied")
    warnings = models.JSONField(default=list, blank=True)
    errors = models.JSONField(default=list, blank=True)
    requires_medical_review = models.BooleanField(default=False)
    requires_fraud_review = models.BooleanField(default=False)
    processing_time_seconds = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    adjudicated_by = models.CharField(max_length=50, default='AUTO', help_text="System or staff member")
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'claim_adjudication_results'
        indexes = [
            models.Index(fields=['adjudication_status']),
            models.Index(fields=['requires_medical_review']),
            models.Index(fields=['adjudication_date']),
        ]

    def __str__(self):
        return f"Adjudication for {self.claim.claim_number}: {self.adjudication_status}"


class MedicalNecessityReview(SyncMixin):
    REVIEW_STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Medically Necessary'),
        ('denied', 'Not Medically Necessary'),
        ('additional_info_needed', 'Need More Information'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    claim = models.ForeignKey(InsuranceClaim, on_delete=models.CASCADE, related_name='medical_reviews')
    review_date = models.DateTimeField(default=timezone.now)
    reviewer = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, related_name='medical_reviews_conducted')
    diagnosis_code = models.CharField(max_length=50, blank=True)
    procedure_code = models.CharField(max_length=50, blank=True)
    clinical_rationale = models.TextField(blank=True)
    medical_records_reviewed = models.TextField(blank=True)
    review_status = models.CharField(max_length=50, choices=REVIEW_STATUS_CHOICES, default='pending')
    denial_reason = models.TextField(blank=True)
    alternative_treatment_suggested = models.TextField(blank=True)
    peer_review_required = models.BooleanField(default=False)
    peer_reviewer = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True, related_name='peer_reviews_conducted')
    final_decision = models.TextField(blank=True)
    appeal_deadline = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'medical_necessity_reviews'
        indexes = [
            models.Index(fields=['claim']),
            models.Index(fields=['review_status']),
            models.Index(fields=['review_date']),
        ]

    def __str__(self):
        return f"Medical Review for {self.claim.claim_number}: {self.review_status}"


# PROVIDER MANAGEMENT MODELS - ISSUE-INS-037, INS-038, INS-040, INS-042

class ProviderCredential(SyncMixin):
    STATUS_CHOICES = [
        ('application_received', 'Application Received'),
        ('under_review', 'Under Review'),
        ('verification_in_progress', 'Verification in Progress'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    insurance_company = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='provider_credentials')
    provider = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='insurance_credentials')
    credential_number = models.CharField(max_length=100, unique=True)
    application_date = models.DateField(default=timezone.now)
    approval_date = models.DateField(null=True, blank=True)
    expiration_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='application_received')
    license_number = models.CharField(max_length=100, blank=True)
    license_verified = models.BooleanField(default=False)
    license_verification_date = models.DateField(null=True, blank=True)
    board_certification = models.CharField(max_length=255, blank=True)
    board_cert_verified = models.BooleanField(default=False)
    malpractice_insurance = models.CharField(max_length=255, blank=True)
    malpractice_verified = models.BooleanField(default=False)
    dea_number = models.CharField(max_length=50, blank=True)
    npi_number = models.CharField(max_length=50, blank=True)
    education_credentials = models.JSONField(default=list, blank=True)
    hospital_affiliations = models.JSONField(default=list, blank=True)
    references_checked = models.BooleanField(default=False)
    background_check_completed = models.BooleanField(default=False)
    credentialing_committee_approved = models.BooleanField(default=False)
    committee_approval_date = models.DateField(null=True, blank=True)
    recredentialing_due_date = models.DateField(null=True, blank=True)
    denial_reason = models.TextField(blank=True)
    verified_by = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True, related_name='credentials_verified')
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'insurance_provider_credentials'  # Renamed from provider_credentials
        indexes = [
            models.Index(fields=['insurance_company', 'status']),
            models.Index(fields=['provider']),
            models.Index(fields=['credential_number']),
            models.Index(fields=['expiration_date']),
        ]

    def __str__(self):
        return f"{self.credential_number} - {self.provider.full_name}: {self.status}"


class ProviderContract(SyncMixin):
    CONTRACT_TYPE_CHOICES = [
        ('fee_for_service', 'Fee-for-Service'),
        ('capitation', 'Capitation'),
        ('case_rate', 'Case Rate'),
        ('per_diem', 'Per Diem'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('under_negotiation', 'Under Negotiation'),
        ('pending_approval', 'Pending Approval'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    insurance_company = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='provider_contracts')
    provider = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='insurance_contracts')
    contract_number = models.CharField(max_length=100, unique=True)
    contract_type = models.CharField(max_length=50, choices=CONTRACT_TYPE_CHOICES)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='draft')
    effective_date = models.DateField()
    termination_date = models.DateField(null=True, blank=True)
    auto_renew = models.BooleanField(default=False)
    renewal_notice_days = models.IntegerField(default=90)
    payment_terms = models.CharField(max_length=255, default='Net 30')
    reimbursement_rates = models.JSONField(default=dict, help_text="Fee schedule or rates")
    capitation_amount_per_member = models.IntegerField(null=True, blank=True)
    services_covered = models.JSONField(default=list)
    quality_metrics = models.JSONField(default=list, blank=True)
    performance_bonus_structure = models.JSONField(default=dict, blank=True)
    claim_submission_deadline_days = models.IntegerField(default=90)
    credentialing_requirements = models.TextField(blank=True)
    termination_clause = models.TextField(blank=True)
    dispute_resolution_process = models.TextField(blank=True)
    contract_document_url = models.URLField(blank=True)
    signed_by_provider = models.BooleanField(default=False)
    provider_signature_date = models.DateField(null=True, blank=True)
    signed_by_insurance = models.BooleanField(default=False)
    insurance_signature_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'insurance_provider_contracts'  # Renamed from provider_contracts
        indexes = [
            models.Index(fields=['insurance_company', 'status']),
            models.Index(fields=['provider', 'status']),
            models.Index(fields=['contract_number']),
            models.Index(fields=['effective_date', 'termination_date']),
        ]

    def __str__(self):
        return f"{self.contract_number} - {self.provider.full_name}"


class ProviderPerformance(SyncMixin):
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    insurance_company = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='provider_performance_records')
    provider = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='performance_records')
    measurement_period_start = models.DateField()
    measurement_period_end = models.DateField()
    total_claims_submitted = models.IntegerField(default=0)
    total_claims_approved = models.IntegerField(default=0)
    total_claims_denied = models.IntegerField(default=0)
    average_claim_amount = models.IntegerField(default=0)
    total_reimbursed = models.IntegerField(default=0)
    claims_denial_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Percentage")
    average_claim_processing_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    patient_complaints_count = models.IntegerField(default=0)
    quality_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="0-100")
    cost_efficiency_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    member_satisfaction_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    readmission_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    preventive_care_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    outlier_flag = models.BooleanField(default=False, help_text="Statistical outlier detected")
    outlier_reason = models.TextField(blank=True)
    performance_tier = models.CharField(max_length=20, choices=[
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('below_average', 'Below Average'),
        ('poor', 'Poor'),
    ], blank=True)
    bonus_earned = models.IntegerField(default=0, help_text="Performance bonus in XOF cents")
    penalty_assessed = models.IntegerField(default=0, help_text="Performance penalty in XOF cents")
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'insurance_provider_performance'  # Renamed from provider_performance
        ordering = ['-measurement_period_end']
        indexes = [
            models.Index(fields=['insurance_company', 'provider']),
            models.Index(fields=['measurement_period_start', 'measurement_period_end']),
            models.Index(fields=['outlier_flag']),
        ]

    def __str__(self):
        return f"{self.provider.full_name} - {self.measurement_period_start} to {self.measurement_period_end}"


# UNDERWRITING MODELS - ISSUE-INS-014, INS-056, INS-057

class UnderwritingApplication(SyncMixin):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('medical_exam_required', 'Medical Exam Required'),
        ('approved_standard', 'Approved - Standard Rate'),
        ('approved_rated', 'Approved - Rated (Higher Premium)'),
        ('approved_with_exclusions', 'Approved with Exclusions'),
        ('declined', 'Declined'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    enrollment_request = models.OneToOneField(EnrollmentRequest, on_delete=models.CASCADE, related_name='underwriting')
    application_number = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='submitted')
    submission_date = models.DateTimeField(default=timezone.now)
    underwriter_assigned = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True, related_name='underwriting_assignments')
    health_questionnaire_data = models.JSONField(default=dict)
    pre_existing_conditions = models.JSONField(default=list)
    medical_exam_required = models.BooleanField(default=False)
    medical_exam_scheduled_date = models.DateField(null=True, blank=True)
    medical_exam_completed = models.BooleanField(default=False)
    medical_exam_results = models.JSONField(default=dict, blank=True)
    risk_score = models.IntegerField(null=True, blank=True, help_text="Calculated risk score")
    premium_rating_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    final_premium_amount = models.IntegerField(null=True, blank=True)
    exclusions_list = models.JSONField(default=list, blank=True)
    decline_reason = models.TextField(blank=True)
    underwriter_notes = models.TextField(blank=True)
    approved_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'underwriting_applications'
        indexes = [
            models.Index(fields=['application_number']),
            models.Index(fields=['status']),
            models.Index(fields=['submission_date']),
        ]

    def __str__(self):
        return f"{self.application_number} - {self.status}"


class RiskAssessment(SyncMixin):
    RISK_LEVEL_CHOICES = [
        ('very_low', 'Very Low Risk'),
        ('low', 'Low Risk'),
        ('moderate', 'Moderate Risk'),
        ('high', 'High Risk'),
        ('very_high', 'Very High Risk'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    underwriting_application = models.OneToOneField(UnderwritingApplication, on_delete=models.CASCADE, related_name='risk_assessment')
    age_risk_score = models.IntegerField(default=0)
    bmi_risk_score = models.IntegerField(default=0)
    smoking_status = models.CharField(max_length=20, choices=[('smoker', 'Smoker'), ('non_smoker', 'Non-Smoker'), ('former', 'Former Smoker')], blank=True)
    smoking_risk_score = models.IntegerField(default=0)
    medical_history_risk_score = models.IntegerField(default=0)
    family_history_risk_score = models.IntegerField(default=0)
    occupation_risk_score = models.IntegerField(default=0)
    lifestyle_risk_score = models.IntegerField(default=0)
    total_risk_score = models.IntegerField(default=0)
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES)
    chronic_conditions = models.JSONField(default=list)
    high_risk_factors = models.JSONField(default=list)
    recommended_exclusions = models.JSONField(default=list, blank=True)
    recommended_premium_adjustment = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    assessment_date = models.DateTimeField(default=timezone.now)
    assessed_by = models.CharField(max_length=50, default='AUTO')
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'risk_assessments'
        indexes = [
            models.Index(fields=['risk_level']),
            models.Index(fields=['assessment_date']),
        ]

    def __str__(self):
        return f"Risk Assessment for {self.underwriting_application.application_number}: {self.risk_level}"


# MEMBER LIFECYCLE MODELS - ISSUE-INS-022, INS-023

class MembershipRenewal(SyncMixin):
    STATUS_CHOICES = [
        ('upcoming', 'Renewal Upcoming'),
        ('notified', 'Member Notified'),
        ('renewed', 'Renewed'),
        ('cancelled', 'Cancelled'),
        ('lapsed', 'Lapsed'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    subscription = models.ForeignKey(InsuranceSubscription, on_delete=models.CASCADE, related_name='renewals')
    current_term_end_date = models.DateField()
    renewal_date = models.DateField()
    renewal_premium = models.IntegerField()
    notification_sent_date = models.DateField(null=True, blank=True)
    member_confirmed = models.BooleanField(default=False)
    member_confirmation_date = models.DateField(null=True, blank=True)
    auto_renewed = models.BooleanField(default=False)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='upcoming')
    payment_due_date = models.DateField()
    payment_received_date = models.DateField(null=True, blank=True)
    grace_period_ends = models.DateField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    new_subscription = models.OneToOneField(InsuranceSubscription, on_delete=models.SET_NULL, null=True, blank=True, related_name='renewal_from')
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'membership_renewals'
        indexes = [
            models.Index(fields=['subscription', 'status']),
            models.Index(fields=['renewal_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Renewal for {self.subscription} - {self.status}"


class GracePeriod(SyncMixin):
    STATUS_CHOICES = [
        ('active', 'Grace Period Active'),
        ('payment_received', 'Payment Received'),
        ('expired', 'Grace Period Expired'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    subscription = models.ForeignKey(InsuranceSubscription, on_delete=models.CASCADE, related_name='grace_periods')
    invoice = models.ForeignKey(InsuranceInvoice, on_delete=models.CASCADE, related_name='grace_periods')
    original_due_date = models.DateField()
    grace_period_start = models.DateField()
    grace_period_end = models.DateField()
    grace_period_days = models.IntegerField(default=30)
    amount_due = models.IntegerField()
    late_fee = models.IntegerField(default=0)
    total_amount_due = models.IntegerField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='active')
    reminder_sent_count = models.IntegerField(default=0)
    last_reminder_sent = models.DateField(null=True, blank=True)
    payment_received = models.BooleanField(default=False)
    payment_date = models.DateField(null=True, blank=True)
    coverage_suspended_during_grace = models.BooleanField(default=False)
    termination_notice_sent = models.BooleanField(default=False)
    termination_notice_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'grace_periods'
        indexes = [
            models.Index(fields=['subscription', 'status']),
            models.Index(fields=['grace_period_end', 'status']),
        ]

    def __str__(self):
        return f"Grace Period for {self.subscription.patient.full_name} - Ends {self.grace_period_end}"


# FRAUD DETECTION MODEL - ISSUE-INS-066

class FraudAlert(SyncMixin):
    ALERT_TYPE_CHOICES = [
        ('duplicate_claim', 'Duplicate Claim Detected'),
        ('unusual_billing_pattern', 'Unusual Billing Pattern'),
        ('service_not_covered', 'Service Not Covered'),
        ('provider_outlier', 'Provider Statistical Outlier'),
        ('member_outlier', 'Member Usage Outlier'),
        ('upcoding_suspected', 'Upcoding Suspected'),
        ('phantom_billing', 'Phantom Billing Suspected'),
        ('identity_theft', 'Possible Identity Theft'),
        ('unbundling', 'Service Unbundling Detected'),
    ]

    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('detected', 'Alert Detected'),
        ('under_investigation', 'Under Investigation'),
        ('confirmed_fraud', 'Confirmed Fraud'),
        ('false_positive', 'False Positive'),
        ('resolved', 'Resolved'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    alert_number = models.CharField(max_length=100, unique=True)
    insurance_company = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='fraud_alerts')
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='detected')
    detection_date = models.DateTimeField(default=timezone.now)
    claim = models.ForeignKey(InsuranceClaim, on_delete=models.SET_NULL, null=True, blank=True, related_name='fraud_alerts')
    provider = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True, related_name='fraud_alerts_provider')
    member = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True, related_name='fraud_alerts_member')
    pattern_description = models.TextField()
    evidence_data = models.JSONField(default=dict, help_text="Data supporting the alert")
    risk_score = models.IntegerField(help_text="Fraud risk score 0-100")
    potential_loss_amount = models.IntegerField(default=0)
    related_claims = models.JSONField(default=list, blank=True, help_text="List of related claim IDs")
    assigned_investigator = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True, related_name='fraud_investigations')
    investigation_notes = models.TextField(blank=True)
    investigation_start_date = models.DateField(null=True, blank=True)
    investigation_end_date = models.DateField(null=True, blank=True)
    outcome = models.TextField(blank=True)
    action_taken = models.TextField(blank=True)
    recovery_amount = models.IntegerField(default=0)
    law_enforcement_notified = models.BooleanField(default=False)
    law_enforcement_case_number = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'fraud_alerts'
        ordering = ['-detection_date']
        indexes = [
            models.Index(fields=['insurance_company', 'status']),
            models.Index(fields=['alert_type', 'severity']),
            models.Index(fields=['provider']),
            models.Index(fields=['member']),
            models.Index(fields=['detection_date']),
            models.Index(fields=['risk_score']),
        ]

    def __str__(self):
        return f"{self.alert_number} - {self.alert_type}: {self.severity}"
