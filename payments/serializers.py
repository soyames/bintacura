from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import *
from core.models import Transaction as CoreTransaction


class FeeLedgerSerializer(serializers.ModelSerializer):  # Serializer for FeeLedger data
    class Meta:  # Meta class implementation
        model = FeeLedger
        fields = "__all__"


class PaymentRequestSerializer(serializers.ModelSerializer):  # Serializer for PaymentRequest data
    from_participant_name = serializers.CharField(source="from_participant.full_name", read_only=True)
    from_participant_email = serializers.EmailField(source="from_participant.email", read_only=True)

    class Meta:  # Meta class implementation
        model = PaymentRequest
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "responded_at"]


class LinkedVendorSerializer(serializers.ModelSerializer):  # Serializer for LinkedVendor data
    class Meta:  # Meta class implementation
        model = LinkedVendor
        fields = "__all__"
        read_only_fields = ["id", "participant", "created_at", "updated_at", "last_used_at"]


class FinancialChatMessageSerializer(serializers.ModelSerializer):  # Serializer for FinancialChatMessage data
    sender_name = serializers.CharField(source="sender.full_name", read_only=True)

    class Meta:  # Meta class implementation
        model = FinancialChatMessage
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class FinancialChatSerializer(serializers.ModelSerializer):  # Serializer for FinancialChat data
    messages = FinancialChatMessageSerializer(many=True, read_only=True)
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:  # Meta class implementation
        model = FinancialChat
        fields = "__all__"
        read_only_fields = ["id", "user", "created_at", "updated_at", "resolved_at"]

    @extend_schema_field(serializers.IntegerField)
    def get_unread_count(self, obj):  # Get unread count
        return obj.messages.filter(is_read=False, message_type="support").count()

    @extend_schema_field(serializers.CharField)
    def get_last_message(self, obj):  # Get last message
        last_msg = obj.messages.order_by("-created_at").first()
        return last_msg.content if last_msg else ""


class FedaPayCustomerSerializer(serializers.ModelSerializer):  # Serializer for FedaPayCustomer data
    participant_email = serializers.EmailField(source="participant.email", read_only=True)
    participant_name = serializers.CharField(source="participant.full_name", read_only=True)

    class Meta:  # Meta class implementation
        model = FedaPayCustomer
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class FedaPayTransactionSerializer(serializers.ModelSerializer):  # Serializer for FedaPayTransaction data
    participant_email = serializers.EmailField(source="participant.email", read_only=True)
    participant_name = serializers.CharField(source="participant.full_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    transaction_type_display = serializers.CharField(source="get_transaction_type_display", read_only=True)

    class Meta:  # Meta class implementation
        model = FedaPayTransaction
        fields = "__all__"
        read_only_fields = [
            "id", "fedapay_transaction_id", "fedapay_reference",
            "created_at", "updated_at", "approved_at", "canceled_at",
            "declined_at", "refunded_at", "fees", "commission",
            "amount_transferred", "receipt_url", "payment_token", "payment_url"
        ]


class WalletTopupRequestSerializer(serializers.Serializer):  # Serializer for WalletTopupRequest data
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=100)
    currency = serializers.CharField(max_length=3, default="XOF")


class ServicePaymentRequestSerializer(serializers.Serializer):
    """Serializer for service payment requests"""
    doctor_id = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=1)
    currency = serializers.CharField(max_length=3, default="XOF")
    service_type = serializers.ChoiceField(
        choices=[
            ('appointment', 'Appointment'),
            ('prescription', 'Prescription'),
            ('lab_test', 'Lab Test'),
            ('consultation', 'Consultation'),
            ('emergency', 'Emergency Service'),
            ('other', 'Other Service')
        ],
        required=True
    )
    service_id = serializers.CharField(max_length=255, required=True)
    description = serializers.CharField(max_length=500, required=True)
    payment_method = serializers.ChoiceField(
        choices=[('wallet', 'Wallet'), ('onsite', 'On-site/Cash')],
        default='wallet'
    )


class PaymentReceiptSerializer(serializers.ModelSerializer):  # Serializer for PaymentReceipt data
    transaction_ref = serializers.CharField(source="transaction.transaction_ref", read_only=True)
    transaction_amount = serializers.DecimalField(
        source="transaction.amount",
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    transaction_currency = serializers.CharField(source="transaction.currency", read_only=True)
    issued_to_name = serializers.CharField(source="issued_to.full_name", read_only=True)
    issued_by_name = serializers.CharField(source="issued_by.full_name", read_only=True)

    class Meta:  # Meta class implementation
        model = PaymentReceipt
        fields = "__all__"
        read_only_fields = ["id", "receipt_number", "pdf_url", "issued_at"]


class ParticipantPhoneSerializer(serializers.ModelSerializer):  # Serializer for ParticipantPhone data
    participant_email = serializers.EmailField(source="participant.email", read_only=True)
    participant_name = serializers.CharField(source="participant.full_name", read_only=True)

    class Meta:  # Meta class implementation
        model = ParticipantPhone
        fields = "__all__"
        read_only_fields = ["id", "participant", "verified_at", "created_at", "updated_at", "verification_code", "verification_code_expires_at"]


class PhoneVerificationSerializer(serializers.Serializer):  # Serializer for PhoneVerification data
    phone_number = serializers.CharField(max_length=20, required=True)
    country_code = serializers.CharField(max_length=2, required=True)
    is_primary = serializers.BooleanField(default=False)


class PhoneVerifyCodeSerializer(serializers.Serializer):  # Serializer for PhoneVerifyCode data
    verification_code = serializers.CharField(max_length=6, required=True)


class ServiceCatalogSerializer(serializers.ModelSerializer):  # Serializer for ServiceCatalog data
    service_provider_email = serializers.EmailField(source="service_provider.email", read_only=True)
    service_provider_name = serializers.CharField(source="service_provider.full_name", read_only=True)
    service_category_display = serializers.CharField(source="get_service_category_display", read_only=True)
    price_formatted = serializers.SerializerMethodField()

    class Meta:  # Meta class implementation
        model = ServiceCatalog
        fields = "__all__"
        read_only_fields = ["id", "service_provider", "service_provider_role", "created_by", "created_at", "updated_at"]

    @extend_schema_field(serializers.CharField)
    def get_price_formatted(self, obj):  # Get price formatted
        from currency_converter.services import CurrencyConverterService
        return CurrencyConverterService.format_amount(obj.price, obj.currency)


class ServiceCatalogCreateSerializer(serializers.ModelSerializer):  # Serializer for ServiceCatalogCreate data
    class Meta:  # Meta class implementation
        model = ServiceCatalog
        fields = ["service_category", "service_name", "service_description", "price", "currency", "duration_minutes", "requires_appointment", "requires_prescription", "metadata"]


class ParticipantGatewayAccountSerializer(serializers.ModelSerializer):  # Serializer for ParticipantGatewayAccount data
    participant_email = serializers.EmailField(source="participant.email", read_only=True)
    participant_name = serializers.CharField(source="participant.full_name", read_only=True)
    phone_number = serializers.CharField(source="participant_phone.phone_number", read_only=True)
    gateway_provider_display = serializers.CharField(source="get_gateway_provider_display", read_only=True)

    class Meta:  # Meta class implementation
        model = ParticipantGatewayAccount
        fields = "__all__"
        read_only_fields = ["id", "participant", "participant_role", "gateway_customer_id", "verified_at", "created_at", "updated_at"]


class GatewayAccountSetupSerializer(serializers.Serializer):  # Serializer for GatewayAccountSetup data
    phone_id = serializers.UUIDField(required=True)
    gateway_provider = serializers.ChoiceField(
        choices=[('fedapay', 'FedaPay'), ('mtn_momo', 'MTN Mobile Money'), ('moov_money', 'Moov Money'), ('orange_money', 'Orange Money')],
        required=True
    )
    payout_mode = serializers.CharField(max_length=50, required=False, allow_blank=True)


class TransactionFeeSerializer(serializers.ModelSerializer):  # Serializer for TransactionFee data
    transaction_ref = serializers.CharField(source="service_transaction.transaction_ref", read_only=True)

    class Meta:  # Meta class implementation
        model = TransactionFee
        fields = "__all__"
        read_only_fields = ["id", "service_transaction", "created_at", "collected_at"]


class GatewayTransactionSerializer(serializers.ModelSerializer):  # Serializer for GatewayTransaction data
    patient_email = serializers.EmailField(source="patient.email", read_only=True)
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    service_provider_email = serializers.EmailField(source="service_provider.email", read_only=True, allow_null=True)
    service_provider_name = serializers.CharField(source="service_provider.full_name", read_only=True, allow_null=True)
    gateway_provider_display = serializers.CharField(source="get_gateway_provider_display", read_only=True)
    transaction_type_display = serializers.CharField(source="get_transaction_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:  # Meta class implementation
        model = GatewayTransaction
        fields = "__all__"
        read_only_fields = ["id", "gateway_transaction_id", "gateway_reference", "created_at", "approved_at", "declined_at", "transferred_at"]


class ServiceTransactionSerializer(serializers.ModelSerializer):  # Serializer for ServiceTransaction data
    patient_email = serializers.EmailField(source="patient.email", read_only=True)
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    service_provider_email = serializers.EmailField(source="service_provider.email", read_only=True)
    service_provider_name = serializers.CharField(source="service_provider.full_name", read_only=True)
    service_type_display = serializers.CharField(source="get_service_type_display", read_only=True)
    payment_method_display = serializers.CharField(source="get_payment_method_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    fee_details = TransactionFeeSerializer(read_only=True)
    gateway_transaction_data = GatewayTransactionSerializer(source="gateway_transaction", read_only=True)
    service_name = serializers.CharField(source="service_catalog_item.service_name", read_only=True, allow_null=True)
    amount_formatted = serializers.SerializerMethodField()

    class Meta:  # Meta class implementation
        model = ServiceTransaction
        fields = "__all__"
        read_only_fields = ["id", "transaction_ref", "patient", "service_provider", "service_provider_role", "created_at", "completed_at", "failed_at", "refunded_at", "cancelled_at"]

    @extend_schema_field(serializers.CharField)
    def get_amount_formatted(self, obj):  # Get amount formatted
        from currency_converter.services import CurrencyConverterService
        return CurrencyConverterService.format_amount(obj.amount, obj.currency)


class ServicePaymentInitiateSerializer(serializers.Serializer):  # Serializer for ServicePaymentInitiate data
    service_catalog_id = serializers.UUIDField(required=False, allow_null=True)
    service_doctor_id = serializers.UUIDField(required=True)
    service_type = serializers.ChoiceField(
        choices=[
            ('appointment', 'Appointment'),
            ('prescription', 'Prescription'),
            ('lab_test', 'Lab Test'),
            ('consultation', 'Consultation'),
            ('pharmacy_purchase', 'Pharmacy Purchase'),
            ('insurance_claim', 'Insurance Claim'),
            ('emergency', 'Emergency Service'),
            ('other', 'Other'),
        ],
        required=True
    )
    service_id = serializers.UUIDField(required=True)
    service_description = serializers.CharField(max_length=500, required=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=1, required=False)
    currency = serializers.CharField(max_length=3, default="XOF")
    payment_method = serializers.ChoiceField(
        choices=[
            ('fedapay_mobile', 'FedaPay Mobile Money'),
            ('fedapay_card', 'FedaPay Card'),
            ('onsite_cash', 'On-site Cash'),
        ],
        required=True
    )
    phone_id = serializers.UUIDField(required=False, allow_null=True)


class FeeCalculationSerializer(serializers.Serializer):  # Serializer for FeeCalculation data
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=1, required=True)
    currency = serializers.CharField(max_length=3, default="XOF")


class PayoutScheduleSerializer(serializers.ModelSerializer):  # Serializer for PayoutSchedule data
    participant_email = serializers.EmailField(source="participant.email", read_only=True)
    participant_name = serializers.CharField(source="participant.full_name", read_only=True)
    payout_status_display = serializers.CharField(source="get_payout_status_display", read_only=True)

    class Meta:  # Meta class implementation
        model = PayoutSchedule
        fields = "__all__"
        read_only_fields = ["id", "participant", "participant_role", "created_at", "processed_at", "failed_at"]
