from rest_framework import serializers
from .models import DoctorData, DoctorAffiliation
from core.models import Participant


class DoctorDataSerializer(serializers.ModelSerializer):  # Serializer for DoctorData data
    participant = serializers.SerializerMethodField()
    specialization_display = serializers.CharField(
        source="get_specialization_display", read_only=True
    )
    consultation_fee = serializers.SerializerMethodField()
    affiliated_hospitals = serializers.SerializerMethodField()

    class Meta:  # Meta class implementation
        model = DoctorData
        fields = [
            "id",
            "participant",
            "specialization",
            "specialization_display",
            "license_number",
            "years_of_experience",
            "qualifications",
            "consultation_fee",
            "bio",
            "languages_spoken",
            "rating",
            "total_reviews",
            "total_consultations",
            "is_available_for_telemedicine",
            "affiliated_hospitals",
        ]
        read_only_fields = [
            "rating",
            "total_reviews",
            "total_consultations",
        ]

    def get_consultation_fee(self, obj):
        """Return consultation fee using model method that uses settings default"""
        return obj.get_consultation_fee()

    def get_participant(self, obj):  # Get participant
        participant = obj.participant
        return {
            "uid": str(participant.uid),
            "email": participant.email,
            "full_name": participant.full_name,
            "phone_number": participant.phone_number,
            "is_verified": participant.is_verified,
            "has_blue_checkmark": participant.has_blue_checkmark,
            "city": participant.city,
            "country": participant.country,
            "profile_picture_url": participant.profile_picture_url,
        }

    def get_affiliated_hospitals(self, obj):  # Get affiliated hospitals
        """Get list of affiliated hospitals from DoctorAffiliation model"""
        affiliations = DoctorAffiliation.objects.filter(
            doctor=obj.participant,
            is_active=True
        ).select_related('hospital')

        return [
            {
                "uid": str(aff.hospital.uid),
                "name": aff.hospital.full_name,
                "is_primary": aff.is_primary,
                "department_id": aff.department_id,
            }
            for aff in affiliations
        ]


class DoctorAffiliationSerializer(serializers.ModelSerializer):  # Serializer for DoctorAffiliation data
    hospital_name = serializers.CharField(source='hospital.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.full_name', read_only=True)

    class Meta:  # Meta class implementation
        model = DoctorAffiliation
        fields = [
            'id',
            'doctor',
            'doctor_name',
            'hospital',
            'hospital_name',
            'is_primary',
            'is_locked',
            'affiliation_date',
            'end_date',
            'is_active',
            'department_id',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'doctor', 'doctor_name', 'hospital_name', 'is_locked', 'created_at', 'updated_at']
