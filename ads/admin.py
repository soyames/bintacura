from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Advertisement


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):  # Admin interface configuration for Advertisement model
    list_display = [
        'title',
        'media_preview',
        'status_badge',
        'display_order',
        'date_range',
        'analytics',
        'created_at'
    ]
    list_filter = ['status', 'media_type', 'created_at', 'start_date']
    search_fields = ['title', 'heading', 'subheading', 'button_text']
    readonly_fields = [
        'view_count',
        'click_count',
        'click_through_rate',
        'created_at',
        'updated_at',
        'media_preview_large'
    ]

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'status')
        }),
        ('Media', {
            'fields': ('media_type', 'image', 'video', 'media_preview_large')
        }),
        ('Content', {
            'fields': ('heading', 'subheading')
        }),
        ('Call to Action', {
            'fields': ('button_text', 'button_link', 'button_opens_new_tab')
        }),
        ('Scheduling', {
            'fields': ('start_date', 'end_date', 'display_order')
        }),
        ('Analytics', {
            'fields': ('view_count', 'click_count', 'click_through_rate'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):  # Set created_by user when saving new advertisement
        if not change:  # If creating new ad
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def media_preview(self, obj):
        """Small preview of media in list view"""
        if obj.media_type == 'image' and obj.image:
            return format_html(
                '<img src="{}" style="width: 60px; height: 40px; object-fit: cover; border-radius: 4px;" />',
                obj.image.url
            )
        elif obj.media_type == 'video' and obj.video:
            return format_html(
                '<span style="color: #007bff;">🎥 Video</span>'
            )
        return format_html('<span style="color: #999;">No media</span>')
    media_preview.short_description = 'Preview'

    def media_preview_large(self, obj):
        """Large preview of media in detail view"""
        if obj.media_type == 'image' and obj.image:
            return format_html(
                '<img src="{}" style="max-width: 500px; max-height: 300px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />',
                obj.image.url
            )
        elif obj.media_type == 'video' and obj.video:
            return format_html(
                '<video controls style="max-width: 500px; max-height: 300px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">'
                '<source src="{}" type="video/mp4">'
                'Your browser does not support the video tag.'
                '</video>',
                obj.video.url
            )
        return format_html('<span style="color: #999;">No media uploaded</span>')
    media_preview_large.short_description = 'Media Preview'

    def status_badge(self, obj):
        """Colored status badge"""
        colors = {
            'draft': '#6c757d',
            'active': '#28a745',
            'inactive': '#ffc107',
            'expired': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        is_active = obj.is_active()

        if obj.status == 'active' and not is_active:
            color = '#ffc107'
            status_text = 'Scheduled'
        else:
            status_text = obj.get_status_display()

        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase;">{}</span>',
            color,
            status_text
        )
    status_badge.short_description = 'Status'

    def date_range(self, obj):
        """Display date range"""
        start = obj.start_date.strftime('%Y-%m-%d %H:%M') if obj.start_date else 'Not set'
        end = obj.end_date.strftime('%Y-%m-%d %H:%M') if obj.end_date else 'No end'

        now = timezone.now()
        if obj.start_date and now < obj.start_date:
            status = '<br><small style="color: #ffc107;">⏰ Scheduled</small>'
        elif obj.end_date and now > obj.end_date:
            status = '<br><small style="color: #dc3545;">⏰ Expired</small>'
        elif obj.status == 'active':
            status = '<br><small style="color: #28a745;">✓ Running</small>'
        else:
            status = ''

        return format_html(
            '<strong>Start:</strong> {}<br><strong>End:</strong> {}{}',
            start,
            end,
            status
        )
    date_range.short_description = 'Schedule'

    def analytics(self, obj):
        """Display analytics"""
        ctr = obj.click_through_rate
        return format_html(
            '<strong>Views:</strong> {}<br>'
            '<strong>Clicks:</strong> {}<br>'
            '<strong>CTR:</strong> <span style="color: {};">{:.2f}%</span>',
            obj.view_count,
            obj.click_count,
            '#28a745' if ctr > 5 else '#ffc107' if ctr > 2 else '#dc3545',
            ctr
        )
    analytics.short_description = 'Performance'

    actions = ['activate_ads', 'deactivate_ads', 'mark_as_expired']

    def activate_ads(self, request, queryset):  # Bulk action to activate selected advertisements
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} ad(s) activated successfully.')
    activate_ads.short_description = 'Activate selected ads'

    def deactivate_ads(self, request, queryset):  # Bulk action to deactivate selected advertisements
        updated = queryset.update(status='inactive')
        self.message_user(request, f'{updated} ad(s) deactivated successfully.')
    deactivate_ads.short_description = 'Deactivate selected ads'

    def mark_as_expired(self, request, queryset):  # Bulk action to mark selected advertisements as expired
        updated = queryset.update(status='expired')
        self.message_user(request, f'{updated} ad(s) marked as expired.')
    mark_as_expired.short_description = 'Mark as expired'
