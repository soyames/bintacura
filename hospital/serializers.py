from rest_framework import serializers
from .models import HospitalStaff, Bed, Admission, DepartmentTask
from core.models import Department


class HospitalStaffSerializer(serializers.ModelSerializer):  # Serializer for HospitalStaff data
    department_name = serializers.CharField(source='department.name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    employment_type_display = serializers.CharField(source='get_employment_type_display', read_only=True)
    hospital = serializers.PrimaryKeyRelatedField(read_only=True, required=False)
    staff_participant = serializers.PrimaryKeyRelatedField(read_only=True, required=False)

    class Meta:  # Meta class implementation
        model = HospitalStaff
        fields = '__all__'
        read_only_fields = ['id', 'hospital', 'staff_participant', 'created_at', 'updated_at']


class BedSerializer(serializers.ModelSerializer):  # Serializer for Bed data
    department_name = serializers.CharField(source='department.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    bed_type_display = serializers.CharField(source='get_bed_type_display', read_only=True)

    class Meta:  # Meta class implementation
        model = Bed
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class AdmissionSerializer(serializers.ModelSerializer):  # Serializer for Admission data
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    bed_number = serializers.CharField(source='bed.bed_number', read_only=True)
    doctor_name = serializers.CharField(source='admitting_doctor.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    admission_type_display = serializers.CharField(source='get_admission_type_display', read_only=True)

    class Meta:  # Meta class implementation
        model = Admission
        fields = '__all__'
        read_only_fields = ['id', 'admission_number', 'created_at', 'updated_at']


class DepartmentTaskSerializer(serializers.ModelSerializer):  # Serializer for DepartmentTask data
    department_name = serializers.CharField(source='department.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True, allow_null=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True, allow_null=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:  # Meta class implementation
        model = DepartmentTask
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class DepartmentSerializer(serializers.ModelSerializer):  # Serializer for Department data
    head_of_department_name = serializers.CharField(source='head_of_department.full_name', read_only=True, allow_null=True)
    available_beds = serializers.SerializerMethodField()

    class Meta:  # Meta class implementation
        model = Department
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_available_beds(self, obj):  # Get available beds
        return obj.total_beds - obj.occupied_beds
