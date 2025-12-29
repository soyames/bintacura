from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from payments.models import PaymentReceipt
from communication.models import Notification


class Command(BaseCommand):
    help = 'Send payment reminders for unpaid invoices after 24 hours'

    def handle(self, *args, **options):
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        unpaid_receipts = PaymentReceipt.objects.filter(
            payment_status='PENDING',
            issued_at__lte=cutoff_time,
            reminder_sent=False
        ).select_related('issued_to', 'issued_by', 'service_transaction')
        
        reminder_count = 0
        
        for receipt in unpaid_receipts:
            try:
                patient = receipt.issued_to
                invoice_number = receipt.invoice_number or receipt.receipt_number
                
                Notification.objects.create(
                    recipient=patient,
                    title="Rappel de paiement",
                    message=f"Votre facture {invoice_number} d'un montant de {receipt.total_amount} {receipt.currency} est toujours impayée. Veuillez effectuer le paiement dès que possible.",
                    notification_type='payment',
                    priority='high'
                )
                
                if patient.email:
                    send_mail(
                        subject=f'Rappel de paiement - Facture {invoice_number}',
                        message=f'''Bonjour {patient.get_full_name()},

Nous vous rappelons que votre facture {invoice_number} d'un montant de {receipt.total_amount} {receipt.currency} est toujours impayée.

Détails de la facture:
- Numéro: {invoice_number}
- Montant: {receipt.total_amount} {receipt.currency}
- Date d'émission: {receipt.issued_at.strftime('%d/%m/%Y')}
- Service: {receipt.service_transaction.service_type if receipt.service_transaction else 'N/A'}

Veuillez effectuer le paiement dès que possible pour éviter toute interruption de service.

Cordialement,
L'équipe BINTACURA
''',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[patient.email],
                        fail_silently=True,
                    )
                
                receipt.reminder_sent = True
                receipt.save(update_fields=['reminder_sent'])
                
                reminder_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error sending reminder for receipt {receipt.id}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully sent {reminder_count} payment reminders')
        )

