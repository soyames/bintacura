from django.contrib import admin
from .models import WearableDevice, WearableData, WearableSyncLog


@admin.register(WearableDevice)
class WearableDeviceAdmin(admin.ModelAdmin):
    list_display = ['patient', 'device_type', 'device_name', 'status', 'last_sync', 'auto_sync_enabled', 'created_at']
    list_filter = ['device_type', 'status', 'auto_sync_enabled', 'created_at']
    search_fields = ['patient__email', 'patient__first_name', 'patient__last_name', 'device_name']
    readonly_fields = ['access_token_encrypted', 'refresh_token_encrypted', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Device Information', {
            'fields': ('patient', 'device_type', 'device_name', 'device_id', 'status')
        }),
        ('Sync Settings', {
            'fields': ('last_sync', 'sync_frequency', 'auto_sync_enabled', 'data_types_enabled')
        }),
        ('OAuth Tokens (Encrypted)', {
            'fields': ('access_token_encrypted', 'refresh_token_encrypted', 'token_expires_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(WearableData)
class WearableDataAdmin(admin.ModelAdmin):
    list_display = ['patient', 'device', 'data_type', 'value', 'unit', 'timestamp', 'created_at']
    list_filter = ['data_type', 'device__device_type', 'timestamp', 'created_at']
    search_fields = ['patient__email', 'patient__first_name', 'patient__last_name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Data Information', {
            'fields': ('device', 'patient', 'data_type', 'timestamp', 'value', 'unit')
        }),
        ('Metadata', {
            'fields': ('metadata', 'source_id'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(WearableSyncLog)
class WearableSyncLogAdmin(admin.ModelAdmin):
    list_display = ['device', 'sync_started_at', 'sync_completed_at', 'status', 'records_fetched', 'records_stored']
    list_filter = ['status', 'sync_started_at', 'device__device_type']
    search_fields = ['device__device_name', 'device__patient__email']
    readonly_fields = ['sync_started_at', 'created_at', 'updated_at']
    date_hierarchy = 'sync_started_at'

