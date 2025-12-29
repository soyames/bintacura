from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from decimal import Decimal
import logging
from .models import PaymentReceipt
from communication.services import EmailService, NotificationService

logger = logging.getLogger(__name__)


class InvoiceReminderService:
    """Service for sending payment reminders for unpaid invoices"""
    
    @staticmethod
    def send_payment_reminders():
        """Send reminders for invoices unpaid after 24 hours"""
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        unpaid_receipts = PaymentReceipt.objects.filter(
            payment_status='PENDING',
            issued_at__lte=cutoff_time,
            reminded_at__isnull=True
        ).select_related('issued_to', 'issued_by', 'transaction', 'service_transaction')
        
        reminder_count = 0
        
        for receipt in unpaid_receipts:
            try:
                InvoiceReminderService._send_single_reminder(receipt)
                receipt.reminded_at = timezone.now()
                receipt.save(update_fields=['reminded_at'])
                reminder_count += 1
            except Exception as e:
                logger.error(f"Failed to send reminder for invoice {receipt.invoice_number}: {str(e)}")
        
        logger.info(f"Sent {reminder_count} payment reminders")
        return reminder_count
    
    @staticmethod
    def _send_single_reminder(receipt: PaymentReceipt):
        """Send reminder for a single invoice"""
        patient = receipt.issued_to
        provider = receipt.issued_by
        
        amount = receipt.total_amount
        currency = receipt.currency
        invoice_number = receipt.invoice_number or receipt.receipt_number
        
        invoice_url = f"https://BINTACURA.bj/patient/view-invoice/?transaction_id={receipt.transaction.id if receipt.transaction else receipt.service_transaction.id}"
        
        email_subject = f"Rappel de paiement - Facture {invoice_number}"
        email_body = f"""
        <h2>Rappel de Paiement</h2>
        <p>Bonjour {patient.full_name},</p>
        
        <p>Nous vous rappelons que votre facture <strong>{invoice_number}</strong> est toujours impayée.</p>
        
        <h3>Détails de la facture:</h3>
        <ul>
            <li><strong>Numéro:</strong> {invoice_number}</li>
            <li><strong>Montant:</strong> {amount} {currency}</li>
            <li><strong>Fournisseur:</strong> {provider.full_name}</li>
            <li><strong>Date d'émission:</strong> {receipt.issued_at.strftime('%d/%m/%Y')}</li>
        </ul>
        
        <p>
            <a href="{invoice_url}" style="display: inline-block; padding: 10px 20px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px;">
                Voir la facture et payer
            </a>
        </p>
        
        <p>Merci de procéder au paiement dans les plus brefs délais.</p>
        
        <p>Cordialement,<br>L'équipe BINTACURA</p>
        """
        
        EmailService.send_email(
            recipient_email=patient.email,
            subject=email_subject,
            html_content=email_body
        )
        
        NotificationService.create_notification(
            participant=patient,
            title="Rappel de paiement",
            message=f"Votre facture {invoice_number} d'un montant de {amount} {currency} est impayée. Veuillez procéder au paiement.",
            notification_type='payment_reminder',
            link=f"/patient/view-invoice/?transaction_id={receipt.transaction.id if receipt.transaction else receipt.service_transaction.id}"
        )
        
        logger.info(f"Sent payment reminder for invoice {invoice_number} to {patient.email}")

