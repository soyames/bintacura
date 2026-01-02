from rest_framework import serializers
from .models import *
from .appointment_service_model import AppointmentService


class AppointmentServiceSerializer(serializers.ModelSerializer):
    """Serializer for additional services in appointment"""
    service_name = serializers.CharField(source='service.name', read_only=True)
    service_category = serializers.CharField(source='service.category', read_only=True)
    
    class Meta:  # Meta class implementation
        model = AppointmentService
        fields = ['id', 'service', 'service_name', 'service_category', 'service_price', 'quantity', 'subtotal', 'created_at']
        read_only_fields = ['id', 'subtotal', 'created_at']


class AppointmentSerializer(serializers.ModelSerializer):  # Serializer for Appointment data
    service_name = serializers.CharField(
        source="service.name", read_only=True, allow_null=True
    )
    queue_info = serializers.SerializerMethodField()
    payment_info = serializers.SerializerMethodField()
    additional_services = AppointmentServiceSerializer(source='appointment_services', many=True, read_only=True)
    doctor = serializers.SerializerMethodField()
    hospital = serializers.SerializerMethodField()
    patient_info = serializers.SerializerMethodField()

    class Meta:  # Meta class implementation
        model = Appointment
        fields = "__all__"
    
    def get_doctor(self, obj) -> dict:
        """Get doctor information"""
        if obj.doctor:
            doctor_name = obj.doctor.full_name or f"Dr. {obj.doctor.email.split('@')[0]}"
            if hasattr(obj.doctor, 'doctorprofile') and obj.doctor.doctorprofile:
                if obj.doctor.doctorprofile.first_name or obj.doctor.doctorprofile.last_name:
                    doctor_name = f"Dr. {obj.doctor.doctorprofile.first_name or ''} {obj.doctor.doctorprofile.last_name or ''}".strip()
            return {
                'id': str(obj.doctor.uid),
                'name': doctor_name,
                'email': obj.doctor.email,
                'phone_number': obj.doctor.phone_number,
                'specialization': obj.doctor.doctorprofile.specialization if hasattr(obj.doctor, 'doctorprofile') and obj.doctor.doctorprofile else None
            }
        return None
    
    def get_hospital(self, obj) -> dict:
        """Get hospital information"""
        if obj.hospital:
            hospital_name = obj.hospital.full_name or obj.hospital.email.split('@')[0]
            if hasattr(obj.hospital, 'hospitalprofile') and obj.hospital.hospitalprofile:
                if obj.hospital.hospitalprofile.organization_name:
                    hospital_name = obj.hospital.hospitalprofile.organization_name
            return {
                'id': str(obj.hospital.uid),
                'name': hospital_name,
                'email': obj.hospital.email,
                'phone_number': obj.hospital.phone_number,
                'address': obj.hospital.address,
                'city': obj.hospital.city
            }
        return None
    
    def get_patient_info(self, obj) -> dict:
        """Get patient information"""
        if obj.patient:
            return {
                'id': str(obj.patient.uid),
                'full_name': obj.patient.full_name or "",
                'email': obj.patient.email,
                'phone_number': obj.patient.phone_number
            }
        return None
    
    def get_queue_info(self, obj) -> dict:
        """Get queue information if exists"""
        try:
            queue_entry = obj.queue_entry
            return {
                'queue_number': queue_entry.queue_number,
                'estimated_wait_time': queue_entry.estimated_wait_time,
                'status': queue_entry.status
            }
        except:
            return None
    
    def get_payment_info(self, obj) -> dict:
        """Get payment details with breakdown"""
        return {
            'payment_status': obj.payment_status,
            'consultation_fee': float(obj.consultation_fee),
            'additional_services_total': float(obj.additional_services_total),
            'original_price': float(obj.original_price),
            'final_price': float(obj.final_price)
        }


class AvailabilitySerializer(serializers.ModelSerializer):  # Serializer for Availability data
    class Meta:  # Meta class implementation
        model = Availability
        fields = "__all__"
        read_only_fields = ["provider", "id", "created_at", "updated_at"]


class AppointmentQueueSerializer(serializers.ModelSerializer):  # Serializer for AppointmentQueue data
    patient_name = serializers.CharField(source='appointment.patient.full_name', read_only=True)
    patient_email = serializers.EmailField(source='appointment.patient.email', read_only=True)
    appointment_time = serializers.TimeField(source='appointment.appointment_time', read_only=True)
    appointment_type = serializers.CharField(source='appointment.type', read_only=True)
    reason = serializers.CharField(source='appointment.reason', read_only=True)
    
    class Meta:  # Meta class implementation
        model = AppointmentQueue
        fields = [
            'id', 'appointment', 'participant', 'queue_number',  # Changed provider to participant
            'estimated_wait_time', 'actual_start_time', 'actual_end_time',
            'status', 'created_at', 'updated_at',
            'patient_name', 'patient_email', 'appointment_time',
            'appointment_type', 'reason'
        ]
        read_only_fields = [
            'id', 'queue_number', 'estimated_wait_time',
            'actual_start_time', 'actual_end_time', 'created_at', 'updated_at'
        ]


class AppointmentBookingSerializer(serializers.Serializer):
    """Serializer for booking appointments with payment"""
    participant_id = serializers.UUIDField(required=False, allow_null=True)
    doctor_id = serializers.UUIDField(required=False, allow_null=True)
    hospital_id = serializers.UUIDField(required=False, allow_null=True)
    additional_service_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        help_text="List of additional service IDs to add to appointment"
    )
    appointment_date = serializers.DateField(required=True)
    appointment_time = serializers.TimeField(required=True)
    type = serializers.ChoiceField(
        choices=[
            ('consultation', 'Consultation'),
            ('follow_up', 'Follow Up'),
            ('emergency', 'Emergency'),
            ('checkup', 'Checkup'),
            ('procedure', 'Procedure')
        ],
        default='consultation'
    )
    
    def validate(self, data):
        participant_id = data.get('participant_id') or data.get('doctor_id') or data.get('hospital_id')
        if not participant_id:
            raise serializers.ValidationError("Either participant_id, doctor_id, or hospital_id is required")
        data['participant_id'] = participant_id
        return data
    reason = serializers.CharField(required=False, allow_blank=True)
    symptoms = serializers.CharField(required=False, allow_blank=True)
    payment_method = serializers.ChoiceField(
        choices=[
            ('wallet', 'Wallet'),
            ('onsite', 'On-site/Cash'),
            ('cash', 'Cash'),
            ('online', 'Online Payment'),
            ('fedapay', 'FedaPay'),
            ('card', 'Credit/Debit Card'),
            ('mobile_money', 'Mobile Money')
        ],
        default='onsite'
    )
