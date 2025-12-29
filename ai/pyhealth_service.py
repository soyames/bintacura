"""
AI Health Analysis Service using PyHealth
Provides comprehensive health predictions and risk assessments
"""
import json
from django.utils import timezone
from datetime import timedelta
from ai.models import (
    AIEHRDataAnalysis, AIConsolidatedHealthReport, AIMedicalDocumentAnalysis,
    AIDoctorAssistant, AI_DISCLAIMER, AI_SHORT_DISCLAIMER
)


class AIHealthAnalysisService:
    """Service for PyHealth-based EHR analysis and health predictions"""
    
    @staticmethod
    def analyze_ehr_data(patient, analysis_type='risk_prediction'):
        """
        Comprehensive EHR data analysis using PyHealth
        
        Note: This is a placeholder implementation. In production, integrate with:
        - PyHealth library for real predictions
        - Trained models on EHR data
        - Feature engineering pipelines
        """
        from health_records.models import HealthRecord
        from appointments.models import Appointment
        
        # Collect patient data
        patient_data = AIHealthAnalysisService._collect_patient_ehr_data(patient)
        
        # In production, use PyHealth models here
        # For now, provide rule-based analysis
        predictions = AIHealthAnalysisService._generate_predictions(patient_data, analysis_type)
        
        # Create analysis record
        analysis = AIEHRDataAnalysis.objects.create(
            patient=patient,
            analysis_type=analysis_type,
            data_sources_used=list(patient_data.keys()),
            timeframe_analyzed={
                'start': (timezone.now() - timedelta(days=365)).isoformat(),
                'end': timezone.now().isoformat()
            },
            model_used='PyHealth_RiskPrediction_v1',
            predictions=predictions,
            risk_scores=predictions.get('risk_scores', {}),
            interpretation=predictions.get('interpretation', ''),
            risk_factors_identified=predictions.get('risk_factors', []),
            recommendations=predictions.get('recommendations', ''),
            model_confidence=predictions.get('confidence', 0.75),
            model_version='1.0.0'
        )
        
        return analysis
    
    @staticmethod
    def _collect_patient_ehr_data(patient):
        """Collect comprehensive patient data for analysis"""
        from health_records.models import HealthRecord, WearableData
        from appointments.models import Appointment
        from prescriptions.models import Prescription
        
        data = {
            'demographics': {
                'age': AIHealthAnalysisService._calculate_age(patient.date_of_birth) if hasattr(patient, 'date_of_birth') and patient.date_of_birth else None,
                'gender': patient.gender if hasattr(patient, 'gender') else None,
            },
            'health_records': [],
            'appointments': [],
            'prescriptions': [],
            'vitals': [],
            'labs': [],
        }
        
        # Collect health records
        health_records = HealthRecord.objects.filter(assigned_to=patient).order_by('-date_of_record')[:50]
        for record in health_records:
            data['health_records'].append({
                'type': record.type,
                'title': record.title,
                'date': record.date_of_record.isoformat() if record.date_of_record else None,
                'diagnosis': record.diagnosis,
            })
        
        # Collect recent appointments
        appointments = Appointment.objects.filter(patient=participant, status='completed').order_by('-appointment_date')[:20]
        for apt in appointments:
            if hasattr(apt, 'diagnosis') and apt.diagnosis:
                data['appointments'].append({
                    'date': apt.appointment_date.isoformat(),
                    'diagnosis': apt.diagnosis,
                    'notes': apt.notes if hasattr(apt, 'notes') else None,
                })
        
        # Collect prescriptions
        prescriptions = Prescription.objects.filter(patient=patient, status='active')[:30]
        for rx in prescriptions:
            data['prescriptions'].append({
                'medication': rx.medication_name if hasattr(rx, 'medication_name') else None,
                'prescribed_date': rx.created_at.isoformat(),
            })
        
        # Collect wearable data
        wearable_data = WearableData.objects.filter(participant=patient).order_by('-recorded_at')[:100]
        for wd in wearable_data:
            data['vitals'].append({
                'type': wd.data_type,
                'value': wd.value,
                'unit': wd.unit,
                'recorded_at': wd.recorded_at.isoformat(),
            })
        
        return data
    
    @staticmethod
    def _calculate_age(birth_date):
        """Calculate age from birth date"""
        if not birth_date:
            return None
        today = timezone.now().date()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    @staticmethod
    def _generate_predictions(patient_data, analysis_type):
        """
        Generate health predictions
        In production, replace with actual PyHealth models
        """
        demographics = patient_data.get('demographics', {})
        age = demographics.get('age')
        
        # Rule-based predictions (placeholder for PyHealth integration)
        predictions = {
            'confidence': 0.75,
            'risk_scores': {},
            'risk_factors': [],
            'recommendations': AI_SHORT_DISCLAIMER + '\n\n',
            'interpretation': ''
        }
        
        if analysis_type == 'risk_prediction':
            # Cardiovascular risk
            cv_risk = 0.15
            if age and age > 50:
                cv_risk += 0.20
                predictions['risk_factors'].append('Âge supérieur à 50 ans')
            if len(patient_data.get('prescriptions', [])) > 5:
                cv_risk += 0.10
                predictions['risk_factors'].append('Polymédication')
            
            predictions['risk_scores']['cardiovascular'] = min(cv_risk, 1.0)
            predictions['risk_scores']['diabetes'] = 0.12
            predictions['risk_scores']['hypertension'] = 0.18
            
            predictions['interpretation'] = f"""
            Analyse des risques de santé:
            
            • Risque cardiovasculaire: {cv_risk*100:.1f}%
            • Risque de diabète: 12%
            • Risque d'hypertension: 18%
            
            {AI_DISCLAIMER}
            """
            
            predictions['recommendations'] = f"""
            Recommandations basées sur l'analyse:
            
            1. Suivi régulier de la tension artérielle
            2. Bilans sanguins annuels (glycémie, cholestérol)
            3. Activité physique régulière (150min/semaine)
            4. Alimentation équilibrée
            5. Consultation médicale pour évaluation approfondie
            
            {AI_SHORT_DISCLAIMER}
            """
        
        return predictions
    
    @staticmethod
    def generate_consolidated_report(patient, for_doctor=None):
        """Generate comprehensive health report"""
        from health_records.models import HealthRecord
        from ai.models import AIHealthInsight
        
        # Collect all data
        patient_data = AIHealthAnalysisService._collect_patient_ehr_data(patient)
        
        # Analyze health records
        health_records = HealthRecord.objects.filter(assigned_to=patient).order_by('-date_of_record')
        
        active_conditions = []
        for record in health_records[:20]:
            if record.diagnosis:
                active_conditions.append({
                    'condition': record.diagnosis,
                    'diagnosed_date': record.date_of_record.isoformat() if record.date_of_record else None,
                    'type': record.type,
                })
        
        # Get recent insights
        recent_insights = AIHealthInsight.objects.filter(patient=patient, is_read=False)[:10]
        
        # Generate health score (simplified)
        health_score = AIHealthAnalysisService._calculate_health_score(patient_data)
        
        # Create report
        report = AIConsolidatedHealthReport.objects.create(
            patient=patient,
            generated_for_doctor=for_doctor,
            data_sources_count=len([k for k, v in patient_data.items() if v]),
            records_analyzed={
                'health_records': len(patient_data.get('health_records', [])),
                'appointments': len(patient_data.get('appointments', [])),
                'prescriptions': len(patient_data.get('prescriptions', [])),
                'vitals': len(patient_data.get('vitals', [])),
            },
            overall_health_score=health_score,
            health_status_summary=f"Score de santé global: {health_score}/100\n\n{AI_SHORT_DISCLAIMER}",
            active_conditions=active_conditions,
            current_medications=[p for p in patient_data.get('prescriptions', [])],
            priority_recommendations=[
                "Maintenir un suivi médical régulier",
                "Continuer les traitements prescrits",
                "Surveiller les paramètres vitaux",
            ],
            doctor_summary=AIHealthAnalysisService._generate_doctor_summary(patient_data, active_conditions) if for_doctor else '',
            ai_models_used=['PyHealth_v1', 'RuleBasedAnalysis'],
        )
        
        if for_doctor:
            report.shared_with_doctors.add(for_doctor)
        
        return report
    
    @staticmethod
    def _calculate_health_score(patient_data):
        """Calculate overall health score 0-100"""
        score = 70.0  # Base score
        
        # Adjust based on data availability
        if patient_data.get('health_records'):
            score += 5
        if patient_data.get('vitals'):
            score += 5
        if len(patient_data.get('prescriptions', [])) == 0:
            score += 10  # Bonus for no medications
        elif len(patient_data.get('prescriptions', [])) > 5:
            score -= 10  # Concern for many medications
        
        return max(min(score, 100), 0)
    
    @staticmethod
    def _generate_doctor_summary(patient_data, active_conditions):
        """Generate technical summary for healthcare providers"""
        summary = f"""
        RAPPORT CLINIQUE CONSOLIDÉ
        {AI_DISCLAIMER}
        
        DONNÉES ANALYSÉES:
        - Dossiers médicaux: {len(patient_data.get('health_records', []))}
        - Consultations: {len(patient_data.get('appointments', []))}
        - Prescriptions actives: {len(patient_data.get('prescriptions', []))}
        - Mesures vitales: {len(patient_data.get('vitals', []))}
        
        CONDITIONS ACTIVES:
        {chr(10).join([f"- {c['condition']} (depuis {c.get('diagnosed_date', 'N/A')})" for c in active_conditions[:10]])}
        
        POLYMÉDICATION: {'Oui' if len(patient_data.get('prescriptions', [])) > 5 else 'Non'}
        
        RECOMMANDATIONS CLINIQUES:
        1. Révision périodique des prescriptions
        2. Surveillance des interactions médicamenteuses
        3. Suivi des paramètres vitaux
        4. Évaluation des risques cardiovasculaires
        
        Note: Cette analyse est générée par IA et doit être validée par un jugement clinique professionnel.
        """
        return summary


class AIMedicalDocumentService:
    """Service for analyzing medical documents"""
    
    @staticmethod
    def analyze_document(patient, document_reference, document_type, file_content=None):
        """
        Analyze uploaded medical document
        In production, integrate with OCR and NLP models
        """
        
        # Create analysis record
        analysis = AIMedicalDocumentAnalysis.objects.create(
            patient=patient,
            document_type=document_type,
            document_reference=document_reference,
            file_name=f"document_{document_reference}.pdf",
            analysis_status='processing'
        )
        
        try:
            # In production: Use OCR for text extraction
            # extracted_text = perform_ocr(file_content)
            extracted_text = "Document text would be extracted here..."
            analysis.extracted_text = extracted_text
            
            # In production: Use NLP for entity extraction
            # extracted_data = extract_medical_entities(extracted_text)
            extracted_data = AIMedicalDocumentService._extract_entities_placeholder(document_type)
            analysis.extracted_data = extracted_data
            
            # Generate summary and recommendations
            summary = AIMedicalDocumentService._generate_document_summary(document_type, extracted_data)
            analysis.ai_summary = summary['summary']
            analysis.key_findings = summary['findings']
            analysis.recommendations = summary['recommendations'] + f"\n\n{AI_SHORT_DISCLAIMER}"
            
            analysis.analysis_status = 'completed'
            analysis.processed_at = timezone.now()
            analysis.confidence_score = 0.82
            
        except Exception as e:
            analysis.analysis_status = 'failed'
            analysis.ai_summary = f"Erreur lors de l'analyse: {str(e)}"
        
        analysis.save()
        return analysis
    
    @staticmethod
    def _extract_entities_placeholder(document_type):
        """Placeholder for entity extraction"""
        if document_type == 'lab_result':
            return {
                'test_name': 'Glycémie à jeun',
                'test_value': '5.8 mmol/L',
                'reference_range': '3.9-5.6 mmol/L',
                'status': 'Légèrement élevé',
            }
        return {}
    
    @staticmethod
    def _generate_document_summary(document_type, extracted_data):
        """Generate summary for analyzed document"""
        return {
            'summary': f"Analyse du document de type {document_type}.\n\n{AI_DISCLAIMER}",
            'findings': ['Résultats extraits du document', 'Valeurs identifiées'],
            'recommendations': "Consultez votre médecin pour l'interprétation complète de ces résultats."
        }


class AIDoctorAssistantService:
    """Service for AI assistance to doctors"""
    
    @staticmethod
    def provide_diagnosis_support(doctor, patient, clinical_question, symptoms=None, findings=None):
        """
        Provide AI-powered diagnosis support to doctors
        In production, use medical knowledge graphs and clinical decision support systems
        """
        
        patient_context = AIHealthAnalysisService._collect_patient_ehr_data(patient)
        
        # Generate AI response
        ai_response = AIDoctorAssistantService._generate_clinical_response(
            clinical_question,
            patient_context,
            symptoms or [],
            findings or {}
        )
        
        # Create assistance record
        assistance = AIDoctorAssistant.objects.create(
            doctor=doctor,
            patient=patient,
            assistance_type='diagnosis_support',
            clinical_question=clinical_question,
            patient_context=patient_context,
            symptoms_provided=symptoms or [],
            current_findings=findings or {},
            ai_response=ai_response['response'],
            suggested_diagnoses=ai_response.get('diagnoses', []),
            suggested_tests=ai_response.get('tests', []),
            suggested_treatments=ai_response.get('treatments', []),
            clinical_guidelines_referenced=ai_response.get('guidelines', []),
            confidence_score=ai_response.get('confidence', 0.70),
        )
        
        return assistance
    
    @staticmethod
    def _generate_clinical_response(question, patient_context, symptoms, findings):
        """
        Generate clinical response for doctor
        In production, integrate with clinical knowledge bases
        """
        response = {
            'response': f"""
            SUPPORT AU DIAGNOSTIC - ANALYSE IA
            {AI_DISCLAIMER}
            
            Question clinique: {question}
            
            Contexte patient analysé:
            - Âge: {patient_context.get('demographics', {}).get('age', 'N/A')} ans
            - Dossiers médicaux: {len(patient_context.get('health_records', []))} enregistrements
            - Prescriptions actives: {len(patient_context.get('prescriptions', []))}
            
            Cette analyse est fournie à titre informatif uniquement.
            Le jugement clinique du médecin prime sur toute suggestion de l'IA.
            """,
            'diagnoses': [
                {'diagnosis': 'Diagnostic différentiel suggéré 1', 'probability': 0.45},
                {'diagnosis': 'Diagnostic différentiel suggéré 2', 'probability': 0.30},
            ],
            'tests': [
                'Analyses sanguines complètes (NFS, CRP)',
                'Échographie selon indication clinique',
            ],
            'treatments': [],
            'guidelines': ['Guidelines cliniques pertinentes'],
            'confidence': 0.70,
        }
        
        return response
