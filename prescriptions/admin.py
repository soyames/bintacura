from django.contrib import admin
from .models import Medication, Prescription, PrescriptionItem, PrescriptionFulfillment, FulfillmentItem, PrescriptionRenewalRequest

@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):  # Admin configuration for Medication model
    list_display = ('name', 'generic_name', 'brand_name', 'category', 'is_controlled_substance', 'requires_prescription')
    list_filter = ('category', 'is_controlled_substance', 'requires_prescription')
    search_fields = ('name', 'generic_name', 'brand_name')

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):  # Admin configuration for Prescription model
    list_display = ('id', 'patient', 'doctor', 'issue_date', 'valid_until', 'status', 'type')
    list_filter = ('status', 'type', 'is_controlled_substance', 'requires_pharmacist_verification')
    search_fields = ('patient__email', 'doctor__email', 'diagnosis')
    date_hierarchy = 'issue_date'
    readonly_fields = ('created_at', 'updated_at')

class PrescriptionItemInline(admin.TabularInline):  # PrescriptionItemInline class implementation
    model = PrescriptionItem
    extra = 1

@admin.register(PrescriptionItem)
class PrescriptionItemAdmin(admin.ModelAdmin):  # Admin configuration for PrescriptionItem model
    list_display = ('prescription', 'medication_name', 'dosage', 'quantity', 'frequency', 'duration_days')
    list_filter = ('frequency',)
    search_fields = ('medication_name', 'prescription__id')

@admin.register(PrescriptionFulfillment)
class PrescriptionFulfillmentAdmin(admin.ModelAdmin):  # Admin configuration for PrescriptionFulfillment model
    list_display = ('id', 'prescription', 'pharmacy', 'pharmacist', 'status', 'fulfillment_date', 'total_cost')
    list_filter = ('status', 'fulfillment_date')
    search_fields = ('prescription__id', 'pharmacy__email')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(FulfillmentItem)
class FulfillmentItemAdmin(admin.ModelAdmin):  # Admin configuration for FulfillmentItem model
    list_display = ('fulfillment', 'prescription_item', 'quantity_fulfilled', 'quantity_remaining', 'unit_price', 'total_price')
    search_fields = ('fulfillment__id', 'prescription_item__medication_name')

@admin.register(PrescriptionRenewalRequest)
class PrescriptionRenewalRequestAdmin(admin.ModelAdmin):  # Admin configuration for PrescriptionRenewalRequest model
    list_display = ('id', 'patient', 'doctor', 'original_prescription', 'status', 'requested_at', 'reviewed_at')
    list_filter = ('status', 'requested_at', 'reviewed_at')
    search_fields = ('patient__email', 'doctor__email', 'patient_notes', 'doctor_notes')
    readonly_fields = ('requested_at', 'created_at', 'updated_at')
    fieldsets = (
        ('Request Information', {
            'fields': ('original_prescription', 'patient', 'doctor', 'status')
        }),
        ('Notes', {
            'fields': ('patient_notes', 'doctor_notes')
        }),
        ('Renewal', {
            'fields': ('renewed_prescription', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('requested_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
