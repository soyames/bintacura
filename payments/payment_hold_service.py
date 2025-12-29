from django.utils import timezone
from payments.models import ProviderPayout, DoctorPayout


def process_provider_payment(provider, amount, transaction_data):  # Process provider payment
    if not provider.has_blue_checkmark:
        payout = ProviderPayout.objects.create(
            provider=provider,
            amount=amount,
            status="on_hold",
            on_hold_reason="Provider does not have blue checkmark verification",
            period_start=timezone.now().date(),
            period_end=timezone.now().date(),
            transaction_count=1,
            **transaction_data,
        )
        return payout, "on_hold"
    else:
        payout = ProviderPayout.objects.create(
            provider=provider,
            amount=amount,
            status="pending",
            period_start=timezone.now().date(),
            period_end=timezone.now().date(),
            transaction_count=1,
            **transaction_data,
        )
        return payout, "pending"


def release_held_payments(provider):  # Release held payments
    if not provider.has_blue_checkmark:
        return 0

    held_payouts = ProviderPayout.objects.filter(provider=provider, status="on_hold")

    released_count = 0
    for payout in held_payouts:
        payout.status = "pending"
        payout.on_hold_reason = ""
        payout.released_from_hold_at = timezone.now()
        payout.save()
        released_count += 1

    held_doctor_payouts = DoctorPayout.objects.filter(doctor=provider, status="on_hold")

    for payout in held_doctor_payouts:
        payout.status = "pending"
        payout.on_hold_reason = ""
        payout.released_from_hold_at = timezone.now()
        payout.save()
        released_count += 1

    return released_count


def get_provider_payment_summary(provider):  # Get provider payment summary
    on_hold_payouts = ProviderPayout.objects.filter(provider=provider, status="on_hold")

    total_on_hold = sum(payout.amount for payout in on_hold_payouts)

    on_hold_doctor_payouts = DoctorPayout.objects.filter(
        doctor=provider, status="on_hold"
    )

    total_on_hold += sum(payout.amount for payout in on_hold_doctor_payouts)

    return {
        "total_on_hold": total_on_hold,
        "on_hold_count": on_hold_payouts.count() + on_hold_doctor_payouts.count(),
        "has_blue_checkmark": provider.has_blue_checkmark,
        "can_receive_payments": provider.has_blue_checkmark,
    }
