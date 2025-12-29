from django.contrib import admin
from .models import Appointment, Availability, AppointmentQueue, AppointmentHistory, StaffTask
from .appointment_service_model import AppointmentService

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):  # Admin configuration for Appointment model
    list_display = ('id', 'patient', 'doctor', 'appointment_date', 'appointment_time', 'status', 'payment_status', 'consultation_fee', 'additional_services_total', 'queue_number')
    list_filter = ('status', 'type', 'payment_status', 'appointment_date')
    search_fields = ('patient__email', 'doctor__email', 'reason')
    date_hierarchy = 'appointment_date'
    ordering = ('-appointment_date', '-appointment_time')

@admin.register(AppointmentService)
class AppointmentServiceAdmin(admin.ModelAdmin):  # Admin configuration for AppointmentService model
    list_display = ('id', 'appointment', 'service', 'service_price', 'quantity', 'subtotal', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('appointment__id', 'service__name')
    readonly_fields = ('created_at', 'subtotal')

@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):  # Admin configuration for Availability model
    list_display = ('participant', 'weekday', 'start_time', 'end_time', 'slot_duration', 'is_active')
    list_filter = ('weekday', 'is_active')
    search_fields = ('participant__email',)

@admin.register(AppointmentQueue)
class AppointmentQueueAdmin(admin.ModelAdmin):  # Admin configuration for AppointmentQueue model
    list_display = ('appointment', 'participant', 'queue_number', 'status', 'estimated_wait_time')
    list_filter = ('status',)
    search_fields = ('appointment__id', 'participant__email')
    ordering = ('queue_number',)

@admin.register(AppointmentHistory)
class AppointmentHistoryAdmin(admin.ModelAdmin):  # Admin configuration for AppointmentHistory model
    list_display = ('appointment', 'changed_by', 'field_name', 'timestamp')
    list_filter = ('field_name', 'timestamp')
    search_fields = ('appointment__id',)
    readonly_fields = ('appointment', 'changed_by', 'field_name', 'old_value', 'new_value', 'change_reason', 'timestamp')

@admin.register(StaffTask)
class StaffTaskAdmin(admin.ModelAdmin):  # Admin configuration for StaffTask model
    list_display = ('title', 'assigned_to', 'assigned_by', 'priority', 'status', 'due_date')
    list_filter = ('status', 'priority')
    search_fields = ('title', 'description', 'assigned_to__email')
    date_hierarchy = 'due_date'
