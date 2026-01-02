from rest_framework import serializers
from .models import Prescription, PrescriptionItem, Medication, PrescriptionFulfillment, FulfillmentItem

class MedicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medication
        fields = '__all__'

class PrescriptionItemSerializer(serializers.ModelSerializer):
    medication_details = MedicationSerializer(source='medication', read_only=True)
    
    class Meta:
        model = PrescriptionItem
        fields = '__all__'

class PrescriptionSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    doctor_last_name = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    pharmacy_name = serializers.SerializerMethodField()
    items = PrescriptionItemSerializer(many=True, read_only=True)
    is_expired = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()
    qr_code_url = serializers.SerializerMethodField()
    qr_code = serializers.SerializerMethodField()
    
    class Meta:
        model = Prescription
        fields = '__all__'
    
    def get_doctor_name(self, obj) -> str:
        try:
            if obj.doctor:
                last_name = obj.doctor.last_name if obj.doctor.last_name else obj.doctor.full_name
                return f"Dr. {last_name}" if last_name else "Dr. Inconnu"
        except Exception:
            pass
        return "Inconnu"
    
    def get_doctor_last_name(self, obj) -> str:
        try:
            if obj.doctor:
                return obj.doctor.last_name if obj.doctor.last_name else obj.doctor.full_name or "Inconnu"
        except Exception:
            pass
        return "Inconnu"
    
    def get_patient_name(self, obj) -> str:
        try:
            if obj.patient:
                first_name = obj.patient.first_name or ""
                last_name = obj.patient.last_name or ""
                full = f"{first_name} {last_name}".strip()
                return full if full else obj.patient.email
        except Exception:
            pass
        return "Inconnu"
    
    def get_pharmacy_name(self, obj) -> dict:
        try:
            if obj.preferred_pharmacy:
                return obj.preferred_pharmacy.last_name or obj.preferred_pharmacy.full_name
        except Exception:
            pass
        return None
    
    def get_is_expired(self, obj) -> dict:
        from django.utils import timezone
        return obj.valid_until < timezone.now().date() if obj.valid_until else False
    
    def get_days_until_expiry(self, obj) -> dict:
        from django.utils import timezone
        if obj.valid_until:
            delta = obj.valid_until - timezone.now().date()
            return delta.days
        return None
    
    def get_qr_code_url(self, obj) -> str:
        from qrcode_generator.services import QRCodeService
        
        try:
            qr_code_obj = QRCodeService.get_qr_code('prescription', obj.id)
            
            if not qr_code_obj:
                qr_data = {
                    'prescription_id': str(obj.id),
                    'patient_id': str(obj.patient.uid) if obj.patient else None,
                    'doctor_id': str(obj.doctor.uid) if obj.doctor else None,
                    'created_date': str(obj.created_at.date()),
                    'valid_until': str(obj.valid_until) if obj.valid_until else None,
                }
                qr_code_obj = QRCodeService.generate_qr_code('prescription', obj.id, qr_data)
            
            if qr_code_obj and qr_code_obj.qr_code_image:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(qr_code_obj.qr_code_image.url)
        except Exception as e:
            pass
        return None
    
    def get_qr_code(self, obj) -> dict:
        from qrcode_generator.services import QRCodeService
        import base64
        
        try:
            qr_code_obj = QRCodeService.get_qr_code('prescription', obj.id)
            
            if not qr_code_obj:
                patient_name = None
                if obj.patient:
                    try:
                        first_name = obj.patient.first_name or ""
                        last_name = obj.patient.last_name or ""
                        patient_name = f"{first_name} {last_name}".strip() or None
                    except:
                        pass
                
                doctor_name = None
                if obj.doctor:
                    try:
                        last_name = obj.doctor.last_name or obj.doctor.full_name or ""
                        doctor_name = f"Dr. {last_name}" if last_name else None
                    except:
                        pass
                
                qr_data = {
                    'type': 'prescription',
                    'prescription_id': str(obj.id),
                    'patient_id': str(obj.patient.uid) if obj.patient else None,
                    'patient_name': patient_name,
                    'doctor_id': str(obj.doctor.uid) if obj.doctor else None,
                    'doctor_name': doctor_name,
                    'issue_date': str(obj.issue_date) if obj.issue_date else None,
                    'valid_until': str(obj.valid_until) if obj.valid_until else None,
                    'status': obj.status,
                }
                qr_code_obj = QRCodeService.generate_qr_code('prescription', obj.id, qr_data)
            
            if qr_code_obj and qr_code_obj.qr_code_image:
                with open(qr_code_obj.qr_code_image.path, 'rb') as img_file:
                    return base64.b64encode(img_file.read()).decode('utf-8')
        except Exception as e:
            pass
        return None

class FulfillmentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FulfillmentItem
        fields = '__all__'

class PrescriptionFulfillmentSerializer(serializers.ModelSerializer):
    pharmacy_name = serializers.SerializerMethodField()
    items = FulfillmentItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = PrescriptionFulfillment
        fields = '__all__'
    
    def get_pharmacy_name(self, obj) -> str:
        if obj.pharmacy:
            return obj.pharmacy.last_name
        return "Unknown"

