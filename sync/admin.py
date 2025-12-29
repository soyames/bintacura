"""
Admin Interface for Sync Models

Provides comprehensive admin views for monitoring and managing
offline-first synchronization infrastructure.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import SyncEvent, SyncInstance, SyncInstanceLog, SyncConflict


@admin.register(SyncEvent)
class SyncEventAdmin(admin.ModelAdmin):
    """Admin interface for SyncEvent model"""

    list_display = [
        'id', 'event_type_badge', 'model_name', 'object_id',
        'timestamp', 'instance_name', 'synced_badge', 'conflict_badge'
    ]
    list_filter = [
        'event_type', 'synced_to_cloud', 'conflict_detected',
        'timestamp', 'model_name'
    ]
    search_fields = ['model_name', 'object_id', 'instance_id']
    readonly_fields = [
        'id', 'timestamp', 'data_hash', 'created_at_display',
        'verify_integrity_status'
    ]
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']

    fieldsets = (
        ('Event Information', {
            'fields': ('id', 'event_type', 'model_name', 'object_id', 'timestamp')
        }),
        ('Instance Tracking', {
            'fields': ('instance_id',)
        }),
        ('Data', {
            'fields': ('data_snapshot', 'changed_fields', 'data_hash', 'verify_integrity_status'),
            'classes': ('collapse',)
        }),
        ('Sync Status', {
            'fields': ('synced_to_cloud', 'synced_at')
        }),
        ('Conflict Information', {
            'fields': ('conflict_detected', 'conflict_resolution'),
            'classes': ('collapse',)
        }),
    )

    def event_type_badge(self, obj):
        """Display event type with color badge"""
        colors = {
            'create': '#28a745',  # green
            'update': '#ffc107',  # yellow
            'delete': '#dc3545',  # red
        }
        color = colors.get(obj.event_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.event_type.upper()
        )
    event_type_badge.short_description = 'Type'

    def synced_badge(self, obj):
        """Display sync status with badge"""
        if obj.synced_to_cloud:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px;">✓ Synced</span>'
            )
        return format_html(
            '<span style="background-color: #ffc107; color: black; padding: 3px 8px; '
            'border-radius: 3px;">⏳ Pending</span>'
        )
    synced_badge.short_description = 'Sync Status'

    def conflict_badge(self, obj):
        """Display conflict status with badge"""
        if obj.conflict_detected:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 8px; '
                'border-radius: 3px;">⚠ Conflict</span>'
            )
        return format_html(
            '<span style="background-color: #28a745; color: white; padding: 3px 8px; '
            'border-radius: 3px;">✓ OK</span>'
        )
    conflict_badge.short_description = 'Conflict'

    def instance_name(self, obj):
        """Display instance name if available"""
        if obj.instance_id:
            try:
                instance = SyncInstance.objects.get(instance_id=obj.instance_id)
                return instance.instance_name
            except SyncInstance.DoesNotExist:
                return str(obj.instance_id)[:8]
        return 'Cloud'
    instance_name.short_description = 'Instance'

    def created_at_display(self, obj):
        """Display timestamp in readable format"""
        return obj.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    created_at_display.short_description = 'Created At'

    def verify_integrity_status(self, obj):
        """Verify data integrity and display status"""
        is_valid = obj.verify_integrity()
        if is_valid:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">✓ Valid</span>'
            )
        return format_html(
            '<span style="color: #dc3545; font-weight: bold;">✗ TAMPERED</span>'
        )
    verify_integrity_status.short_description = 'Data Integrity'

    def has_add_permission(self, request):
        """Disable manual creation of sync events (auto-generated only)"""
        return False


@admin.register(SyncInstance)
class SyncInstanceAdmin(admin.ModelAdmin):
    """Admin interface for SyncInstance model"""

    list_display = [
        'instance_name', 'instance_type', 'organization', 'platform',
        'status_badge', 'last_sync_display', 'sync_enabled'
    ]
    list_filter = ['instance_type', 'platform', 'is_active', 'sync_enabled', 'registered_at']
    search_fields = ['instance_name', 'api_key', 'organization__name']
    readonly_fields = [
        'instance_id', 'api_key', 'registered_at', 'last_sync_at',
        'token_display'
    ]

    fieldsets = (
        ('Instance Information', {
            'fields': ('instance_id', 'instance_name', 'instance_type', 'organization')
        }),
        ('Device Information', {
            'fields': ('platform', 'hardware_id', 'os_version')
        }),
        ('Authentication', {
            'fields': ('api_key', 'api_secret_hash', 'token_display'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'registered_at', 'last_sync_at')
        }),
        ('Sync Configuration', {
            'fields': ('sync_enabled', 'sync_interval_minutes')
        }),
    )

    actions = ['activate_instances', 'deactivate_instances', 'generate_new_tokens']

    def status_badge(self, obj):
        """Display active status with badge"""
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px;">✓ Active</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 3px 8px; '
            'border-radius: 3px;">✗ Inactive</span>'
        )
    status_badge.short_description = 'Status'

    def last_sync_display(self, obj):
        """Display last sync time in readable format"""
        if obj.last_sync_at:
            delta = timezone.now() - obj.last_sync_at
            if delta.days > 0:
                return f"{delta.days}d ago"
            elif delta.seconds > 3600:
                return f"{delta.seconds // 3600}h ago"
            elif delta.seconds > 60:
                return f"{delta.seconds // 60}m ago"
            else:
                return "Just now"
        return "Never"
    last_sync_display.short_description = 'Last Sync'

    def token_display(self, obj):
        """Display JWT token generation button"""
        token = obj.generate_jwt_token()
        return format_html(
            '<textarea readonly style="width: 100%; height: 100px; font-family: monospace; '
            'font-size: 11px;">{}</textarea>',
            token
        )
    token_display.short_description = 'JWT Token (365 days)'

    def activate_instances(self, request, queryset):
        """Bulk activate instances"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} instance(s) activated.')
    activate_instances.short_description = 'Activate selected instances'

    def deactivate_instances(self, request, queryset):
        """Bulk deactivate instances"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} instance(s) deactivated.')
    deactivate_instances.short_description = 'Deactivate selected instances'

    def generate_new_tokens(self, request, queryset):
        """Generate new JWT tokens for selected instances"""
        for instance in queryset:
            token = instance.generate_jwt_token()
            self.message_user(
                request,
                f'New token for {instance.instance_name}: {token[:50]}...'
            )
    generate_new_tokens.short_description = 'Generate new JWT tokens'


@admin.register(SyncInstanceLog)
class SyncInstanceLogAdmin(admin.ModelAdmin):
    """Admin interface for SyncInstanceLog model"""

    list_display = [
        'id', 'instance', 'direction_badge', 'status_badge',
        'started_at', 'duration', 'records_summary', 'conflicts_detected'
    ]
    list_filter = ['direction', 'status', 'started_at', 'instance']
    search_fields = ['instance__instance_name', 'error_message']
    readonly_fields = [
        'id', 'instance', 'direction', 'started_at', 'completed_at',
        'records_pushed', 'records_pulled', 'conflicts_detected',
        'errors_count', 'error_message', 'metadata'
    ]
    date_hierarchy = 'started_at'
    ordering = ['-started_at']

    fieldsets = (
        ('Sync Information', {
            'fields': ('id', 'instance', 'direction', 'status')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at')
        }),
        ('Statistics', {
            'fields': (
                'records_pushed', 'records_pulled',
                'conflicts_detected', 'errors_count'
            )
        }),
        ('Error Details', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )

    def direction_badge(self, obj):
        """Display direction with badge"""
        if obj.direction == 'push':
            return format_html(
                '<span style="background-color: #007bff; color: white; padding: 3px 8px; '
                'border-radius: 3px;">↑ PUSH</span>'
            )
        return format_html(
            '<span style="background-color: #17a2b8; color: white; padding: 3px 8px; '
            'border-radius: 3px;">↓ PULL</span>'
        )
    direction_badge.short_description = 'Direction'

    def status_badge(self, obj):
        """Display status with color badge"""
        colors = {
            'success': '#28a745',
            'partial': '#ffc107',
            'failed': '#dc3545',
            'in_progress': '#17a2b8',
            'pending': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.status.upper()
        )
    status_badge.short_description = 'Status'

    def duration(self, obj):
        """Calculate and display sync duration"""
        if obj.completed_at and obj.started_at:
            delta = obj.completed_at - obj.started_at
            seconds = delta.total_seconds()
            if seconds < 60:
                return f"{seconds:.1f}s"
            elif seconds < 3600:
                return f"{seconds / 60:.1f}m"
            else:
                return f"{seconds / 3600:.1f}h"
        elif obj.status == 'in_progress':
            delta = timezone.now() - obj.started_at
            return f"{delta.total_seconds():.1f}s (ongoing)"
        return "N/A"
    duration.short_description = 'Duration'

    def records_summary(self, obj):
        """Display records pushed/pulled summary"""
        return f"↑{obj.records_pushed} ↓{obj.records_pulled}"
    records_summary.short_description = 'Records'

    def has_add_permission(self, request):
        """Disable manual creation of sync logs (auto-generated only)"""
        return False

    def has_change_permission(self, request, obj=None):
        """Make logs read-only"""
        return False


@admin.register(SyncConflict)
class SyncConflictAdmin(admin.ModelAdmin):
    """Admin interface for SyncConflict model"""

    list_display = [
        'id', 'conflict_type_badge', 'model_name', 'object_id',
        'instance', 'resolution_status', 'detected_at', 'manual_required'
    ]
    list_filter = [
        'conflict_type', 'resolved', 'requires_manual_resolution',
        'resolution_strategy', 'detected_at'
    ]
    search_fields = ['model_name', 'object_id', 'notes']
    readonly_fields = [
        'id', 'conflict_type', 'model_name', 'object_id',
        'local_version', 'cloud_version', 'detected_at', 'instance'
    ]
    date_hierarchy = 'detected_at'
    ordering = ['-detected_at']

    fieldsets = (
        ('Conflict Information', {
            'fields': ('id', 'conflict_type', 'model_name', 'object_id', 'instance', 'detected_at')
        }),
        ('Conflicting Versions', {
            'fields': ('local_version', 'cloud_version'),
            'classes': ('collapse',)
        }),
        ('Resolution', {
            'fields': (
                'resolved', 'resolution_strategy', 'resolved_at',
                'resolved_by', 'requires_manual_resolution', 'notes'
            )
        }),
    )

    actions = ['resolve_cloud_wins', 'resolve_local_wins', 'mark_manual_required']

    def conflict_type_badge(self, obj):
        """Display conflict type with badge"""
        colors = {
            'update_update': '#ffc107',
            'delete_update': '#fd7e14',
            'create_create': '#20c997',
            'payment': '#dc3545',
            'other': '#6c757d',
        }
        color = colors.get(obj.conflict_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_conflict_type_display()
        )
    conflict_type_badge.short_description = 'Type'

    def resolution_status(self, obj):
        """Display resolution status with badge"""
        if obj.resolved:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px;">✓ Resolved ({})</span>',
                obj.resolution_strategy
            )
        elif obj.requires_manual_resolution:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 8px; '
                'border-radius: 3px;">⚠ Manual Required</span>'
            )
        return format_html(
            '<span style="background-color: #ffc107; color: black; padding: 3px 8px; '
            'border-radius: 3px;">⏳ Pending</span>'
        )
    resolution_status.short_description = 'Resolution'

    def manual_required(self, obj):
        """Display manual resolution requirement"""
        if obj.requires_manual_resolution:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">YES</span>'
            )
        return format_html(
            '<span style="color: #28a745;">No</span>'
        )
    manual_required.short_description = 'Manual?'

    def resolve_cloud_wins(self, request, queryset):
        """Bulk resolve conflicts with cloud version winning"""
        count = queryset.filter(resolved=False).update(
            resolved=True,
            resolution_strategy='cloud_wins',
            resolved_at=timezone.now(),
            resolved_by=request.user.participant if hasattr(request.user, 'participant') else None
        )
        self.message_user(request, f'{count} conflict(s) resolved (cloud wins).')
    resolve_cloud_wins.short_description = 'Resolve: Cloud Wins'

    def resolve_local_wins(self, request, queryset):
        """Bulk resolve conflicts with local version winning"""
        count = queryset.filter(resolved=False).update(
            resolved=True,
            resolution_strategy='local_wins',
            resolved_at=timezone.now(),
            resolved_by=request.user.participant if hasattr(request.user, 'participant') else None
        )
        self.message_user(request, f'{count} conflict(s) resolved (local wins).')
    resolve_local_wins.short_description = 'Resolve: Local Wins'

    def mark_manual_required(self, request, queryset):
        """Mark conflicts as requiring manual resolution"""
        count = queryset.filter(resolved=False).update(
            requires_manual_resolution=True
        )
        self.message_user(request, f'{count} conflict(s) marked for manual resolution.')
    mark_manual_required.short_description = 'Mark as Manual Required'
