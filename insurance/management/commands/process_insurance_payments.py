"""
Management command to process recurring insurance premium payments
Run this daily via cron/scheduler: python manage.py process_insurance_payments
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import uuid

from insurance.models import InsuranceSubscription, InsuranceInvoice
from core.services import WalletService


class Command(BaseCommand):  # Command class implementation
    help = "Process recurring insurance premium payments for active subscriptions"

    def add_arguments(self, parser):  # Add arguments
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run without actually processing payments",
        )
        parser.add_argument(
            "--days-ahead",
            type=int,
            default=0,
            help="Process payments due in the next N days (default: 0 = today only)",
        )

    def calculate_next_payment_date(self, current_date, frequency):
        """Calculate next payment date based on frequency"""
        if frequency == "monthly":
            return current_date + relativedelta(months=1)
        elif frequency == "quarterly":
            return current_date + relativedelta(months=3)
        elif frequency == "semi_annual":
            return current_date + relativedelta(months=6)
        elif frequency == "annual":
            return current_date + relativedelta(years=1)
        return current_date + relativedelta(months=1)

    def handle(self, *args, **options):  # Handle
        dry_run = options["dry_run"]
        days_ahead = options["days_ahead"]

        today = timezone.now().date()
        cutoff_date = today + timedelta(days=days_ahead)

        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write(f"Processing Insurance Premium Payments")
        self.stdout.write(f"Date: {today}")
        self.stdout.write(f"Processing payments due on or before: {cutoff_date}")
        self.stdout.write(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        self.stdout.write(f"{'=' * 60}\n")

        # Get all active subscriptions with payments due
        subscriptions = InsuranceSubscription.objects.filter(
            status="active", auto_renew=True, next_payment_date__lte=cutoff_date
        ).select_related("patient", "insurance_package__company")

        total = subscriptions.count()
        self.stdout.write(f"Found {total} subscription(s) due for payment\n")

        if total == 0:
            self.stdout.write(self.style.SUCCESS("No payments to process"))
            return

        processed = 0
        failed = 0
        skipped = 0

        for subscription in subscriptions:
            patient_name = subscription.patient.full_name
            package_name = subscription.insurance_package.name
            amount = subscription.premium_amount

            self.stdout.write(
                f"\nProcessing: {patient_name} - {package_name} ({amount} CFA)"
            )

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f"  [DRY RUN] Would charge {amount} CFA")
                )
                processed += 1
                continue

            try:
                with transaction.atomic():
                    # Process payment
                    payment_result = WalletService.make_payment(
                        patient=subscription.patient,
                        recipient=subscription.insurance_package.company,
                        amount=amount,
                        description=f"Insurance Premium - {package_name} ({subscription.get_payment_frequency_display()})",
                        payment_method=subscription.payment_method,
                        metadata={
                            "subscription_id": str(subscription.id),
                            "insurance_package_id": str(
                                subscription.insurance_package.id
                            ),
                            "insurance_package_name": package_name,
                            "payment_frequency": subscription.payment_frequency,
                            "type": "insurance_premium_recurring",
                        },
                    )

                    transaction_ref = payment_result[
                        "patient_transaction"
                    ].transaction_ref

                    # Calculate period dates
                    period_start = subscription.next_payment_date
                    period_end = self.calculate_next_payment_date(
                        period_start, subscription.payment_frequency
                    ) - timedelta(days=1)

                    # Create invoice
                    invoice = InsuranceInvoice.objects.create(
                        invoice_number=f"INV-{uuid.uuid4().hex[:10].upper()}",
                        subscription=subscription,
                        patient=subscription.patient,
                        insurance_package=subscription.insurance_package,
                        amount=amount,
                        status="paid",
                        issue_date=today,
                        due_date=subscription.next_payment_date,
                        paid_date=today,
                        transaction_ref=str(transaction_ref),
                        payment_method=subscription.payment_method,
                        period_start=period_start,
                        period_end=period_end,
                    )

                    # Update subscription
                    subscription.last_payment_date = today
                    subscription.next_payment_date = self.calculate_next_payment_date(
                        subscription.next_payment_date, subscription.payment_frequency
                    )
                    subscription.total_paid += amount
                    subscription.payment_count += 1
                    subscription.save()

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ Payment processed - Invoice: {invoice.invoice_number}, "
                            f"Next payment: {subscription.next_payment_date}"
                        )
                    )
                    processed += 1

            except ValueError as e:
                # Insufficient balance or validation error
                self.stdout.write(self.style.ERROR(f"  ✗ Payment failed: {str(e)}"))

                # Create overdue invoice
                invoice = InsuranceInvoice.objects.create(
                    invoice_number=f"INV-{uuid.uuid4().hex[:10].upper()}",
                    subscription=subscription,
                    patient=subscription.patient,
                    insurance_package=subscription.insurance_package,
                    amount=amount,
                    status="overdue",
                    issue_date=today,
                    due_date=subscription.next_payment_date,
                    period_start=subscription.next_payment_date,
                    period_end=self.calculate_next_payment_date(
                        subscription.next_payment_date, subscription.payment_frequency
                    )
                    - timedelta(days=1),
                    notes=f"Payment failed: {str(e)}",
                )

                # Suspend subscription if payment is more than 7 days overdue
                days_overdue = (today - subscription.next_payment_date).days
                if days_overdue > 7:
                    subscription.status = "suspended"
                    subscription.save()
                    if subscription.insurance_card:
                        subscription.insurance_card.status = "suspended"
                        subscription.insurance_card.save()
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ! Subscription suspended due to {days_overdue} days overdue"
                        )
                    )

                failed += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Unexpected error: {str(e)}"))
                failed += 1

        # Summary
        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write("SUMMARY")
        self.stdout.write(f"{'=' * 60}")
        self.stdout.write(f"Total subscriptions: {total}")
        self.stdout.write(self.style.SUCCESS(f"Successfully processed: {processed}"))
        if failed > 0:
            self.stdout.write(self.style.ERROR(f"Failed: {failed}"))
        if skipped > 0:
            self.stdout.write(self.style.WARNING(f"Skipped: {skipped}"))
        self.stdout.write(f"{'=' * 60}\n")

        if not dry_run and processed > 0:
            self.stdout.write(
                self.style.SUCCESS(f"✓ Processed {processed} payment(s) successfully")
            )
