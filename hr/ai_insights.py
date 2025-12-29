"""
HR AI Insights Module
=====================

AI-powered analytics for HR operations WITHOUT requiring external LLM.

Features:
- Attendance pattern detection (late patterns, Monday/Friday absences)
- Performance trend analysis (improving/declining trends)
- Employee churn risk prediction (0-100 score)
- Leave approval recommendations (rule-based decision support)

All algorithms use statistical analysis and pattern recognition.
"""

from django.db.models import Count, Avg, Sum, Q, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


class HRAnalytics:
    """AI-powered HR analytics using statistical methods (no LLM required)"""

    @staticmethod
    def analyze_attendance_patterns(employee, days=30):
        """
        Detect attendance patterns using statistical methods.

        Args:
            employee: Employee instance
            days: Number of days to analyze (default 30)

        Returns:
            dict: Attendance analysis with detected patterns
        """
        from .models import Attendance

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        attendance_records = Attendance.objects.filter(
            employee=employee,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')

        total_days = attendance_records.count()

        if total_days == 0:
            return {
                'employee_id': str(employee.id),
                'employee_name': employee.user.full_name,
                'analysis_period_days': days,
                'message': 'No attendance data available for analysis',
                'patterns_detected': 0,
                'patterns': []
            }

        late_days = attendance_records.filter(status='late').count()
        absent_days = attendance_records.filter(status='absent').count()
        present_days = attendance_records.filter(status='present').count()

        patterns = []

        # Pattern 1: Frequent lateness (>20% late)
        late_rate = late_days / total_days if total_days > 0 else 0
        if late_rate > 0.2:
            patterns.append({
                'type': 'frequent_lateness',
                'severity': 'medium',
                'metric': f'{late_days}/{total_days} days ({late_rate*100:.1f}%)',
                'message': f'Employee frequently late: {late_days} out of {total_days} days',
                'recommendation': 'Schedule meeting to discuss punctuality concerns',
                'priority': 'medium',
                'detected_at': timezone.now().isoformat()
            })

        # Pattern 2: Monday/Friday absence pattern
        monday_absences = attendance_records.filter(
            date__week_day=2,  # Monday (ISO week day: 1=Monday)
            status='absent'
        ).count()

        friday_absences = attendance_records.filter(
            date__week_day=6,  # Friday
            status='absent'
        ).count()

        weekend_absence_rate = (monday_absences + friday_absences) / total_days if total_days > 0 else 0

        if weekend_absence_rate > 0.15:  # >15% Monday/Friday absences
            patterns.append({
                'type': 'weekend_pattern',
                'severity': 'medium',
                'metric': f'{monday_absences + friday_absences} Mon/Fri absences',
                'message': f'High Monday/Friday absence rate detected: {weekend_absence_rate*100:.1f}%',
                'recommendation': 'Investigate potential weekend-related issues or burnout',
                'priority': 'medium',
                'detected_at': timezone.now().isoformat()
            })

        # Pattern 3: Consecutive absences
        consecutive_count = HRAnalytics._detect_consecutive_absences(attendance_records)

        if consecutive_count > 3:
            patterns.append({
                'type': 'extended_absence',
                'severity': 'high',
                'metric': f'{consecutive_count} consecutive absences',
                'message': f'{consecutive_count} consecutive days absent detected',
                'recommendation': 'Check if employee needs medical leave or support',
                'priority': 'high',
                'detected_at': timezone.now().isoformat()
            })

        # Pattern 4: Declining attendance trend
        if total_days >= 14:  # Need at least 2 weeks
            first_week_rate = HRAnalytics._calculate_attendance_rate(
                attendance_records[:7] if attendance_records.count() > 7 else attendance_records
            )
            last_week_rate = HRAnalytics._calculate_attendance_rate(
                attendance_records.reverse()[:7] if attendance_records.count() > 7 else attendance_records.reverse()
            )

            if first_week_rate - last_week_rate > 0.20:  # >20% decline
                patterns.append({
                    'type': 'declining_trend',
                    'severity': 'medium',
                    'metric': f'{(first_week_rate - last_week_rate)*100:.1f}% decline',
                    'message': 'Attendance rate declining over analysis period',
                    'recommendation': 'Investigate recent changes affecting employee attendance',
                    'priority': 'medium',
                    'detected_at': timezone.now().isoformat()
                })

        # Calculate overall attendance rate
        attendance_rate = ((total_days - absent_days) / total_days * 100) if total_days > 0 else 0

        return {
            'employee_id': str(employee.id),
            'employee_name': employee.user.full_name,
            'job_title': employee.job_title,
            'department': employee.department.name if employee.department else 'N/A',
            'analysis_period': {
                'days': days,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'attendance_summary': {
                'total_working_days': total_days,
                'present_days': present_days,
                'late_days': late_days,
                'absent_days': absent_days,
                'attendance_rate': round(attendance_rate, 2),
                'late_rate': round(late_rate * 100, 2),
                'absence_rate': round((absent_days / total_days * 100) if total_days > 0 else 0, 2)
            },
            'patterns_detected': len(patterns),
            'patterns': patterns,
            'overall_status': 'excellent' if attendance_rate >= 98 else 'good' if attendance_rate >= 95 else 'needs_attention' if attendance_rate >= 85 else 'critical',
            'generated_at': timezone.now().isoformat()
        }

    @staticmethod
    def _detect_consecutive_absences(attendance_records):
        """Helper to detect maximum consecutive absence streak"""
        absences = attendance_records.filter(status='absent').order_by('date')

        if not absences.exists():
            return 0

        max_consecutive = 1
        current_consecutive = 1
        prev_date = None

        for absence in absences:
            if prev_date and (absence.date - prev_date).days == 1:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 1
            prev_date = absence.date

        return max_consecutive

    @staticmethod
    def _calculate_attendance_rate(attendance_records):
        """Calculate attendance rate for given records"""
        total = attendance_records.count()
        if total == 0:
            return 0.0

        present = attendance_records.filter(Q(status='present') | Q(status='late')).count()
        return present / total

    @staticmethod
    def analyze_performance_trend(employee, reviews_count=5):
        """
        Analyze performance trend from historical reviews.

        Args:
            employee: Employee instance
            reviews_count: Number of recent reviews to analyze

        Returns:
            dict: Performance trend analysis
        """
        from .models import PerformanceReview

        RATING_SCORES = {
            'excellent': 5,
            'good': 4,
            'satisfactory': 3,
            'needs_improvement': 2,
            'poor': 1
        }

        reviews = PerformanceReview.objects.filter(
            employee=employee
        ).order_by('-review_period_end')[:reviews_count]

        if reviews.count() < 2:
            return {
                'employee_id': str(employee.id),
                'employee_name': employee.user.full_name,
                'trend': 'insufficient_data',
                'message': 'Not enough review history for trend analysis (minimum 2 reviews required)',
                'reviews_analyzed': reviews.count(),
                'generated_at': timezone.now().isoformat()
            }

        # Convert ratings to numeric scores
        scores = []
        review_details = []

        for review in reviews:
            score = RATING_SCORES.get(review.overall_rating, 3)
            scores.append(score)
            review_details.append({
                'date': review.review_period_end.isoformat(),
                'rating': review.overall_rating,
                'score': score
            })

        # Calculate trend (simple linear regression)
        n = len(scores)
        avg_change = (scores[0] - scores[-1]) / (n - 1)

        if avg_change > 0.3:
            trend_direction = 'improving'
            trend_message = 'Performance showing consistent improvement over time'
        elif avg_change < -0.3:
            trend_direction = 'declining'
            trend_message = 'Performance declining over recent reviews'
        else:
            trend_direction = 'stable'
            trend_message = 'Performance relatively stable'

        # Calculate consistency (variance)
        mean_score = sum(scores) / len(scores)
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        std_dev = variance ** 0.5
        consistency = 'consistent' if variance < 0.5 else 'variable' if variance < 1.0 else 'inconsistent'

        # Generate insights
        insights = []

        if trend_direction == 'improving':
            insights.append({
                'type': 'positive_trend',
                'message': trend_message,
                'recommendation': 'Consider for promotion, raise, or additional responsibilities',
                'priority': 'low',
                'action_item': 'Recognition discussion'
            })
        elif trend_direction == 'declining':
            insights.append({
                'type': 'negative_trend',
                'message': trend_message,
                'recommendation': 'Schedule performance improvement plan (PIP) meeting',
                'priority': 'high',
                'action_item': 'Intervention required'
            })

        if consistency == 'inconsistent':
            insights.append({
                'type': 'inconsistent_performance',
                'message': 'Performance varies significantly between review periods',
                'recommendation': 'Investigate factors affecting consistency (workload, support, training)',
                'priority': 'medium',
                'action_item': 'Root cause analysis'
            })

        # Current performance status
        current_score = scores[0]
        if current_score >= 4:
            performance_status = 'excellent'
        elif current_score >= 3:
            performance_status = 'satisfactory'
        else:
            performance_status = 'needs_improvement'

        return {
            'employee_id': str(employee.id),
            'employee_name': employee.user.full_name,
            'job_title': employee.job_title,
            'reviews_analyzed': reviews.count(),
            'performance_metrics': {
                'current_score': current_score,
                'current_rating': reviews[0].overall_rating,
                'average_score': round(mean_score, 2),
                'score_range': f'{min(scores)}-{max(scores)}',
                'standard_deviation': round(std_dev, 2)
            },
            'trend_analysis': {
                'direction': trend_direction,
                'message': trend_message,
                'rate_of_change': round(avg_change, 2),
                'consistency': consistency,
                'variance': round(variance, 2)
            },
            'recent_reviews': review_details[:3],  # Last 3 reviews
            'insights': insights,
            'performance_status': performance_status,
            'generated_at': timezone.now().isoformat()
        }

    @staticmethod
    def calculate_churn_risk(employee):
        """
        Calculate employee churn (turnover) risk score.

        Uses multiple factors to predict likelihood of employee leaving:
        - Tenure (new employees are higher risk)
        - Performance ratings
        - Attendance issues
        - Leave request frequency
        - Payroll problems

        Args:
            employee: Employee instance

        Returns:
            dict: Churn risk assessment with score 0-100
        """
        from .models import LeaveRequest, Payroll, PerformanceReview, Attendance

        risk_score = 0.0
        risk_factors = []

        # Factor 1: Tenure (new employees higher risk)
        tenure_days = (timezone.now().date() - employee.hire_date).days
        tenure_months = tenure_days / 30

        if tenure_days < 90:  # < 3 months (probation period)
            risk_score += 25
            risk_factors.append({
                'factor': 'Very short tenure (probation period)',
                'detail': f'{tenure_months:.1f} months',
                'impact': 'high',
                'points': 25
            })
        elif tenure_days < 180:  # < 6 months
            risk_score += 20
            risk_factors.append({
                'factor': 'Short tenure',
                'detail': f'{tenure_months:.1f} months',
                'impact': 'high',
                'points': 20
            })
        elif tenure_days > 730:  # > 2 years (more stable)
            risk_score -= 10

        # Factor 2: Recent performance
        recent_review = PerformanceReview.objects.filter(
            employee=employee
        ).order_by('-review_period_end').first()

        if recent_review:
            RATING_SCORES = {
                'excellent': 5, 'good': 4, 'satisfactory': 3,
                'needs_improvement': 2, 'poor': 1
            }
            rating_score = RATING_SCORES.get(recent_review.overall_rating, 3)

            if rating_score <= 2:
                risk_score += 30
                risk_factors.append({
                    'factor': 'Low performance rating',
                    'detail': recent_review.overall_rating,
                    'impact': 'high',
                    'points': 30
                })
            elif rating_score == 5:
                risk_score -= 5  # Excellent performers less likely to leave

        # Factor 3: Attendance issues
        recent_attendance = Attendance.objects.filter(
            employee=employee,
            date__gte=timezone.now().date() - timedelta(days=30)
        )

        if recent_attendance.exists():
            total_days = recent_attendance.count()
            absent_days = recent_attendance.filter(status='absent').count()
            absence_rate = absent_days / total_days if total_days > 0 else 0

            if absence_rate > 0.15:  # >15% absences
                risk_score += 20
                risk_factors.append({
                    'factor': 'High absence rate',
                    'detail': f'{absence_rate*100:.0f}% in last 30 days',
                    'impact': 'medium',
                    'points': 20
                })

        # Factor 4: Frequent leave requests (potential job hunting)
        leave_requests = LeaveRequest.objects.filter(
            employee=employee,
            created_at__gte=timezone.now() - timedelta(days=90)
        ).count()

        if leave_requests > 5:
            risk_score += 15
            risk_factors.append({
                'factor': 'Frequent leave requests',
                'detail': f'{leave_requests} requests in 90 days',
                'impact': 'medium',
                'points': 15
            })

        # Factor 5: Payroll issues (major retention factor)
        failed_payrolls = Payroll.objects.filter(
            employee=employee,
            payment_status='failed',
            pay_period_end__gte=timezone.now().date() - timedelta(days=180)
        ).count()

        if failed_payrolls > 0:
            risk_score += 25
            risk_factors.append({
                'factor': 'Payroll issues',
                'detail': f'{failed_payrolls} failed payment(s) in 6 months',
                'impact': 'critical',
                'points': 25
            })

        # Factor 6: Employment type (temporary workers higher risk)
        if employee.employment_type in ['contract', 'temporary']:
            risk_score += 10
            risk_factors.append({
                'factor': 'Non-permanent employment',
                'detail': employee.employment_type,
                'impact': 'low',
                'points': 10
            })

        # Normalize risk score to 0-100
        risk_score = min(max(risk_score, 0), 100)

        # Determine risk level and recommendation
        if risk_score < 30:
            risk_level = 'low'
            recommendation = 'Continue regular employee engagement activities'
            action_priority = 'low'
        elif risk_score < 60:
            risk_level = 'medium'
            recommendation = 'Schedule 1-on-1 meeting to discuss satisfaction, concerns, and career goals'
            action_priority = 'medium'
        else:
            risk_level = 'high'
            recommendation = 'URGENT: Immediate intervention required - schedule retention meeting with HR and manager'
            action_priority = 'high'

        return {
            'employee_id': str(employee.id),
            'employee_name': employee.user.full_name,
            'job_title': employee.job_title,
            'department': employee.department.name if employee.department else 'N/A',
            'tenure_months': round(tenure_months, 1),
            'churn_risk': {
                'score': round(risk_score, 1),
                'level': risk_level,
                'percentage': f'{risk_score:.0f}%'
            },
            'risk_factors': risk_factors,
            'risk_factors_count': len(risk_factors),
            'total_risk_points': sum(f['points'] for f in risk_factors),
            'recommendation': recommendation,
            'action_priority': action_priority,
            'next_steps': HRAnalytics._get_churn_prevention_steps(risk_level),
            'generated_at': timezone.now().isoformat()
        }

    @staticmethod
    def _get_churn_prevention_steps(risk_level):
        """Get actionable steps to prevent employee churn"""
        steps = {
            'low': [
                'Maintain regular check-ins',
                'Recognize achievements and contributions',
                'Provide growth opportunities'
            ],
            'medium': [
                'Schedule 1-on-1 meeting within 1 week',
                'Discuss career development and satisfaction',
                'Address any concerns promptly',
                'Review compensation and benefits'
            ],
            'high': [
                'URGENT: Schedule retention meeting within 24-48 hours',
                'Involve HR and direct manager',
                'Identify and address root causes immediately',
                'Consider retention bonus or promotion',
                'Create action plan with employee input'
            ]
        }
        return steps.get(risk_level, steps['medium'])

    @staticmethod
    def recommend_leave_approval(leave_request):
        """
        Provide AI recommendation for leave approval decision.

        Uses rule-based logic to analyze:
        - Employee's leave balance
        - Department coverage during requested period
        - Leave type priority
        - Advance notice given

        Args:
            leave_request: LeaveRequest instance

        Returns:
            dict: Approval recommendation with reasoning
        """
        from .models import LeaveRequest, Employee

        employee = leave_request.employee

        # Calculate leave duration
        leave_days = (leave_request.end_date - leave_request.start_date).days + 1

        # Check employee's leave balance (this year)
        year = timezone.now().year
        total_leave_taken = LeaveRequest.objects.filter(
            employee=employee,
            status='approved',
            start_date__year=year
        ).exclude(
            id=leave_request.id
        ).aggregate(
            total_days=Sum(
                F('end_date') - F('start_date') + 1
            )
        )['total_days'] or 0

        # Assume 20 days annual leave entitlement
        annual_leave_days = 20
        leave_balance_remaining = annual_leave_days - total_leave_taken - leave_days

        # Check department coverage
        overlapping_leaves = LeaveRequest.objects.filter(
            employee__department=employee.department,
            status='approved',
            start_date__lte=leave_request.end_date,
            end_date__gte=leave_request.start_date
        ).exclude(id=leave_request.id).count()

        department_size = Employee.objects.filter(
            department=employee.department,
            status='active'
        ).count()

        coverage_percentage = ((department_size - overlapping_leaves - 1) / department_size * 100) if department_size > 0 else 0

        # Initialize recommendation
        recommendation = {
            'decision': 'approve',
            'confidence': 0.0,
            'factors': [],
            'concerns': [],
            'conditions': []
        }

        # Factor 1: Leave balance
        if leave_balance_remaining >= 0:
            recommendation['factors'].append({
                'factor': 'Leave balance',
                'detail': f'Employee has adequate leave balance ({leave_balance_remaining} days remaining)',
                'weight': 0.3
            })
            recommendation['confidence'] += 0.3
        else:
            recommendation['concerns'].append({
                'concern': 'Insufficient leave balance',
                'detail': f'Exceeds annual entitlement by {abs(leave_balance_remaining)} days',
                'severity': 'high'
            })
            recommendation['confidence'] -= 0.3
            recommendation['decision'] = 'review_required'

        # Factor 2: Department coverage
        if coverage_percentage >= 70:
            recommendation['factors'].append({
                'factor': 'Department coverage',
                'detail': f'Adequate coverage ({coverage_percentage:.0f}% staffed)',
                'weight': 0.4
            })
            recommendation['confidence'] += 0.4
        elif coverage_percentage >= 50:
            recommendation['factors'].append({
                'factor': 'Department coverage',
                'detail': f'Acceptable coverage ({coverage_percentage:.0f}% staffed)',
                'weight': 0.2
            })
            recommendation['confidence'] += 0.2
        else:
            recommendation['concerns'].append({
                'concern': 'Low department coverage',
                'detail': f'Only {coverage_percentage:.0f}% staffed during requested period',
                'severity': 'high'
            })
            recommendation['confidence'] -= 0.3
            recommendation['decision'] = 'review_required'
            recommendation['conditions'].append(
                'Consider if dates can be adjusted for better coverage'
            )

        # Factor 3: Leave type priority
        high_priority_types = ['sick', 'maternity', 'paternity', 'emergency', 'bereavement']
        if leave_request.leave_type in high_priority_types:
            recommendation['factors'].append({
                'factor': 'Leave type priority',
                'detail': f'{leave_request.leave_type.title()} leave has high priority',
                'weight': 0.3
            })
            recommendation['confidence'] += 0.3
            recommendation['decision'] = 'approve'  # Override for high priority

        # Factor 4: Advance notice
        if leave_request.start_date > timezone.now().date():
            days_notice = (leave_request.start_date - timezone.now().date()).days
        else:
            days_notice = 0

        if days_notice >= 14:  # 2 weeks notice
            recommendation['factors'].append({
                'factor': 'Advance notice',
                'detail': f'Excellent advance notice ({days_notice} days)',
                'weight': 0.1
            })
            recommendation['confidence'] += 0.1
        elif days_notice >= 7:  # 1 week notice
            recommendation['factors'].append({
                'factor': 'Advance notice',
                'detail': f'Adequate advance notice ({days_notice} days)',
                'weight': 0.05
            })
            recommendation['confidence'] += 0.05
        elif days_notice < 3 and leave_request.leave_type not in high_priority_types:
            recommendation['concerns'].append({
                'concern': 'Short notice',
                'detail': f'Only {days_notice} days advance notice',
                'severity': 'medium'
            })
            recommendation['confidence'] -= 0.2

        # Final decision logic
        if recommendation['confidence'] < 0.3:
            recommendation['decision'] = 'manual_review'
            recommendation['reason'] = 'Multiple concerns detected - manager review required'
        elif recommendation['confidence'] >= 0.7:
            recommendation['decision'] = 'approve'
            recommendation['reason'] = 'Strong approval factors with minimal concerns'
        else:
            recommendation['decision'] = 'review_recommended'
            recommendation['reason'] = 'Mixed factors - manager discretion advised'

        return {
            'leave_request_id': str(leave_request.id),
            'employee_name': employee.user.full_name,
            'leave_details': {
                'type': leave_request.leave_type,
                'start_date': leave_request.start_date.isoformat(),
                'end_date': leave_request.end_date.isoformat(),
                'duration_days': leave_days,
                'advance_notice_days': days_notice
            },
            'leave_balance': {
                'annual_entitlement': annual_leave_days,
                'already_taken': total_leave_taken,
                'requested': leave_days,
                'remaining_after': leave_balance_remaining
            },
            'department_impact': {
                'department': employee.department.name if employee.department else 'N/A',
                'department_size': department_size,
                'overlapping_leaves': overlapping_leaves,
                'coverage_percentage': round(coverage_percentage, 1)
            },
            'recommendation': recommendation,
            'generated_at': timezone.now().isoformat()
        }

    @staticmethod
    def get_employee_insights(participant):
        """
        Get all AI insights for an employee (for unified dashboard).

        This method is called by the central AI coordinator to aggregate
        HR insights with other app insights.

        Args:
            participant: Participant instance (user)

        Returns:
            list: All HR insights for this employee
        """
        from .models import Employee

        # Check if this participant has employment records
        if not hasattr(participant, 'employment_records'):
            return []

        employee = participant.employment_records.filter(status='active').first()
        if not employee:
            return []

        insights = []

        # Get attendance insights
        try:
            attendance_analysis = HRAnalytics.analyze_attendance_patterns(employee, days=30)
            if attendance_analysis['patterns_detected'] > 0:
                insights.append({
                    'type': 'hr_attendance',
                    'category': 'Human Resources',
                    'title': f'{attendance_analysis["patterns_detected"]} Attendance Pattern(s) Detected',
                    'summary': f"Attendance rate: {attendance_analysis['attendance_summary']['attendance_rate']:.1f}%",
                    'data': attendance_analysis,
                    'priority': 'high' if attendance_analysis['overall_status'] == 'critical' else 'medium',
                    'action_required': attendance_analysis['overall_status'] in ['critical', 'needs_attention']
                })
        except Exception:
            pass  # Skip if no attendance data

        # Get churn risk insights
        try:
            churn_analysis = HRAnalytics.calculate_churn_risk(employee)
            if churn_analysis['churn_risk']['level'] in ['medium', 'high']:
                insights.append({
                    'type': 'hr_churn_risk',
                    'category': 'Human Resources',
                    'title': f'{churn_analysis["churn_risk"]["level"].title()} Employee Churn Risk',
                    'summary': f"Risk score: {churn_analysis['churn_risk']['score']}/100 - {len(churn_analysis['risk_factors'])} factors identified",
                    'data': churn_analysis,
                    'priority': 'critical' if churn_analysis['churn_risk']['level'] == 'high' else 'medium',
                    'action_required': True
                })
        except Exception:
            pass  # Skip if data unavailable

        # Get performance insights
        try:
            performance_analysis = HRAnalytics.analyze_performance_trend(employee)
            if performance_analysis.get('insights') and len(performance_analysis['insights']) > 0:
                insights.append({
                    'type': 'hr_performance',
                    'category': 'Human Resources',
                    'title': f'Performance Trend: {performance_analysis["trend_analysis"]["direction"].title()}',
                    'summary': performance_analysis['trend_analysis']['message'],
                    'data': performance_analysis,
                    'priority': 'high' if performance_analysis['trend_analysis']['direction'] == 'declining' else 'low',
                    'action_required': performance_analysis['trend_analysis']['direction'] == 'declining'
                })
        except Exception:
            pass  # Skip if not enough performance reviews

        return insights
