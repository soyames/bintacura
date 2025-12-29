import qrcode
import json
import base64
from io import BytesIO
from django.conf import settings
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)


class QRCodeService:
    """Service for generating and managing QR codes for invoices"""
    
    @staticmethod
    def generate_invoice_qr_data(receipt):
        """Generate data for QR code"""
        qr_data = {
            'invoice_number': receipt.invoice_number or receipt.receipt_number,
            'receipt_id': str(receipt.id),
            'amount': str(receipt.total_amount),
            'currency': receipt.currency,
            'patient_id': str(receipt.issued_to.pk),
            'patient_name': receipt.issued_to.full_name or receipt.issued_to.email,
            'payment_status': receipt.payment_status,
            'issued_at': receipt.issued_at.isoformat() if receipt.issued_at else None,
            'verification_url': f"{settings.FRONTEND_URL}/verify-invoice/{receipt.id}"
        }
        
        if receipt.service_transaction:
            qr_data['service_provider_id'] = str(receipt.service_transaction.service_provider.pk)
            qr_data['service_provider_name'] = receipt.service_transaction.service_provider.full_name or receipt.service_transaction.service_provider.email
            qr_data['service_type'] = receipt.service_transaction.service_type
            qr_data['payment_method'] = receipt.service_transaction.payment_method
        
        return json.dumps(qr_data)
    
    @staticmethod
    def generate_qr_code_image(data, size=10, border=4):
        """Generate QR code image and return as base64 - Deprecated: Use QRCodeService from qrcode_generator app"""
        from qrcode_generator.services import QRCodeService
        return QRCodeService.generate_qr_code(data)
        
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{img_base64}"
    
    @staticmethod
    def generate_invoice_qr_code(receipt):
        """Generate complete QR code for invoice"""
        try:
            qr_data = QRCodeService.generate_invoice_qr_data(receipt)
            qr_image_base64 = QRCodeService.generate_qr_code_image(qr_data)
            
            receipt.qr_code = qr_image_base64
            receipt.save(update_fields=['qr_code'])
            
            logger.info(f"QR code generated for invoice {receipt.invoice_number}")
            return qr_image_base64
            
        except Exception as e:
            logger.error(f"Failed to generate QR code for invoice {receipt.invoice_number}: {e}")
            return None
    
    @staticmethod
    def verify_qr_data(qr_data_string):
        """Verify QR code data and return invoice information"""
        try:
            qr_data = json.loads(qr_data_string)
            
            from payments.models import PaymentReceipt
            receipt_id = qr_data.get('receipt_id')
            
            if not receipt_id:
                return {'valid': False, 'error': 'Invalid QR code data'}
            
            receipt = PaymentReceipt.objects.filter(id=receipt_id).first()
            
            if not receipt:
                return {'valid': False, 'error': 'Invoice not found'}
            
            return {
                'valid': True,
                'receipt': receipt,
                'invoice_number': receipt.invoice_number or receipt.receipt_number,
                'amount': receipt.total_amount,
                'currency': receipt.currency,
                'status': receipt.payment_status,
                'patient_name': receipt.issued_to.get_full_name(),
                'issued_at': receipt.issued_at,
            }
            
        except json.JSONDecodeError:
            return {'valid': False, 'error': 'Invalid QR code format'}
        except Exception as e:
            logger.error(f"Error verifying QR code: {e}")
            return {'valid': False, 'error': 'Verification failed'}
