from django.contrib import admin
from .models import (
    HospitalStaff, Bed, Admission, DepartmentTask, EmergencyVisit, TriageAssessment,
    ICUAdmission, OperatingRoom, SurgerySchedule, StaffShift, OnCallSchedule,
    StaffCredential, PhysicianOrder, CriticalValueAlert, EquipmentMaintenance
)


@admin.register(HospitalStaff)
class HospitalStaffAdmin(admin.ModelAdmin):  # Admin configuration for HospitalStaff model
    list_display = ['full_name', 'hospital', 'role', 'department', 'employment_type', 'is_active', 'hire_date']
    list_filter = ['hospital', 'role', 'department', 'employment_type', 'is_active']
    search_fields = ['full_name', 'email', 'phone_number']


@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):  # Admin configuration for Bed model
    list_display = ['bed_number', 'room_number', 'department', 'bed_type', 'status', 'floor_number']
    list_filter = ['hospital', 'department', 'status', 'bed_type']
    search_fields = ['bed_number', 'room_number']


@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):  # Admin configuration for Admission model
    list_display = ['admission_number', 'patient', 'hospital', 'department', 'status', 'admission_date']
    list_filter = ['hospital', 'department', 'status', 'admission_type']
    search_fields = ['admission_number', 'patient__email', 'patient__full_name']


@admin.register(DepartmentTask)
class DepartmentTaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'department', 'assigned_to', 'priority', 'status', 'due_date']
    list_filter = ['department', 'priority', 'status']
    search_fields = ['title', 'description']


@admin.register(EmergencyVisit)
class EmergencyVisitAdmin(admin.ModelAdmin):
    list_display = ['ed_number', 'patient', 'hospital', 'arrival_time', 'status', 'assigned_doctor']
    list_filter = ['hospital', 'status', 'arrival_mode', 'arrival_time']
    search_fields = ['ed_number', 'patient__full_name', 'patient__email', 'chief_complaint']
    date_hierarchy = 'arrival_time'
    readonly_fields = ['ed_number', 'created_at', 'updated_at']


@admin.register(TriageAssessment)
class TriageAssessmentAdmin(admin.ModelAdmin):
    list_display = ['ed_visit', 'esi_level', 'color_code', 'triage_nurse', 'triage_time']
    list_filter = ['esi_level', 'color_code', 'triage_time']
    search_fields = ['ed_visit__ed_number', 'ed_visit__patient__full_name', 'chief_complaint']
    date_hierarchy = 'triage_time'


@admin.register(ICUAdmission)
class ICUAdmissionAdmin(admin.ModelAdmin):
    list_display = ['icu_admission_number', 'patient', 'hospital', 'icu_admission_time', 'status', 'apache_score']
    list_filter = ['hospital', 'status', 'admission_source', 'mechanical_ventilation']
    search_fields = ['icu_admission_number', 'patient__full_name', 'admission_diagnosis']
    date_hierarchy = 'icu_admission_time'
    readonly_fields = ['icu_admission_number', 'created_at', 'updated_at']


@admin.register(OperatingRoom)
class OperatingRoomAdmin(admin.ModelAdmin):
    list_display = ['or_number', 'or_name', 'hospital', 'or_type', 'status', 'floor_number']
    list_filter = ['hospital', 'status', 'or_type', 'is_active']
    search_fields = ['or_number', 'or_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(SurgerySchedule)
class SurgeryScheduleAdmin(admin.ModelAdmin):
    list_display = ['surgery_number', 'patient', 'procedure_name', 'scheduled_date', 'operating_room', 'status', 'primary_surgeon']
    list_filter = ['hospital', 'status', 'procedure_category', 'scheduled_date']
    search_fields = ['surgery_number', 'patient__full_name', 'procedure_name', 'procedure_code']
    date_hierarchy = 'scheduled_date'
    readonly_fields = ['surgery_number', 'created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {'fields': ('surgery_number', 'hospital', 'patient', 'admission')}),
        ('Scheduling', {'fields': ('operating_room', 'scheduled_date', 'scheduled_start_time', 'estimated_duration_minutes', 'scheduled_end_time')}),
        ('Surgery Details', {'fields': ('procedure_name', 'procedure_code', 'procedure_category', 'surgery_type')}),
        ('Surgical Team', {'fields': ('primary_surgeon', 'assistant_surgeon', 'anesthesiologist', 'scrub_nurse', 'circulating_nurse')}),
        ('Equipment', {'fields': ('special_equipment', 'implants_needed')}),
        ('Pre-Op', {'fields': ('pre_op_checklist_complete', 'consent_signed', 'surgical_site_marked')}),
        ('Actual Times', {'fields': ('actual_start_time', 'actual_end_time', 'actual_duration_minutes')}),
        ('Post-Op', {'fields': ('estimated_blood_loss_ml', 'complications', 'post_op_destination', 'post_op_orders')}),
        ('Status', {'fields': ('status', 'cancellation_reason', 'notes')}),
    )


@admin.register(StaffShift)
class StaffShiftAdmin(admin.ModelAdmin):
    list_display = ['staff', 'department', 'shift_date', 'shift_type', 'start_time', 'end_time', 'status']
    list_filter = ['hospital', 'department', 'shift_type', 'status', 'shift_date']
    search_fields = ['staff__full_name', 'department__name']
    date_hierarchy = 'shift_date'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(OnCallSchedule)
class OnCallScheduleAdmin(admin.ModelAdmin):
    list_display = ['staff', 'department', 'start_datetime', 'end_datetime', 'priority', 'status', 'was_called']
    list_filter = ['hospital', 'department', 'priority', 'status', 'was_called']
    search_fields = ['staff__full_name', 'contact_phone']
    date_hierarchy = 'start_datetime'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(StaffCredential)
class StaffCredentialAdmin(admin.ModelAdmin):
    list_display = ['staff', 'credential_type', 'credential_name', 'issue_date', 'expiration_date', 'status', 'is_verified']
    list_filter = ['credential_type', 'status', 'is_verified', 'expiration_date']
    search_fields = ['staff__full_name', 'credential_name', 'credential_number', 'issuing_organization']
    date_hierarchy = 'expiration_date'
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Staff', {'fields': ('staff',)}),
        ('Credential Details', {'fields': ('credential_type', 'credential_name', 'issuing_organization', 'credential_number')}),
        ('Dates', {'fields': ('issue_date', 'expiration_date', 'verification_date')}),
        ('Status', {'fields': ('status', 'is_verified', 'verified_by')}),
        ('Document', {'fields': ('document_file',)}),
        ('Alerts', {'fields': ('expiration_alert_sent', 'days_before_expiration_alert')}),
        ('Notes', {'fields': ('notes',)}),
    )


@admin.register(PhysicianOrder)
class PhysicianOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'patient', 'order_type', 'priority', 'status', 'ordering_physician', 'order_datetime']
    list_filter = ['hospital', 'order_type', 'priority', 'status', 'order_datetime']
    search_fields = ['order_number', 'patient__full_name', 'order_description']
    date_hierarchy = 'order_datetime'
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {'fields': ('order_number', 'hospital', 'patient', 'admission')}),
        ('Order Details', {'fields': ('order_type', 'order_description', 'clinical_indication', 'priority')}),
        ('Ordering', {'fields': ('ordering_physician', 'order_datetime')}),
        ('Drug Interaction', {'fields': ('drug_interaction_checked', 'drug_interaction_warnings')}),
        ('Execution', {'fields': ('status', 'acknowledged_by', 'acknowledged_datetime', 'completed_by', 'completed_datetime')}),
        ('Cancellation', {'fields': ('cancelled_by', 'cancellation_reason')}),
        ('Notes', {'fields': ('notes',)}),
    )


@admin.register(CriticalValueAlert)
class CriticalValueAlertAdmin(admin.ModelAdmin):
    list_display = ['patient', 'test_name', 'result_value', 'alert_type', 'severity', 'status', 'alert_created']
    list_filter = ['hospital', 'alert_type', 'severity', 'status', 'alert_created']
    search_fields = ['patient__full_name', 'test_name', 'result_value']
    date_hierarchy = 'alert_created'
    readonly_fields = ['created_at']
    fieldsets = (
        ('Patient Information', {'fields': ('hospital', 'patient', 'admission')}),
        ('Lab Test', {'fields': ('test_name', 'result_value', 'normal_range', 'unit_of_measure')}),
        ('Alert Details', {'fields': ('alert_type', 'severity', 'result_datetime', 'alert_created')}),
        ('Notification', {'fields': ('status', 'notified_physician', 'notification_datetime', 'notification_method')}),
        ('Acknowledgment', {'fields': ('acknowledged_by', 'acknowledged_datetime', 'action_taken')}),
        ('Notes', {'fields': ('notes',)}),
    )


@admin.register(EquipmentMaintenance)
class EquipmentMaintenanceAdmin(admin.ModelAdmin):
    list_display = ['maintenance_number', 'equipment_name', 'maintenance_type', 'scheduled_date', 'status', 'maintenance_passed']
    list_filter = ['hospital', 'maintenance_type', 'status', 'scheduled_date', 'department']
    search_fields = ['maintenance_number', 'equipment_name', 'equipment_serial_number']
    date_hierarchy = 'scheduled_date'
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Hospital', {'fields': ('hospital',)}),
        ('Equipment', {'fields': ('equipment_name', 'equipment_serial_number', 'equipment_location', 'department')}),
        ('Maintenance Details', {'fields': ('maintenance_type', 'maintenance_number', 'scheduled_date', 'completed_date')}),
        ('Personnel', {'fields': ('performed_by', 'supervised_by')}),
        ('Results', {'fields': ('status', 'maintenance_passed', 'findings', 'corrective_actions')}),
        ('Next Maintenance', {'fields': ('next_maintenance_due', 'maintenance_frequency_days')}),
        ('Cost', {'fields': ('maintenance_cost',)}),
        ('Notes', {'fields': ('notes',)}),
    )
