from rest_framework import serializers
from .models import *
from patient.models import PatientData, DependentProfile
from doctor.models import DoctorData
from .validators import validate_date_of_birth, validate_phone_number_format
from django.core.exceptions import ValidationError as DjangoValidationError


class ParticipantSerializer(serializers.ModelSerializer):  # Serializer for Participant model with all fields
    class Meta:
        model = Participant
        fields = "__all__"

    def validate_date_of_birth(self, value):
        """Validate date of birth is not in the future - ISSUE-PAT-005"""
        if value:
            try:
                validate_date_of_birth(value)
            except DjangoValidationError as e:
                raise serializers.ValidationError(e.message)
        return value

    def validate_phone_number(self, value):
        """Validate phone number format - ISSUE-PAT-049"""
        if value:
            try:
                validate_phone_number_format(value)
            except DjangoValidationError as e:
                raise serializers.ValidationError(e.message)
        return value

    def validate_email(self, value):
        """Check for duplicate email during updates - ISSUE-PAT-050"""
        if value:
            # Check if email already exists for a different user
            existing = Participant.objects.filter(email=value).exclude(
                uid=self.instance.uid if self.instance else None
            ).first()
            if existing:
                raise serializers.ValidationError(
                    f"Cet email est déjà utilisé pour un compte {existing.role}. "
                    "Chaque email ne peut être utilisé qu'une seule fois sur la plateforme."
                )
        return value


class ParticipantProfileSerializer(serializers.ModelSerializer):  # Serializer for ParticipantProfile model with all fields
    class Meta:
        model = ParticipantProfile
        fields = "__all__"


class PatientDataSerializer(serializers.ModelSerializer):  # Serializer for PatientData model with all fields
    class Meta:
        model = PatientData
        fields = "__all__"


class DoctorDataSerializer(serializers.ModelSerializer):  # Serializer for DoctorData model with participant info and services
    id = serializers.UUIDField(source="participant.uid", read_only=True)
    name = serializers.CharField(source="participant.full_name", read_only=True)
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    specialty = serializers.CharField(source="get_specialization_display", read_only=True)
    email = serializers.EmailField(source="participant.email", read_only=True)
    phone = serializers.CharField(source="participant.phone_number", read_only=True)
    profile_picture = serializers.URLField(source="participant.profile_picture_url", read_only=True)
    services = serializers.SerializerMethodField()

    def get_first_name(self, obj):  # Extract first name from participant's full name
        full_name = obj.participant.full_name
        return full_name.split()[0] if full_name else ""

    def get_last_name(self, obj):  # Extract last name from participant's full name
        full_name = obj.participant.full_name
        parts = full_name.split()
        return " ".join(parts[1:]) if len(parts) > 1 else ""

    def get_services(self, obj):
        from core.models import ProviderService
        services = ProviderService.objects.filter(
            provider=obj.participant, is_active=True, is_available=True
        )
        return ProviderServiceSerializer(services, many=True).data

    class Meta:
        model = DoctorData
        fields = [
            "id",
            "name",
            "first_name",
            "last_name",
            "specialty",
            "email",
            "phone",
            "profile_picture",
            "specialization",
            "license_number",
            "years_of_experience",
            "qualifications",
            "consultation_fee",
            "bio",
            "languages_spoken",
            "rating",
            "total_reviews",
            "is_available_for_telemedicine",
            "affiliated_hospitals",
            "services",
        ]


class ProviderDataSerializer(serializers.ModelSerializer):  # Serializer for ProviderData model with services
    participant_id = serializers.UUIDField(source="participant.uid", read_only=True)
    services = serializers.SerializerMethodField()

    def get_services(self, obj):
        from core.models import ProviderService
        services = ProviderService.objects.filter(
            provider=obj.participant, is_active=True, is_available=True
        )
        return ProviderServiceSerializer(services, many=True).data

    class Meta:
        model = ProviderData
        fields = [
            "participant_id",
            "provider_name",
            "provider_type",
            "license_number",
            "address",
            "city",
            "state",
            "country",
            "phone_number",
            "email",
            "website",
            "services_offered",
            "operating_hours",
            "emergency_services",
            "bed_capacity",
            "rating",
            "total_reviews",
            "services",
        ]


class ProviderServiceSerializer(serializers.ModelSerializer):  # Serializer for ProviderService model with category display
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = ProviderService
        fields = [
            "id",
            "name",
            "category",
            "category_display",
            "description",
            "price",
            "currency",
            "duration_minutes",
            "is_active",
            "is_available",
        ]


class WalletSerializer(serializers.ModelSerializer):  # Serializer for Wallet model with participant information
    participant_email = serializers.EmailField(
        source="participant.email", read_only=True
    )
    participant_name = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = [
            "id",
            "participant",
            "participant_email",
            "participant_name",
            "balance",
            "currency",
            "status",
            "created_at",
            "last_transaction_date",
        ]
        read_only_fields = ["id", "created_at", "last_transaction_date"]

    def get_participant_name(self, obj):  # Get participant's full name from profile or email
        profile = getattr(obj.participant, "profile", None)
        if profile:
            return f"{profile.first_name} {profile.last_name}"
        return obj.participant.email


class TransactionSerializer(serializers.ModelSerializer):  # Serializer for Transaction model with wallet and participant details
    wallet_owner = serializers.EmailField(
        source="wallet.participant.email", read_only=True
    )
    recipient_email = serializers.EmailField(source="recipient.email", read_only=True)
    sender_email = serializers.EmailField(source="sender.email", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "transaction_ref",
            "wallet",
            "wallet_owner",
            "transaction_type",
            "amount",
            "currency",
            "status",
            "payment_method",
            "description",
            "reference_id",
            "recipient",
            "recipient_email",
            "sender",
            "sender_email",
            "balance_before",
            "balance_after",
            "created_at",
            "completed_at",
            "metadata",
        ]
        read_only_fields = [
            "id",
            "transaction_ref",
            "created_at",
            "balance_before",
            "balance_after",
        ]


class DependentProfileSerializer(serializers.ModelSerializer):  # Serializer for DependentProfile model with calculated age
    age = serializers.SerializerMethodField()

    class Meta:
        model = DependentProfile
        fields = [
            "id",
            "patient",
            "full_name",
            "date_of_birth",
            "age",
            "gender",
            "relationship",
            "blood_type",
            "allergies",
            "chronic_conditions",
            "photo_url",
            "phone_number",
            "email",
            "address",
            "medical_notes",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "patient", "age", "created_at", "updated_at"]

    def get_age(self, obj):  # Calculate age from date of birth
        from datetime import date

        today = date.today()
        return (
            today.year
            - obj.date_of_birth.year
            - (
                (today.month, today.day)
                < (obj.date_of_birth.month, obj.date_of_birth.day)
            )
        )

    def validate_date_of_birth(self, value):
        """Validate date of birth is not in the future - ISSUE-PAT-005"""
        if value:
            try:
                validate_date_of_birth(value)
            except DjangoValidationError as e:
                raise serializers.ValidationError(e.message)
        return value

    def validate(self, attrs):
        """
        Validate that the dependent is not a duplicate - ISSUE-PAT-004
        Check for existing dependent with same name and date of birth
        """
        full_name = attrs.get('full_name')
        date_of_birth = attrs.get('date_of_birth')

        # Get the patient from context or instance
        if self.instance:
            patient = self.instance.patient
        else:
            patient = self.context.get('request').user if self.context.get('request') else None

        if patient and full_name and date_of_birth:
            # Check for duplicate dependents
            existing = DependentProfile.objects.filter(
                patient=patient,
                full_name__iexact=full_name,
                date_of_birth=date_of_birth,
                is_active=True
            ).exclude(id=self.instance.id if self.instance else None)

            if existing.exists():
                raise serializers.ValidationError({
                    'full_name': "Un dépendant avec le même nom et date de naissance existe déjà.",
                    'date_of_birth': "Un dépendant avec le même nom et date de naissance existe déjà."
                })

        return attrs


class HospitalProfileSerializer(serializers.ModelSerializer):  # Serializer for hospital participant with services
    name = serializers.CharField(source='full_name')
    phone = serializers.CharField(source='phone_number')
    services = serializers.SerializerMethodField()
    consultation_fee = serializers.SerializerMethodField()

    class Meta:
        model = Participant
        fields = [
            "uid",
            "name",
            "address",
            "city",
            "latitude",
            "longitude",
            "phone",
            "email",
            "consultation_fee",
            "services",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["uid", "created_at"]

    def get_consultation_fee(self, obj):
        """Return consultation fee using model method that uses settings default"""
        if hasattr(obj, 'hospital_data'):
            return obj.hospital_data.get_consultation_fee()
        from django.conf import settings
        return getattr(settings, 'DEFAULT_CONSULTATION_FEE_XOF', 3500)

    def get_services(self, obj):
        try:
            from hospital.models import HospitalDepartment
            departments = HospitalDepartment.objects.filter(hospital=obj)
            return ', '.join([dept.name for dept in departments]) if departments.exists() else 'Services généraux'
        except:
            return 'Services généraux'


