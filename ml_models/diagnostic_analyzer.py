"""
Diagnostic Interpretation ML Model using Pattern Recognition and Clustering
Lightweight model - calculated on-the-fly, no model persistence
Phase 11: Added caching for improved performance
"""
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from django.utils import timezone
from datetime import timedelta
import numpy as np

# Import caching utilities
try:
    from ai.cache_utils import cache_ai_result
except ImportError:
    # Fallback if caching not available
    def cache_ai_result(prefix, timeout=None, participant_param='participant'):
        def decorator(func):
            return func
        return decorator


class DiagnosticAnalyzer:
    """
    AI-powered diagnostic interpretation for patients
    Analyzes diagnosis patterns, severity, and trends
    """

    @staticmethod
    @cache_ai_result('diagnostic_analysis', timeout=1800, participant_param='patient')
    def analyze_patient_diagnostics(patient, days_back=365):
        """
        Comprehensive diagnostic analysis for a patient
        Cached for 30 minutes for improved performance

        Args:
            patient: Patient Participant object
            days_back: Historical period to analyze (default 365 days)

        Returns:
            dict: Diagnostic insights with patterns and recommendations
        """
        from health_records.models import HealthRecord

        cutoff_date = timezone.now().date() - timedelta(days=days_back)

        # Get diagnostic records
        diagnostics = HealthRecord.objects.filter(
            assigned_to=patient,
            type='diagnosis',
            date_of_record__gte=cutoff_date
        ).order_by('-date_of_record')

        if not diagnostics.exists():
            return {
                'status': 'no_data',
                'message': 'No diagnostic records found for analysis'
            }

        # Extract diagnostic patterns
        diagnosis_list = []
        symptom_list = []
        treatment_list = []
        severity_scores = []

        for record in diagnostics:
            if record.diagnosis:
                diagnosis_list.append(record.diagnosis.lower())

            if record.symptoms:
                symptoms = record.symptoms.lower().split(',')
                symptom_list.extend([s.strip() for s in symptoms])

            if record.treatment:
                treatment_list.append(record.treatment.lower())

            # Calculate severity score based on keywords
            severity = DiagnosticAnalyzer._calculate_severity_score(record)
            severity_scores.append(severity)

        # Frequency analysis
        from collections import Counter
        diagnosis_freq = Counter(diagnosis_list)
        symptom_freq = Counter(symptom_list)

        # Identify patterns
        chronic_conditions = []
        acute_conditions = []

        for diagnosis, count in diagnosis_freq.most_common(10):
            if count >= 2:  # Recurring diagnosis
                chronic_conditions.append({
                    'diagnosis': diagnosis,
                    'occurrences': count,
                    'type': 'chronic'
                })
            else:
                acute_conditions.append({
                    'diagnosis': diagnosis,
                    'occurrences': count,
                    'type': 'acute'
                })

        # Calculate overall health risk score
        avg_severity = np.mean(severity_scores) if severity_scores else 0
        health_risk_score = min(100, avg_severity * 10)  # Scale to 0-100

        # Determine risk level
        if health_risk_score >= 70:
            risk_level = 'high'
            risk_color = 'red'
        elif health_risk_score >= 40:
            risk_level = 'medium'
            risk_color = 'orange'
        else:
            risk_level = 'low'
            risk_color = 'green'

        # Generate recommendations
        recommendations = DiagnosticAnalyzer._generate_diagnostic_recommendations(
            chronic_conditions,
            acute_conditions,
            avg_severity,
            symptom_freq
        )

        return {
            'status': 'analyzed',
            'patient_id': str(patient.id),
            'analysis_period_days': days_back,
            'total_diagnostic_records': diagnostics.count(),
            'health_risk_score': round(health_risk_score, 1),
            'risk_level': risk_level,
            'risk_color': risk_color,
            'avg_severity': round(avg_severity, 2),
            'chronic_conditions': chronic_conditions[:5],  # Top 5
            'acute_conditions': acute_conditions[:5],  # Top 5
            'common_symptoms': [
                {'symptom': symptom, 'frequency': freq}
                for symptom, freq in symptom_freq.most_common(10)
            ],
            'recommendations': recommendations,
            'generated_at': timezone.now()
        }

    @staticmethod
    def _calculate_severity_score(record):
        """
        Calculate severity score based on diagnosis and symptoms keywords
        Returns: float 0.0-10.0
        """
        severity = 3.0  # Default medium severity

        # High severity keywords
        high_severity_keywords = [
            'cancer', 'tumor', 'malignant', 'stroke', 'heart attack',
            'myocardial infarction', 'sepsis', 'pneumonia', 'covid',
            'critical', 'severe', 'emergency', 'acute', 'chronic'
        ]

        # Low severity keywords
        low_severity_keywords = [
            'mild', 'minor', 'common cold', 'headache', 'flu',
            'allergy', 'routine', 'checkup'
        ]

        diagnosis_text = (record.diagnosis + ' ' + record.symptoms + ' ' + record.treatment).lower()

        # Check for high severity
        for keyword in high_severity_keywords:
            if keyword in diagnosis_text:
                severity += 2.0

        # Check for low severity
        for keyword in low_severity_keywords:
            if keyword in diagnosis_text:
                severity -= 1.0

        return max(0.0, min(10.0, severity))  # Clamp to 0-10

    @staticmethod
    def _generate_diagnostic_recommendations(chronic_conditions, acute_conditions, avg_severity, symptom_freq):
        """Generate personalized recommendations based on diagnostic analysis"""
        recommendations = []

        if chronic_conditions:
            recommendations.append({
                'priority': 'high',
                'title': 'Chronic Condition Management',
                'description': f'You have {len(chronic_conditions)} chronic condition(s). Regular monitoring and treatment adherence are essential.',
                'action': 'Schedule regular follow-up appointments with your healthcare provider.'
            })

        if avg_severity >= 7:
            recommendations.append({
                'priority': 'high',
                'title': 'High Severity Alert',
                'description': 'Recent diagnoses show high severity. Immediate medical attention may be required.',
                'action': 'Consult with a specialist for comprehensive evaluation.'
            })

        if symptom_freq:
            top_symptoms = [s for s, _ in symptom_freq.most_common(3)]
            recommendations.append({
                'priority': 'medium',
                'title': 'Common Symptoms Detected',
                'description': f'Most frequent symptoms: {", ".join(top_symptoms)}',
                'action': 'Discuss symptom management strategies with your doctor.'
            })

        if not chronic_conditions and avg_severity < 4:
            recommendations.append({
                'priority': 'low',
                'title': 'Good Health Status',
                'description': 'Your diagnostic history shows relatively good health.',
                'action': 'Continue preventive care and regular checkups.'
            })

        return recommendations

    @staticmethod
    @cache_ai_result('lab_interpretation', timeout=1800, participant_param='patient')
    def interpret_lab_results(patient, days_back=90):
        """
        Interpret lab results and detect abnormal patterns
        Cached for 30 minutes for improved performance

        Args:
            patient: Patient Participant object
            days_back: Historical period to analyze (default 90 days)

        Returns:
            dict: Lab result interpretation with trends
        """
        from health_records.models import HealthRecord

        cutoff_date = timezone.now().date() - timedelta(days=days_back)

        lab_results = HealthRecord.objects.filter(
            assigned_to=patient,
            type='lab_result',
            date_of_record__gte=cutoff_date
        ).order_by('-date_of_record')

        if not lab_results.exists():
            return {
                'status': 'no_data',
                'message': 'No lab results found for analysis'
            }

        # Analyze lab trends
        abnormal_findings = []
        normal_findings = []

        abnormal_keywords = [
            'abnormal', 'elevated', 'low', 'high', 'critical',
            'deficient', 'excess', 'out of range'
        ]

        for lab in lab_results:
            lab_text = (lab.title + ' ' + lab.diagnosis + ' ' + lab.notes).lower()

            is_abnormal = any(keyword in lab_text for keyword in abnormal_keywords)

            if is_abnormal:
                abnormal_findings.append({
                    'date': lab.date_of_record.strftime('%Y-%m-%d'),
                    'title': lab.title,
                    'finding': lab.diagnosis or lab.notes[:100]
                })
            else:
                normal_findings.append({
                    'date': lab.date_of_record.strftime('%Y-%m-%d'),
                    'title': lab.title
                })

        # Calculate abnormality rate
        total_labs = lab_results.count()
        abnormal_count = len(abnormal_findings)
        abnormality_rate = (abnormal_count / total_labs * 100) if total_labs > 0 else 0

        # Generate interpretation
        if abnormality_rate >= 50:
            interpretation = 'High number of abnormal lab results detected. Immediate medical consultation recommended.'
            priority = 'high'
        elif abnormality_rate >= 25:
            interpretation = 'Some abnormal lab results found. Follow up with your healthcare provider.'
            priority = 'medium'
        else:
            interpretation = 'Most lab results are within normal range.'
            priority = 'low'

        return {
            'status': 'interpreted',
            'patient_id': str(patient.id),
            'analysis_period_days': days_back,
            'total_lab_results': total_labs,
            'abnormal_count': abnormal_count,
            'normal_count': len(normal_findings),
            'abnormality_rate': round(abnormality_rate, 1),
            'priority': priority,
            'interpretation': interpretation,
            'abnormal_findings': abnormal_findings[:10],  # Top 10 most recent
            'generated_at': timezone.now()
        }

    @staticmethod
    @cache_ai_result('health_risk_prediction', timeout=3600, participant_param='patient')
    def predict_health_risks(patient):
        """
        Predict health risks based on diagnostic and lab history
        Uses pattern recognition to identify potential future health issues
        Cached for 1 hour for improved performance

        Args:
            patient: Patient Participant object

        Returns:
            dict: Predicted health risks and preventive recommendations
        """
        # Get diagnostic analysis
        diagnostic_analysis = DiagnosticAnalyzer.analyze_patient_diagnostics(patient)

        if diagnostic_analysis['status'] != 'analyzed':
            return diagnostic_analysis

        # Get lab result interpretation
        lab_analysis = DiagnosticAnalyzer.interpret_lab_results(patient)

        # Combine risk factors
        risk_factors = []
        predicted_risks = []

        # Chronic conditions increase risk
        if diagnostic_analysis.get('chronic_conditions'):
            risk_factors.append('Multiple chronic conditions detected')
            predicted_risks.append({
                'risk': 'Disease Progression',
                'probability': 'Medium to High',
                'prevention': 'Regular monitoring and treatment adherence'
            })

        # High severity patterns
        if diagnostic_analysis.get('avg_severity', 0) >= 6:
            risk_factors.append('High severity diagnostic patterns')
            predicted_risks.append({
                'risk': 'Complications',
                'probability': 'Medium',
                'prevention': 'Specialist consultation and proactive management'
            })

        # Abnormal lab results
        if lab_analysis.get('status') == 'interpreted' and lab_analysis.get('abnormality_rate', 0) >= 30:
            risk_factors.append('Elevated abnormal lab result rate')
            predicted_risks.append({
                'risk': 'Metabolic or Systemic Issues',
                'probability': 'Medium',
                'prevention': 'Comprehensive health screening and lifestyle modifications'
            })

        # Calculate overall risk score
        risk_score = 0
        if diagnostic_analysis.get('health_risk_score', 0) >= 50:
            risk_score += 30
        if lab_analysis.get('abnormality_rate', 0) >= 30:
            risk_score += 30
        if len(diagnostic_analysis.get('chronic_conditions', [])) >= 2:
            risk_score += 40

        risk_score = min(100, risk_score)

        return {
            'status': 'predicted',
            'patient_id': str(patient.id),
            'overall_risk_score': risk_score,
            'risk_level': 'high' if risk_score >= 60 else 'medium' if risk_score >= 30 else 'low',
            'risk_factors': risk_factors,
            'predicted_risks': predicted_risks,
            'diagnostic_summary': diagnostic_analysis,
            'lab_summary': lab_analysis,
            'generated_at': timezone.now()
        }
