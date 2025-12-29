"""
Analytics Predictive AI Module
No LLM required - Uses statistical methods, linear regression, and time series analysis
"""
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q
from datetime import timedelta, datetime
from decimal import Decimal
import statistics
from core.models import Participant, Transaction
from appointments.models import Appointment
from prescriptions.models import Prescription
from .models import PlatformStatistics, UserGrowthMetrics, RevenueMetrics


class PredictiveAnalytics:
    """AI-powered predictive analytics using statistical methods"""

    @staticmethod
    def predict_user_growth(days_forward=30, historical_days=90):
        """
        Predict user growth using simple linear regression

        Args:
            days_forward: Number of days to forecast (default 30)
            historical_days: Days of historical data to analyze (default 90)

        Returns:
            dict: User growth predictions with trend analysis
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=historical_days)

        # Get historical user registration data
        daily_registrations = []
        current_date = start_date

        while current_date <= end_date:
            daily_count = Participant.objects.filter(
                created_at__date=current_date
            ).count()
            daily_registrations.append(daily_count)
            current_date += timedelta(days=1)

        if len(daily_registrations) < 7:
            return {
                'status': 'insufficient_data',
                'message': 'Not enough historical data for prediction (minimum 7 days required)'
            }

        # Calculate simple linear regression
        n = len(daily_registrations)
        x_values = list(range(n))

        mean_x = sum(x_values) / n
        mean_y = sum(daily_registrations) / n

        # Calculate slope (trend)
        numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, daily_registrations))
        denominator = sum((x - mean_x) ** 2 for x in x_values)

        slope = numerator / denominator if denominator != 0 else 0
        intercept = mean_y - (slope * mean_x)

        # Forecast future registrations
        forecast = []
        for day in range(1, days_forward + 1):
            predicted_value = slope * (n + day) + intercept
            predicted_value = max(0, round(predicted_value, 0))  # Can't have negative registrations
            forecast.append({
                'day': day,
                'predicted_registrations': int(predicted_value)
            })

        # Calculate trend strength
        if len(daily_registrations) > 1:
            variance = statistics.variance(daily_registrations)
            std_dev = statistics.stdev(daily_registrations)
        else:
            variance = 0
            std_dev = 0

        # Determine trend direction
        if slope > 0.5:
            trend = 'growing'
        elif slope < -0.5:
            trend = 'declining'
        else:
            trend = 'stable'

        # Current totals
        total_users = Participant.objects.filter(is_active=True).count()
        predicted_total = total_users + sum(f['predicted_registrations'] for f in forecast)

        # Calculate growth rate
        recent_30_days = sum(daily_registrations[-30:]) if len(daily_registrations) >= 30 else sum(daily_registrations)
        previous_30_days = sum(daily_registrations[-60:-30]) if len(daily_registrations) >= 60 else recent_30_days

        growth_rate = ((recent_30_days - previous_30_days) / previous_30_days * 100) if previous_30_days > 0 else 0

        return {
            'status': 'forecasted',
            'forecast_period_days': days_forward,
            'current_metrics': {
                'total_active_users': total_users,
                'avg_daily_registrations': round(mean_y, 1),
                'growth_rate_percent': round(growth_rate, 1),
                'trend': trend,
                'slope': round(slope, 2)
            },
            'predictions': {
                'total_new_users_forecast': sum(f['predicted_registrations'] for f in forecast),
                'projected_total_users': predicted_total,
                'daily_forecast': forecast[:7]  # First 7 days for display
            },
            'statistics': {
                'historical_variance': round(variance, 2),
                'historical_std_dev': round(std_dev, 2),
                'min_daily': min(daily_registrations),
                'max_daily': max(daily_registrations),
                'median_daily': statistics.median(daily_registrations)
            },
            'generated_at': timezone.now()
        }

    @staticmethod
    def forecast_revenue(days_forward=30, historical_days=90):
        """
        Forecast revenue using moving averages and trend detection

        Args:
            days_forward: Number of days to forecast (default 30)
            historical_days: Days of historical data to analyze (default 90)

        Returns:
            dict: Revenue forecast with confidence intervals
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=historical_days)

        # Get historical revenue data
        daily_revenue = []
        current_date = start_date

        while current_date <= end_date:
            day_revenue = Transaction.objects.filter(
                created_at__date=current_date,
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            daily_revenue.append(float(day_revenue))
            current_date += timedelta(days=1)

        if len(daily_revenue) < 7:
            return {
                'status': 'insufficient_data',
                'message': 'Not enough historical data for forecast (minimum 7 days required)'
            }

        # Calculate moving averages (7-day and 30-day)
        if len(daily_revenue) >= 7:
            ma_7 = sum(daily_revenue[-7:]) / 7
        else:
            ma_7 = sum(daily_revenue) / len(daily_revenue)

        if len(daily_revenue) >= 30:
            ma_30 = sum(daily_revenue[-30:]) / 30
        else:
            ma_30 = sum(daily_revenue) / len(daily_revenue)

        # Calculate trend using linear regression
        n = len(daily_revenue)
        x_values = list(range(n))

        mean_x = sum(x_values) / n
        mean_y = sum(daily_revenue) / n

        numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, daily_revenue))
        denominator = sum((x - mean_x) ** 2 for x in x_values)

        slope = numerator / denominator if denominator != 0 else 0
        intercept = mean_y - (slope * mean_x)

        # Forecast using trend + moving average
        forecast = []
        for day in range(1, days_forward + 1):
            # Use weighted combination of trend and moving average
            trend_prediction = slope * (n + day) + intercept
            ma_prediction = ma_7  # Use 7-day MA as baseline

            # 70% trend, 30% moving average
            predicted_value = (0.7 * trend_prediction) + (0.3 * ma_prediction)
            predicted_value = max(0, predicted_value)

            forecast.append({
                'day': day,
                'predicted_revenue': round(predicted_value, 2)
            })

        # Calculate statistics
        std_dev = statistics.stdev(daily_revenue) if len(daily_revenue) > 1 else 0

        # Determine trend health
        if slope > 0:
            revenue_trend = 'increasing'
        elif slope < -100:
            revenue_trend = 'declining'
        else:
            revenue_trend = 'stable'

        # Calculate growth rate
        recent_30_days = sum(daily_revenue[-30:]) if len(daily_revenue) >= 30 else sum(daily_revenue)
        previous_30_days = sum(daily_revenue[-60:-30]) if len(daily_revenue) >= 60 else recent_30_days

        growth_rate = ((recent_30_days - previous_30_days) / previous_30_days * 100) if previous_30_days > 0 else 0

        total_forecast = sum(f['predicted_revenue'] for f in forecast)

        return {
            'status': 'forecasted',
            'forecast_period_days': days_forward,
            'current_metrics': {
                'avg_daily_revenue': round(mean_y, 2),
                'ma_7_days': round(ma_7, 2),
                'ma_30_days': round(ma_30, 2),
                'revenue_trend': revenue_trend,
                'growth_rate_percent': round(growth_rate, 1)
            },
            'forecast': {
                'total_predicted_revenue': round(total_forecast, 2),
                'avg_daily_forecast': round(total_forecast / days_forward, 2),
                'daily_forecast': forecast[:7]  # First 7 days
            },
            'confidence_metrics': {
                'historical_std_dev': round(std_dev, 2),
                'variance': round(std_dev ** 2, 2),
                'prediction_confidence': 'high' if std_dev < mean_y * 0.3 else 'medium' if std_dev < mean_y * 0.6 else 'low'
            },
            'generated_at': timezone.now()
        }

    @staticmethod
    def predict_appointment_completion_rate(days_forward=30):
        """
        Predict appointment completion rates based on historical patterns

        Args:
            days_forward: Number of days to analyze (default 30)

        Returns:
            dict: Appointment completion rate predictions
        """
        end_date = timezone.now().date()
        start_date_90 = end_date - timedelta(days=90)
        start_date_30 = end_date - timedelta(days=30)

        # Get historical appointment data (last 90 days)
        total_appointments_90 = Appointment.objects.filter(
            appointment_date__gte=start_date_90,
            appointment_date__lte=end_date
        ).count()

        completed_appointments_90 = Appointment.objects.filter(
            appointment_date__gte=start_date_90,
            appointment_date__lte=end_date,
            status='completed'
        ).count()

        cancelled_appointments_90 = Appointment.objects.filter(
            appointment_date__gte=start_date_90,
            appointment_date__lte=end_date,
            status='cancelled'
        ).count()

        no_show_appointments_90 = Appointment.objects.filter(
            appointment_date__gte=start_date_90,
            appointment_date__lte=end_date,
            status='no_show'
        ).count()

        # Last 30 days for comparison
        total_appointments_30 = Appointment.objects.filter(
            appointment_date__gte=start_date_30,
            appointment_date__lte=end_date
        ).count()

        completed_appointments_30 = Appointment.objects.filter(
            appointment_date__gte=start_date_30,
            appointment_date__lte=end_date,
            status='completed'
        ).count()

        if total_appointments_90 == 0:
            return {
                'status': 'no_data',
                'message': 'No appointment data available for analysis'
            }

        # Calculate rates
        completion_rate_90 = (completed_appointments_90 / total_appointments_90 * 100) if total_appointments_90 > 0 else 0
        completion_rate_30 = (completed_appointments_30 / total_appointments_30 * 100) if total_appointments_30 > 0 else 0

        cancellation_rate_90 = (cancelled_appointments_90 / total_appointments_90 * 100) if total_appointments_90 > 0 else 0
        no_show_rate_90 = (no_show_appointments_90 / total_appointments_90 * 100) if total_appointments_90 > 0 else 0

        # Trend analysis
        if completion_rate_30 > completion_rate_90 + 5:
            trend = 'improving'
        elif completion_rate_30 < completion_rate_90 - 5:
            trend = 'declining'
        else:
            trend = 'stable'

        # Predict future appointments
        avg_daily_appointments = total_appointments_90 / 90
        predicted_appointments = avg_daily_appointments * days_forward

        # Predict future completion rate using weighted average (70% recent, 30% historical)
        predicted_completion_rate = (0.7 * completion_rate_30) + (0.3 * completion_rate_90)
        predicted_completed = (predicted_appointments * predicted_completion_rate) / 100

        # Analyze by day of week
        appointments_by_day = {}
        for i in range(7):
            day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][i]
            day_appointments = Appointment.objects.filter(
                appointment_date__gte=start_date_90,
                appointment_date__lte=end_date,
                appointment_date__week_day=i+2  # Django week_day: 1=Sunday, 2=Monday
            ).count()
            appointments_by_day[day_name] = day_appointments

        busiest_day = max(appointments_by_day.items(), key=lambda x: x[1])[0] if appointments_by_day else 'Unknown'

        return {
            'status': 'analyzed',
            'analysis_period_days': 90,
            'forecast_period_days': days_forward,
            'historical_metrics': {
                'total_appointments_90_days': total_appointments_90,
                'completed_appointments': completed_appointments_90,
                'cancelled_appointments': cancelled_appointments_90,
                'no_show_appointments': no_show_appointments_90,
                'completion_rate_percent': round(completion_rate_90, 1),
                'cancellation_rate_percent': round(cancellation_rate_90, 1),
                'no_show_rate_percent': round(no_show_rate_90, 1)
            },
            'recent_metrics': {
                'completion_rate_30_days': round(completion_rate_30, 1),
                'trend': trend
            },
            'predictions': {
                'predicted_appointments': round(predicted_appointments, 0),
                'predicted_completion_rate': round(predicted_completion_rate, 1),
                'predicted_completed_appointments': round(predicted_completed, 0),
                'predicted_cancellations': round((predicted_appointments * cancellation_rate_90) / 100, 0),
                'predicted_no_shows': round((predicted_appointments * no_show_rate_90) / 100, 0)
            },
            'patterns': {
                'busiest_day_of_week': busiest_day,
                'avg_daily_appointments': round(avg_daily_appointments, 1),
                'appointments_by_day': appointments_by_day
            },
            'recommendations': _generate_appointment_recommendations(
                completion_rate_90, cancellation_rate_90, no_show_rate_90, trend
            ),
            'generated_at': timezone.now()
        }

    @staticmethod
    def analyze_platform_usage_patterns(days=90):
        """
        Analyze platform usage patterns and identify trends

        Args:
            days: Number of days to analyze (default 90)

        Returns:
            dict: Platform usage patterns and insights
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # Analyze user activity by role
        role_activity = {}
        roles = ['patient', 'doctor', 'hospital', 'pharmacy', 'insurance_company']

        for role in roles:
            # Count active users (those with transactions or appointments)
            role_users = Participant.objects.filter(role=role, is_active=True).count()

            if role == 'patient':
                active_users = Participant.objects.filter(
                    role=role,
                    is_active=True
                ).filter(
                    Q(sender_transactions__created_at__gte=start_date) |
                    Q(patient_appointments__appointment_date__gte=start_date)
                ).distinct().count()
            elif role == 'doctor':
                active_users = Participant.objects.filter(
                    role=role,
                    is_active=True
                ).filter(
                    Q(receiver_transactions__created_at__gte=start_date) |
                    Q(doctor_appointments__appointment_date__gte=start_date)
                ).distinct().count()
            else:
                active_users = Participant.objects.filter(
                    role=role,
                    is_active=True,
                    receiver_transactions__created_at__gte=start_date
                ).distinct().count()

            activity_rate = (active_users / role_users * 100) if role_users > 0 else 0

            role_activity[role] = {
                'total_users': role_users,
                'active_users': active_users,
                'activity_rate_percent': round(activity_rate, 1),
                'inactive_users': role_users - active_users
            }

        # Analyze transaction patterns
        total_transactions = Transaction.objects.filter(
            created_at__gte=start_date
        ).count()

        completed_transactions = Transaction.objects.filter(
            created_at__gte=start_date,
            status='completed'
        ).count()

        transaction_success_rate = (completed_transactions / total_transactions * 100) if total_transactions > 0 else 0

        # Analyze peak usage hours (last 30 days)
        hour_distribution = {}
        recent_transactions = Transaction.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        )

        for hour in range(24):
            hour_count = recent_transactions.filter(
                created_at__hour=hour
            ).count()
            hour_distribution[f"{hour:02d}:00"] = hour_count

        peak_hour = max(hour_distribution.items(), key=lambda x: x[1])[0] if hour_distribution else 'Unknown'

        # Calculate engagement score (0-100)
        overall_users = Participant.objects.filter(is_active=True).count()
        overall_active = sum(data['active_users'] for data in role_activity.values())
        overall_activity_rate = (overall_active / overall_users * 100) if overall_users > 0 else 0

        engagement_score = min(100, (
            (overall_activity_rate * 0.4) +
            (transaction_success_rate * 0.3) +
            (min(100, (total_transactions / days) * 0.3))  # Transaction frequency
        ))

        # Determine platform health
        if engagement_score >= 80:
            platform_health = 'excellent'
        elif engagement_score >= 60:
            platform_health = 'good'
        elif engagement_score >= 40:
            platform_health = 'fair'
        else:
            platform_health = 'needs_improvement'

        return {
            'status': 'analyzed',
            'analysis_period_days': days,
            'engagement_metrics': {
                'engagement_score': round(engagement_score, 1),
                'platform_health': platform_health,
                'overall_activity_rate': round(overall_activity_rate, 1),
                'total_active_users': overall_active,
                'total_registered_users': overall_users
            },
            'role_activity': role_activity,
            'transaction_metrics': {
                'total_transactions': total_transactions,
                'completed_transactions': completed_transactions,
                'success_rate_percent': round(transaction_success_rate, 1),
                'avg_daily_transactions': round(total_transactions / days, 1)
            },
            'usage_patterns': {
                'peak_hour': peak_hour,
                'hourly_distribution': hour_distribution
            },
            'recommendations': _generate_usage_recommendations(
                engagement_score, role_activity, transaction_success_rate
            ),
            'generated_at': timezone.now()
        }

    @staticmethod
    def get_predictive_insights():
        """
        Get all predictive analytics insights for unified dashboard

        Returns:
            list: All analytics insights with priority levels
        """
        insights = []

        # User growth insights
        user_growth = PredictiveAnalytics.predict_user_growth(days_forward=30)
        if user_growth['status'] == 'forecasted':
            trend = user_growth['current_metrics']['trend']
            growth_rate = user_growth['current_metrics']['growth_rate_percent']

            priority = 'high' if trend == 'declining' else 'medium' if growth_rate < 5 else 'low'

            insights.append({
                'type': 'user_growth_forecast',
                'priority': priority,
                'title': f"User Growth: {trend.title()} ({growth_rate:+.1f}%)",
                'description': f"Predicted {user_growth['predictions']['total_new_users_forecast']} new users in next 30 days",
                'data': user_growth,
                'module': 'analytics'
            })

        # Revenue forecast insights
        revenue_forecast = PredictiveAnalytics.forecast_revenue(days_forward=30)
        if revenue_forecast['status'] == 'forecasted':
            revenue_trend = revenue_forecast['current_metrics']['revenue_trend']
            total_forecast = revenue_forecast['forecast']['total_predicted_revenue']

            priority = 'high' if revenue_trend == 'declining' else 'low'

            insights.append({
                'type': 'revenue_forecast',
                'priority': priority,
                'title': f"Revenue Forecast: ${total_forecast:,.2f} (30 days)",
                'description': f"Revenue trend is {revenue_trend}",
                'data': revenue_forecast,
                'module': 'analytics'
            })

        # Appointment completion insights
        appointment_analysis = PredictiveAnalytics.predict_appointment_completion_rate()
        if appointment_analysis['status'] == 'analyzed':
            completion_rate = appointment_analysis['historical_metrics']['completion_rate_percent']
            trend = appointment_analysis['recent_metrics']['trend']

            priority = 'high' if completion_rate < 70 or trend == 'declining' else 'medium' if completion_rate < 85 else 'low'

            insights.append({
                'type': 'appointment_completion',
                'priority': priority,
                'title': f"Appointment Completion: {completion_rate:.1f}% ({trend})",
                'description': appointment_analysis['recommendations'][0] if appointment_analysis['recommendations'] else 'Completion rate within normal range',
                'data': appointment_analysis,
                'module': 'analytics'
            })

        # Platform usage insights
        usage_patterns = PredictiveAnalytics.analyze_platform_usage_patterns()
        if usage_patterns['status'] == 'analyzed':
            engagement_score = usage_patterns['engagement_metrics']['engagement_score']
            platform_health = usage_patterns['engagement_metrics']['platform_health']

            priority = 'high' if engagement_score < 40 else 'medium' if engagement_score < 70 else 'low'

            insights.append({
                'type': 'platform_engagement',
                'priority': priority,
                'title': f"Platform Engagement: {engagement_score:.0f}/100 ({platform_health})",
                'description': f"{usage_patterns['engagement_metrics']['total_active_users']} active users out of {usage_patterns['engagement_metrics']['total_registered_users']}",
                'data': usage_patterns,
                'module': 'analytics'
            })

        return insights


def _generate_appointment_recommendations(completion_rate, cancellation_rate, no_show_rate, trend):
    """Generate recommendations based on appointment metrics"""
    recommendations = []

    if completion_rate < 70:
        recommendations.append("CRITICAL: Low completion rate. Implement appointment reminder system.")
    elif completion_rate < 85:
        recommendations.append("Consider implementing automated appointment confirmations.")

    if cancellation_rate > 20:
        recommendations.append("HIGH: High cancellation rate. Review cancellation policies and reasons.")

    if no_show_rate > 15:
        recommendations.append("Implement no-show penalties or deposit system to reduce no-shows.")

    if trend == 'declining':
        recommendations.append("WARNING: Completion rate is declining. Investigate causes immediately.")
    elif trend == 'improving':
        recommendations.append("Positive trend detected. Continue current appointment management practices.")

    if not recommendations:
        recommendations.append("Appointment completion metrics are healthy. Maintain current standards.")

    return recommendations


def _generate_usage_recommendations(engagement_score, role_activity, transaction_success_rate):
    """Generate recommendations based on platform usage patterns"""
    recommendations = []

    if engagement_score < 40:
        recommendations.append("CRITICAL: Low engagement score. Launch user engagement campaigns.")
    elif engagement_score < 70:
        recommendations.append("Moderate engagement. Consider incentive programs to boost activity.")

    # Check for role-specific issues
    for role, data in role_activity.items():
        if data['activity_rate_percent'] < 30 and data['total_users'] > 10:
            recommendations.append(f"Low activity among {role}s ({data['activity_rate_percent']:.1f}%). Target re-engagement campaigns.")

    if transaction_success_rate < 80:
        recommendations.append("Transaction success rate below optimal. Review payment processing reliability.")

    if not recommendations:
        recommendations.append("Platform usage is healthy. Focus on maintaining current engagement levels.")

    return recommendations
