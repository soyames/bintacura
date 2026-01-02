from django.contrib import admin
from .models import HealthRecord, WearableDevice, WearableData, DocumentUpload, TelemedicineSession

@admin.register(HealthRecord)
class HealthRecordAdmin(admin.ModelAdmin):  # Admin configuration for HealthRecord model
    list_display = ('id', 'assigned_to', 'created_by', 'type', 'title', 'date_of_record', 'is_encrypted', 'created_at')
    list_filter = ('type', 'is_encrypted', 'is_patient_uploaded')
    search_fields = ('assigned_to__email', 'title')
    date_hierarchy = 'date_of_record'

@admin.register(WearableDevice)
class WearableDeviceAdmin(admin.ModelAdmin):  # Admin configuration for WearableDevice model
    list_display = ('id', 'patient', 'device_name', 'device_type', 'manufacturer', 'status', 'is_connected', 'battery_level', 'last_sync_time')
    list_filter = ('device_type', 'status', 'is_connected')
    search_fields = ('patient__email', 'device_id', 'device_name')

@admin.register(WearableData)
class WearableDataAdmin(admin.ModelAdmin):  # Admin configuration for WearableData model
    list_display = ('id', 'patient', 'device', 'steps', 'heart_rate', 'blood_oxygen', 'timestamp', 'synced_at')
    list_filter = ('device_type',)
    search_fields = ('patient__email',)
    date_hierarchy = 'timestamp'

# NOTE: MenstrualCycle admin has been moved to menstruation.admin

@admin.register(DocumentUpload)
class DocumentUploadAdmin(admin.ModelAdmin):  # Admin configuration for DocumentUpload model
    list_display = ('id', 'uploaded_by', 'document_type', 'file_name', 'status', 'uploaded_at')
    list_filter = ('document_type', 'status')
    search_fields = ('uploaded_by__email', 'file_name')
    date_hierarchy = 'uploaded_at'

@admin.register(TelemedicineSession)
class TelemedicineSessionAdmin(admin.ModelAdmin):  # Admin configuration for TelemedicineSession model
    list_display = ('id', 'patient', 'doctor', 'session_id', 'status', 'scheduled_start_time', 'duration_minutes')
    list_filter = ('status',)
    search_fields = ('patient__email', 'doctor__email', 'session_id')
    date_hierarchy = 'scheduled_start_time'
