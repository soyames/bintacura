from django.contrib import admin
from .models import HealthRecord, DocumentUpload, TelemedicineSession
# NOTE: Wearable device models are now in the wearable_devices app

@admin.register(HealthRecord)
class HealthRecordAdmin(admin.ModelAdmin):  # Admin configuration for HealthRecord model
    list_display = ('id', 'assigned_to', 'created_by', 'type', 'title', 'date_of_record', 'is_encrypted', 'created_at')
    list_filter = ('type', 'is_encrypted', 'is_patient_uploaded')
    search_fields = ('assigned_to__email', 'title')
    date_hierarchy = 'date_of_record'

# NOTE: Wearable device admin has been moved to wearable_devices.admin

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
