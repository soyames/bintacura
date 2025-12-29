"""
Hospital Operations AI Analytics Module
No LLM required - Uses statistical methods, pattern recognition, and trend analysis
"""
from django.utils import timezone
from django.db.models import Count, Avg, Q, F, Sum
from datetime import timedelta, datetime
from decimal import Decimal
from .models import Bed, Admission, HospitalStaff, DepartmentTask


class HospitalAI:
    """AI-powered hospital operations analytics using statistical methods"""

    @staticmethod
    def predict_bed_occupancy(hospital, days_forward=7):
        """
        Predict bed occupancy using discharge patterns and admission rates

        Args:
            hospital: Hospital participant
            days_forward: Number of days to forecast (default 7)

        Returns:
            dict: Bed occupancy forecast with recommendations
        """
        # Get current bed status
        total_beds = Bed.objects.filter(hospital=hospital).count()
        occupied_beds = Bed.objects.filter(hospital=hospital, status='occupied').count()
        available_beds = Bed.objects.filter(hospital=hospital, status='available').count()
        maintenance_beds = Bed.objects.filter(hospital=hospital, status='maintenance').count()

        if total_beds == 0:
            return {
                'status': 'no_data',
                'message': 'No beds configured in the system'
            }

        current_occupancy_rate = (occupied_beds / total_beds * 100) if total_beds > 0 else 0

        # Analyze historical discharge patterns (last 30 days)
        lookback_days = 30
        start_date = timezone.now() - timedelta(days=lookback_days)

        # Count discharges by day of week
        discharges = Admission.objects.filter(
            hospital=hospital,
            status='discharged',
            actual_discharge_date__gte=start_date
        )

        total_discharges = discharges.count()
        avg_discharges_per_day = total_discharges / lookback_days if lookback_days > 0 else 0

        # Analyze admission patterns
        admissions = Admission.objects.filter(
            hospital=hospital,
            admission_date__gte=start_date
        )

        total_admissions = admissions.count()
        avg_admissions_per_day = total_admissions / lookback_days if lookback_days > 0 else 0

        # Calculate net bed usage trend
        net_change_per_day = avg_admissions_per_day - avg_discharges_per_day

        # Forecast occupancy
        forecasted_occupied = occupied_beds + (net_change_per_day * days_forward)
        forecasted_occupied = max(0, min(total_beds, forecasted_occupied))  # Clamp to valid range
        forecasted_occupancy_rate = (forecasted_occupied / total_beds * 100) if total_beds > 0 else 0

        # Analyze by bed type
        bed_type_analysis = []
        bed_types = ['standard', 'icu', 'private', 'semi_private', 'pediatric', 'maternity']

        for bed_type in bed_types:
            type_total = Bed.objects.filter(hospital=hospital, bed_type=bed_type).count()
            if type_total == 0:
                continue

            type_occupied = Bed.objects.filter(hospital=hospital, bed_type=bed_type, status='occupied').count()
            type_occupancy_rate = (type_occupied / type_total * 100) if type_total > 0 else 0

            bed_type_analysis.append({
                'bed_type': bed_type,
                'total': type_total,
                'occupied': type_occupied,
                'available': type_total - type_occupied,
                'occupancy_rate': round(type_occupancy_rate, 1)
            })

        # Determine alert level
        if forecasted_occupancy_rate > 95:
            alert_level = 'critical'
            recommendation = "CRITICAL: Hospital approaching full capacity. Prepare overflow protocols."
        elif forecasted_occupancy_rate > 85:
            alert_level = 'warning'
            recommendation = "WARNING: High occupancy expected. Consider expediting discharges."
        elif forecasted_occupancy_rate < 50:
            alert_level = 'low_occupancy'
            recommendation = "Low occupancy forecasted. Opportunity for elective procedures."
        else:
            alert_level = 'normal'
            recommendation = "Occupancy within normal range."

        # Analyze average length of stay
        recent_stays = Admission.objects.filter(
            hospital=hospital,
            status='discharged',
            actual_discharge_date__gte=start_date
        )

        avg_stay_days = 0
        if recent_stays.exists():
            total_stay_days = 0
            count = 0
            for admission in recent_stays:
                if admission.actual_discharge_date and admission.admission_date:
                    stay_duration = (admission.actual_discharge_date.date() - admission.admission_date.date()).days
                    total_stay_days += stay_duration
                    count += 1

            avg_stay_days = round(total_stay_days / count, 1) if count > 0 else 0

        return {
            'status': 'forecasted',
            'forecast_period_days': days_forward,
            'current_status': {
                'total_beds': total_beds,
                'occupied_beds': occupied_beds,
                'available_beds': available_beds,
                'maintenance_beds': maintenance_beds,
                'occupancy_rate': round(current_occupancy_rate, 1)
            },
            'forecast': {
                'expected_occupied_beds': round(forecasted_occupied, 0),
                'expected_occupancy_rate': round(forecasted_occupancy_rate, 1),
                'avg_admissions_per_day': round(avg_admissions_per_day, 1),
                'avg_discharges_per_day': round(avg_discharges_per_day, 1),
                'net_change_per_day': round(net_change_per_day, 1)
            },
            'bed_type_breakdown': bed_type_analysis,
            'avg_length_of_stay_days': avg_stay_days,
            'alert_level': alert_level,
            'recommendation': recommendation,
            'generated_at': timezone.now()
        }

    @staticmethod
    def optimize_staff_scheduling(hospital, department=None, days_forward=7):
        """
        Optimize staff scheduling based on patient volume analysis

        Args:
            hospital: Hospital participant
            department: Optional - specific department to analyze
            days_forward: Number of days to forecast (default 7)

        Returns:
            dict: Staff scheduling recommendations
        """
        # Analyze current staffing levels
        staff_query = HospitalStaff.objects.filter(
            hospital=hospital,
            is_active=True
        )

        if department:
            staff_query = staff_query.filter(department=department)

        total_staff = staff_query.count()

        # Count staff by role
        staff_by_role = {}
        for role_code, role_name in HospitalStaff.ROLE_CHOICES:
            role_count = staff_query.filter(role=role_code).count()
            if role_count > 0:
                staff_by_role[role_code] = {
                    'role_name': role_name,
                    'count': role_count
                }

        # Analyze patient volume (last 30 days)
        lookback_days = 30
        start_date = timezone.now() - timedelta(days=lookback_days)

        # Current admissions
        current_admissions_query = Admission.objects.filter(
            hospital=hospital,
            status='admitted'
        )

        if department:
            current_admissions_query = current_admissions_query.filter(department=department)

        current_patients = current_admissions_query.count()

        # Historical admission patterns
        historical_admissions = Admission.objects.filter(
            hospital=hospital,
            admission_date__gte=start_date
        )

        if department:
            historical_admissions = historical_admissions.filter(department=department)

        total_historical_admissions = historical_admissions.count()
        avg_daily_admissions = total_historical_admissions / lookback_days if lookback_days > 0 else 0

        # Analyze admission patterns by day of week
        day_patterns = {}
        for admission in historical_admissions:
            day_of_week = admission.admission_date.strftime('%A')
            if day_of_week not in day_patterns:
                day_patterns[day_of_week] = 0
            day_patterns[day_of_week] += 1

        # Identify peak days
        peak_day = max(day_patterns.items(), key=lambda x: x[1])[0] if day_patterns else 'Unknown'
        peak_day_count = max(day_patterns.values()) if day_patterns else 0

        # Calculate staff-to-patient ratio
        staff_to_patient_ratio = (total_staff / current_patients) if current_patients > 0 else 0

        # Determine staffing adequacy
        # Ideal ratios (simplified):
        # Doctors: 1:10, Nurses: 1:5, Other staff: varies
        doctors_count = staff_query.filter(role__in=['doctor', 'surgeon']).count()
        nurses_count = staff_query.filter(role='nurse').count()

        ideal_doctors = current_patients / 10
        ideal_nurses = current_patients / 5

        doctor_shortage = max(0, ideal_doctors - doctors_count)
        nurse_shortage = max(0, ideal_nurses - nurses_count)

        recommendations = []

        if doctor_shortage > 0:
            recommendations.append({
                'type': 'staffing_shortage',
                'role': 'Doctor',
                'current': doctors_count,
                'recommended': round(ideal_doctors, 0),
                'shortage': round(doctor_shortage, 0),
                'priority': 'high' if doctor_shortage > 2 else 'medium'
            })

        if nurse_shortage > 0:
            recommendations.append({
                'type': 'staffing_shortage',
                'role': 'Nurse',
                'current': nurses_count,
                'recommended': round(ideal_nurses, 0),
                'shortage': round(nurse_shortage, 0),
                'priority': 'high' if nurse_shortage > 3 else 'medium'
            })

        # Analyze emergency admissions
        emergency_admissions = historical_admissions.filter(admission_type='emergency').count()
        emergency_rate = (emergency_admissions / total_historical_admissions * 100) if total_historical_admissions > 0 else 0

        if emergency_rate > 30:
            recommendations.append({
                'type': 'high_emergency_rate',
                'description': f"High emergency admission rate ({emergency_rate:.1f}%). Consider emergency staffing protocols.",
                'priority': 'high'
            })

        # Overall staffing status
        if staff_to_patient_ratio >= 0.5:
            staffing_status = 'adequate'
        elif staff_to_patient_ratio >= 0.3:
            staffing_status = 'moderate'
        else:
            staffing_status = 'critical'

        return {
            'status': 'analyzed',
            'department_name': department.name if department else 'All Departments',
            'current_staffing': {
                'total_staff': total_staff,
                'current_patients': current_patients,
                'staff_to_patient_ratio': round(staff_to_patient_ratio, 2),
                'staffing_status': staffing_status,
                'staff_by_role': staff_by_role
            },
            'patient_volume_analysis': {
                'avg_daily_admissions': round(avg_daily_admissions, 1),
                'peak_day': peak_day,
                'peak_day_admissions': peak_day_count,
                'emergency_admission_rate': round(emergency_rate, 1)
            },
            'recommendations': recommendations,
            'generated_at': timezone.now()
        }

    @staticmethod
    def predict_equipment_maintenance(hospital):
        """
        Predict equipment maintenance needs based on task patterns

        Note: Using DepartmentTask as proxy for maintenance tracking

        Args:
            hospital: Hospital participant

        Returns:
            dict: Maintenance predictions and recommendations
        """
        # Get all departments for this hospital
        from core.models import Department
        departments = Department.objects.filter(
            organization=hospital
        )

        # Analyze maintenance-related tasks
        lookback_days = 90
        start_date = timezone.now() - timedelta(days=lookback_days)

        maintenance_analysis = []

        for dept in departments:
            # Get tasks for this department (using DepartmentTask as proxy)
            dept_tasks = DepartmentTask.objects.filter(
                department=dept,
                created_at__gte=start_date
            )

            total_tasks = dept_tasks.count()
            if total_tasks == 0:
                continue

            # Analyze task completion rate
            completed_tasks = dept_tasks.filter(status='completed').count()
            pending_tasks = dept_tasks.filter(status='pending').count()
            in_progress_tasks = dept_tasks.filter(status='in_progress').count()
            overdue_tasks = dept_tasks.filter(
                status__in=['pending', 'in_progress'],
                due_date__lt=timezone.now()
            ).count()

            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

            # Analyze high priority tasks
            high_priority_tasks = dept_tasks.filter(priority__in=['high', 'urgent']).count()
            high_priority_rate = (high_priority_tasks / total_tasks * 100) if total_tasks > 0 else 0

            # Determine department status
            if overdue_tasks > 5 or completion_rate < 50:
                dept_status = 'critical'
                dept_recommendation = f"CRITICAL: {overdue_tasks} overdue tasks, {completion_rate:.1f}% completion rate"
            elif overdue_tasks > 2 or completion_rate < 70:
                dept_status = 'warning'
                dept_recommendation = f"WARNING: {overdue_tasks} overdue tasks need attention"
            else:
                dept_status = 'healthy'
                dept_recommendation = "Department task management is healthy"

            maintenance_analysis.append({
                'department': dept.name,
                'total_tasks': total_tasks,
                'completed': completed_tasks,
                'pending': pending_tasks,
                'in_progress': in_progress_tasks,
                'overdue': overdue_tasks,
                'completion_rate': round(completion_rate, 1),
                'high_priority_rate': round(high_priority_rate, 1),
                'status': dept_status,
                'recommendation': dept_recommendation
            })

        # Sort by status (critical first)
        maintenance_analysis.sort(
            key=lambda x: (x['status'] == 'critical', x['status'] == 'warning', x['overdue']),
            reverse=True
        )

        # Overall hospital maintenance score
        if maintenance_analysis:
            avg_completion = sum(d['completion_rate'] for d in maintenance_analysis) / len(maintenance_analysis)
            total_overdue = sum(d['overdue'] for d in maintenance_analysis)

            if avg_completion >= 80 and total_overdue < 5:
                overall_status = 'excellent'
            elif avg_completion >= 70 and total_overdue < 10:
                overall_status = 'good'
            elif avg_completion >= 60 and total_overdue < 20:
                overall_status = 'fair'
            else:
                overall_status = 'poor'
        else:
            avg_completion = 0
            total_overdue = 0
            overall_status = 'no_data'

        return {
            'status': 'analyzed',
            'overall_status': overall_status,
            'overall_completion_rate': round(avg_completion, 1),
            'total_overdue_tasks': total_overdue,
            'departments_analyzed': len(maintenance_analysis),
            'department_details': maintenance_analysis,
            'generated_at': timezone.now()
        }

    @staticmethod
    def get_hospital_insights(hospital):
        """
        Get all hospital AI insights for unified dashboard
        Called by central AI coordinator

        Returns:
            list: All hospital insights with priority levels
        """
        insights = []

        # Bed occupancy insights
        bed_forecast = HospitalAI.predict_bed_occupancy(hospital, days_forward=7)
        if bed_forecast['status'] == 'forecasted':
            priority = 'high' if bed_forecast['alert_level'] == 'critical' else 'medium' if bed_forecast['alert_level'] == 'warning' else 'low'

            insights.append({
                'type': 'bed_occupancy',
                'priority': priority,
                'title': f"Bed Occupancy Forecast: {bed_forecast['forecast']['expected_occupancy_rate']:.1f}%",
                'description': bed_forecast['recommendation'],
                'data': bed_forecast,
                'module': 'hospital'
            })

        # Staffing insights
        staff_analysis = HospitalAI.optimize_staff_scheduling(hospital)
        if staff_analysis['status'] == 'analyzed' and staff_analysis['recommendations']:
            high_priority_recs = [r for r in staff_analysis['recommendations'] if r.get('priority') == 'high']

            priority = 'high' if high_priority_recs else 'medium'

            insights.append({
                'type': 'staff_scheduling',
                'priority': priority,
                'title': f"{len(staff_analysis['recommendations'])} Staffing Recommendations",
                'description': f"Staff-to-patient ratio: {staff_analysis['current_staffing']['staff_to_patient_ratio']:.2f}",
                'data': staff_analysis,
                'module': 'hospital'
            })

        # Maintenance insights
        maintenance = HospitalAI.predict_equipment_maintenance(hospital)
        if maintenance['status'] == 'analyzed':
            critical_depts = [d for d in maintenance['department_details'] if d['status'] == 'critical']

            if critical_depts or maintenance['overall_status'] == 'poor':
                priority = 'high'
            elif maintenance['total_overdue_tasks'] > 0:
                priority = 'medium'
            else:
                priority = 'low'

            insights.append({
                'type': 'maintenance',
                'priority': priority,
                'title': f"Maintenance Task Status: {maintenance['overall_status'].title()}",
                'description': f"{maintenance['total_overdue_tasks']} overdue tasks across departments",
                'data': maintenance,
                'module': 'hospital'
            })

        return insights
