"""
Enhanced Employee Churn Prediction using Logistic Regression
Lightweight model - calculated on-the-fly, no model persistence
"""
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from django.utils import timezone
from datetime import timedelta
import numpy as np


class ChurnPredictor:
    """
    Predicts employee churn using Logistic Regression
    More sophisticated than rule-based approach in hr/ai_insights.py
    """

    @staticmethod
    def train_and_predict(organization):
        """
        Train churn prediction model and predict for all employees

        Args:
            organization: Organization to analyze

        Returns:
            dict: Churn predictions with probabilities
        """
        from hr.models import Employee, Attendance, PerformanceReview, LeaveRequest
        from core.models import Payroll

        employees = Employee.objects.filter(
            organization=organization,
            status='active'
        )

        if employees.count() < 10:
            return {
                'status': 'insufficient_data',
                'message': 'Need at least 10 employees for ML churn prediction'
            }

        # Prepare training data
        X = []  # Features
        y = []  # Labels (1 = churned, 0 = stayed) - we'll use proxy indicators
        employee_data = []
        lookback_days = 90

        start_date = timezone.now() - timedelta(days=lookback_days)

        for employee in employees[:100]:  # Limit to 100 to avoid memory issues
            user = employee.user

            # Feature 1: Tenure (days since joining)
            tenure_days = (timezone.now().date() - employee.joining_date).days if employee.joining_date else 0

            # Feature 2: Attendance rate
            total_attendance = Attendance.objects.filter(
                employee=user,
                date__gte=start_date
            ).count()
            present_attendance = Attendance.objects.filter(
                employee=user,
                date__gte=start_date,
                status='present'
            ).count()
            attendance_rate = (present_attendance / total_attendance * 100) if total_attendance > 0 else 100

            # Feature 3: Performance score (average of recent reviews)
            recent_reviews = PerformanceReview.objects.filter(
                employee=user,
                review_date__gte=start_date - timedelta(days=180)
            ).order_by('-review_date')[:3]
            avg_performance = np.mean([r.overall_rating for r in recent_reviews]) if recent_reviews.exists() else 3.0

            # Feature 4: Leave request frequency
            leave_count = LeaveRequest.objects.filter(
                employee=user,
                start_date__gte=start_date
            ).count()

            # Feature 5: Payroll issues (late/failed payments)
            payroll_issues = Payroll.objects.filter(
                employee=user,
                status__in=['failed', 'pending'],
                created_at__gte=start_date
            ).count()

            # Feature 6: Employment type (0 = permanent, 1 = temporary)
            is_temporary = 1 if employee.employment_type in ['temporary', 'contract'] else 0

            # Create feature vector
            features = [
                tenure_days,
                attendance_rate,
                avg_performance,
                leave_count,
                payroll_issues,
                is_temporary
            ]

            X.append(features)

            # Label (proxy): High risk indicators
            # If tenure < 180 days AND (attendance < 85% OR performance < 2.5 OR leave_count > 5)
            is_high_risk = (
                (tenure_days < 180 and (attendance_rate < 85 or avg_performance < 2.5 or leave_count > 5)) or
                (payroll_issues > 2)
            )
            y.append(1 if is_high_risk else 0)

            employee_data.append({
                'employee_id': str(employee.user.uid),
                'employee_name': employee.user.full_name,
                'features': features
            })

        if len(X) < 10:
            return {
                'status': 'insufficient_data',
                'message': 'Insufficient employee data for ML prediction'
            }

        # Convert to numpy arrays
        X = np.array(X)
        y = np.array(y)

        # Check if we have both classes
        if len(np.unique(y)) < 2:
            # All employees in same class, use rule-based fallback
            return {
                'status': 'homogeneous_data',
                'message': 'All employees have similar risk profile. Using statistical analysis instead.',
                'high_risk_count': int(y.sum()),
                'low_risk_count': int(len(y) - y.sum())
            }

        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Train Logistic Regression model
        model = LogisticRegression(random_state=42, max_iter=1000)
        model.fit(X_scaled, y)

        # Predict churn probabilities
        churn_probabilities = model.predict_proba(X_scaled)[:, 1]  # Probability of class 1 (churn)
        predictions = model.predict(X_scaled)

        # Compile results
        prediction_results = []
        for i, emp_data in enumerate(employee_data):
            churn_prob = float(churn_probabilities[i])
            prediction = int(predictions[i])

            # Determine risk level based on probability
            if churn_prob > 0.7:
                risk_level = 'critical'
            elif churn_prob > 0.5:
                risk_level = 'high'
            elif churn_prob > 0.3:
                risk_level = 'medium'
            else:
                risk_level = 'low'

            prediction_results.append({
                'employee_id': emp_data['employee_id'],
                'employee_name': emp_data['employee_name'],
                'churn_probability': round(churn_prob * 100, 1),
                'risk_level': risk_level,
                'prediction': 'likely_to_churn' if prediction == 1 else 'likely_to_stay'
            })

        # Sort by churn probability (descending)
        prediction_results.sort(key=lambda x: x['churn_probability'], reverse=True)

        # Calculate statistics
        high_risk_count = sum(1 for p in prediction_results if p['risk_level'] in ['critical', 'high'])
        critical_count = sum(1 for p in prediction_results if p['risk_level'] == 'critical')

        # Get top 10 at-risk employees
        top_at_risk = prediction_results[:10]

        return {
            'status': 'predicted',
            'model_type': 'Logistic Regression',
            'total_employees_analyzed': len(employee_data),
            'high_risk_count': high_risk_count,
            'critical_risk_count': critical_count,
            'model_accuracy': 'N/A (unsupervised proxy labels)',
            'top_at_risk_employees': top_at_risk,
            'all_predictions': prediction_results,
            'recommendations': _generate_churn_recommendations(critical_count, high_risk_count, len(employee_data)),
            'generated_at': timezone.now()
        }

    @staticmethod
    def predict_single_employee(employee):
        """
        Predict churn for a single employee

        Args:
            employee: Employee object

        Returns:
            dict: Churn prediction for the employee
        """
        # Run full prediction and filter for this employee
        org_predictions = ChurnPredictor.train_and_predict(employee.organization)

        if org_predictions['status'] != 'predicted':
            return org_predictions

        # Find this employee in results
        employee_id = str(employee.user.uid)
        for pred in org_predictions['all_predictions']:
            if pred['employee_id'] == employee_id:
                return {
                    'status': 'predicted',
                    'employee_prediction': pred,
                    'organization_context': {
                        'total_high_risk': org_predictions['high_risk_count'],
                        'total_employees': org_predictions['total_employees_analyzed']
                    }
                }

        return {
            'status': 'not_found',
            'message': 'Employee not found in prediction results'
        }


def _generate_churn_recommendations(critical_count, high_risk_count, total_employees):
    """Generate recommendations based on churn predictions"""
    recommendations = []

    if critical_count > 0:
        recommendations.append({
            'priority': 'critical',
            'title': f'{critical_count} Employees at Critical Churn Risk',
            'actions': [
                'Schedule immediate 1-on-1 meetings with management',
                'Review compensation and benefits',
                'Identify and address immediate concerns',
                'Consider retention bonuses or promotions'
            ]
        })

    if high_risk_count > total_employees * 0.2:
        recommendations.append({
            'priority': 'high',
            'title': f'High Overall Churn Risk ({high_risk_count} employees)',
            'actions': [
                'Review organizational culture and work environment',
                'Conduct employee satisfaction survey',
                'Improve onboarding and training programs',
                'Enhance career development opportunities'
            ]
        })

    if critical_count == 0 and high_risk_count < total_employees * 0.1:
        recommendations.append({
            'priority': 'low',
            'title': 'Low Churn Risk - Maintain Current Practices',
            'actions': [
                'Continue current retention strategies',
                'Monitor employee satisfaction regularly',
                'Recognize and reward good performance'
            ]
        })

    return recommendations
