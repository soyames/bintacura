"""
Patient Segmentation using K-Means Clustering
Lightweight model - calculated on-the-fly, no model persistence
"""
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from django.utils import timezone
from datetime import timedelta
import numpy as np


class PatientSegmentation:
    """
    Segments patients into groups based on:
    - Visit frequency
    - Average spending
    - Appointment completion rate
    - Prescription adherence
    """

    @staticmethod
    def segment_patients(organization, n_clusters=4):
        """
        Segment patients using K-Means clustering

        Args:
            organization: Organization to analyze patients for
            n_clusters: Number of segments (default 4: VIP, Regular, At-Risk, Inactive)

        Returns:
            dict: Patient segments with characteristics
        """
        from core.models import Participant, Transaction
        from appointments.models import Appointment
        from prescriptions.models import Prescription

        # Get patients affiliated with organization
        patients = Participant.objects.filter(
            role='patient',
            affiliated_provider=organization,
            is_active=True
        )

        if patients.count() < n_clusters:
            return {
                'status': 'insufficient_data',
                'message': f'Need at least {n_clusters} patients for segmentation. Found: {patients.count()}'
            }

        # Prepare features for each patient
        patient_features = []
        patient_ids = []
        lookback_days = 180  # Last 6 months

        start_date = timezone.now() - timedelta(days=lookback_days)

        for patient in patients[:200]:  # Limit to 200 patients to avoid memory issues
            # Feature 1: Visit frequency (appointments in last 6 months)
            visit_count = Appointment.objects.filter(
                patient=patient,
                appointment_date__gte=start_date,
                status='completed'
            ).count()

            # Feature 2: Average spending
            transactions = Transaction.objects.filter(
                sender=patient,
                status='completed',
                created_at__gte=start_date
            )
            total_spending = sum(float(t.amount) for t in transactions)
            avg_spending = total_spending / max(visit_count, 1)

            # Feature 3: Appointment completion rate
            total_appointments = Appointment.objects.filter(
                patient=patient,
                appointment_date__gte=start_date
            ).count()
            completion_rate = (visit_count / total_appointments * 100) if total_appointments > 0 else 0

            # Feature 4: Prescription count (engagement indicator)
            prescription_count = Prescription.objects.filter(
                patient=patient,
                created_at__gte=start_date
            ).count()

            patient_features.append([
                visit_count,
                avg_spending,
                completion_rate,
                prescription_count
            ])
            patient_ids.append(str(patient.uid))

        if len(patient_features) < n_clusters:
            return {
                'status': 'insufficient_data',
                'message': f'Insufficient patient data for segmentation'
            }

        # Convert to numpy array
        X = np.array(patient_features)

        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Apply K-Means clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(X_scaled)

        # Analyze each cluster
        segments = []
        segment_names = ['VIP Patients', 'Regular Patients', 'At-Risk Patients', 'Inactive Patients']

        for cluster_id in range(n_clusters):
            cluster_mask = cluster_labels == cluster_id
            cluster_features = X[cluster_mask]

            if len(cluster_features) == 0:
                continue

            # Calculate cluster statistics
            avg_visits = np.mean(cluster_features[:, 0])
            avg_spending = np.mean(cluster_features[:, 1])
            avg_completion = np.mean(cluster_features[:, 2])
            avg_prescriptions = np.mean(cluster_features[:, 3])

            # Determine segment characteristics
            if avg_visits > 3 and avg_spending > 100:
                segment_type = 'VIP Patients'
                priority = 'high'
                recommendation = 'Maintain excellent service. Offer loyalty rewards.'
            elif avg_visits > 1 and avg_completion > 70:
                segment_type = 'Regular Patients'
                priority = 'medium'
                recommendation = 'Continue standard care. Encourage preventive visits.'
            elif avg_completion < 50 or avg_visits < 1:
                segment_type = 'At-Risk Patients'
                priority = 'high'
                recommendation = 'Re-engagement campaign needed. Send appointment reminders.'
            else:
                segment_type = 'Inactive Patients'
                priority = 'medium'
                recommendation = 'Reactivation campaign. Offer health checkup incentives.'

            segments.append({
                'segment_id': cluster_id,
                'segment_name': segment_type,
                'patient_count': int(cluster_mask.sum()),
                'priority': priority,
                'characteristics': {
                    'avg_visits_6months': round(avg_visits, 1),
                    'avg_spending_per_visit': round(avg_spending, 2),
                    'avg_completion_rate': round(avg_completion, 1),
                    'avg_prescriptions_6months': round(avg_prescriptions, 1)
                },
                'recommendation': recommendation
            })

        # Sort segments by priority and size
        segments.sort(key=lambda x: (x['priority'] == 'high', x['patient_count']), reverse=True)

        return {
            'status': 'segmented',
            'total_patients_analyzed': len(patient_ids),
            'n_clusters': n_clusters,
            'lookback_period_days': lookback_days,
            'segments': segments,
            'generated_at': timezone.now()
        }

    @staticmethod
    def get_patient_segment(patient, organization):
        """
        Get the segment for a specific patient

        Args:
            patient: Patient participant
            organization: Organization

        Returns:
            dict: Patient's segment information
        """
        # Run segmentation
        segmentation = PatientSegmentation.segment_patients(organization)

        if segmentation['status'] != 'segmented':
            return segmentation

        # This is a simplified version - in production, you'd want to cache the segmentation
        # and retrieve the specific patient's segment
        return {
            'status': 'success',
            'message': 'Patient segmentation complete',
            'segments_available': segmentation['segments']
        }
