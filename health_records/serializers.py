from rest_framework import serializers
from .models import *
from core.models import Participant

class HealthRecordSerializer(serializers.ModelSerializer):  # Serializer for HealthRecord data
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=Participant.objects.all(),
        error_messages={
            'does_not_exist': 'Patient not found',
            'incorrect_type': 'Invalid patient ID format',
            'required': 'Patient ID is required'
        }
    )
    created_by_name = serializers.SerializerMethodField()
    created_by_contact = serializers.SerializerMethodField()
    can_view_details = serializers.SerializerMethodField()

    class Meta:  # Meta class implementation
        model = HealthRecord
        fields = '__all__'
        read_only_fields = ('created_by',)

    def validate_assigned_to(self, value):  # Validate assigned_to is a patient
        if value.role != 'patient':
            raise serializers.ValidationError('Records can only be assigned to patients')
        return value

    def validate(self, data):  # Additional validation
        # Ensure required fields are present for creation
        if not self.instance:  # Creating new record
            required_fields = ['type', 'title', 'date_of_record']
            for field in required_fields:
                if field not in data or not data[field]:
                    raise serializers.ValidationError({field: f'{field} is required'})
        return data

    def get_created_by_name(self, obj):  # Get creator's full name
        return obj.created_by.full_name if obj.created_by else 'Unknown'

    def get_created_by_contact(self, obj):  # Get creator's contact info
        if obj.created_by:
            return {'email': obj.created_by.email, 'phone': obj.created_by.phone_number or ''}
        return None

    def get_can_view_details(self, obj):  # Check if current participant can view full details
        request = self.context.get('request')
        if not request or not request.user:
            return False
        participant = request.user

        # Patient can view their own records
        if participant.role == 'patient' and obj.assigned_to_id == participant.uid:
            return True

        # Creator can view
        if (participant.role == 'doctor' or participant.role == 'hospital') and obj.created_by_id == participant.uid:
            return True

        # Participants in participants list can view (for referrals)
        if obj.participants and str(participant.uid) in obj.participants:
            return True

        return False

class WearableDataSerializer(serializers.ModelSerializer):  # Serializer for WearableData data
    class Meta:  # Meta class implementation
        model = WearableData
        fields = '__all__'
