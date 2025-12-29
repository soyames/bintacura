"""
Advanced Revenue Forecasting using Linear Regression with Seasonality
Lightweight model - calculated on-the-fly, no model persistence
"""
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from django.utils import timezone
from datetime import timedelta, date
import numpy as np


class AdvancedRevenueForecast:
    """
    Advanced revenue forecasting using Linear Regression with seasonal components
    More sophisticated than simple moving averages
    """

    @staticmethod
    def forecast_revenue(organization, days_forward=30, historical_days=180):
        """
        Forecast revenue using ML with seasonal adjustment

        Args:
            organization: Organization to forecast for
            days_forward: Days to forecast (default 30)
            historical_days: Historical period to analyze (default 180)

        Returns:
            dict: Revenue forecast with confidence intervals
        """
        from core.models import Transaction

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=historical_days)

        # Collect daily revenue data
        daily_revenue = {}
        current_date = start_date

        while current_date <= end_date:
            day_revenue = Transaction.objects.filter(
                receiver=organization,
                status='completed',
                created_at__date=current_date
            ).aggregate(total=models.Sum('amount'))['total'] or 0

            daily_revenue[current_date] = float(day_revenue)
            current_date += timedelta(days=1)

        if len(daily_revenue) < 30:
            return {
                'status': 'insufficient_data',
                'message': 'Need at least 30 days of revenue data for ML forecasting'
            }

        # Prepare features for ML model
        X = []  # Features: [day_number, day_of_week, day_of_month, is_weekend]
        y = []  # Target: revenue

        dates = sorted(daily_revenue.keys())
        for i, date_key in enumerate(dates):
            day_of_week = date_key.weekday()  # 0 = Monday, 6 = Sunday
            day_of_month = date_key.day
            is_weekend = 1 if day_of_week >= 5 else 0
            is_month_end = 1 if day_of_month >= 25 else 0

            X.append([
                i,  # Sequential day number (trend)
                day_of_week,  # Seasonal: day of week
                day_of_month,  # Seasonal: day of month
                is_weekend,  # Binary: weekend effect
                is_month_end  # Binary: month-end effect
            ])
            y.append(daily_revenue[date_key])

        # Convert to numpy arrays
        X = np.array(X)
        y = np.array(y)

        # Train Linear Regression model
        model = LinearRegression()
        model.fit(X, y)

        # Calculate model performance
        y_pred_train = model.predict(X)
        residuals = y - y_pred_train
        rmse = np.sqrt(np.mean(residuals ** 2))
        mae = np.mean(np.abs(residuals))

        # Generate forecast for next N days
        forecast_dates = []
        forecast_values = []
        last_day_number = len(dates)

        for day in range(1, days_forward + 1):
            forecast_date = end_date + timedelta(days=day)
            day_of_week = forecast_date.weekday()
            day_of_month = forecast_date.day
            is_weekend = 1 if day_of_week >= 5 else 0
            is_month_end = 1 if day_of_month >= 25 else 0

            X_forecast = np.array([[
                last_day_number + day,
                day_of_week,
                day_of_month,
                is_weekend,
                is_month_end
            ]])

            predicted_revenue = model.predict(X_forecast)[0]
            predicted_revenue = max(0, predicted_revenue)  # Can't have negative revenue

            forecast_dates.append(forecast_date)
            forecast_values.append(predicted_revenue)

        # Calculate confidence intervals (±1.96 * RMSE for 95% CI)
        confidence_interval = 1.96 * rmse

        # Detect trend
        recent_30_days = y[-30:]
        previous_30_days = y[-60:-30] if len(y) >= 60 else y[:30]
        trend_change = (np.mean(recent_30_days) - np.mean(previous_30_days)) / np.mean(previous_30_days) * 100 if np.mean(previous_30_days) > 0 else 0

        if trend_change > 5:
            trend = 'increasing'
        elif trend_change < -5:
            trend = 'decreasing'
        else:
            trend = 'stable'

        # Calculate total forecast
        total_forecast = sum(forecast_values)

        # Daily forecast breakdown (first 7 days)
        daily_forecast = []
        for i in range(min(7, len(forecast_dates))):
            daily_forecast.append({
                'date': forecast_dates[i].strftime('%Y-%m-%d'),
                'predicted_revenue': round(forecast_values[i], 2),
                'lower_bound': round(max(0, forecast_values[i] - confidence_interval), 2),
                'upper_bound': round(forecast_values[i] + confidence_interval, 2)
            })

        return {
            'status': 'forecasted',
            'model_type': 'Linear Regression with Seasonality',
            'forecast_period_days': days_forward,
            'historical_period_days': historical_days,
            'current_metrics': {
                'avg_daily_revenue': round(np.mean(y), 2),
                'trend': trend,
                'trend_change_percent': round(trend_change, 1),
                'last_30_days_avg': round(np.mean(recent_30_days), 2)
            },
            'forecast_summary': {
                'total_predicted_revenue': round(total_forecast, 2),
                'avg_daily_forecast': round(total_forecast / days_forward, 2),
                'confidence_interval_95': round(confidence_interval, 2)
            },
            'daily_forecast': daily_forecast,
            'model_performance': {
                'rmse': round(rmse, 2),
                'mae': round(mae, 2),
                'r_squared': round(model.score(X, y), 3)
            },
            'feature_importance': {
                'trend_coefficient': round(model.coef_[0], 4),
                'day_of_week_coefficient': round(model.coef_[1], 4),
                'weekend_effect': round(model.coef_[3], 2),
                'month_end_effect': round(model.coef_[4], 2)
            },
            'generated_at': timezone.now()
        }

    @staticmethod
    def compare_with_baseline(organization, days_forward=30):
        """
        Compare ML forecast with simple baseline (moving average)

        Args:
            organization: Organization
            days_forward: Forecast period

        Returns:
            dict: Comparison of ML vs baseline forecast
        """
        from analytics.predictive_analytics import PredictiveAnalytics

        # Get ML forecast
        ml_forecast = AdvancedRevenueForecast.forecast_revenue(organization, days_forward)

        if ml_forecast['status'] != 'forecasted':
            return ml_forecast

        # Get baseline forecast (from predictive_analytics.py)
        baseline_forecast = PredictiveAnalytics.forecast_revenue(organization, days_forward)

        if baseline_forecast['status'] != 'forecasted':
            return {
                'status': 'comparison_unavailable',
                'ml_forecast': ml_forecast
            }

        # Compare
        ml_total = ml_forecast['forecast_summary']['total_predicted_revenue']
        baseline_total = baseline_forecast['forecast']['total_predicted_revenue']

        difference = ml_total - baseline_total
        difference_percent = (difference / baseline_total * 100) if baseline_total > 0 else 0

        return {
            'status': 'compared',
            'ml_forecast_total': round(ml_total, 2),
            'baseline_forecast_total': round(baseline_total, 2),
            'difference': round(difference, 2),
            'difference_percent': round(difference_percent, 1),
            'recommendation': _get_forecast_recommendation(ml_forecast, baseline_forecast),
            'ml_details': ml_forecast,
            'baseline_details': baseline_forecast,
            'generated_at': timezone.now()
        }


def _get_forecast_recommendation(ml_forecast, baseline_forecast):
    """Generate recommendation based on forecast comparison"""
    ml_trend = ml_forecast['current_metrics']['trend']
    ml_r_squared = ml_forecast['model_performance']['r_squared']

    if ml_r_squared > 0.7:
        confidence = 'high'
    elif ml_r_squared > 0.5:
        confidence = 'medium'
    else:
        confidence = 'low'

    if ml_trend == 'increasing':
        recommendation = f"Revenue trending upward. {confidence.title()} confidence in ML forecast. Consider capacity expansion."
    elif ml_trend == 'decreasing':
        recommendation = f"Revenue trending downward. {confidence.title()} confidence in ML forecast. Review pricing and marketing strategy."
    else:
        recommendation = f"Revenue stable. {confidence.title()} confidence in ML forecast. Maintain current operations."

    return recommendation


# Import django models for the forecast_revenue function
from django.db import models
