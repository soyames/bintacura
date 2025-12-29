from celery import shared_task
from django.utils import timezone
from .models import InsuranceInvoice, InsuranceSubscription


@shared_task
def process_pending_invoices():  # Process pending invoices
    from datetime import date
    today = date.today()
    
    overdue_invoices = InsuranceInvoice.objects.filter(
        due_date__lt=today,
        status="pending"
    )
    overdue_invoices.update(status="overdue")
    
    return f"Marked {overdue_invoices.count()} invoices as overdue"


@shared_task
def generate_monthly_invoices():  # Generate monthly invoices
    from datetime import date
    today = date.today()
    
    subscriptions = InsuranceSubscription.objects.filter(
        status="active",
        next_payment_date=today
    )
    
    invoice_count = 0
    for subscription in subscriptions:
        invoice_number = f"INV-{subscription.id}-{today.strftime('%Y%m%d')}"
        InsuranceInvoice.objects.create(
            invoice_number=invoice_number,
            subscription=subscription,
            patient=subscription.patient,
            insurance_package=subscription.insurance_package,
            amount=subscription.premium_amount,
            issue_date=today,
            due_date=today,
            period_start=today,
            period_end=today,
        )
        invoice_count += 1
    
    return f"Generated {invoice_count} invoices"
