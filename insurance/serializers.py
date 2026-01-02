from rest_framework import serializers
from decimal import Decimal
import logging
from currency_converter.services import CurrencyConverterService
from .models import (
    InsurancePackage,
    PatientInsuranceCard,
    InsuranceClaim,
    InsuranceSubscription,
    InsuranceInvoice,
    ClaimAttachment,
    HealthcarePartnerNetwork,
    InsuranceCoverageEnquiry,
    InsuranceStaff,
)

logger = logging.getLogger(__name__)


class InsurancePackageSerializer(serializers.ModelSerializer):  # Serializer for InsurancePackage data
    company_name = serializers.CharField(source="company.full_name", read_only=True)
    company_logo = serializers.CharField(
        source="company.profile_picture_url", read_only=True
    )
    type = serializers.CharField(source="package_type", read_only=True)
    monthly_premium = serializers.IntegerField(source="premium_amount", read_only=True)
    coverage_limit = serializers.IntegerField(
        source="max_coverage_amount", read_only=True
    )
    payment_frequency_display = serializers.CharField(
        source="get_payment_frequency_display", read_only=True
    )
    premium_amount_local = serializers.SerializerMethodField()
    coverage_limit_local = serializers.SerializerMethodField()

    class Meta:  # Meta class implementation
        model = InsurancePackage
        fields = [
            "id",
            "company",
            "company_name",
            "company_logo",
            "name",
            "description",
            "type",
            "monthly_premium",
            "coverage_limit",
            "package_type",
            "payment_frequency",
            "payment_frequency_display",
            "is_active",
            "consultation_discount_percentage",
            "is_consultation_free",
            "coverage_details",
            "premium_amount",
            "max_coverage_amount",
            "premium_amount_local",
            "coverage_limit_local",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "company", "created_at", "updated_at"]

    def get_premium_amount_local(self, obj) -> dict:
        """Convert premium amount to user's local currency"""
        base_currency = 'XOF'  # Insurance prices in XOF cents
        user = self.context.get('request').user if self.context.get('request') else None

        if not user or not user.is_authenticated:
            # Return in base currency if no user context
            # Convert from XOF cents to XOF
            amount_xof = Decimal(str(obj.premium_amount)) / 100
            return {
                'amount': float(amount_xof),
                'currency': base_currency,
                'formatted': CurrencyConverterService.format_amount(amount_xof, base_currency),
            }

        user_currency = CurrencyConverterService.get_participant_currency(user)
        # Convert from XOF cents to XOF (note: premium_amount already in cents)
        amount_xof = Decimal(str(obj.premium_amount)) / 100

        if base_currency != user_currency:
            try:
                conversion_result = CurrencyConverterService.convert(amount_xof, base_currency, user_currency)
                # Ensure we extract the number from the dict
                if isinstance(conversion_result, dict):
                    converted_amount = conversion_result.get('converted_amount', amount_xof)
                else:
                    converted_amount = conversion_result
            except Exception as e:
                logger.error(f"Currency conversion error: {e}")
                converted_amount = amount_xof
                user_currency = base_currency
        else:
            converted_amount = amount_xof

        return {
            'amount': float(converted_amount),
            'currency': user_currency,
            'formatted': CurrencyConverterService.format_amount(converted_amount, user_currency),
            'original_amount': float(amount_xof),
            'original_currency': base_currency,
            'needs_conversion': base_currency != user_currency
        }

    def get_coverage_limit_local(self, obj) -> dict:
        """Convert coverage limit to user's local currency"""
        if not obj.max_coverage_amount:
            return None

        base_currency = 'XOF'
        user = self.context.get('request').user if self.context.get('request') else None

        if not user or not user.is_authenticated:
            # Convert from XOF cents to XOF
            amount_xof = Decimal(str(obj.max_coverage_amount)) / 100
            return {
                'amount': float(amount_xof),
                'currency': base_currency,
                'formatted': CurrencyConverterService.format_amount(amount_xof, base_currency),
            }

        user_currency = CurrencyConverterService.get_participant_currency(user)
        # Convert from XOF cents to XOF
        amount_xof = Decimal(str(obj.max_coverage_amount)) / 100

        if base_currency != user_currency:
            try:
                conversion_result = CurrencyConverterService.convert(amount_xof, base_currency, user_currency)
                # Ensure we extract the number from the dict
                if isinstance(conversion_result, dict):
                    converted_amount = conversion_result.get('converted_amount', amount_xof)
                else:
                    converted_amount = conversion_result
            except Exception as e:
                logger.error(f"Currency conversion error: {e}")
                converted_amount = amount_xof
                user_currency = base_currency
        else:
            converted_amount = amount_xof

        return {
            'amount': float(converted_amount),
            'currency': user_currency,
            'formatted': CurrencyConverterService.format_amount(converted_amount, user_currency),
            'original_amount': float(amount_xof),
            'original_currency': base_currency,
            'needs_conversion': base_currency != user_currency
        }


class PatientInsuranceCardSerializer(serializers.ModelSerializer):  # Serializer for PatientInsuranceCard data
    insurance_package_name = serializers.CharField(
        source="insurance_package.name", read_only=True
    )
    company_name = serializers.CharField(
        source="insurance_package.company.full_name", read_only=True
    )

    class Meta:  # Meta class implementation
        model = PatientInsuranceCard
        fields = "__all__"


class InsuranceClaimSerializer(serializers.ModelSerializer):  # Serializer for InsuranceClaim data
    healthcare_provider_name = serializers.CharField(source="healthcare_provider.full_name", read_only=True)
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    
    class Meta:  # Meta class implementation
        model = InsuranceClaim
        fields = "__all__"


class InsuranceSubscriptionSerializer(serializers.ModelSerializer):  # Serializer for InsuranceSubscription data
    insurance_package_name = serializers.CharField(
        source="insurance_package.name", read_only=True
    )
    company_name = serializers.CharField(
        source="insurance_package.company.full_name", read_only=True
    )
    company_logo = serializers.CharField(
        source="insurance_package.company.profile_picture_url", read_only=True
    )
    payment_frequency_display = serializers.CharField(
        source="get_payment_frequency_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    insurance_card = PatientInsuranceCardSerializer(read_only=True)
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    approved_by_name = serializers.CharField(source="approved_by.full_name", read_only=True)
    assigned_to_name = serializers.CharField(source="assigned_to.full_name", read_only=True)
    premium_amount_local = serializers.SerializerMethodField()
    monthly_premium = serializers.SerializerMethodField()

    class Meta:  # Meta class implementation
        model = InsuranceSubscription
        fields = "__all__"

    def get_premium_amount_local(self, obj) -> str:
        """Convert premium amount to patient's local currency"""
        base_currency = 'XOF'
        patient_currency = CurrencyConverterService.get_participant_currency(obj.patient)
        # Convert from XOF cents to XOF
        amount_xof = Decimal(str(obj.premium_amount)) / 100

        if base_currency != patient_currency:
            try:
                conversion_result = CurrencyConverterService.convert(amount_xof, base_currency, patient_currency)
                # Ensure we extract the number from the dict
                if isinstance(conversion_result, dict):
                    converted_amount = conversion_result.get('converted_amount', amount_xof)
                else:
                    converted_amount = conversion_result
            except Exception as e:
                logger.error(f"Currency conversion error: {e}")
                converted_amount = amount_xof
                patient_currency = base_currency
        else:
            converted_amount = amount_xof

        return {
            'amount': float(converted_amount),
            'currency': patient_currency,
            'formatted': CurrencyConverterService.format_amount(converted_amount, patient_currency),
            'original_amount': float(amount_xof),
            'original_currency': base_currency,
            'needs_conversion': base_currency != patient_currency
        }

    def get_monthly_premium(self, obj) -> dict:
        """Alias for premium_amount_local for backwards compatibility"""
        return self.get_premium_amount_local(obj)['amount']


class InsuranceInvoiceSerializer(serializers.ModelSerializer):  # Serializer for InsuranceInvoice data
    insurance_package_name = serializers.CharField(
        source="insurance_package.name", read_only=True
    )
    company_name = serializers.CharField(
        source="insurance_package.company.full_name", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    amount_local = serializers.SerializerMethodField()

    class Meta:  # Meta class implementation
        model = InsuranceInvoice
        fields = "__all__"

    def get_amount_local(self, obj) -> str:
        """Convert invoice amount to patient's local currency"""
        base_currency = 'XOF'  # Insurance invoices in XOF cents
        patient_currency = CurrencyConverterService.get_participant_currency(obj.patient)
        # Convert from XOF cents to XOF
        amount_xof = Decimal(str(obj.amount)) / 100

        if base_currency != patient_currency:
            try:
                conversion_result = CurrencyConverterService.convert(amount_xof, base_currency, patient_currency)
                # Ensure we extract the number from the dict
                if isinstance(conversion_result, dict):
                    converted_amount = conversion_result.get('converted_amount', amount_xof)
                else:
                    converted_amount = conversion_result
            except Exception as e:
                logger.error(f"Currency conversion error: {e}")
                converted_amount = amount_xof
                patient_currency = base_currency
        else:
            converted_amount = amount_xof

        return {
            'amount': float(converted_amount),
            'currency': patient_currency,
            'formatted': CurrencyConverterService.format_amount(converted_amount, patient_currency),
            'original_amount': float(amount_xof),
            'original_currency': base_currency,
            'needs_conversion': base_currency != patient_currency
        }


class ClaimAttachmentSerializer(serializers.ModelSerializer):  # Serializer for ClaimAttachment data
    uploaded_by_name = serializers.CharField(
        source="uploaded_by.full_name", read_only=True
    )
    verified_by_name = serializers.CharField(
        source="verified_by.full_name", read_only=True
    )
    document_type_display = serializers.CharField(
        source="get_document_type_display", read_only=True
    )

    class Meta:  # Meta class implementation
        model = ClaimAttachment
        fields = [
            "id",
            "claim",
            "document_type",
            "document_type_display",
            "file_url",
            "file_name",
            "file_size",
            "mime_type",
            "description",
            "uploaded_by",
            "uploaded_by_name",
            "is_verified",
            "verified_by",
            "verified_by_name",
            "verified_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "is_verified",
            "verified_by",
            "verified_at",
        ]


class HealthcarePartnerNetworkSerializer(serializers.ModelSerializer):  # Serializer for HealthcarePartnerNetwork data
    insurance_company_name = serializers.CharField(
        source="insurance_company.full_name", read_only=True
    )
    partner_name = serializers.CharField(source="healthcare_partner.full_name", read_only=True)
    insurance_package_name = serializers.CharField(
        source="insurance_package.name", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    tier_display = serializers.CharField(source="get_tier_display", read_only=True)

    class Meta:  # Meta class implementation
        model = HealthcarePartnerNetwork
        fields = [
            "id",
            "insurance_company",
            "insurance_company_name",
            "healthcare_partner",
            "partner_name",
            "insurance_package",
            "insurance_package_name",
            "status",
            "status_display",
            "tier",
            "tier_display",
            "discount_percentage",
            "contracted_rate",
            "services_covered",
            "start_date",
            "end_date",
            "contract_number",
            "is_preferred",
            "patient_copay_percentage",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class InsuranceCoverageEnquirySerializer(serializers.ModelSerializer):  # Serializer for InsuranceCoverageEnquiry data
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    insurance_package_name = serializers.CharField(
        source="insurance_package.name", read_only=True
    )
    company_name = serializers.CharField(
        source="insurance_package.company.full_name", read_only=True
    )
    service_type_display = serializers.CharField(
        source="get_service_type_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    reviewed_by_name = serializers.CharField(
        source="reviewed_by.full_name", read_only=True
    )
    healthcare_provider_name = serializers.CharField(source="healthcare_provider.full_name", read_only=True)

    class Meta:  # Meta class implementation
        model = InsuranceCoverageEnquiry
        fields = [
            "id",
            "enquiry_number",
            "patient",
            "patient_name",
            "insurance_card",
            "insurance_package",
            "insurance_package_name",
            "company_name",
            "service_type",
            "service_type_display",
            "service_name",
            "service_description",
            "estimated_cost",
            "healthcare_provider",
            "healthcare_provider_name",
            "planned_date",
            "medical_necessity",
            "doctor_recommendation",
            "status",
            "status_display",
            "insurance_coverage_percentage",
            "insurance_covers_amount",
            "patient_pays_amount",
            "approval_notes",
            "rejection_reason",
            "conditions",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "expires_at",
            "attachment_urls",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "enquiry_number",
            "reviewed_by",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]


class InsuranceStaffSerializer(serializers.ModelSerializer):  # Serializer for InsuranceStaff data
    staff_name = serializers.CharField(source="staff_participant.full_name", read_only=True)
    staff_email = serializers.CharField(source="staff_participant.email", read_only=True)
    staff_role_display = serializers.CharField(source="get_staff_role_display", read_only=True)
    supervisor_name = serializers.CharField(source="supervisor.staff_participant.full_name", read_only=True)

    class Meta:  # Meta class implementation
        model = InsuranceStaff
        fields = [
            "id",
            "staff_participant",
            "staff_name",
            "staff_email",
            "insurance_company",
            "staff_role",
            "staff_role_display",
            "department",
            "employee_id",
            "permissions",
            "is_active",
            "supervisor",
            "supervisor_name",
            "hire_date",
            "termination_date",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
