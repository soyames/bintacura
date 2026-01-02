from django.contrib import admin
from .models import MenstrualCycle, CycleSymptom, CycleReminder


@admin.register(MenstrualCycle)
class MenstrualCycleAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'cycle_start_date', 'cycle_length',
        'period_length', 'flow_intensity', 'is_active_cycle'
    ]
    list_filter = ['is_active_cycle', 'flow_intensity', 'mood', 'cycle_start_date']
    search_fields = ['patient__full_name', 'patient__email']
    readonly_fields = [
        'created_at', 'updated_at',
        'predicted_ovulation_date', 'predicted_next_period_date',
        'predicted_fertile_window_start', 'predicted_fertile_window_end'
    ]
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient', 'is_active_cycle')
        }),
        ('Cycle Dates', {
            'fields': (
                'cycle_start_date', 'cycle_end_date',
                'period_length', 'cycle_length'
            )
        }),
        ('Cycle Details', {
            'fields': ('flow_intensity', 'symptoms', 'mood', 'notes')
        }),
        ('Predictions', {
            'fields': (
                'predicted_ovulation_date', 'predicted_next_period_date',
                'predicted_fertile_window_start', 'predicted_fertile_window_end'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CycleSymptom)
class CycleSymptomAdmin(admin.ModelAdmin):
    list_display = ['cycle', 'date', 'symptom_type', 'severity', 'created_at']
    list_filter = ['symptom_type', 'severity', 'date']
    search_fields = ['cycle__patient__full_name', 'symptom_type', 'notes']
    readonly_fields = ['uid', 'created_at']


@admin.register(CycleReminder)
class CycleReminderAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'reminder_type', 'reminder_date',
        'reminder_time', 'is_sent', 'is_enabled'
    ]
    list_filter = ['reminder_type', 'is_sent', 'is_enabled', 'reminder_date']
    search_fields = ['patient__full_name', 'patient__email', 'message']
    readonly_fields = ['created_at', 'updated_at']
