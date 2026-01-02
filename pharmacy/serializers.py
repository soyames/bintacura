from rest_framework import serializers
from .models import (
    PharmacyInventory, PharmacyOrder, PharmacyOrderItem,
    PharmacySupplier, PharmacyPurchase, PharmacyPurchaseItem,
    PharmacySale, PharmacySaleItem, PharmacyStaff,
    DoctorPharmacyReferral, PharmacyBonusConfig,
    PharmacyCounter, OrderQueue, DeliveryTracking, PickupVerification
)
from prescriptions.serializers import MedicationSerializer

class PharmacyInventorySerializer(serializers.ModelSerializer):  # Serializer for PharmacyInventory data
    medication_details = MedicationSerializer(source='medication', read_only=True)
    pharmacy_name = serializers.CharField(source='pharmacy.provider_data.provider_name', read_only=True)
    pharmacy_address = serializers.CharField(source='pharmacy.provider_data.address', read_only=True)
    pharmacy_phone = serializers.CharField(source='pharmacy.provider_data.phone_number', read_only=True)

    class Meta:  # Meta class implementation
        model = PharmacyInventory
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class PharmacyOrderItemSerializer(serializers.ModelSerializer):  # Serializer for PharmacyOrderItem data
    medication_details = MedicationSerializer(source='medication', read_only=True)

    class Meta:  # Meta class implementation
        model = PharmacyOrderItem
        fields = '__all__'
        read_only_fields = ['id']

class PharmacyOrderSerializer(serializers.ModelSerializer):  # Serializer for PharmacyOrder data
    items = PharmacyOrderItemSerializer(many=True, read_only=True)
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)

    class Meta:  # Meta class implementation
        model = PharmacyOrder
        fields = '__all__'
        read_only_fields = ['id', 'order_number', 'created_at', 'updated_at']

class PharmacySupplierSerializer(serializers.ModelSerializer):  # Serializer for PharmacySupplier data
    class Meta:  # Meta class implementation
        model = PharmacySupplier
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class PharmacyPurchaseItemSerializer(serializers.ModelSerializer):  # Serializer for PharmacyPurchaseItem data
    medication_details = MedicationSerializer(source='medication', read_only=True)

    class Meta:  # Meta class implementation
        model = PharmacyPurchaseItem
        fields = '__all__'
        read_only_fields = ['id']

class PharmacyPurchaseSerializer(serializers.ModelSerializer):  # Serializer for PharmacyPurchase data
    items = PharmacyPurchaseItemSerializer(many=True, read_only=True)
    supplier_details = PharmacySupplierSerializer(source='supplier', read_only=True)

    class Meta:  # Meta class implementation
        model = PharmacyPurchase
        fields = '__all__'
        read_only_fields = ['id', 'purchase_number', 'created_at', 'updated_at']

class PharmacySaleItemSerializer(serializers.ModelSerializer):  # Serializer for PharmacySaleItem data
    medication_details = MedicationSerializer(source='medication', read_only=True)

    class Meta:  # Meta class implementation
        model = PharmacySaleItem
        fields = '__all__'
        read_only_fields = ['id']

class PharmacySaleSerializer(serializers.ModelSerializer):  # Serializer for PharmacySale data
    items = PharmacySaleItemSerializer(many=True, read_only=True)
    patient_name = serializers.CharField(source='patient.full_name', read_only=True, allow_null=True)

    class Meta:  # Meta class implementation
        model = PharmacySale
        fields = '__all__'
        read_only_fields = ['id', 'sale_number', 'created_at']

class PharmacyStaffSerializer(serializers.ModelSerializer):  # Serializer for PharmacyStaff data
    pharmacy = serializers.PrimaryKeyRelatedField(read_only=True, required=False)
    staff_participant = serializers.PrimaryKeyRelatedField(read_only=True, required=False)
    auto_generate_password = serializers.BooleanField(write_only=True, default=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    assigned_counter = serializers.SerializerMethodField()
    participant_uid = serializers.CharField(source='staff_participant.uid', read_only=True)
    participant_id = serializers.IntegerField(source='staff_participant.id', read_only=True)

    class Meta:  # Meta class implementation
        model = PharmacyStaff
        fields = '__all__'
        read_only_fields = ['id', 'pharmacy', 'staff_participant', 'created_at', 'updated_at']

    def get_assigned_counter(self, obj) -> dict:
        if obj.staff_participant:
            counter = PharmacyCounter.objects.filter(current_staff=obj.staff_participant).first()
            if counter:
                return {
                    'id': counter.id,
                    'counter_number': counter.counter_number,
                    'counter_name': counter.counter_name
                }
        return None

class DoctorPharmacyReferralSerializer(serializers.ModelSerializer):  # Serializer for DoctorPharmacyReferral data
    doctor_name = serializers.CharField(source='doctor.full_name', read_only=True)
    pharmacy_name = serializers.CharField(source='pharmacy.provider_data.provider_name', read_only=True)
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)

    class Meta:  # Meta class implementation
        model = DoctorPharmacyReferral
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'bonus_earned']

class PharmacyBonusConfigSerializer(serializers.ModelSerializer):  # Serializer for PharmacyBonusConfig data
    doctor_name = serializers.CharField(source='doctor.full_name', read_only=True, allow_null=True)

    class Meta:  # Meta class implementation
        model = PharmacyBonusConfig
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PharmacyCounterSerializer(serializers.ModelSerializer):
    current_staff_name = serializers.CharField(source='current_staff.full_name', read_only=True, allow_null=True)
    pharmacy_name = serializers.CharField(source='pharmacy.full_name', read_only=True)
    
    class Meta:
        model = PharmacyCounter
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class OrderQueueSerializer(serializers.ModelSerializer):
    order_details = PharmacyOrderSerializer(source='order', read_only=True)
    claimed_by_name = serializers.CharField(source='claimed_by.full_name', read_only=True, allow_null=True)
    counter_name = serializers.CharField(source='counter.counter_name', read_only=True, allow_null=True)
    patient_name = serializers.CharField(source='order.patient.full_name', read_only=True)
    
    class Meta:
        model = OrderQueue
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'qr_code', 'queue_number']


class DeliveryTrackingSerializer(serializers.ModelSerializer):
    order_details = PharmacyOrderSerializer(source='order', read_only=True)
    delivery_person_name = serializers.CharField(source='delivery_person.full_name', read_only=True, allow_null=True)
    patient_name = serializers.CharField(source='order.patient.full_name', read_only=True)
    
    class Meta:
        model = DeliveryTracking
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'tracking_number', 'patient_confirmation_code']


class PickupVerificationSerializer(serializers.ModelSerializer):
    order_details = PharmacyOrderSerializer(source='order', read_only=True)
    scanned_by_name = serializers.CharField(source='scanned_by.full_name', read_only=True, allow_null=True)
    counter_name = serializers.CharField(source='counter.counter_name', read_only=True, allow_null=True)
    patient_name = serializers.CharField(source='order.patient.full_name', read_only=True)
    
    class Meta:
        model = PickupVerification
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'qr_code', 'verification_code']
