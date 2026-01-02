from rest_framework import serializers
from pharmacy.models import PharmacyData


class PharmacyDataSerializer(serializers.ModelSerializer):
    """Serializer for pharmacy data including activation code management"""
    participant_uid = serializers.UUIDField(source='participant.uid', read_only=True)
    participant_name = serializers.CharField(source='participant.full_name', read_only=True)
    participant_email = serializers.EmailField(source='participant.email', read_only=True)
    is_verified = serializers.BooleanField(source='participant.is_verified', read_only=True)
    
    # Activation code fields
    is_activation_code_expired = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()
    activation_status = serializers.SerializerMethodField()
    
    class Meta:
        model = PharmacyData
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
            'registration_number',
            'consultation_fee',
            'has_delivery',
            'delivery_radius_km',
            'accepts_prescriptions',
            'has_refrigeration',
            'operates_24_7',
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


class PharmacyDataDetailSerializer(PharmacyDataSerializer):
    """Extended serializer with sensitive information for authenticated requests"""
    # This includes activation code - only use in authenticated contexts
    pass


class PharmacyDataPublicSerializer(serializers.ModelSerializer):
    """Public serializer without sensitive activation code information"""
    participant_name = serializers.CharField(source='participant.full_name', read_only=True)
    is_verified = serializers.BooleanField(source='participant.is_verified', read_only=True)
    
    class Meta:
        model = PharmacyData
        fields = [
            'participant_name',
            'is_verified',
            'consultation_fee',
            'has_delivery',
            'delivery_radius_km',
            'accepts_prescriptions',
            'has_refrigeration',
            'operates_24_7',
            'operating_hours',
            'rating',
            'total_reviews',
        ]
