from django.contrib import admin
from .models import (
    FeeLedger,
    HealthTransaction,
    ProviderPayout,
    DoctorPayout,
    PaymentReceipt,
    PaymentRequest,
    Transfer,
    LinkedVendor,
    FinancialChat,
    FinancialChatMessage,
    FedaPayCustomer,
    FedaPayTransaction,
    FedaPayPayout,
    FedaPayWebhookEvent,
    InvoiceSettings,
    Vendor,
    ExpenseCategory,
    VendorInvoice,
)
from .participant_payment_models import ParticipantPaymentMethod, PaymentMethodVerification


@admin.register(FeeLedger)
class FeeLedgerAdmin(admin.ModelAdmin):  # Admin configuration for FeeLedger model
    list_display = (
        "id",
        "provider",
        "service_amount",
        "fee_amount",
        "fee_percentage",
        "status",
        "payment_method",
        "created_at",
    )
    list_filter = ("status", "payment_method")
    search_fields = ("provider__email", "related_transaction_id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(HealthTransaction)
class HealthTransactionAdmin(admin.ModelAdmin):  # Admin configuration for HealthTransaction model
    list_display = ("id", "patient", "provider", "transaction", "created_at")
    search_fields = ("patient__email", "provider__email")


@admin.register(ProviderPayout)
class ProviderPayoutAdmin(admin.ModelAdmin):  # Admin configuration for ProviderPayout model
    list_display = (
        "id",
        "provider",
        "amount",
        "status",
        "period_start",
        "period_end",
        "transaction_count",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("provider__email",)
    date_hierarchy = "created_at"


@admin.register(DoctorPayout)
class DoctorPayoutAdmin(admin.ModelAdmin):  # Admin configuration for DoctorPayout model
    list_display = (
        "id",
        "doctor",
        "amount",
        "status",
        "period_start",
        "period_end",
        "consultation_count",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("doctor__email",)
    date_hierarchy = "created_at"


@admin.register(PaymentReceipt)
class PaymentReceiptAdmin(admin.ModelAdmin):  # Admin configuration for PaymentReceipt model
    list_display = ("id", "receipt_number", "issued_to", "issued_by", "issued_at")
    search_fields = ("receipt_number", "issued_to__email")
    readonly_fields = ("issued_at",)


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):  # Admin configuration for PaymentRequest model
    list_display = (
        "id",
        "from_participant",
        "to_participant",
        "amount",
        "status",
        "created_at",
        "responded_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("from_participant__email", "to_participant__email")
    readonly_fields = ("created_at", "updated_at", "responded_at")
    date_hierarchy = "created_at"


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):  # Admin configuration for Transfer model
    list_display = (
        "id",
        "from_participant",
        "to_participant",
        "amount",
        "transfer_type",
        "status",
        "created_at",
        "completed_at",
    )
    list_filter = ("transfer_type", "status", "created_at")
    search_fields = ("from_participant__email", "to_participant__email", "external_reference")
    readonly_fields = ("created_at", "updated_at", "completed_at")
    date_hierarchy = "created_at"


@admin.register(LinkedVendor)
class LinkedVendorAdmin(admin.ModelAdmin):  # Admin configuration for LinkedVendor model
    list_display = (
        "id",
        "participant",
        "vendor_type",
        "vendor_name",
        "status",
        "is_default",
        "is_verified",
        "created_at",
        "last_used_at",
    )
    list_filter = ("vendor_type", "status", "is_verified", "is_default")
    search_fields = ("participant__email", "vendor_name", "account_identifier")
    readonly_fields = ("created_at", "updated_at", "last_used_at")
    date_hierarchy = "created_at"


@admin.register(FinancialChat)
class FinancialChatAdmin(admin.ModelAdmin):  # Admin configuration for FinancialChat model
    list_display = (
        "id",
        "participant",
        "subject",
        "status",
        "priority",
        "assigned_to",
        "created_at",
        "resolved_at",
    )
    list_filter = ("status", "priority", "created_at")
    search_fields = ("participant__email", "subject")
    readonly_fields = ("created_at", "updated_at", "resolved_at")
    date_hierarchy = "created_at"


@admin.register(FinancialChatMessage)
class FinancialChatMessageAdmin(admin.ModelAdmin):  # Admin configuration for FinancialChatMessage model
    list_display = ("id", "chat", "sender", "message_type", "is_read", "created_at")
    list_filter = ("message_type", "is_read", "created_at")
    search_fields = ("sender__email", "content")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(FedaPayCustomer)
class FedaPayCustomerAdmin(admin.ModelAdmin):  # Admin configuration for FedaPayCustomer model
    list_display = (
        "id",
        "participant",
        "fedapay_customer_id",
        "email",
        "phone_number",
        "created_at",
    )
    search_fields = ("participant__email", "email", "fedapay_customer_id")
    readonly_fields = ("created_at", "updated_at")
    list_filter = ("created_at",)


@admin.register(FedaPayTransaction)
class FedaPayTransactionAdmin(admin.ModelAdmin):  # Admin configuration for FedaPayTransaction model
    list_display = (
        "id",
        "participant",
        "transaction_type",
        "amount",
        "currency",
        "status",
        "fedapay_reference",
        "created_at",
    )
    list_filter = ("transaction_type", "status", "currency", "created_at")
    search_fields = (
        "participant__email",
        "fedapay_reference",
        "fedapay_transaction_id",
        "description",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "approved_at",
        "canceled_at",
        "declined_at",
        "refunded_at",
    )
    date_hierarchy = "created_at"
    fieldsets = (
        ("Basic Information", {
            "fields": (
                "participant",
                "fedapay_customer",
                "transaction_type",
                "description",
            )
        }),
        ("FedaPay Details", {
            "fields": (
                "fedapay_transaction_id",
                "fedapay_reference",
                "payment_token",
                "payment_url",
                "receipt_url",
            )
        }),
        ("Transaction Details", {
            "fields": (
                "amount",
                "currency",
                "status",
                "payment_method",
                "core_transaction",
            )
        }),
        ("Fees & Commissions", {
            "fields": (
                "fees",
                "commission",
                "amount_transferred",
            )
        }),
        ("Metadata", {
            "fields": (
                "metadata",
                "custom_metadata",
                "callback_url",
            ),
            "classes": ("collapse",),
        }),
        ("Error Information", {
            "fields": (
                "last_error_code",
                "last_error_message",
            ),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": (
                "created_at",
                "updated_at",
                "approved_at",
                "canceled_at",
                "declined_at",
                "refunded_at",
            )
        }),
    )


@admin.register(FedaPayPayout)
class FedaPayPayoutAdmin(admin.ModelAdmin):  # Admin configuration for FedaPayPayout model
    list_display = (
        "id",
        "provider",
        "amount",
        "currency",
        "status",
        "mode",
        "created_at",
        "sent_at",
    )
    list_filter = ("status", "mode", "currency", "created_at")
    search_fields = (
        "provider__email",
        "fedapay_reference",
        "fedapay_payout_id",
        "phone_number",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "scheduled_at",
        "sent_at",
        "failed_at",
    )
    date_hierarchy = "created_at"


@admin.register(FedaPayWebhookEvent)
class FedaPayWebhookEventAdmin(admin.ModelAdmin):  # Admin configuration for FedaPayWebhookEvent model
    list_display = (
        "id",
        "event_type",
        "event_id",
        "processed",
        "created_at",
        "processed_at",
    )
    list_filter = ("event_type", "processed", "created_at")
    search_fields = ("event_type", "event_id")
    readonly_fields = ("created_at", "processed_at")
    date_hierarchy = "created_at"
    
    fieldsets = (
        ("Event Information", {
            "fields": (
                "event_id",
                "event_type",
                "fedapay_transaction",
                "fedapay_payout",
            )
        }),
        ("Processing Status", {
            "fields": (
                "processed",
                "processing_error",
            )
        }),
        ("Payload", {
            "fields": ("payload",),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": (
                "created_at",
                "processed_at",
            )
        }),
    )


# ========================================
# INVOICE CUSTOMIZATION ADMIN
# ISSUE-DOC-030: Invoice branding and customization
# ========================================

@admin.register(InvoiceSettings)
class InvoiceSettingsAdmin(admin.ModelAdmin):
    """Admin interface for managing provider invoice customization settings"""
    list_display = (
        "participant",
        "business_name",
        "invoice_prefix",
        "template_choice",
        "auto_generate_invoices",
        "created_at",
    )
    list_filter = ("template_choice", "auto_generate_invoices", "include_qr_code")
    search_fields = ("participant__full_name", "participant__email", "business_name")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Provider", {
            "fields": ("participant",)
        }),
        ("Branding", {
            "fields": (
                "logo_url",
                "logo_file",
                "business_name",
                "tagline",
            )
        }),
        ("Template & Colors", {
            "fields": (
                "template_choice",
                "primary_color",
                "secondary_color",
                "accent_color",
            )
        }),
        ("Invoice Numbering", {
            "fields": (
                "invoice_prefix",
                "invoice_number_format",
                "next_invoice_number",
            )
        }),
        ("Contact Information", {
            "fields": (
                "address",
                "city",
                "postal_code",
                "country",
                "phone",
                "email",
                "website",
            )
        }),
        ("Tax & Legal", {
            "fields": (
                "tax_id",
                "registration_number",
            )
        }),
        ("Invoice Content", {
            "fields": (
                "header_text",
                "footer_text",
                "terms_and_conditions",
                "payment_instructions",
            )
        }),
        ("Settings", {
            "fields": (
                "auto_generate_invoices",
                "include_qr_code",
                "include_payment_link",
                "send_invoice_email",
            )
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )


# ========================================
# VENDOR MANAGEMENT ADMIN
# ISSUE-DOC-036: Vendor/supplier payment management
# ========================================

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    """Admin interface for managing vendors and suppliers"""
    list_display = (
        "vendor_name",
        "vendor_type",
        "participant",
        "email",
        "phone",
        "is_active",
        "created_at",
    )
    list_filter = ("vendor_type", "is_active", "created_at")
    search_fields = ("vendor_name", "vendor_code", "email", "phone", "participant__full_name")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Provider", {
            "fields": ("participant",)
        }),
        ("Basic Information", {
            "fields": (
                "vendor_name",
                "vendor_type",
                "vendor_code",
            )
        }),
        ("Contact Information", {
            "fields": (
                "contact_person",
                "email",
                "phone",
                "address",
                "city",
                "country",
            )
        }),
        ("Financial Information", {
            "fields": (
                "tax_id",
                "payment_terms",
                "bank_account",
                "mobile_money_number",
            )
        }),
        ("Settings", {
            "fields": (
                "is_active",
                "notes",
            )
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    """Admin interface for managing expense categories"""
    list_display = (
        "name",
        "code",
        "participant",
        "is_tax_deductible",
        "is_active",
        "created_at",
    )
    list_filter = ("is_tax_deductible", "is_active", "created_at")
    search_fields = ("name", "code", "participant__full_name")
    readonly_fields = ("created_at",)


@admin.register(VendorInvoice)
class VendorInvoiceAdmin(admin.ModelAdmin):
    """Admin interface for managing vendor invoices (accounts payable)"""
    list_display = (
        "invoice_number",
        "vendor",
        "participant",
        "invoice_date",
        "due_date",
        "total_amount",
        "amount_paid",
        "payment_status",
        "is_overdue",
    )
    list_filter = ("payment_status", "invoice_date", "due_date", "expense_category")
    search_fields = (
        "invoice_number",
        "vendor__vendor_name",
        "participant__full_name",
        "description",
    )
    readonly_fields = ("created_at", "updated_at", "get_balance_due")
    date_hierarchy = "invoice_date"

    fieldsets = (
        ("Provider & Vendor", {
            "fields": (
                "participant",
                "vendor",
                "expense_category",
            )
        }),
        ("Invoice Details", {
            "fields": (
                "invoice_number",
                "invoice_date",
                "due_date",
            )
        }),
        ("Amounts", {
            "fields": (
                "subtotal",
                "tax_amount",
                "total_amount",
                "amount_paid",
                "get_balance_due",
                "currency",
            )
        }),
        ("Payment Status", {
            "fields": (
                "payment_status",
                "payment_date",
                "payment_method",
                "payment_reference",
            )
        }),
        ("Additional Information", {
            "fields": (
                "description",
                "notes",
                "attachment",
            )
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )

    def get_balance_due(self, obj):
        """Display balance due in admin"""
        return f"{obj.get_balance_due()} {obj.currency}"
    get_balance_due.short_description = "Balance Due"


# ========================================
# PARTICIPANT PAYMENT METHODS ADMIN
# External payment account linking for service providers
# ========================================

@admin.register(ParticipantPaymentMethod)
class ParticipantPaymentMethodAdmin(admin.ModelAdmin):
    """Admin interface for managing participant payment account linking"""
    list_display = (
        'participant_name',
        'participant_role',
        'method_type',
        'payment_details',
        'is_verified',
        'is_primary',
        'status',
        'created_at',
    )
    list_filter = ('method_type', 'status', 'is_verified', 'is_primary', 'mobile_money_provider', 'created_at')
    search_fields = (
        'participant__full_name',
        'participant__email',
        'bank_name',
        'account_number',
        'account_name',
        'phone_number',
        'gateway_account_id',
    )
    readonly_fields = ('id', 'created_at', 'updated_at', 'verified_at')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Participant', {
            'fields': ('participant',)
        }),
        ('Method Type', {
            'fields': ('method_type',)
        }),
        ('Bank Account Details', {
            'fields': ('bank_name', 'account_number', 'account_name', 'swift_code'),
            'classes': ('collapse',),
        }),
        ('Mobile Money Details', {
            'fields': ('mobile_money_provider', 'phone_number'),
            'classes': ('collapse',),
        }),
        ('Gateway Integration', {
            'fields': ('gateway_provider', 'gateway_account_id')
        }),
        ('Verification', {
            'fields': ('is_verified', 'verification_code', 'verification_code_expires_at', 'verified_at')
        }),
        ('Primary & Status', {
            'fields': ('is_primary', 'status', 'rejection_reason')
        }),
        ('Metadata', {
            'fields': ('notes', 'metadata'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at')
        }),
    )

    def participant_name(self, obj):
        return obj.participant.full_name
    participant_name.short_description = 'Participant'
    participant_name.admin_order_field = 'participant__full_name'

    def participant_role(self, obj):
        return obj.participant.get_role_display()
    participant_role.short_description = 'Role'
    participant_role.admin_order_field = 'participant__role'

    def payment_details(self, obj):
        return obj.get_display_name()
    payment_details.short_description = 'Payment Details'


@admin.register(PaymentMethodVerification)
class PaymentMethodVerificationAdmin(admin.ModelAdmin):
    """Admin interface for tracking payment method verification attempts"""
    list_display = (
        'payment_method_participant',
        'payment_method_type',
        'verification_type',
        'status',
        'attempt_count',
        'max_attempts',
        'created_at',
        'verified_at',
    )
    list_filter = ('verification_type', 'status', 'created_at')
    search_fields = (
        'payment_method__participant__full_name',
        'payment_method__participant__email',
        'otp_code',
        'deposit_reference',
    )
    readonly_fields = ('id', 'created_at', 'updated_at', 'verified_at', 'failed_at')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Payment Method', {
            'fields': ('payment_method',)
        }),
        ('Verification Type', {
            'fields': ('verification_type',)
        }),
        ('OTP Verification', {
            'fields': ('otp_code', 'otp_sent_at', 'otp_expires_at'),
            'classes': ('collapse',),
        }),
        ('Micro-Deposit Verification', {
            'fields': ('deposit_amount_1', 'deposit_amount_2', 'deposit_reference'),
            'classes': ('collapse',),
        }),
        ('Status & Attempts', {
            'fields': ('status', 'attempt_count', 'max_attempts', 'failure_reason')
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at', 'verified_at', 'failed_at')
        }),
    )

    def payment_method_participant(self, obj):
        return obj.payment_method.participant.full_name
    payment_method_participant.short_description = 'Participant'
    payment_method_participant.admin_order_field = 'payment_method__participant__full_name'

    def payment_method_type(self, obj):
        return obj.payment_method.get_method_type_display()
    payment_method_type.short_description = 'Method Type'
    payment_method_type.admin_order_field = 'payment_method__method_type'
