from rest_framework import serializers
from .models import PatientData, DependentProfile, PreventiveCareReminder, PersonalHealthNote
from core.models import Participant
from core.validators import validate_date_of_birth
from django.core.exceptions import ValidationError as DjangoValidationError


class PatientDataSerializer(serializers.ModelSerializer):  # Serializer for PatientData data
    participant = serializers.SerializerMethodField()
    marital_status_display = serializers.CharField(
        source="get_marital_status_display", read_only=True
    )

    class Meta:  # Meta class implementation
        model = PatientData
        fields = [
            "id",
            "participant",
            "blood_type",
            "allergies",
            "chronic_conditions",
            "current_medications",
            "medical_history",
            "height",
            "weight",
            "primary_doctor_id",
            "insurance_provider",
            "insurance_policy_number",
            "marital_status",
            "marital_status_display",
            "number_of_children",
            "profession",
            "home_doctor_id",
        ]

    def get_participant(self, obj) -> dict:  # Get participant
        participant = obj.participant
        return {
            "uid": str(participant.uid),
            "email": participant.email,
            "full_name": participant.full_name,
            "phone_number": participant.phone_number,
            "date_of_birth": participant.date_of_birth,
            "gender": participant.gender,
            "city": participant.city,
            "country": participant.country,
            "address": participant.address,
            "profile_picture_url": participant.profile_picture_url,
        }


class DependentProfileSerializer(serializers.ModelSerializer):  # Serializer for DependentProfile data
    relationship_display = serializers.CharField(
        source="get_relationship_display", read_only=True
    )
    gender_display = serializers.CharField(source="get_gender_display", read_only=True)

    class Meta:  # Meta class implementation
        model = DependentProfile
        fields = [
            "id",
            "patient",
            "full_name",
            "date_of_birth",
            "gender",
            "gender_display",
            "relationship",
            "relationship_display",
            "blood_type",
            "allergies",
            "chronic_conditions",
            "photo_url",
            "phone_number",
            "email",
            "address",
            "medical_notes",
            "created_at",
            "updated_at",
            "is_active",
        ]
        read_only_fields = ["id", "patient", "created_at", "updated_at"]

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


class PreventiveCareReminderSerializer(serializers.ModelSerializer):
    """Serializer for Preventive Care Reminders"""
    reminder_type_display = serializers.CharField(
        source="get_reminder_type_display", read_only=True
    )
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    
    class Meta:
        model = PreventiveCareReminder
        fields = [
            'id',
            'patient',
            'patient_name',
            'reminder_type',
            'reminder_type_display',
            'due_date',
            'description',
            'is_completed',
            'completed_date',
            'reminder_sent',
            'last_reminder_date',
            'created_at',
        ]
        read_only_fields = ['id', 'patient', 'reminder_sent', 'last_reminder_date', 'created_at']


class PersonalHealthNoteSerializer(serializers.ModelSerializer):
    """Serializer for Personal Health Notes"""
    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    
    class Meta:
        model = PersonalHealthNote
        fields = [
            'id',
            'patient',
            'patient_name',
            'title',
            'content',
            'note_date',
            'category',
            'category_display',
            'tags',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'patient', 'created_at', 'updated_at']
