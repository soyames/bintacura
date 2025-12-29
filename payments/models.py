from django.db import models
from django.utils import timezone
import uuid
from core.models import (
    Participant,
    Transaction as CoreTransaction,
    Wallet as CoreWallet,
)
from core.mixins import SyncMixin
from qrcode_generator.services import QRCodeService


class FeeLedger(SyncMixin):  # Tracks platform fees collected from service transactions
    STATUS_CHOICES = [
        ("UNCOLLECTED", "Uncollected"),
        ("COLLECTED", "Collected"),
        ("WAIVED", "Waived"),
        ("DISPUTED", "Disputed"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("WALLET", "Wallet"),
        ("CASH", "Cash"),
        ("EXTERNAL_GATEWAY", "External Gateway"),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)

    related_transaction_id = models.UUIDField()
    provider = models.ForeignKey(
        Participant, on_delete=models.SET_NULL, null=True, related_name="fee_ledgers"
    )
    provider_role = models.CharField(max_length=50)

    service_amount = models.BigIntegerField()
    fee_amount = models.BigIntegerField()
    fee_percentage = models.FloatField()

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="UNCOLLECTED"
    )
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES)
    collection_method = models.CharField(max_length=50, blank=True)

    collected_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:  # Meta class implementation
        db_table = "fee_ledgers"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["related_transaction_id"]),
        ]


class HealthTransaction(SyncMixin):  # Links core transactions to healthcare services like appointments and prescriptions
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    transaction = models.OneToOneField(
        CoreTransaction, on_delete=models.CASCADE, related_name="health_transaction"
    )
    patient = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="health_transactions"
    )
    provider = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="provider_health_transactions",
    )
    appointment_id = models.UUIDField(null=True, blank=True)
    prescription_id = models.UUIDField(null=True, blank=True)
    health_record_id = models.UUIDField(null=True, blank=True)
    service_description = models.TextField()

    class Meta:  # Meta class implementation
        db_table = "health_transactions"


class ProviderPayout(SyncMixin):  # Manages scheduled payouts to healthcare providers
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("on_hold", "On Hold"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)

    provider = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="payouts"
    )
    amount = models.BigIntegerField()
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    period_start = models.DateField()
    period_end = models.DateField()
    transaction_count = models.IntegerField(default=0)
    total_fees_deducted = models.BigIntegerField(default=0)
    payout_method = models.CharField(max_length=50)
    payout_details = models.JSONField(default=dict, blank=True)
    on_hold_reason = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    released_from_hold_at = models.DateTimeField(null=True, blank=True)

    class Meta:  # Meta class implementation
        db_table = "participant_payouts"  # Renamed from provider_payouts to use participant namespace
        ordering = ["-created_at"]


class DoctorPayout(SyncMixin):  # Manages scheduled payouts to doctors for consultations
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("on_hold", "On Hold"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    doctor = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="doctor_payouts"
    )
    amount = models.BigIntegerField()
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    period_start = models.DateField()
    period_end = models.DateField()
    consultation_count = models.IntegerField(default=0)
    total_fees_deducted = models.BigIntegerField(default=0)
    payout_method = models.CharField(max_length=50)
    payout_details = models.JSONField(default=dict, blank=True)
    on_hold_reason = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    released_from_hold_at = models.DateTimeField(null=True, blank=True)

    class Meta:  # Meta class implementation
        db_table = "doctor_payouts"
        ordering = ["-created_at"]


class PaymentReceipt(SyncMixin):  # Generates and stores payment receipts for transactions
    TRANSACTION_TYPE_CHOICES = [
        ('APPOINTMENT', 'Appointment Payment'),
        ('PRESCRIPTION', 'Prescription Purchase'),
        ('CONSULTATION', 'Consultation Fee'),
        ('WALLET_DEPOSIT', 'Wallet Deposit'),
        ('WALLET_WITHDRAWAL', 'Wallet Withdrawal'),
        ('INSURANCE_CLAIM', 'Insurance Claim'),
        ('TRANSPORT', 'Transport Service'),
        ('PHARMACY', 'Pharmacy Purchase'),
        ('HOSPITAL_SERVICE', 'Hospital Service'),
        ('LAB_TEST', 'Laboratory Test'),
        ('OTHER', 'Other'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('PAID', 'Paid'),
        ('PENDING', 'Pending'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    transaction = models.OneToOneField(
        CoreTransaction, on_delete=models.CASCADE, related_name="receipt", null=True, blank=True
    )
    service_transaction = models.OneToOneField(
        'ServiceTransaction', on_delete=models.CASCADE, related_name="receipt", null=True, blank=True
    )
    receipt_number = models.CharField(max_length=100, unique=True)
    invoice_number = models.CharField(max_length=100, unique=True, null=True, blank=True)
    invoice_sequence = models.IntegerField(null=True, blank=True, db_index=True)
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPE_CHOICES, default='OTHER')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PAID')
    issued_to = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="receipts"
    )
    issued_by = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="issued_receipts", null=True, blank=True
    )
    issued_to_name = models.CharField(max_length=255, blank=True)
    issued_to_address = models.TextField(blank=True)
    issued_to_city = models.CharField(max_length=100, blank=True)
    issued_to_country = models.CharField(max_length=100, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    platform_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    payment_method = models.CharField(max_length=50, default='cash', blank=True)
    payment_gateway = models.CharField(max_length=50, blank=True)
    transaction_reference = models.CharField(max_length=255, blank=True)
    gateway_transaction_id = models.CharField(max_length=255, blank=True)
    pdf_url = models.URLField(blank=True)
    pdf_file = models.FileField(upload_to='receipts/%Y/%m/', blank=True, null=True)
    qr_code = models.TextField(blank=True)
    service_details = models.JSONField(default=dict, blank=True)
    line_items = models.JSONField(default=list, blank=True)
    billing_date = models.DateTimeField(null=True, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    issued_at = models.DateTimeField(default=timezone.now)
    reminder_sent = models.BooleanField(default=False)
    reminded_at = models.DateTimeField(null=True, blank=True)

    class Meta:  # Meta class implementation
        db_table = "payment_receipts"
        ordering = ["-issued_at"]
        indexes = [
            models.Index(fields=['issued_to', '-issued_at']),
            models.Index(fields=['transaction_type', '-issued_at']),
            models.Index(fields=['receipt_number']),
        ]
    
    def __str__(self):  # Return string representation
        return f"Receipt {self.receipt_number} - {self.transaction_type}"
    
    def get_display_invoice_number(self):
        return self.invoice_number if self.invoice_number else self.receipt_number
    
    def ensure_invoice_data(self):
        if not self.invoice_number or not self.qr_code:
            from .invoice_number_service import InvoiceNumberService
            from .qr_service import QRCodeService
            
            if not self.invoice_number:
                service_provider_role = 'doctor'
                if self.service_transaction:
                    service_provider_role = self.service_transaction.service_provider_role
                elif self.transaction and self.transaction.recipient:
                    service_provider_role = self.transaction.recipient.role
                
                invoice_data = InvoiceNumberService.generate_invoice_number(
                    service_provider_role=service_provider_role
                )
                self.invoice_number = invoice_data['invoice_number']
                self.invoice_sequence = invoice_data['sequence']
            
            if not self.qr_code:
                QRCodeService.generate_invoice_qr_code(self)
            
            self.save()


class PaymentRequest(SyncMixin):  # Manages payment requests sent between participants
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    from_participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="sent_payment_requests"
    )
    to_participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="received_payment_requests"
    )
    amount = models.BigIntegerField()
    currency = models.CharField(max_length=3, default="USD")
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    transaction = models.ForeignKey(
        CoreTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_request",
    )
    metadata = models.JSONField(default=dict, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:  # Meta class implementation
        db_table = "payment_requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["to_participant", "status"]),
            models.Index(fields=["from_participant", "status"]),
        ]


class Transfer(SyncMixin):  # Records money transfers between wallets and external accounts
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    TRANSFER_TYPE_CHOICES = [
        ("internal", "Internal Transfer"),
        ("external", "External Transfer"),
        ("bank", "Bank Transfer"),
        ("mobile_money", "Mobile Money"),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Unique key to prevent duplicate transactions during sync"
    )
    from_wallet = models.ForeignKey(
        CoreWallet, on_delete=models.CASCADE, related_name="outgoing_transfers"
    )
    to_wallet = models.ForeignKey(
        CoreWallet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incoming_transfers",
    )
    from_participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="sent_transfers"
    )
    to_participant = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_transfers",
    )
    amount = models.BigIntegerField()
    fee = models.BigIntegerField(default=0)
    total_amount = models.BigIntegerField()
    currency = models.CharField(max_length=3, default="USD")
    transfer_type = models.CharField(max_length=20, choices=TRANSFER_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    description = models.TextField(blank=True)
    external_reference = models.CharField(max_length=255, blank=True)
    external_account_details = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_reason = models.TextField(blank=True)

    class Meta:  # Meta class implementation
        db_table = "transfers"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["from_participant", "status"]),
            models.Index(fields=["to_participant", "status"]),
            models.Index(fields=["transfer_type"]),
        ]


class LinkedVendor(SyncMixin):  # Stores participant linked payment methods and accounts
    VENDOR_TYPE_CHOICES = [
        ("payment_gateway", "Payment Gateway"),
        ("bank", "Bank Account"),
        ("mobile_money", "Mobile Money"),
        ("credit_card", "Credit Card"),
        ("debit_card", "Debit Card"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("pending_verification", "Pending Verification"),
        ("suspended", "Suspended"),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="linked_vendors"
    )
    vendor_type = models.CharField(max_length=30, choices=VENDOR_TYPE_CHOICES)
    vendor_name = models.CharField(max_length=100)
    account_identifier = models.CharField(max_length=255)
    encrypted_credentials = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="active")
    is_default = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:  # Meta class implementation
        db_table = "linked_vendors"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["participant", "status"]),
            models.Index(fields=["vendor_type"]),
        ]


class FinancialChat(SyncMixin):  # Manages support chat conversations about financial transactions
    MESSAGE_TYPE_CHOICES = [
        ("user", "User Message"),
        ("support", "Support Message"),
        ("system", "System Message"),
    ]

    STATUS_CHOICES = [
        ("open", "Open"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="financial_chats"
    )
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    priority = models.CharField(max_length=20, default="normal")
    assigned_to = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_financial_chats",
    )
    related_transaction = models.ForeignKey(
        CoreTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chats",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:  # Meta class implementation
        db_table = "financial_chats"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["participant", "status"]),
            models.Index(fields=["status"]),
        ]


class FinancialChatMessage(SyncMixin):  # Stores individual messages in financial support chats
    MESSAGE_TYPE_CHOICES = [
        ("user", "User Message"),
        ("support", "Support Message"),
        ("system", "System Message"),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    chat = models.ForeignKey(
        FinancialChat, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="financial_messages"
    )
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES)
    content = models.TextField()
    attachments = models.JSONField(default=list, blank=True)
    is_read = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:  # Meta class implementation
        db_table = "financial_chat_messages"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["chat", "created_at"]),
        ]


class FedaPayCustomer(SyncMixin):  # Links participants to their FedaPay customer accounts
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    participant = models.OneToOneField(
        Participant, on_delete=models.CASCADE, related_name="fedapay_customer"
    )
    fedapay_customer_id = models.IntegerField(unique=True)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20, blank=True)

    class Meta:  # Meta class implementation
        db_table = "fedapay_customers"
        indexes = [
            models.Index(fields=["fedapay_customer_id"]),
            models.Index(fields=["participant"]),
        ]

    def __str__(self):  # Return string representation
        return f"{self.participant.email} - FedaPay ID: {self.fedapay_customer_id}"


class FedaPayTransaction(SyncMixin):  # Tracks FedaPay payment gateway transactions
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("canceled", "Canceled"),
        ("declined", "Declined"),
        ("refunded", "Refunded"),
        ("transferred", "Transferred"),
    ]

    TRANSACTION_TYPE_CHOICES = [
        ("wallet_topup", "Wallet Top-up"),
        ("service_payment", "Service Payment"),
        ("refund", "Refund"),
        ("payout", "Payout"),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Unique key to prevent duplicate transactions during sync"
    )
    fedapay_transaction_id = models.IntegerField(unique=True, null=True, blank=True)
    fedapay_reference = models.CharField(max_length=100, unique=True, null=True, blank=True)

    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="fedapay_transactions"
    )
    fedapay_customer = models.ForeignKey(
        FedaPayCustomer, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions"
    )
    
    core_transaction = models.OneToOneField(
        CoreTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name="fedapay_transaction"
    )
    
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    
    description = models.TextField()
    payment_method = models.CharField(max_length=50, blank=True)
    payment_token = models.CharField(max_length=500, blank=True)
    payment_url = models.URLField(blank=True)
    
    callback_url = models.URLField(blank=True)
    receipt_url = models.URLField(blank=True)
    
    fees = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_transferred = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    metadata = models.JSONField(default=dict, blank=True)
    custom_metadata = models.JSONField(default=dict, blank=True)
    
    last_error_code = models.CharField(max_length=100, blank=True)
    last_error_message = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)

    class Meta:  # Meta class implementation
        db_table = "fedapay_transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["participant", "status"]),
            models.Index(fields=["fedapay_transaction_id"]),
            models.Index(fields=["fedapay_reference"]),
            models.Index(fields=["transaction_type"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):  # Return string representation
        return f"{self.participant.email} - {self.transaction_type} - {self.amount} {self.currency}"


class FedaPayPayout(SyncMixin):  # Manages FedaPay payouts to providers
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("scheduled", "Scheduled"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    fedapay_payout_id = models.IntegerField(unique=True, null=True, blank=True)
    fedapay_reference = models.CharField(max_length=100, unique=True, null=True, blank=True)
    
    provider = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="fedapay_payouts"
    )
    fedapay_customer = models.ForeignKey(
        FedaPayCustomer, on_delete=models.SET_NULL, null=True, blank=True, related_name="payouts"
    )
    
    provider_payout = models.ForeignKey(
        ProviderPayout, on_delete=models.SET_NULL, null=True, blank=True, related_name="fedapay_payouts"
    )
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    
    mode = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=20, blank=True)
    
    fees = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_transferred = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    metadata = models.JSONField(default=dict, blank=True)
    last_error_code = models.CharField(max_length=100, blank=True)
    last_error_message = models.TextField(blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    class Meta:  # Meta class implementation
        db_table = "fedapay_payouts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["fedapay_payout_id"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):  # Return string representation
        return f"Payout to {self.provider.email} - {self.amount} {self.currency}"


class FedaPayWebhookEvent(SyncMixin):  # Records webhook events received from FedaPay
    EVENT_TYPE_CHOICES = [
        ("transaction.approved", "Transaction Approved"),
        ("transaction.canceled", "Transaction Canceled"),
        ("transaction.declined", "Transaction Declined"),
        ("transaction.refunded", "Transaction Refunded"),
        ("payout.sent", "Payout Sent"),
        ("payout.failed", "Payout Failed"),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    event_id = models.IntegerField(unique=True, null=True, blank=True)
    event_type = models.CharField(max_length=50)
    
    fedapay_transaction = models.ForeignKey(
        FedaPayTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name="webhook_events"
    )
    fedapay_payout = models.ForeignKey(
        FedaPayPayout, on_delete=models.SET_NULL, null=True, blank=True, related_name="webhook_events"
    )
    
    payload = models.JSONField()
    processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:  # Meta class implementation
        db_table = "fedapay_webhook_events"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "processed"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):  # Return string representation
        return f"{self.event_type} - {self.created_at}"


class ParticipantPhone(SyncMixin):  # Stores and verifies participant phone numbers for payments
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="participant_phones"
    )
    phone_number = models.CharField(max_length=20, help_text="E.164 format, e.g., +22997000000")
    country_code = models.CharField(max_length=2, help_text="ISO country code, e.g., BJ, TG, CI")
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, blank=True)
    verification_code_expires_at = models.DateTimeField(null=True, blank=True)
    verification_method = models.CharField(
        max_length=20,
        choices=[('sms', 'SMS'), ('call', 'Call'), ('whatsapp', 'WhatsApp')],
        default='sms'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    last_used_for_payment_at = models.DateTimeField(null=True, blank=True)

    class Meta:  # Meta class implementation
        db_table = "participant_phones"
        ordering = ["-is_primary", "-created_at"]
        indexes = [
            models.Index(fields=["participant", "is_primary"]),
            models.Index(fields=["phone_number"]),
            models.Index(fields=["is_verified"]),
        ]
        unique_together = [["participant", "phone_number"]]

    def __str__(self):  # Return string representation
        return f"{self.participant.email} - {self.phone_number}"


class ServiceCatalog(SyncMixin):  # Catalogs services offered by healthcare providers with pricing
    SERVICE_CATEGORY_CHOICES = [
        ('consultation', 'Consultation'),
        ('surgery', 'Surgery'),
        ('diagnostic', 'Diagnostic'),
        ('laboratory', 'Laboratory'),
        ('imaging', 'Imaging'),
        ('therapy', 'Therapy'),
        ('pharmacy', 'Pharmacy'),
        ('emergency', 'Emergency'),
        ('vaccination', 'Vaccination'),
        ('dental', 'Dental'),
        ('maternity', 'Maternity'),
        ('pediatric', 'Pediatric'),
        ('insurance_plan', 'Insurance Plan'),
        ('other', 'Other'),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    service_provider = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="catalog_services",
        limit_choices_to={'role__in': ['doctor', 'hospital', 'pharmacy', 'insurance_company']}
    )
    service_provider_role = models.CharField(max_length=50)
    service_category = models.CharField(max_length=50, choices=SERVICE_CATEGORY_CHOICES)
    service_name = models.CharField(max_length=255)
    service_description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    duration_minutes = models.IntegerField(null=True, blank=True, help_text="Estimated duration")
    is_active = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    requires_appointment = models.BooleanField(default=True)
    requires_prescription = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    created_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_services"
    )

    class Meta:  # Meta class implementation
        db_table = "service_catalog"
        ordering = ["service_category", "service_name"]
        indexes = [
            models.Index(fields=["service_provider", "is_active"]),
            models.Index(fields=["service_category", "is_active"]),
            models.Index(fields=["region_code", "is_active"]),
            models.Index(fields=["service_provider_role", "is_active"]),
        ]

    def __str__(self):  # Return string representation
        return f"{self.service_name} - {self.service_provider.full_name}"

    def save(self, *args, **kwargs):  # Save
        if not self.service_provider_role:
            self.service_provider_role = self.service_provider.role
        super().save(*args, **kwargs)


class ParticipantGatewayAccount(SyncMixin):  # Links participant payment accounts to gateway providers
    GATEWAY_PROVIDER_CHOICES = [
        ('fedapay', 'FedaPay'),
        ('mtn_momo', 'MTN Mobile Money'),
        ('moov_money', 'Moov Money'),
        ('orange_money', 'Orange Money'),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="gateway_accounts"
    )
    participant_role = models.CharField(max_length=50)
    participant_phone = models.ForeignKey(
        ParticipantPhone, on_delete=models.CASCADE, related_name="gateway_accounts"
    )
    gateway_provider = models.CharField(max_length=50, choices=GATEWAY_PROVIDER_CHOICES)
    gateway_customer_id = models.CharField(max_length=255, blank=True)
    gateway_account_number = models.CharField(max_length=255)
    payout_mode = models.CharField(
        max_length=50,
        blank=True,
        help_text="For FedaPay: mtn, moov, mtn_ci, moov_tg, etc."
    )
    account_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:  # Meta class implementation
        db_table = "participant_gateway_accounts"
        ordering = ["-is_default", "-created_at"]
        indexes = [
            models.Index(fields=["participant", "gateway_provider"]),
            models.Index(fields=["gateway_provider", "gateway_customer_id"]),
            models.Index(fields=["participant", "is_default"]),
        ]
        unique_together = [["participant", "gateway_provider", "gateway_account_number"]]

    def __str__(self):  # Return string representation
        return f"{self.participant.email} - {self.gateway_provider}"

    def save(self, *args, **kwargs):  # Save
        if not self.participant_role:
            self.participant_role = self.participant.role
        if not self.gateway_account_number:
            self.gateway_account_number = self.participant_phone.phone_number
        super().save(*args, **kwargs)


class ServiceTransaction(SyncMixin):  # Records patient payments for healthcare services
    SERVICE_TYPE_CHOICES = [
        ('appointment', 'Appointment'),
        ('prescription', 'Prescription'),
        ('lab_test', 'Lab Test'),
        ('consultation', 'Consultation'),
        ('pharmacy_purchase', 'Pharmacy Purchase'),
        ('insurance_claim', 'Insurance Claim'),
        ('emergency', 'Emergency Service'),
        ('other', 'Other'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('fedapay_mobile', 'FedaPay Mobile Money'),
        ('fedapay_card', 'FedaPay Card'),
        ('mtn_momo', 'MTN Mobile Money'),
        ('moov_money', 'Moov Money'),
        ('orange_money', 'Orange Money'),
        ('onsite_cash', 'On-site Cash'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    transaction_ref = models.CharField(max_length=100, unique=True)
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Unique key to prevent duplicate transactions during sync"
    )
    patient = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="patient_service_transactions",
        limit_choices_to={'role': 'patient'}
    )
    service_provider = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="provider_service_transactions",
        limit_choices_to={'role__in': ['doctor', 'hospital', 'pharmacy', 'insurance_company']}
    )
    service_provider_role = models.CharField(max_length=50)
    service_catalog_item = models.ForeignKey(
        ServiceCatalog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions"
    )
    service_type = models.CharField(max_length=50, choices=SERVICE_TYPE_CHOICES)
    service_id = models.UUIDField(help_text="Reference to specific service instance")
    service_description = models.TextField()
    
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Amount in USD (reference currency)")
    amount_local = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Amount in participant local currency")
    currency_code = models.CharField(max_length=3, null=True, blank=True, help_text="Local currency code")
    exchange_rate_used = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True, help_text="Exchange rate at transaction time")
    conversion_timestamp = models.DateTimeField(null=True, blank=True, help_text="When currency conversion was performed")
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES)
    patient_phone = models.ForeignKey(
        ParticipantPhone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patient_transactions"
    )
    provider_phone = models.ForeignKey(
        ParticipantPhone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="provider_transactions"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    gateway_transaction = models.ForeignKey(
        'GatewayTransaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_transactions"
    )
    metadata = models.JSONField(default=dict, blank=True)
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:  # Meta class implementation
        db_table = "service_transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["patient", "status"]),
            models.Index(fields=["service_provider", "status"]),
            models.Index(fields=["transaction_ref"]),
            models.Index(fields=["service_type", "status"]),
            models.Index(fields=["region_code", "-created_at"]),
        ]

    def __str__(self):  # Return string representation
        return f"{self.transaction_ref} - {self.patient.email} to {self.service_provider.email}"

    def save(self, *args, **kwargs):  # Save
        if not self.transaction_ref:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.transaction_ref = f"STX-{timestamp}-{str(self.id)[:8].upper()}"
        if not self.service_provider_role:
            self.service_provider_role = self.service_provider.role
        super().save(*args, **kwargs)


class TransactionFee(SyncMixin):  # Calculates and tracks fees for service transactions
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    service_transaction = models.OneToOneField(
        ServiceTransaction, on_delete=models.CASCADE, related_name="fee_details"
    )
    
    gross_amount_usd = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Gross amount in USD")
    gross_amount_local = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Gross amount in local currency")
    currency_code = models.CharField(max_length=3, default='USD')
    exchange_rate_used = models.DecimalField(max_digits=12, decimal_places=6, default=1.0)
    
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2)
    platform_fee_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.01)
    platform_fee_amount_usd = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Commission in USD")
    platform_fee_amount_local = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Commission in local currency")
    platform_fee_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    tax_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.18)
    tax_amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True, help_text="Tax in USD")
    tax_amount_local = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True, help_text="Tax in local currency")
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    total_fee_amount = models.DecimalField(max_digits=12, decimal_places=2)
    net_amount_to_provider = models.DecimalField(max_digits=12, decimal_places=2)
    fee_collected = models.BooleanField(default=False)
    collected_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:  # Meta class implementation
        db_table = "transaction_fees"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["service_transaction"]),
            models.Index(fields=["fee_collected"]),
        ]

    def __str__(self):  # Return string representation
        return f"Fee for {self.service_transaction.transaction_ref}"


class GatewayTransaction(SyncMixin):  # Tracks transactions processed through payment gateways
    GATEWAY_PROVIDER_CHOICES = [
        ('fedapay', 'FedaPay'),
        ('mtn_momo', 'MTN Mobile Money'),
        ('moov_money', 'Moov Money'),
        ('orange_money', 'Orange Money'),
    ]

    TRANSACTION_TYPE_CHOICES = [
        ('payment_collection', 'Payment Collection'),
        ('payout', 'Payout'),
        ('refund', 'Refund'),
    ]
    
    PAYMENT_CONTEXT_CHOICES = [
        ('patient_service', 'Patient Service Payment'),
        ('b2b_supplier', 'B2B Supplier Payment'),
        ('payroll', 'Payroll Payment'),
        ('vendor_payment', 'Vendor Payment'),
        ('insurance_claim', 'Insurance Claim'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
        ('refunded', 'Refunded'),
        ('transferred', 'Transferred'),
        ('cancelled', 'Cancelled'),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Unique key to prevent duplicate transactions during sync"
    )
    gateway_provider = models.CharField(max_length=50, choices=GATEWAY_PROVIDER_CHOICES)
    gateway_transaction_id = models.CharField(max_length=255, blank=True)
    gateway_reference = models.CharField(max_length=255, blank=True)
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPE_CHOICES)
    payment_context = models.CharField(max_length=50, choices=PAYMENT_CONTEXT_CHOICES, default='patient_service', help_text="Context/purpose of payment")
    patient = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="patient_gateway_transactions"
    )
    service_provider = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="provider_gateway_transactions"
    )
    patient_phone = models.ForeignKey(
        ParticipantPhone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patient_gateway_transactions"
    )
    provider_phone = models.ForeignKey(
        ParticipantPhone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="provider_gateway_transactions"
    )
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Amount in USD (reference)")
    amount_local = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Amount in local currency")
    currency_code = models.CharField(max_length=3, null=True, blank=True, help_text="Local currency code")
    exchange_rate_used = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True, help_text="Exchange rate used")
    conversion_timestamp = models.DateTimeField(null=True, blank=True, help_text="Currency conversion time")
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=100, blank=True)
    payment_url = models.URLField(blank=True)
    payment_token = models.CharField(max_length=500, blank=True)
    fees = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.01, help_text="Platform commission rate (default 1%)")
    amount_transferred = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    webhook_data = models.JSONField(default=list, blank=True, help_text="Array of webhook payloads")
    last_error_code = models.CharField(max_length=100, blank=True)
    last_error_message = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)
    transferred_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:  # Meta class implementation
        db_table = "gateway_transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["gateway_provider", "gateway_transaction_id"]),
            models.Index(fields=["gateway_reference"]),
            models.Index(fields=["patient", "status"]),
            models.Index(fields=["service_provider", "status"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self):  # Return string representation
        return f"{self.gateway_provider} - {self.gateway_reference or self.id}"


class PayoutSchedule(SyncMixin):  # Schedules and manages periodic payouts to providers
    PAYOUT_STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="payout_schedules",
        limit_choices_to={'role__in': ['doctor', 'hospital', 'pharmacy', 'insurance_company']}
    )
    participant_role = models.CharField(max_length=50)
    period_start = models.DateField()
    period_end = models.DateField()
    total_transactions_count = models.IntegerField(default=0)
    total_gross_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_fees_deducted = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payout_status = models.CharField(max_length=20, choices=PAYOUT_STATUS_CHOICES, default='scheduled')
    gateway_payout = models.ForeignKey(
        GatewayTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payout_schedules"
    )
    scheduled_for = models.DateTimeField()
    processed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:  # Meta class implementation
        db_table = "payout_schedules"
        ordering = ["-scheduled_for"]
        indexes = [
            models.Index(fields=["participant", "payout_status"]),
            models.Index(fields=["payout_status", "scheduled_for"]),
            models.Index(fields=["period_start", "period_end"]),
        ]

    def __str__(self):  # Return string representation
        return f"Payout for {self.participant.email} - {self.period_start} to {self.period_end}"

    def save(self, *args, **kwargs):  # Save
        if not self.participant_role:
            self.participant_role = self.participant.role
        super().save(*args, **kwargs)


# ========================================
# INVOICE CUSTOMIZATION MODELS
# ISSUE-DOC-030: Invoice branding and customization
# ========================================

class InvoiceSettings(SyncMixin):  # Stores invoice customization preferences for providers
    """
    Allows doctors, hospitals, pharmacies, and insurance companies to:
    - Upload custom logo
    - Customize invoice template
    - Set custom numbering format
    - Configure colors and branding
    """
    TEMPLATE_CHOICES = [
        ('standard', 'Standard Template'),
        ('modern', 'Modern Template'),
        ('classic', 'Classic Template'),
        ('minimal', 'Minimal Template'),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    participant = models.OneToOneField(
        Participant,
        on_delete=models.CASCADE,
        related_name="invoice_settings",
        limit_choices_to={'role__in': ['doctor', 'hospital', 'pharmacy', 'insurance_company']}
    )

    # Logo and Branding
    logo_url = models.URLField(blank=True, help_text="URL to clinic/organization logo")
    logo_file = models.FileField(upload_to='invoice_logos/%Y/%m/', blank=True, null=True)
    business_name = models.CharField(max_length=255, blank=True, help_text="Custom business name for invoices")
    tagline = models.CharField(max_length=255, blank=True, help_text="Business tagline")

    # Template and Colors
    template_choice = models.CharField(max_length=20, choices=TEMPLATE_CHOICES, default='standard')
    primary_color = models.CharField(max_length=7, default='#2563eb', help_text="Hex color code (e.g., #2563eb)")
    secondary_color = models.CharField(max_length=7, default='#64748b', help_text="Secondary hex color")
    accent_color = models.CharField(max_length=7, default='#f59e0b', help_text="Accent hex color")

    # Invoice Numbering
    invoice_prefix = models.CharField(max_length=20, blank=True, help_text="e.g., 'DR-KOU-', 'CLINIC-'")
    invoice_number_format = models.CharField(
        max_length=50,
        default='{prefix}{year}-{sequence}',
        help_text="Format: {prefix}{year}-{sequence}, {prefix}{month}{year}-{sequence}"
    )
    next_invoice_number = models.IntegerField(default=1, help_text="Next invoice sequence number")

    # Contact Information
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)

    # Tax and Legal
    tax_id = models.CharField(max_length=100, blank=True, help_text="Tax ID / VAT number")
    registration_number = models.CharField(max_length=100, blank=True)

    # Invoice Content
    header_text = models.TextField(blank=True, help_text="Custom text in invoice header")
    footer_text = models.TextField(
        blank=True,
        default="Thank you for your business!",
        help_text="Custom text in invoice footer"
    )
    terms_and_conditions = models.TextField(blank=True)
    payment_instructions = models.TextField(blank=True)

    # Settings
    auto_generate_invoices = models.BooleanField(
        default=True,
        help_text="Automatically generate invoice after consultation/service"
    )
    include_qr_code = models.BooleanField(default=True)
    include_payment_link = models.BooleanField(default=True)
    send_invoice_email = models.BooleanField(default=True)

    class Meta:
        db_table = "invoice_settings"
        verbose_name = "Invoice Settings"
        verbose_name_plural = "Invoice Settings"

    def __str__(self):
        return f"Invoice Settings - {self.participant.full_name}"

    def get_next_invoice_number(self):
        """Generate next invoice number and increment"""
        from datetime import datetime

        current_number = self.next_invoice_number
        year = datetime.now().year
        month = datetime.now().strftime('%m')

        invoice_number = self.invoice_number_format.format(
            prefix=self.invoice_prefix,
            year=year,
            month=month,
            sequence=str(current_number).zfill(4)
        )

        # Increment for next time
        self.next_invoice_number += 1
        self.save(update_fields=['next_invoice_number'])

        return invoice_number


# ========================================
# VENDOR MANAGEMENT MODELS
# ISSUE-DOC-036: Vendor/supplier payment management
# ========================================

class Vendor(SyncMixin):  # Manages vendor/supplier information for accounts payable
    """
    Allows providers to track:
    - Medical suppliers
    - Equipment vendors
    - Staff payments
    - Utility providers
    - Other business expenses
    """
    VENDOR_TYPE_CHOICES = [
        ('supplier', 'Medical Supplier'),
        ('equipment', 'Equipment Vendor'),
        ('staff', 'Staff/Employee'),
        ('utility', 'Utility Provider'),
        ('service', 'Service Provider'),
        ('consultant', 'Consultant'),
        ('other', 'Other'),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="vendors",
        limit_choices_to={'role__in': ['doctor', 'hospital', 'pharmacy', 'insurance_company']}
    )

    # Basic Information
    vendor_name = models.CharField(max_length=255)
    vendor_type = models.CharField(max_length=50, choices=VENDOR_TYPE_CHOICES, default='supplier')
    vendor_code = models.CharField(max_length=50, blank=True, help_text="Custom vendor code/ID")

    # Contact Information
    contact_person = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)

    # Financial Information
    tax_id = models.CharField(max_length=100, blank=True)
    payment_terms = models.CharField(
        max_length=50,
        default='Net 30',
        help_text="e.g., 'Net 30', 'Due on Receipt', 'Net 60'"
    )
    bank_account = models.CharField(max_length=255, blank=True)
    mobile_money_number = models.CharField(max_length=50, blank=True)

    # Settings
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "vendors"
        ordering = ['vendor_name']
        indexes = [
            models.Index(fields=['participant', 'is_active']),
            models.Index(fields=['vendor_type']),
        ]
        unique_together = ['participant', 'vendor_code']

    def __str__(self):
        return f"{self.vendor_name} ({self.get_vendor_type_display()})"


class ExpenseCategory(SyncMixin):  # Categorizes business expenses for tax and reporting
    """
    ISSUE-DOC-038: Expense categorization system
    Allows providers to categorize expenses for:
    - Tax reporting
    - Profit/Loss statements
    - Budget tracking
    """
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="expense_categories",
        limit_choices_to={'role__in': ['doctor', 'hospital', 'pharmacy', 'insurance_company']}
    )

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True, help_text="Accounting code")
    description = models.TextField(blank=True)
    is_tax_deductible = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "expense_categories"
        ordering = ['name']
        unique_together = ['participant', 'name']
        verbose_name_plural = "Expense Categories"

    def __str__(self):
        return self.name


class VendorInvoice(SyncMixin):  # Tracks vendor invoices and payments (accounts payable)
    """
    ISSUE-DOC-037: Accounts payable system
    Tracks outgoing payments to vendors and suppliers
    """
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('paid', 'Paid'),
        ('partially_paid', 'Partially Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="vendor_invoices",
        limit_choices_to={'role__in': ['doctor', 'hospital', 'pharmacy', 'insurance_company']}
    )
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="invoices")
    expense_category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vendor_invoices"
    )

    # Invoice Details
    invoice_number = models.CharField(max_length=255, help_text="Vendor's invoice number")
    invoice_date = models.DateField()
    due_date = models.DateField()

    # Amounts
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')

    # Status
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    payment_reference = models.CharField(max_length=255, blank=True)

    # Additional Information
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    attachment = models.FileField(upload_to='vendor_invoices/%Y/%m/', blank=True, null=True)

    class Meta:
        db_table = "vendor_invoices"
        ordering = ['-invoice_date']
        indexes = [
            models.Index(fields=['participant', 'payment_status']),
            models.Index(fields=['vendor', 'payment_status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['invoice_date']),
        ]

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.vendor.vendor_name}"

    def get_balance_due(self):
        """Calculate remaining balance"""
        return self.total_amount - self.amount_paid

    def is_overdue(self):
        """Check if invoice is overdue"""
        from datetime import date
        return self.due_date < date.today() and self.payment_status != 'paid'

    def save(self, *args, **kwargs):
        """Auto-update payment status based on amount paid"""
        if self.amount_paid >= self.total_amount:
            self.payment_status = 'paid'
        elif self.amount_paid > 0:
            self.payment_status = 'partially_paid'
        elif self.is_overdue():
            self.payment_status = 'overdue'

        super().save(*args, **kwargs)

# Import participant payment method models
from .participant_payment_models import ParticipantPaymentMethod, PaymentMethodVerification
