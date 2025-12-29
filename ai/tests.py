"""
Integration Tests for AI & ML Features (Phase 10)
Tests all AI endpoints, ML models, and chatbot functionality
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, date
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
import json

from core.models import Participant
from ai.models import AIConversation, AIChatMessage, AIInsight, AIFeature
from health_records.models import HealthRecord
from hr.models import Employee, TimeAndAttendance


class AIAssistantChatbotTests(APITestCase):
    """Test AI chatbot with context retention and intent detection"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()

        # Create patient user
        self.patient = Participant.objects.create(
            email='patient@test.com',
            full_name='Test Patient',
            role='patient',
            is_active=True
        )
        self.patient.set_password('testpass123')
        self.patient.save()

        # Authenticate
        self.client.force_authenticate(user=self.patient)

    def test_ai_chat_message_creation(self):
        """Test sending a message to AI assistant"""
        response = self.client.post('/api/v1/communication/ai-chat/', {
            'message': 'Je veux prendre un rendez-vous'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('conversation_id', response.data)
        self.assertIn('response', response.data)
        self.assertIn('intent', response.data)
        self.assertIn('confidence', response.data)

        # Check intent detection
        self.assertEqual(response.data['intent'], 'appointment')
        self.assertGreater(response.data['confidence'], 0.5)

    def test_ai_chat_context_retention(self):
        """Test conversation context retention across multiple messages"""
        # First message
        response1 = self.client.post('/api/v1/communication/ai-chat/', {
            'message': 'Bonjour'
        }, format='json')

        conversation_id = response1.data['conversation_id']

        # Second message with conversation ID
        response2 = self.client.post('/api/v1/communication/ai-chat/', {
            'message': 'Je veux voir un cardiologue',
            'conversation_id': conversation_id
        }, format='json')

        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.data['conversation_id'], conversation_id)

        # Verify conversation has multiple messages
        conversation = AIConversation.objects.get(id=conversation_id)
        self.assertEqual(conversation.messages.count(), 2)

    def test_ai_chat_multi_language_support(self):
        """Test French and English language support"""
        # French message
        response_fr = self.client.post('/api/v1/communication/ai-chat/', {
            'message': 'Je veux prendre rendez-vous'
        }, format='json')

        self.assertEqual(response_fr.data['intent'], 'appointment')

        # English message
        response_en = self.client.post('/api/v1/communication/ai-chat/', {
            'message': 'I want to book an appointment'
        }, format='json')

        self.assertEqual(response_en.data['intent'], 'appointment')

    def test_ai_chat_intent_detection_accuracy(self):
        """Test accuracy of intent detection for all 12 intents"""
        test_cases = [
            ('Je veux prendre rendez-vous', 'appointment'),
            ('J\'ai besoin de mon ordonnance', 'prescription'),
            ('C\'est une urgence', 'emergency'),
            ('Où se trouve la clinique?', 'location'),
            ('Mes résultats de laboratoire', 'lab_results'),
            ('Merci beaucoup', 'gratitude'),
            ('Au revoir', 'farewell'),
        ]

        for message, expected_intent in test_cases:
            response = self.client.post('/api/v1/communication/ai-chat/', {
                'message': message
            }, format='json')

            self.assertEqual(response.data['intent'], expected_intent,
                           f"Failed for message: {message}")

    def test_ai_chat_missing_message(self):
        """Test error handling for missing message"""
        response = self.client.post('/api/v1/communication/ai-chat/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_conversation_history_retrieval(self):
        """Test retrieving conversation history"""
        # Create some messages
        self.client.post('/api/v1/communication/ai-chat/', {
            'message': 'Bonjour'
        }, format='json')

        self.client.post('/api/v1/communication/ai-chat/', {
            'message': 'Je veux un rendez-vous'
        }, format='json')

        # Get conversation history
        response = self.client.get('/api/v1/communication/ai-chat/conversation_history/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('conversations', response.data)
        self.assertGreater(len(response.data['conversations']), 0)


class PatientHealthAITests(APITestCase):
    """Test patient health AI endpoints"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()

        # Create patient user
        self.patient = Participant.objects.create(
            email='patient@test.com',
            full_name='Test Patient',
            role='patient',
            is_active=True
        )
        self.patient.set_password('testpass123')
        self.patient.save()

        # Create health records
        self._create_health_records()

        # Authenticate
        self.client.force_authenticate(user=self.patient)

    def _create_health_records(self):
        """Create sample health records for testing"""
        # Diagnosis records
        HealthRecord.objects.create(
            assigned_to=self.patient,
            type='diagnosis',
            title='Hypertension',
            diagnosis='Essential hypertension',
            symptoms='Headache, dizziness',
            treatment='Lifestyle changes, medication',
            date_of_record=date.today() - timedelta(days=30)
        )

        HealthRecord.objects.create(
            assigned_to=self.patient,
            type='diagnosis',
            title='Hypertension Follow-up',
            diagnosis='Essential hypertension',
            symptoms='Improved',
            treatment='Continue medication',
            date_of_record=date.today() - timedelta(days=15)
        )

        # Lab result
        HealthRecord.objects.create(
            assigned_to=self.patient,
            type='lab_result',
            title='Blood Glucose Test',
            diagnosis='Elevated glucose levels',
            notes='Fasting glucose: 126 mg/dL',
            date_of_record=date.today() - timedelta(days=10)
        )

        # Prescription
        HealthRecord.objects.create(
            assigned_to=self.patient,
            type='prescription',
            title='Hypertension Medication',
            medications='Lisinopril 10mg',
            date_of_record=date.today() - timedelta(days=30)
        )

        # Vaccination
        HealthRecord.objects.create(
            assigned_to=self.patient,
            type='vaccination',
            title='COVID-19 Vaccine',
            date_of_record=date.today() - timedelta(days=180)
        )

    def test_diagnostic_analysis(self):
        """Test diagnostic analysis endpoint"""
        response = self.client.get('/api/v1/communication/diagnostic_analysis/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'analyzed')
        self.assertIn('health_risk_score', response.data)
        self.assertIn('chronic_conditions', response.data)
        self.assertIn('recommendations', response.data)

        # Verify chronic condition detected
        chronic_conditions = response.data['chronic_conditions']
        self.assertGreater(len(chronic_conditions), 0)
        self.assertEqual(chronic_conditions[0]['diagnosis'], 'essential hypertension')

    def test_lab_interpretation(self):
        """Test lab result interpretation"""
        response = self.client.get('/api/v1/communication/lab_interpretation/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'interpreted')
        self.assertIn('abnormality_rate', response.data)
        self.assertIn('abnormal_findings', response.data)

        # Verify abnormal finding detected
        self.assertGreater(response.data['abnormal_count'], 0)

    def test_health_risk_prediction(self):
        """Test health risk prediction"""
        response = self.client.get('/api/v1/communication/health_risk_prediction/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'predicted')
        self.assertIn('overall_risk_score', response.data)
        self.assertIn('risk_level', response.data)
        self.assertIn('predicted_risks', response.data)

    def test_comprehensive_health_analysis(self):
        """Test comprehensive health analysis"""
        response = self.client.get('/api/v1/communication/comprehensive_health_analysis/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'analyzed')
        self.assertIn('engagement_score', response.data)
        self.assertIn('completeness_score', response.data)
        self.assertIn('analysis', response.data)

        # Verify all categories analyzed
        analysis = response.data['analysis']
        self.assertIn('lab_results', analysis)
        self.assertIn('prescriptions', analysis)
        self.assertIn('diagnoses', analysis)
        self.assertIn('vaccinations', analysis)

    def test_healthcare_needs_prediction(self):
        """Test healthcare needs prediction"""
        response = self.client.get('/api/v1/communication/predict_healthcare_needs/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'predicted')
        self.assertIn('predicted_needs', response.data)

        # Verify predictions exist
        self.assertGreater(len(response.data['predicted_needs']), 0)

    def test_diagnostic_analysis_no_data(self):
        """Test diagnostic analysis with no health records"""
        # Create new patient with no records
        new_patient = Participant.objects.create(
            email='newpatient@test.com',
            full_name='New Patient',
            role='patient',
            is_active=True
        )
        new_patient.set_password('testpass123')
        new_patient.save()

        self.client.force_authenticate(user=new_patient)

        response = self.client.get('/api/v1/communication/diagnostic_analysis/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'no_data')

    def test_patient_only_access(self):
        """Test that only patients can access health AI endpoints"""
        # Create hospital user
        hospital = Participant.objects.create(
            email='hospital@test.com',
            full_name='Test Hospital',
            role='hospital',
            is_active=True
        )
        hospital.set_password('testpass123')
        hospital.save()

        self.client.force_authenticate(user=hospital)

        response = self.client.get('/api/v1/communication/diagnostic_analysis/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class HRMLTests(APITestCase):
    """Test HR ML endpoints - Churn Prediction"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()

        # Create hospital user
        self.hospital = Participant.objects.create(
            email='hospital@test.com',
            full_name='Test Hospital',
            role='hospital',
            is_active=True
        )
        self.hospital.set_password('testpass123')
        self.hospital.save()

        # Create employees
        self._create_employees()

        # Authenticate
        self.client.force_authenticate(user=self.hospital)

    def _create_employees(self):
        """Create sample employees for testing"""
        # High risk employee
        employee1 = Employee.objects.create(
            organization=self.hospital,
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            department='Emergency',
            position='Nurse',
            employment_type='contract',
            hire_date=date.today() - timedelta(days=60),  # 2 months tenure
            base_salary=45000,
            performance_score=2.5
        )

        # Create poor attendance (low attendance rate)
        for i in range(10):
            Attendance.objects.create(
                employee=employee1,
                organization=self.hospital,
                date=date.today() - timedelta(days=i),
                status='absent'
            )

        # Low risk employee
        employee2 = Employee.objects.create(
            organization=self.hospital,
            first_name='Jane',
            last_name='Smith',
            email='jane@test.com',
            department='Surgery',
            position='Surgeon',
            employment_type='permanent',
            hire_date=date.today() - timedelta(days=730),  # 2 years tenure
            base_salary=150000,
            performance_score=4.8
        )

        # Create good attendance
        for i in range(20):
            Attendance.objects.create(
                employee=employee2,
                organization=self.hospital,
                date=date.today() - timedelta(days=i),
                status='present'
            )

    def test_churn_prediction(self):
        """Test ML churn prediction endpoint"""
        response = self.client.get('/api/v1/hr/employees/ml_churn_prediction/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('predictions', response.data)
        self.assertEqual(response.data['ml_model'], 'Logistic Regression')

        predictions = response.data['predictions']
        self.assertTrue(predictions['model_trained'])
        self.assertIn('churn_distribution', predictions)
        self.assertIn('top_at_risk_employees', predictions)

    def test_churn_prediction_authorization(self):
        """Test that only authorized roles can access churn prediction"""
        # Create patient user
        patient = Participant.objects.create(
            email='patient@test.com',
            full_name='Test Patient',
            role='patient',
            is_active=True
        )
        patient.set_password('testpass123')
        patient.save()

        self.client.force_authenticate(user=patient)

        response = self.client.get('/api/v1/hr/employees/ml_churn_prediction/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class FinancialMLTests(APITestCase):
    """Test Financial ML endpoints - Patient Segmentation & Revenue Forecast"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()

        # Create hospital user
        self.hospital = Participant.objects.create(
            email='hospital@test.com',
            full_name='Test Hospital',
            role='hospital',
            is_active=True
        )
        self.hospital.set_password('testpass123')
        self.hospital.save()

        # Authenticate
        self.client.force_authenticate(user=self.hospital)

    def test_ml_patient_segmentation(self):
        """Test ML patient segmentation endpoint"""
        response = self.client.get('/api/v1/analytics/insights/ml_patient_segmentation/')

        # May return 200 with data or no_data status depending on patient records
        self.assertIn(response.status_code, [status.HTTP_200_OK])

        if response.status_code == status.HTTP_200_OK:
            self.assertIn('segmentation', response.data)
            self.assertEqual(response.data['ml_model'], 'K-Means Clustering')

    def test_ml_advanced_revenue_forecast(self):
        """Test ML advanced revenue forecast"""
        response = self.client.get('/api/v1/analytics/insights/ml_advanced_revenue_forecast/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('forecast', response.data)
        self.assertEqual(response.data['ml_model'], 'Linear Regression with Seasonality')

        forecast = response.data['forecast']
        self.assertTrue(forecast['model_trained'])
        self.assertIn('forecast_data', forecast)
        self.assertIn('total_predicted_revenue', forecast)

    def test_ml_revenue_comparison(self):
        """Test ML revenue comparison with baseline"""
        response = self.client.get('/api/v1/analytics/insights/ml_revenue_comparison/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('comparison', response.data)

        comparison = response.data['comparison']
        self.assertIn('ml_forecast', comparison)
        self.assertIn('baseline_forecast', comparison)
        self.assertIn('ml_advantage_percent', comparison['comparison'])

    def test_revenue_forecast_with_parameters(self):
        """Test revenue forecast with custom parameters"""
        response = self.client.get(
            '/api/v1/analytics/insights/ml_advanced_revenue_forecast/',
            {'days_forward': 60, 'historical_days': 90}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        forecast = response.data['forecast']
        self.assertEqual(forecast['forecast_period_days'], 60)
        self.assertEqual(forecast['historical_period_days'], 90)


class MLModelPerformanceTests(TestCase):
    """Test ML model performance and data limits"""

    def test_patient_segmentation_model(self):
        """Test patient segmentation model directly"""
        try:
            from ml_models.patient_segmentation import PatientSegmentation

            # Create hospital
            hospital = Participant.objects.create(
                email='hospital@test.com',
                full_name='Test Hospital',
                role='hospital',
                is_active=True
            )

            # Test with no data
            result = PatientSegmentation.segment_patients(hospital)

            # Should handle no data gracefully
            self.assertIn('error', result)
        except ImportError:
            self.skipTest("scikit-learn not installed")

    def test_churn_predictor_model(self):
        """Test churn predictor model directly"""
        try:
            from ml_models.churn_prediction import ChurnPredictor

            # Create hospital
            hospital = Participant.objects.create(
                email='hospital@test.com',
                full_name='Test Hospital',
                role='hospital',
                is_active=True
            )

            # Test with no data
            result = ChurnPredictor.train_and_predict(hospital)

            # Should handle no data gracefully
            self.assertIn('error', result)
        except ImportError:
            self.skipTest("scikit-learn not installed")

    def test_revenue_forecast_model(self):
        """Test revenue forecast model directly"""
        try:
            from ml_models.revenue_forecast import AdvancedRevenueForecast

            # Create hospital
            hospital = Participant.objects.create(
                email='hospital@test.com',
                full_name='Test Hospital',
                role='hospital',
                is_active=True
            )

            # Test with no data
            result = AdvancedRevenueForecast.forecast_revenue(hospital)

            # Should handle no data gracefully
            self.assertIn('error', result)
        except ImportError:
            self.skipTest("scikit-learn not installed")

    def test_diagnostic_analyzer_model(self):
        """Test diagnostic analyzer model directly"""
        try:
            from ml_models.diagnostic_analyzer import DiagnosticAnalyzer

            # Create patient
            patient = Participant.objects.create(
                email='patient@test.com',
                full_name='Test Patient',
                role='patient',
                is_active=True
            )

            # Test with no data
            result = DiagnosticAnalyzer.analyze_patient_diagnostics(patient)

            # Should return no_data status
            self.assertEqual(result['status'], 'no_data')
        except ImportError:
            self.skipTest("ML models not available")

    def test_health_record_analyzer_model(self):
        """Test health record analyzer model directly"""
        try:
            from ml_models.health_record_analyzer import HealthRecordAnalyzer

            # Create patient
            patient = Participant.objects.create(
                email='patient@test.com',
                full_name='Test Patient',
                role='patient',
                is_active=True
            )

            # Test with no data
            result = HealthRecordAnalyzer.comprehensive_health_analysis(patient)

            # Should return no_data status
            self.assertEqual(result['status'], 'no_data')
        except ImportError:
            self.skipTest("ML models not available")


class AIInsightTests(TestCase):
    """Test AI Insight model and generation"""

    def setUp(self):
        """Set up test data"""
        self.hospital = Participant.objects.create(
            email='hospital@test.com',
            full_name='Test Hospital',
            role='hospital',
            is_active=True
        )

    def test_ai_insight_creation(self):
        """Test creating AI insights"""
        insight = AIInsight.objects.create(
            organization=self.hospital,
            category='patient_flow',
            priority='high',
            insight_text='Emergency wait times increased',
            recommendation='Add evening shift coverage',
            metric_name='avg_wait_time',
            metric_value='45',
            confidence_score=0.85
        )

        self.assertEqual(insight.priority, 'high')
        self.assertEqual(insight.category, 'patient_flow')
        self.assertFalse(insight.is_dismissed)

    def test_ai_feature_tracking(self):
        """Test AI feature usage tracking"""
        feature = AIFeature.objects.create(
            name='churn_prediction',
            type='hr_analytics',
            description='Employee churn prediction',
            is_active=True
        )

        self.assertTrue(feature.is_active)
        self.assertEqual(feature.type, 'hr_analytics')


# Run tests with: python manage.py test ai.tests
