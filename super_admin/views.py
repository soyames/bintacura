from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.utils import timezone
from datetime import timedelta
from core.models import Participant
from payments.models import ServiceTransaction, FedaPayTransaction
from appointments.models import Appointment
from core.decorators import role_required

@login_required
@role_required('super_admin')
def dashboard(request):
    """Super admin dashboard with platform statistics"""
    
    # Get participant statistics
    total_participants = Participant.objects.count()
    patients = Participant.objects.filter(role='patient').count()
    doctors = Participant.objects.filter(role='doctor').count()
    hospitals = Participant.objects.filter(role='hospital').count()
    pharmacies = Participant.objects.filter(role='pharmacy').count()
    insurance_companies = Participant.objects.filter(role='insurance_company').count()
    
    # Verification statistics
    pending_verification = Participant.objects.filter(
        role__in=['doctor', 'hospital', 'pharmacy', 'insurance_company'],
        verification_status='pending'
    ).count()
    
    verified_providers = Participant.objects.filter(
        role__in=['doctor', 'hospital', 'pharmacy', 'insurance_company'],
        verification_status='verified'
    ).count()
    
    # Financial statistics
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    total_revenue = ServiceTransaction.objects.filter(
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    daily_revenue = ServiceTransaction.objects.filter(
        status='completed',
        created_at__date=today
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    weekly_revenue = ServiceTransaction.objects.filter(
        status='completed',
        created_at__date__gte=week_ago
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    monthly_revenue = ServiceTransaction.objects.filter(
        status='completed',
        created_at__date__gte=month_ago
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Appointment statistics
    active_appointments = Appointment.objects.filter(
        status__in=['scheduled', 'in_progress']
    ).count()
    
    today_appointments = Appointment.objects.filter(
        appointment_date=today
    ).count()
    
    # Recent activity
    recent_registrations = Participant.objects.order_by('-date_joined')[:10]
    recent_payments = ServiceTransaction.objects.filter(
        status='completed'
    ).order_by('-created_at')[:10]
    
    context = {
        'total_participants': total_participants,
        'patients': patients,
        'doctors': doctors,
        'hospitals': hospitals,
        'pharmacies': pharmacies,
        'insurance_companies': insurance_companies,
        'pending_verification': pending_verification,
        'verified_providers': verified_providers,
        'total_revenue': total_revenue,
        'daily_revenue': daily_revenue,
        'weekly_revenue': weekly_revenue,
        'monthly_revenue': monthly_revenue,
        'active_appointments': active_appointments,
        'today_appointments': today_appointments,
        'recent_registrations': recent_registrations,
        'recent_payments': recent_payments,
    }
    
    return render(request, 'super_admin/dashboard.html', context)


@login_required
@role_required('super_admin')
def verification_queue(request):
    """List all participants pending verification"""
    
    pending_doctors = Participant.objects.filter(
        role='doctor',
        verification_status='pending'
    ).order_by('date_joined')
    
    pending_hospitals = Participant.objects.filter(
        role='hospital',
        verification_status='pending'
    ).order_by('date_joined')
    
    pending_pharmacies = Participant.objects.filter(
        role='pharmacy',
        verification_status='pending'
    ).order_by('date_joined')
    
    pending_insurance = Participant.objects.filter(
        role='insurance_company',
        verification_status='pending'
    ).order_by('date_joined')
    
    context = {
        'pending_doctors': pending_doctors,
        'pending_hospitals': pending_hospitals,
        'pending_pharmacies': pending_pharmacies,
        'pending_insurance': pending_insurance,
    }
    
    return render(request, 'super_admin/verification_queue.html', context)


@login_required
@role_required('super_admin')
def verification_detail(request, uid):
    """View detailed information for verification"""
    
    participant = get_object_or_404(Participant, uid=uid)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if action == 'approve':
            participant.verification_status = 'verified'
            participant.verified_at = timezone.now()
            participant.verified_by = request.user.participant
            participant.verification_notes = notes
            participant.save()
            messages.success(request, f'{participant.get_full_name()} has been verified.')
            return redirect('super_admin:verification_queue')
        
        elif action == 'reject':
            reason = request.POST.get('reason', '')
            participant.verification_status = 'rejected'
            participant.rejection_reason = reason
            participant.verification_notes = notes
            participant.save()
            messages.warning(request, f'{participant.get_full_name()} has been rejected.')
            return redirect('super_admin:verification_queue')
    
    context = {
        'participant': participant,
    }
    
    return render(request, 'super_admin/verification_detail.html', context)


@login_required
@role_required('super_admin')
def participants_list(request):
    """List all participants with filtering"""
    
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    
    participants = Participant.objects.all()
    
    if role_filter:
        participants = participants.filter(role=role_filter)
    
    if status_filter:
        if status_filter == 'active':
            participants = participants.filter(is_active=True)
        elif status_filter == 'inactive':
            participants = participants.filter(is_active=False)
    
    participants = participants.order_by('-date_joined')
    
    context = {
        'participants': participants,
        'role_filter': role_filter,
        'status_filter': status_filter,
    }
    
    return render(request, 'super_admin/participants_list.html', context)


@login_required
@role_required('super_admin')
def financial_reports(request):
    """View financial reports and analytics"""
    
    today = timezone.now().date()
    month_ago = today - timedelta(days=30)
    
    # Payment statistics
    total_payments = ServiceTransaction.objects.filter(status='completed').count()
    total_amount = ServiceTransaction.objects.filter(
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Monthly breakdown
    monthly_payments = ServiceTransaction.objects.filter(
        status='completed',
        created_at__date__gte=month_ago
    ).values('created_at__date').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('created_at__date')
    
    context = {
        'total_payments': total_payments,
        'total_amount': total_amount,
        'monthly_payments': monthly_payments,
    }
    
    return render(request, 'super_admin/financial_reports.html', context)
