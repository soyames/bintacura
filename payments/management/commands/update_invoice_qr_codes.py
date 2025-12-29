from django.core.management.base import BaseCommand
from django.db import transaction
from payments.models import PaymentReceipt
from payments.invoice_number_service import InvoiceNumberService
from payments.qr_service import QRCodeService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update all invoices to ensure they have invoice numbers and QR codes'

    def handle(self, *args, **options):
        self.stdout.write('Starting invoice update process...')
        
        receipts_without_invoice = PaymentReceipt.objects.filter(
            invoice_number__isnull=True
        ) | PaymentReceipt.objects.filter(invoice_number='')
        
        receipts_without_qr = PaymentReceipt.objects.filter(
            qr_code__isnull=True
        ) | PaymentReceipt.objects.filter(qr_code='')
        
        total_updated = 0
        
        with transaction.atomic():
            for receipt in receipts_without_invoice:
                try:
                    service_provider_role = 'doctor'
                    
                    if receipt.service_transaction:
                        service_provider_role = receipt.service_transaction.service_provider_role
                    elif receipt.transaction and receipt.transaction.recipient:
                        service_provider_role = receipt.transaction.recipient.role
                    
                    invoice_data = InvoiceNumberService.generate_invoice_number(
                        service_provider_role=service_provider_role
                    )
                    
                    receipt.invoice_number = invoice_data['invoice_number']
                    receipt.invoice_sequence = invoice_data['sequence']
                    receipt.save(update_fields=['invoice_number', 'invoice_sequence'])
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Updated invoice number for receipt {receipt.receipt_number}')
                    )
                    total_updated += 1
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Failed to update invoice for receipt {receipt.receipt_number}: {e}')
                    )
            
            for receipt in receipts_without_qr:
                try:
                    QRCodeService.generate_invoice_qr_code(receipt)
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Generated QR code for receipt {receipt.receipt_number}')
                    )
                    total_updated += 1
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Failed to generate QR code for receipt {receipt.receipt_number}: {e}')
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✓ Successfully updated {total_updated} invoices')
        )
