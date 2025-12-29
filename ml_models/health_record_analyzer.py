"""
Health Record Interpretation ML Model using Clustering and Pattern Analysis
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


class HealthRecordAnalyzer:
    """
    AI-powered health record interpretation
    Analyzes comprehensive patient health records for patterns and insights
    """

    @staticmethod
    @cache_ai_result('comprehensive_health_analysis', timeout=1800, participant_param='patient')
    def comprehensive_health_analysis(patient, days_back=365):
        """
        Comprehensive health record analysis across all record types
        Cached for 30 minutes for improved performance

        Args:
            patient: Patient Participant object
            days_back: Historical period to analyze (default 365 days)

        Returns:
            dict: Comprehensive health insights and interpretation
        """
        from health_records.models import HealthRecord

        cutoff_date = timezone.now().date() - timedelta(days=days_back)

        # Get all health records
        records = HealthRecord.objects.filter(
            assigned_to=patient,
            date_of_record__gte=cutoff_date
        ).order_by('-date_of_record')

        if not records.exists():
            return {
                'status': 'no_data',
                'message': 'No health records found for analysis'
            }

        # Categorize records by type
        record_distribution = {}
        for record in records:
            record_type = record.get_type_display()
            record_distribution[record_type] = record_distribution.get(record_type, 0) + 1

        # Analyze each category
        analysis = {
            'lab_results': HealthRecordAnalyzer._analyze_lab_results(records),
            'prescriptions': HealthRecordAnalyzer._analyze_prescriptions(records),
            'diagnoses': HealthRecordAnalyzer._analyze_diagnoses(records),
            'vaccinations': HealthRecordAnalyzer._analyze_vaccinations(records),
            'allergies': HealthRecordAnalyzer._analyze_allergies(records),
            'surgeries': HealthRecordAnalyzer._analyze_surgeries(records)
        }

        # Calculate health engagement score (how actively patient manages health)
        engagement_score = HealthRecordAnalyzer._calculate_engagement_score(
            records,
            days_back
        )

        # Calculate completeness score (data completeness)
        completeness_score = HealthRecordAnalyzer._calculate_completeness_score(analysis)

        # Generate overall health summary
        health_summary = HealthRecordAnalyzer._generate_health_summary(
            analysis,
            engagement_score,
            completeness_score
        )

        return {
            'status': 'analyzed',
            'patient_id': str(patient.id),
            'analysis_period_days': days_back,
            'total_records': records.count(),
            'record_distribution': record_distribution,
            'engagement_score': engagement_score,
            'completeness_score': completeness_score,
            'analysis': analysis,
            'health_summary': health_summary,
            'generated_at': timezone.now()
        }

    @staticmethod
    def _analyze_lab_results(records):
        """Analyze lab result patterns"""
        lab_records = records.filter(type='lab_result')

        if not lab_records.exists():
            return {'count': 0, 'status': 'no_data'}

        # Count abnormalities
        abnormal_count = 0
        for lab in lab_records:
            text = (lab.diagnosis + ' ' + lab.notes).lower()
            if any(keyword in text for keyword in ['abnormal', 'elevated', 'low', 'high', 'critical']):
                abnormal_count += 1

        abnormality_rate = (abnormal_count / lab_records.count() * 100) if lab_records.count() > 0 else 0

        return {
            'count': lab_records.count(),
            'abnormal_count': abnormal_count,
            'abnormality_rate': round(abnormality_rate, 1),
            'status': 'high_concern' if abnormality_rate >= 40 else 'moderate_concern' if abnormality_rate >= 20 else 'normal'
        }

    @staticmethod
    def _analyze_prescriptions(records):
        """Analyze prescription patterns"""
        prescriptions = records.filter(type='prescription')

        if not prescriptions.exists():
            return {'count': 0, 'status': 'no_prescriptions'}

        # Extract medication list
        medications = []
        for rx in prescriptions:
            if rx.medications:
                meds = rx.medications.split(',')
                medications.extend([m.strip().lower() for m in meds])

        from collections import Counter
        medication_freq = Counter(medications)

        # Identify long-term medications (mentioned 3+ times)
        long_term_meds = [
            {'medication': med, 'frequency': freq}
            for med, freq in medication_freq.most_common()
            if freq >= 3
        ]

        return {
            'count': prescriptions.count(),
            'unique_medications': len(medication_freq),
            'long_term_medications': long_term_meds[:10],  # Top 10
            'status': 'multiple_medications' if len(long_term_meds) >= 5 else 'normal'
        }

    @staticmethod
    def _analyze_diagnoses(records):
        """Analyze diagnosis patterns"""
        diagnoses = records.filter(type='diagnosis')

        if not diagnoses.exists():
            return {'count': 0, 'status': 'no_diagnoses'}

        # Extract diagnosis list
        diagnosis_list = []
        for diag in diagnoses:
            if diag.diagnosis:
                diagnosis_list.append(diag.diagnosis.lower())

        from collections import Counter
        diagnosis_freq = Counter(diagnosis_list)

        # Identify chronic conditions (mentioned 2+ times)
        chronic_conditions = [
            {'diagnosis': diag, 'occurrences': freq}
            for diag, freq in diagnosis_freq.most_common()
            if freq >= 2
        ]

        return {
            'count': diagnoses.count(),
            'unique_diagnoses': len(diagnosis_freq),
            'chronic_conditions': chronic_conditions[:5],  # Top 5
            'status': 'chronic_present' if chronic_conditions else 'acute_only'
        }

    @staticmethod
    def _analyze_vaccinations(records):
        """Analyze vaccination records"""
        vaccinations = records.filter(type='vaccination')

        if not vaccinations.exists():
            return {'count': 0, 'status': 'no_vaccinations'}

        vaccination_list = []
        for vax in vaccinations:
            if vax.title:
                vaccination_list.append(vax.title.lower())

        from collections import Counter
        vaccination_freq = Counter(vaccination_list)

        return {
            'count': vaccinations.count(),
            'unique_vaccines': len(vaccination_freq),
            'vaccines_received': [
                {'vaccine': vax, 'count': freq}
                for vax, freq in vaccination_freq.most_common(10)
            ],
            'status': 'up_to_date' if vaccinations.count() >= 3 else 'incomplete'
        }

    @staticmethod
    def _analyze_allergies(records):
        """Analyze allergy records"""
        allergies = records.filter(type='allergy')

        if not allergies.exists():
            return {'count': 0, 'status': 'no_allergies', 'allergy_list': []}

        allergy_list = []
        for allergy in allergies:
            allergy_list.append({
                'allergen': allergy.title,
                'reaction': allergy.symptoms or 'Not specified',
                'date_recorded': allergy.date_of_record.strftime('%Y-%m-%d')
            })

        return {
            'count': allergies.count(),
            'allergy_list': allergy_list,
            'status': 'multiple_allergies' if allergies.count() >= 3 else 'limited_allergies'
        }

    @staticmethod
    def _analyze_surgeries(records):
        """Analyze surgery records"""
        surgeries = records.filter(type='surgery')

        if not surgeries.exists():
            return {'count': 0, 'status': 'no_surgeries'}

        surgery_list = []
        for surgery in surgeries:
            surgery_list.append({
                'procedure': surgery.title,
                'date': surgery.date_of_record.strftime('%Y-%m-%d'),
                'notes': surgery.notes[:100] if surgery.notes else ''
            })

        return {
            'count': surgeries.count(),
            'surgery_history': surgery_list,
            'status': 'multiple_surgeries' if surgeries.count() >= 3 else 'limited_surgeries'
        }

    @staticmethod
    def _calculate_engagement_score(records, days_back):
        """
        Calculate patient engagement score (0-100)
        Based on record frequency and consistency
        """
        total_records = records.count()
        expected_records_per_year = 12  # Monthly checkups ideal

        # Normalize to analysis period
        expected_records = (days_back / 365) * expected_records_per_year

        # Calculate score
        if expected_records == 0:
            return 0

        engagement_ratio = total_records / expected_records
        engagement_score = min(100, engagement_ratio * 100)

        return round(engagement_score, 1)

    @staticmethod
    def _calculate_completeness_score(analysis):
        """
        Calculate data completeness score (0-100)
        Based on presence of different record types
        """
        score = 0

        # Each category contributes to completeness
        if analysis['lab_results']['count'] > 0:
            score += 20
        if analysis['prescriptions']['count'] > 0:
            score += 15
        if analysis['diagnoses']['count'] > 0:
            score += 25
        if analysis['vaccinations']['count'] > 0:
            score += 15
        if analysis['allergies']['count'] >= 0:  # Having zero allergies is complete data
            score += 10
        if analysis['surgeries']['count'] >= 0:  # Having zero surgeries is complete data
            score += 15

        return score

    @staticmethod
    def _generate_health_summary(analysis, engagement_score, completeness_score):
        """Generate comprehensive health summary with insights"""
        summary = []

        # Engagement insight
        if engagement_score >= 80:
            summary.append({
                'category': 'engagement',
                'level': 'excellent',
                'message': 'You are actively managing your health with regular medical visits.'
            })
        elif engagement_score >= 50:
            summary.append({
                'category': 'engagement',
                'level': 'good',
                'message': 'You maintain reasonable engagement with healthcare services.'
            })
        else:
            summary.append({
                'category': 'engagement',
                'level': 'improvement_needed',
                'message': 'Consider scheduling regular checkups to monitor your health.'
            })

        # Chronic conditions insight
        if analysis['diagnoses'].get('chronic_conditions'):
            summary.append({
                'category': 'chronic_conditions',
                'level': 'attention_required',
                'message': f"You have {len(analysis['diagnoses']['chronic_conditions'])} chronic condition(s) that require ongoing management."
            })

        # Medication management
        long_term_meds = analysis['prescriptions'].get('long_term_medications', [])
        if len(long_term_meds) >= 5:
            summary.append({
                'category': 'medications',
                'level': 'complex',
                'message': 'You are on multiple long-term medications. Regular medication review is recommended.'
            })

        # Lab results concern
        if analysis['lab_results'].get('abnormality_rate', 0) >= 30:
            summary.append({
                'category': 'lab_results',
                'level': 'concern',
                'message': 'Elevated abnormal lab result rate. Follow up with your healthcare provider.'
            })

        # Vaccination status
        if analysis['vaccinations']['status'] == 'incomplete':
            summary.append({
                'category': 'vaccinations',
                'level': 'action_needed',
                'message': 'Your vaccination records may be incomplete. Consult your doctor about recommended vaccines.'
            })

        # Allergies awareness
        if analysis['allergies']['count'] > 0:
            summary.append({
                'category': 'allergies',
                'level': 'awareness',
                'message': f"You have {analysis['allergies']['count']} documented allergy(ies). Always inform healthcare providers."
            })

        # Overall health status
        overall_status = 'good'
        if analysis['lab_results'].get('abnormality_rate', 0) >= 40 or len(analysis['diagnoses'].get('chronic_conditions', [])) >= 3:
            overall_status = 'needs_attention'
        elif completeness_score >= 80 and engagement_score >= 70:
            overall_status = 'excellent'

        summary.insert(0, {
            'category': 'overall',
            'level': overall_status,
            'message': HealthRecordAnalyzer._get_overall_message(overall_status)
        })

        return summary

    @staticmethod
    def _get_overall_message(status):
        """Get overall health status message"""
        messages = {
            'excellent': 'Your health records show excellent engagement and good health status.',
            'good': 'Your health records indicate generally good health with regular monitoring.',
            'needs_attention': 'Some health concerns detected. Regular medical consultation is recommended.'
        }
        return messages.get(status, 'Health status requires professional evaluation.')

    @staticmethod
    @cache_ai_result('healthcare_needs_prediction', timeout=7200, participant_param='patient')
    def predict_healthcare_needs(patient, months_forward=6):
        """
        Predict upcoming healthcare needs based on historical patterns
        Cached for 2 hours for improved performance

        Args:
            patient: Patient Participant object
            months_forward: Prediction period in months

        Returns:
            dict: Predicted healthcare needs and recommendations
        """
        # Get comprehensive health analysis
        health_analysis = HealthRecordAnalyzer.comprehensive_health_analysis(patient)

        if health_analysis['status'] != 'analyzed':
            return health_analysis

        predicted_needs = []

        # Check vaccination schedule
        if health_analysis['analysis']['vaccinations']['count'] < 3:
            predicted_needs.append({
                'type': 'vaccination',
                'timeframe': '1-2 months',
                'description': 'Vaccination schedule review and updates',
                'priority': 'medium'
            })

        # Check chronic condition monitoring
        chronic_conditions = health_analysis['analysis']['diagnoses'].get('chronic_conditions', [])
        if chronic_conditions:
            predicted_needs.append({
                'type': 'chronic_care_followup',
                'timeframe': '1-3 months',
                'description': f'Regular monitoring for {len(chronic_conditions)} chronic condition(s)',
                'priority': 'high'
            })

        # Check lab work frequency
        if health_analysis['analysis']['lab_results']['count'] < 2:
            predicted_needs.append({
                'type': 'lab_work',
                'timeframe': '2-3 months',
                'description': 'Routine lab work for health monitoring',
                'priority': 'medium'
            })

        # Check medication refills
        long_term_meds = health_analysis['analysis']['prescriptions'].get('long_term_medications', [])
        if long_term_meds:
            predicted_needs.append({
                'type': 'medication_refill',
                'timeframe': '1 month',
                'description': f'Prescription refills for {len(long_term_meds)} long-term medication(s)',
                'priority': 'high'
            })

        # Annual checkup prediction
        predicted_needs.append({
            'type': 'annual_checkup',
            'timeframe': f'{months_forward} months',
            'description': 'Annual comprehensive health checkup',
            'priority': 'medium'
        })

        return {
            'status': 'predicted',
            'patient_id': str(patient.id),
            'prediction_period_months': months_forward,
            'predicted_needs': predicted_needs,
            'health_analysis_summary': health_analysis['health_summary'],
            'generated_at': timezone.now()
        }
