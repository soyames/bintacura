from django.db import models
from core.sync_mixin import SyncMixin
import uuid

class QRCode(SyncMixin):
    content_type = models.CharField(max_length=100)
    object_id = models.UUIDField()
    qr_code_image = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    qr_code_data = models.TextField()
    is_active = models.BooleanField(default=True)
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    
    class Meta:
        db_table = 'qrcode_generator_qrcodes'
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"QR Code for {self.content_type} - {self.object_id}"
