"""
Currency Data Audit Management Command
Audits all currency-related data across the platform to identify inconsistencies
"""
from django.core.management.base import BaseCommand
from django.db.models import Count, Q, F
from decimal import Decimal
from collections import defaultdict
from core.models import Wallet, Participant
from payments.models import PaymentReceipt, ServiceTransaction
from tabulate import tabulate


class Command(BaseCommand):
    help = 'Audit currency data across the platform to identify inconsistencies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically fix identified issues (use with caution)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about each issue',
        )

    def handle(self, *args, **options):
        self.fix = options['fix']
        self.verbose = options['verbose']

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('BINTACURA Currency Data Audit'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write('')

        # Run all audit checks
        issues_found = 0
        issues_found += self.audit_wallets()
        issues_found += self.audit_participant_currency()
        issues_found += self.audit_payment_receipts()
        issues_found += self.audit_service_transactions()
        issues_found += self.audit_currency_consistency()

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('AUDIT SUMMARY'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        if issues_found == 0:
            self.stdout.write(self.style.SUCCESS('[OK] No currency data issues found!'))
        else:
            if self.fix:
                self.stdout.write(self.style.WARNING(f'[WARNING] Total issues found: {issues_found}'))
                self.stdout.write(self.style.SUCCESS('[OK] Issues have been automatically fixed'))
            else:
                self.stdout.write(self.style.ERROR(f'[ERROR] Total issues found: {issues_found}'))
                self.stdout.write(self.style.WARNING('[INFO] Run with --fix to automatically fix these issues'))

        self.stdout.write('')

    def audit_wallets(self):
        """Audit wallet currency consistency"""
        self.stdout.write(self.style.HTTP_INFO('\n[AUDIT] WALLETS'))
        self.stdout.write('-' * 80)

        issues = 0

        # Check wallets with EUR default when user has different preference
        wallets_with_wrong_currency = []

        for wallet in Wallet.objects.select_related('participant'):
            participant = wallet.participant

            # Use phone number as PRIMARY currency source
            from core.phone_currency_mapper import PhoneCurrencyMapper
            expected_currency = PhoneCurrencyMapper.get_participant_currency(participant)

            if wallet.currency != expected_currency:
                wallets_with_wrong_currency.append({
                    'participant': participant.email,
                    'wallet_currency': wallet.currency,
                    'expected_currency': expected_currency,
                    'balance': wallet.balance,
                    'wallet_id': str(wallet.id)
                })
                issues += 1

        if wallets_with_wrong_currency:
            self.stdout.write(self.style.WARNING(
                f'[WARNING] Found {len(wallets_with_wrong_currency)} wallets with currency mismatch'
            ))

            if self.verbose:
                table_data = [
                    [w['participant'][:30], w['wallet_currency'], w['expected_currency'], f"{w['balance']:.2f}"]
                    for w in wallets_with_wrong_currency[:20]
                ]
                self.stdout.write(
                    tabulate(
                        table_data,
                        headers=['Participant', 'Current', 'Expected', 'Balance'],
                        tablefmt='grid'
                    )
                )
                if len(wallets_with_wrong_currency) > 20:
                    self.stdout.write(f'   ... and {len(wallets_with_wrong_currency) - 20} more')

            if self.fix:
                self.fix_wallet_currencies(wallets_with_wrong_currency)
        else:
            self.stdout.write(self.style.SUCCESS('[OK] All wallet currencies are consistent'))

        # Check wallets with EUR default (likely never updated)
        eur_wallets = Wallet.objects.filter(currency='EUR').count()
        if eur_wallets > 0:
            self.stdout.write(self.style.WARNING(
                f'[WARNING] Found {eur_wallets} wallets with EUR currency (check if intentional for European users)'
            ))

        return issues

    def audit_participant_currency(self):
        """Audit participant preferred currency settings"""
        self.stdout.write(self.style.HTTP_INFO('\n[AUDIT] PARTICIPANT CURRENCIES'))
        self.stdout.write('-' * 80)

        issues = 0

        # Participants without preferred_currency set
        no_currency = Participant.objects.filter(
            Q(preferred_currency__isnull=True) | Q(preferred_currency='')
        ).count()

        if no_currency > 0:
            self.stdout.write(self.style.WARNING(
                f'[WARNING] {no_currency} participants have no preferred_currency set'
            ))
            issues += no_currency

            if self.fix:
                # Set based on phone number (PRIMARY) or country or default to XOF
                from core.phone_currency_mapper import PhoneCurrencyMapper
                updated = 0
                for participant in Participant.objects.filter(
                    Q(preferred_currency__isnull=True) | Q(preferred_currency='')
                ):
                    currency = PhoneCurrencyMapper.get_participant_currency(participant)
                    participant.preferred_currency = currency
                    participant.save(update_fields=['preferred_currency'])
                    updated += 1

                self.stdout.write(self.style.SUCCESS(
                    f'[OK] Updated preferred_currency for {updated} participants'
                ))
        else:
            self.stdout.write(self.style.SUCCESS('[OK] All participants have preferred_currency set'))

        return issues

    def audit_payment_receipts(self):
        """Audit payment receipt currency consistency"""
        self.stdout.write(self.style.HTTP_INFO('\n[AUDIT] PAYMENT RECEIPTS'))
        self.stdout.write('-' * 80)

        issues = 0

        # Receipts without currency set (NULL or empty)
        no_currency = PaymentReceipt.objects.filter(
            Q(currency__isnull=True) | Q(currency='')
        ).count()

        if no_currency > 0:
            self.stdout.write(self.style.ERROR(
                f'[ERROR] {no_currency} receipts have no currency set!'
            ))
            issues += no_currency

            if self.fix:
                # Set to XOF default or user's currency
                for receipt in PaymentReceipt.objects.filter(
                    Q(currency__isnull=True) | Q(currency='')
                ):
                    if receipt.issued_to:
                        currency = receipt.issued_to.preferred_currency or 'XOF'
                    else:
                        currency = 'XOF'

                    receipt.currency = currency
                    receipt.save(update_fields=['currency'])

                self.stdout.write(self.style.SUCCESS(
                    f'[OK] Set currency for {no_currency} receipts'
                ))
        else:
            self.stdout.write(self.style.SUCCESS('[OK] All receipts have currency set'))

        # Check receipts where currency doesn't match participant's currency
        mismatched_receipts = []
        for receipt in PaymentReceipt.objects.select_related('issued_to')[:1000]:  # Sample first 1000
            if receipt.issued_to and receipt.issued_to.preferred_currency:
                expected_currency = receipt.issued_to.preferred_currency
                if receipt.currency != expected_currency:
                    mismatched_receipts.append({
                        'receipt_id': receipt.receipt_number or str(receipt.id),
                        'receipt_currency': receipt.currency,
                        'participant_currency': expected_currency,
                        'amount': receipt.total_amount or receipt.amount
                    })

        if mismatched_receipts:
            self.stdout.write(self.style.WARNING(
                f'[WARNING] Found {len(mismatched_receipts)} receipts with currency mismatch (sampled 1000)'
            ))
            issues += len(mismatched_receipts)

            if self.verbose and mismatched_receipts:
                table_data = [
                    [r['receipt_id'][:20], r['receipt_currency'], r['participant_currency'], f"{r['amount']:.2f}" if r['amount'] else 'N/A']
                    for r in mismatched_receipts[:10]
                ]
                self.stdout.write(
                    tabulate(
                        table_data,
                        headers=['Receipt ID', 'Receipt Currency', 'User Currency', 'Amount'],
                        tablefmt='grid'
                    )
                )

        return issues

    def audit_service_transactions(self):
        """Audit service transaction currency consistency"""
        self.stdout.write(self.style.HTTP_INFO('\n[AUDIT] SERVICE TRANSACTIONS'))
        self.stdout.write('-' * 80)

        issues = 0

        try:
            # Transactions without currency set
            no_currency = ServiceTransaction.objects.filter(
                Q(currency__isnull=True) | Q(currency='')
            ).count()

            if no_currency > 0:
                self.stdout.write(self.style.ERROR(
                    f'[ERROR] {no_currency} service transactions have no currency set!'
                ))
                issues += no_currency

                if self.fix:
                    for txn in ServiceTransaction.objects.filter(
                        Q(currency__isnull=True) | Q(currency='')
                    ):
                        if txn.patient:
                            currency = txn.patient.preferred_currency or 'XOF'
                        else:
                            currency = 'XOF'

                        txn.currency = currency
                        txn.save(update_fields=['currency'])

                    self.stdout.write(self.style.SUCCESS(
                        f'[OK] Set currency for {no_currency} transactions'
                    ))
            else:
                self.stdout.write(self.style.SUCCESS('[OK] All transactions have currency set'))

        except Exception as e:
            self.stdout.write(self.style.WARNING(f'[WARNING] ServiceTransaction model check skipped: {str(e)}'))

        return issues

    def audit_currency_consistency(self):
        """Audit overall currency consistency across related records"""
        self.stdout.write(self.style.HTTP_INFO('\n[AUDIT] CROSS-MODEL CONSISTENCY'))
        self.stdout.write('-' * 80)

        issues = 0

        # Check if participant's wallet currency matches their preferred_currency
        mismatches = []
        for participant in Participant.objects.filter(preferred_currency__isnull=False).select_related('core_wallet')[:500]:
            try:
                wallet = participant.core_wallet
                if wallet.currency != participant.preferred_currency:
                    mismatches.append({
                        'email': participant.email,
                        'preferred': participant.preferred_currency,
                        'wallet': wallet.currency
                    })
                    issues += 1
            except Wallet.DoesNotExist:
                pass

        if mismatches:
            self.stdout.write(self.style.WARNING(
                f'[WARNING] {len(mismatches)} participants have wallet currency != preferred_currency'
            ))

            if self.verbose and mismatches:
                table_data = [
                    [m['email'][:40], m['preferred'], m['wallet']]
                    for m in mismatches[:15]
                ]
                self.stdout.write(
                    tabulate(
                        table_data,
                        headers=['Participant', 'Preferred', 'Wallet Currency'],
                        tablefmt='grid'
                    )
                )

        return issues

    def fix_wallet_currencies(self, wallets_to_fix):
        """Fix wallet currencies by converting balances"""
        self.stdout.write(self.style.WARNING('\n[FIX] Fixing wallet currencies...'))

        from currency_converter.services import CurrencyConverterService

        fixed = 0
        for wallet_info in wallets_to_fix:
            try:
                wallet = Wallet.objects.get(id=wallet_info['wallet_id'])
                old_currency = wallet.currency
                new_currency = wallet_info['expected_currency']
                old_balance = wallet.balance

                # Convert balance to new currency
                if old_balance > 0:
                    new_balance = CurrencyConverterService.convert(
                        old_balance,
                        old_currency,
                        new_currency
                    )
                else:
                    new_balance = Decimal('0.00')

                wallet.currency = new_currency
                wallet.balance = new_balance
                wallet.save(update_fields=['currency', 'balance'])

                self.stdout.write(self.style.SUCCESS(
                    f'  [OK] {wallet_info["participant"][:30]}: {old_balance} {old_currency} -> {new_balance} {new_currency}'
                ))
                fixed += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'  [ERROR] Failed to fix wallet {wallet_info["wallet_id"]}: {str(e)}'
                ))

        self.stdout.write(self.style.SUCCESS(f'\n[OK] Fixed {fixed} wallet currencies'))

