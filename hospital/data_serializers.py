from rest_framework import serializers
from hospital.models import HospitalData


class HospitalDataSerializer(serializers.ModelSerializer):
    """Serializer for hospital data including activation code management"""
    participant_uid = serializers.UUIDField(source='participant.uid', read_only=True)
    participant_name = serializers.CharField(source='participant.full_name', read_only=True)
    participant_email = serializers.EmailField(source='participant.email', read_only=True)
    is_verified = serializers.BooleanField(source='participant.is_verified', read_only=True)
    
    # Activation code fields
    is_activation_code_expired = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()
    activation_status = serializers.SerializerMethodField()
    
    class Meta:
        model = HospitalData
        fields = [
            'id',
            'participant_uid',
            'participant_name',
            'participant_email',
            'is_verified',
            'license_number',
            'identifier',
            'activation_code',
            'activation_code_issued_at',
            'activation_code_expires_at',
            'activation_code_validity_years',
            'is_activation_code_expired',
            'days_until_expiry',
            'activation_status',
            'bed_capacity',
            'consultation_fee',
            'emergency_services',
            'has_icu',
            'has_laboratory',
            'operating_hours',
            'rating',
            'total_reviews',
        ]
        read_only_fields = [
            'id',
            'participant_uid',
            'identifier',
            'activation_code',
            'activation_code_issued_at',
            'activation_code_expires_at',
            'rating',
            'total_reviews',
        ]
    
    def get_is_activation_code_expired(self, obj):
        """Check if activation code is expired"""
        return obj.is_activation_code_expired()
    
    def get_days_until_expiry(self, obj):
        """Get days until activation code expires"""
        return obj.days_until_expiry()
    
    def get_activation_status(self, obj):
        """Get human-readable activation status"""
        if not obj.identifier:
            return 'not_verified'
        if not obj.activation_code:
            return 'pending_activation'
        if obj.is_activation_code_expired():
            return 'expired'
        
        days = obj.days_until_expiry()
        if days is None:
            return 'active'
        if days <= 30:
            return 'expiring_soon'
        return 'active'


class HospitalDataDetailSerializer(HospitalDataSerializer):
    """Extended serializer with sensitive information for authenticated requests"""
    # This includes activation code - only use in authenticated contexts
    pass


class HospitalDataPublicSerializer(serializers.ModelSerializer):
    """Public serializer without sensitive activation code information"""
    participant_name = serializers.CharField(source='participant.full_name', read_only=True)
    is_verified = serializers.BooleanField(source='participant.is_verified', read_only=True)
    
    class Meta:
        model = HospitalData
        fields = [
            'participant_name',
            'is_verified',
            'bed_capacity',
            'consultation_fee',
            'emergency_services',
            'has_icu',
            'has_laboratory',
            'operating_hours',
            'rating',
            'total_reviews',
        ]
