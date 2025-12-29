from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import JournalEntry, JournalEntryLine, BankAccount
from django.db.models import Sum


@receiver(post_save, sender=JournalEntryLine)
def update_bank_balance(sender, instance, created, **kwargs):
    """Update bank account balance when journal entries are posted"""
    if instance.journal_entry.status == 'posted' and instance.account.bank_accounts.exists():
        bank_account = instance.account.bank_accounts.first()
        # Recalculate balance from all posted entries
        posted_entries = JournalEntryLine.objects.filter(
            account=instance.account,
            journal_entry__status='posted'
        )
        total_debits = posted_entries.aggregate(Sum('debit_amount'))['debit_amount__sum'] or 0
        total_credits = posted_entries.aggregate(Sum('credit_amount'))['credit_amount__sum'] or 0

        bank_account.current_balance = bank_account.opening_balance + total_debits - total_credits
        bank_account.save()
