from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class InvoiceNumberService:
    """Centralized service for generating sequential invoice numbers across all payment types"""
    
    @staticmethod
    @transaction.atomic
    def generate_invoice_number(service_provider_role=None):
        """
        Generate a centralized sequential invoice number with role prefix
        Format: #D001, #H002, #P003, #I004, etc.
        
        Prefix based on service provider role:
        - D = Doctor
        - H = Hospital
        - P = Pharmacy
        - I = Insurance Company
        
        Number increments globally across all transactions (001, 002, 003...)
        
        Examples:
        - First transaction (patient→doctor): #D001
        - Second transaction (patient→pharmacy): #P002
        - Third transaction (patient→doctor): #D003
        - Fourth transaction (patient→hospital): #H004
        
        Args:
            service_provider_role (str): Role of service provider (doctor, hospital, pharmacy, insurance_company)
        
        Returns:
            tuple: (invoice_number, sequence_number) e.g., ("#D001", 1)
        """
        from .models import PaymentReceipt
        
        role_prefix_map = {
            'doctor': 'D',
            'hospital': 'H',
            'pharmacy': 'P',
            'insurance_company': 'I',
        }
        
        prefix = role_prefix_map.get(service_provider_role, 'T')
        
        last_receipt = PaymentReceipt.objects.filter(
            invoice_sequence__isnull=False
        ).order_by('-invoice_sequence').select_for_update().first()
        
        if last_receipt and last_receipt.invoice_sequence:
            next_number = last_receipt.invoice_sequence + 1
        else:
            next_number = 1
        
        invoice_number = f"#{prefix}{next_number:03d}"
        
        logger.info(f"Generated invoice number: {invoice_number} (seq: {next_number}) for role: {service_provider_role}")
        
        return invoice_number, next_number
    
    @staticmethod
    @transaction.atomic
    def generate_receipt_number():
        """
        Generate a receipt reference number (for internal background tracking)
        Format: INV-YYYYMM-NNNNNN
        Example: INV-202412-000001
        
        This is for backend tracking and auditing, not shown to users
        
        Returns:
            str: The generated receipt number
        """
        from .models import PaymentReceipt
        
        now = timezone.now()
        year_month = now.strftime('%Y%m')
        prefix = f"INV-{year_month}-"
        
        last_receipt = PaymentReceipt.objects.filter(
            receipt_number__startswith=prefix
        ).order_by('-receipt_number').select_for_update().first()
        
        if last_receipt and last_receipt.receipt_number:
            try:
                last_number = int(last_receipt.receipt_number.split('-')[-1])
                next_number = last_number + 1
            except (ValueError, IndexError):
                next_number = 1
        else:
            next_number = 1
        
        receipt_number = f"{prefix}{next_number:06d}"
        
        logger.info(f"Generated receipt tracking number: {receipt_number}")
        
        return receipt_number
    
    @staticmethod
    def get_current_invoice_count():
        """Get the total count of invoices issued"""
        from .models import PaymentReceipt
        return PaymentReceipt.objects.filter(invoice_number__isnull=False).count()
    
    @staticmethod
    def get_monthly_invoice_count(year=None, month=None):
        """Get invoice count for a specific month based on receipt_number (background tracking)"""
        from .models import PaymentReceipt
        
        if not year or not month:
            now = timezone.now()
            year = now.year
            month = now.month
        
        year_month = f"{year:04d}{month:02d}"
        prefix = f"INV-{year_month}-"
        
        return PaymentReceipt.objects.filter(
            receipt_number__startswith=prefix
        ).count()
    
    @staticmethod
    def validate_invoice_number(invoice_number):
        """
        Validate invoice number format (#D001, #H002, etc.)
        
        Args:
            invoice_number (str): Invoice number to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not invoice_number:
            return False
        
        import re
        pattern = r'^#[DHPIT]\d{3,}$'
        return bool(re.match(pattern, invoice_number))
