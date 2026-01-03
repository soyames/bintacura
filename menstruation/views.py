from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Avg, Count
from datetime import timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from collections import Counter

from .models import MenstrualCycle, CycleSymptom, CycleReminder
from .serializers import (
    MenstrualCycleSerializer,
    CycleSymptomSerializer,
    CycleReminderSerializer,
    CycleStatsSerializer
)
from core.models import Participant


# ==================== WEB VIEWS ====================

@login_required
def menstruation_tracker(request):
    """Main menstruation tracker page - only for female patients"""
    # Check if user is female
    if request.user.role != 'patient':
        messages.error(request, "Cette fonctionnalité est réservée aux patients.")
        return redirect('patient:dashboard')
    
    gender = getattr(request.user, 'gender', '').lower()
    if gender not in ['female', 'feminin', 'f']:
        messages.error(request, "Cette fonctionnalité est réservée aux patientes.")
        return redirect('patient:dashboard')
    
    # Get current active cycle
    current_cycle = MenstrualCycle.objects.filter(
        patient=request.user,
        is_active_cycle=True
    ).first()
    
    # Get recent cycles (last 6 months)
    six_months_ago = timezone.now().date() - timedelta(days=180)
    recent_cycles = MenstrualCycle.objects.filter(
        patient=request.user,
        cycle_start_date__gte=six_months_ago
    ).order_by('-cycle_start_date')[:6]
    
    # Calculate statistics
    stats = calculate_cycle_stats(request.user)
    
    # Get upcoming reminders
    upcoming_reminders = CycleReminder.objects.filter(
        patient=request.user,
        reminder_date__gte=timezone.now().date(),
        is_enabled=True,
        is_sent=False
    ).order_by('reminder_date')[:5]
    
    context = {
        'current_cycle': current_cycle,
        'recent_cycles': recent_cycles,
        'stats': stats,
        'upcoming_reminders': upcoming_reminders,
        'today': timezone.now().date(),
    }
    
    return render(request, 'menstruation/tracker.html', context)


@login_required
def log_period(request):
    """Log a new period start"""
    if request.method == 'POST':
        from datetime import datetime
        
        start_date_str = request.POST.get('cycle_start_date')
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        period_length = int(request.POST.get('period_length', 5))
        cycle_length = int(request.POST.get('cycle_length', 28))
        flow_intensity = request.POST.get('flow_intensity', 'medium')
        mood = request.POST.get('mood', 'normal')
        notes = request.POST.get('notes', '')
        symptoms = request.POST.getlist('symptoms')  # Multiple selection
        
        # Close any existing active cycle
        MenstrualCycle.objects.filter(
            patient=request.user,
            is_active_cycle=True
        ).update(is_active_cycle=False, cycle_end_date=start_date)
        
        # Create new cycle
        cycle = MenstrualCycle.objects.create(
            patient=request.user,
            cycle_start_date=start_date,
            period_length=period_length,
            cycle_length=cycle_length,
            flow_intensity=flow_intensity,
            mood=mood,
            notes=notes,
            symptoms=symptoms,
            is_active_cycle=True
        )
        
        # Create reminders for this cycle
        create_cycle_reminders(cycle)
        
        messages.success(request, "Cycle enregistré avec succès!")
        return redirect('menstruation:tracker')
    
    return render(request, 'menstruation/log_period.html')


@login_required
def cycle_details(request, cycle_id):
    """View detailed information about a specific cycle"""
    cycle = get_object_or_404(
        MenstrualCycle,
        id=cycle_id,
        patient=request.user
    )
    
    # Get daily symptoms for this cycle
    daily_symptoms = CycleSymptom.objects.filter(cycle=cycle).order_by('date')
    
    context = {
        'cycle': cycle,
        'daily_symptoms': daily_symptoms,
    }
    
    return render(request, 'menstruation/cycle_details.html', context)


@login_required
def log_symptom(request, cycle_id):
    """Log daily symptoms for a cycle"""
    cycle = get_object_or_404(
        MenstrualCycle,
        id=cycle_id,
        patient=request.user
    )
    
    if request.method == 'POST':
        symptom_date_str = request.POST.get('date', '').strip()
        symptom_type = request.POST.get('symptom_type')
        severity = request.POST.get('severity', 1)
        notes = request.POST.get('notes', '')
        
        # Convert date string to date object
        from datetime import datetime
        symptom_date = None
        if symptom_date_str:
            try:
                symptom_date = datetime.strptime(symptom_date_str, '%Y-%m-%d').date()
            except ValueError:
                symptom_date = timezone.now().date()
        
        # If no date provided, default to today
        if symptom_date is None:
            symptom_date = timezone.now().date()
        
        CycleSymptom.objects.create(
            cycle=cycle,
            date=symptom_date,
            symptom_type=symptom_type,
            severity=int(severity) if severity else 1,
            notes=notes
        )
        
        messages.success(request, "Symptôme enregistré!")
        return redirect('menstruation:cycle_details', cycle_id=cycle.id)
    
    return render(request, 'menstruation/log_symptom.html', {
        'cycle': cycle,
        'today': timezone.now().date().isoformat()
    })


@login_required
def cycle_calendar(request):
    """Calendar view of menstrual cycles"""
    # Get all cycles for the user
    cycles = MenstrualCycle.objects.filter(
        patient=request.user
    ).order_by('cycle_start_date')
    
    # Prepare calendar data
    calendar_events = []
    for cycle in cycles:
        # Period days
        calendar_events.append({
            'title': 'Period',
            'start': cycle.cycle_start_date.isoformat(),
            'end': (cycle.cycle_start_date + timedelta(days=cycle.period_length)).isoformat(),
            'color': '#ef5350',
            'type': 'period'
        })
        
        # Ovulation day
        if cycle.predicted_ovulation_date:
            calendar_events.append({
                'title': 'Ovulation',
                'start': cycle.predicted_ovulation_date.isoformat(),
                'color': '#66bb6a',
                'type': 'ovulation'
            })
        
        # Fertile window
        if cycle.predicted_fertile_window_start and cycle.predicted_fertile_window_end:
            calendar_events.append({
                'title': 'Fertile Window',
                'start': cycle.predicted_fertile_window_start.isoformat(),
                'end': cycle.predicted_fertile_window_end.isoformat(),
                'color': '#ffca28',
                'type': 'fertile'
            })
    
    context = {
        'calendar_events': calendar_events,
    }
    
    return render(request, 'menstruation/calendar.html', context)


# ==================== API VIEWS ====================

class MenstrualCycleViewSet(viewsets.ModelViewSet):
    """API ViewSet for menstrual cycles"""
    queryset = MenstrualCycle.objects.all()
    serializer_class = MenstrualCycleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter to user's own cycles"""
        if self.request.user.role == 'patient':
            return MenstrualCycle.objects.filter(patient=self.request.user)
        return MenstrualCycle.objects.none()
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current active cycle"""
        cycle = MenstrualCycle.objects.filter(
            patient=request.user,
            is_active_cycle=True
        ).first()
        
        if cycle:
            serializer = self.get_serializer(cycle)
            return Response(serializer.data)
        return Response({'detail': 'No active cycle'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get cycle statistics"""
        stats = calculate_cycle_stats(request.user)
        serializer = CycleStatsSerializer(stats)
        return Response(serializer.data)


class CycleSymptomViewSet(viewsets.ModelViewSet):
    """API ViewSet for cycle symptoms"""
    queryset = CycleSymptom.objects.all()
    serializer_class = CycleSymptomSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter to user's own symptoms"""
        if self.request.user.role == 'patient':
            return CycleSymptom.objects.filter(cycle__patient=request.user)
        return CycleSymptom.objects.none()


class CycleReminderViewSet(viewsets.ModelViewSet):
    """API ViewSet for cycle reminders"""
    queryset = CycleReminder.objects.all()
    serializer_class = CycleReminderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter to user's own reminders"""
        if self.request.user.role == 'patient':
            return CycleReminder.objects.filter(patient=request.user)
        return CycleReminder.objects.none()


# ==================== HELPER FUNCTIONS ====================

def calculate_cycle_stats(user):
    """Calculate cycle statistics for a user"""
    cycles = MenstrualCycle.objects.filter(patient=user)
    
    if not cycles.exists():
        return {
            'average_cycle_length': 28,
            'average_period_length': 5,
            'total_cycles': 0,
            'last_period_date': None,
            'next_predicted_period': None,
            'common_symptoms': []
        }
    
    # Calculate averages
    avg_cycle_length = cycles.aggregate(Avg('cycle_length'))['cycle_length__avg'] or 28
    avg_period_length = cycles.aggregate(Avg('period_length'))['period_length__avg'] or 5
    
    # Get last period
    last_cycle = cycles.order_by('-cycle_start_date').first()
    
    # Find common symptoms
    all_symptoms = []
    for cycle in cycles:
        if cycle.symptoms:
            all_symptoms.extend(cycle.symptoms)
    
    symptom_counts = Counter(all_symptoms)
    common_symptoms = [symptom for symptom, count in symptom_counts.most_common(5)]
    
    return {
        'average_cycle_length': int(avg_cycle_length),
        'average_period_length': int(avg_period_length),
        'total_cycles': cycles.count(),
        'last_period_date': last_cycle.cycle_start_date if last_cycle else None,
        'next_predicted_period': last_cycle.predicted_next_period_date if last_cycle else None,
        'common_symptoms': common_symptoms
    }


def create_cycle_reminders(cycle):
    """Create reminders for a new cycle"""
    from datetime import datetime, date
    import logging
    logger = logging.getLogger(__name__)
    
    # Helper to ensure dates
    def ensure_date(d):
        if isinstance(d, str):
            try:
                return datetime.strptime(d, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                logger.warning(f"Could not parse date string: {d}")
                return None
        elif isinstance(d, datetime):
            return d.date()
        return d
    
    # Period starting reminder (1 day before predicted next period)
    if cycle.predicted_next_period_date:
        try:
            next_period_date = ensure_date(cycle.predicted_next_period_date)
            if next_period_date:
                CycleReminder.objects.create(
                    patient=cycle.patient,
                    reminder_type='period_starting',
                    reminder_date=next_period_date - timedelta(days=1),
                    message="Vos règles devraient commencer demain."
                )
        except Exception as e:
            logger.error(f"Failed to create period_starting reminder: {e}")
    
    # Ovulation reminder
    if cycle.predicted_ovulation_date:
        try:
            ovulation_date = ensure_date(cycle.predicted_ovulation_date)
            if ovulation_date:
                CycleReminder.objects.create(
                    patient=cycle.patient,
                    reminder_type='ovulation',
                    reminder_date=ovulation_date,
                    message="Jour d'ovulation prédit aujourd'hui."
                )
        except Exception as e:
            logger.error(f"Failed to create ovulation reminder: {e}")
    
    # Fertile window reminder
    if cycle.predicted_fertile_window_start:
        try:
            fertile_start = ensure_date(cycle.predicted_fertile_window_start)
            if fertile_start:
                CycleReminder.objects.create(
                    patient=cycle.patient,
                    reminder_type='fertile_window',
                    reminder_date=fertile_start,
                    message="Début de votre fenêtre fertile."
                )
        except Exception as e:
            logger.error(f"Failed to create fertile_window reminder: {e}")
