from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import PayrollRun, LeaveRequest, LeaveBalance, TimeAndAttendance


@receiver(post_save, sender=PayrollRun)
def update_payroll_totals(sender, instance, **kwargs):
    """Update payroll run totals when deductions change"""
    if not kwargs.get('raw', False):
        instance.calculate_totals()


@receiver(post_save, sender=LeaveRequest)
def update_leave_balance_on_approval(sender, instance, created, **kwargs):
    """Update leave balance when request is approved"""
    if not created and instance.status == 'approved':
        # Get or create leave balance for the year
        balance, created = LeaveBalance.objects.get_or_create(
            employee=instance.employee,
            leave_type=instance.leave_type,
            year=instance.start_date.year,
            defaults={
                'entitled_days': instance.leave_type.days_per_year,
                'used_days': 0,
                'remaining_days': instance.leave_type.days_per_year,
            }
        )

        # Update used days
        balance.used_days += instance.days_requested
        balance.calculate_remaining()

    # Update pending days when status changes
    if not created and instance.status in ['pending', 'approved', 'rejected', 'cancelled']:
        balance = LeaveBalance.objects.filter(
            employee=instance.employee,
            leave_type=instance.leave_type,
            year=instance.start_date.year
        ).first()

        if balance:
            # Recalculate pending days from all pending requests
            from django.db.models import Sum
            pending_total = LeaveRequest.objects.filter(
                employee=instance.employee,
                leave_type=instance.leave_type,
                status='pending',
                start_date__year=instance.start_date.year
            ).aggregate(total=Sum('days_requested'))['total'] or 0

            balance.pending_days = pending_total
            balance.calculate_remaining()


@receiver(post_save, sender=TimeAndAttendance)
def calculate_attendance_hours(sender, instance, **kwargs):
    """Calculate hours when attendance record is updated"""
    if instance.clock_out and not kwargs.get('raw', False):
        instance.calculate_hours()
