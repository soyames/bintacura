import qrcode
from io import BytesIO
from django.core.files import File
from .models import QRCode
import json

class QRCodeService:
    @staticmethod
    def generate_qr_code(content_type, object_id, data_dict):
        qr_data = json.dumps(data_dict)
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        qr_code_obj, created = QRCode.objects.update_or_create(
            content_type=content_type,
            object_id=object_id,
            defaults={'qr_code_data': qr_data, 'is_active': True}
        )
        qr_code_obj.qr_code_image.save(f'{content_type}_{object_id}.png', File(buffer), save=True)
        return qr_code_obj
    
    @staticmethod
    def get_qr_code(content_type, object_id):
        try:
            return QRCode.objects.get(content_type=content_type, object_id=object_id, is_active=True)
        except QRCode.DoesNotExist:
            return None
    
    @staticmethod
    def deactivate_qr_code(content_type, object_id):
        QRCode.objects.filter(content_type=content_type, object_id=object_id).update(is_active=False)
