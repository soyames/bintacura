from django.contrib import admin
from .models import QRCode

@admin.register(QRCode)
class QRCodeAdmin(admin.ModelAdmin):
    list_display = ['id', 'content_type', 'object_id', 'created_at', 'is_active']
    list_filter = ['content_type', 'is_active', 'created_at']
    search_fields = ['content_type', 'object_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
