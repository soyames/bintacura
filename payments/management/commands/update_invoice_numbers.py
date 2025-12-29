from django.core.management.base import BaseCommand
from django.db import transaction
from payments.models import PaymentReceipt
from payments.invoice_number_service import InvoiceNumberService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update existing receipts with human-readable invoice numbers'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting invoice number update...')
        
        with transaction.atomic():
            receipts = PaymentReceipt.objects.filter(
                invoice_number__isnull=True
            ).order_by('issued_at')
            
            total = receipts.count()
            self.stdout.write(f'Found {total} receipts without human-readable invoice numbers')
            
            updated = 0
            for receipt in receipts:
                provider_role = None
                if receipt.issued_by:
                    provider_role = receipt.issued_by.role
                
                invoice_number, sequence = InvoiceNumberService.generate_invoice_number(provider_role)
                receipt.invoice_number = invoice_number
                receipt.invoice_sequence = sequence
                receipt.save(update_fields=['invoice_number', 'invoice_sequence'])
                
                updated += 1
                if updated % 100 == 0:
                    self.stdout.write(f'Updated {updated}/{total} receipts...')
            
            self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated} receipts'))
