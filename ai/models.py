from django.db import models
from django.utils import timezone
from core.models import Participant
from doctor.models import DoctorData
import uuid


# AI Disclaimer Constants
AI_DISCLAIMER = """
⚠️ AVERTISSEMENT IMPORTANT / IMPORTANT DISCLAIMER:

Cette analyse est générée par intelligence artificielle à titre informatif uniquement et ne constitue PAS un avis médical professionnel.

• NE REMPLACE PAS une consultation médicale avec un professionnel de santé qualifié
• Les recommandations sont basées sur des données générales et peuvent ne pas s'appliquer à votre situation spécifique
• En cas d'urgence médicale, contactez immédiatement les services d'urgence (112/SAMU)
• Consultez toujours votre médecin avant de prendre des décisions concernant votre santé
• Cette IA peut faire des erreurs - vérifiez toujours les informations importantes avec un professionnel

This AI-generated analysis is for informational purposes only and does NOT constitute professional medical advice.

• Does NOT replace consultation with a qualified healthcare professional
• Recommendations are based on general data and may not apply to your specific situation
• In case of medical emergency, immediately contact emergency services (112/SAMU)
• Always consult your doctor before making health decisions
• This AI can make errors - always verify important information with a professional
"""

AI_SHORT_DISCLAIMER = "⚠️ Ceci est un conseil IA informatif, pas un avis médical. Consultez un professionnel de santé."


class AIConversation(models.Model):  # Stores AI chat conversations with patients
    CONVERSATION_STATUS_CHOICES = [
        ('active', 'Active'),
        ('archived', 'Archived'),
        ('escalated', 'Escalated to Human'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='ai_conversations')
    title = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=CONVERSATION_STATUS_CHOICES, default='active')
    started_at = models.DateTimeField(default=timezone.now)
    last_message_at = models.DateTimeField(default=timezone.now)
    escalated_to_staff = models.BooleanField(default=False)
    escalated_at = models.DateTimeField(null=True, blank=True)
    sentiment_score = models.FloatField(default=0.5, help_text="Sentiment analysis score 0-1")
    
    class Meta:
        db_table = 'ai_conversations'
        ordering = ['-last_message_at']
        indexes = [
            models.Index(fields=['participant', '-last_message_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Conversation {self.id} - {self.participant.full_name}"


class AIChatMessage(models.Model):  # Individual messages in AI chat conversations
    MESSAGE_TYPE_CHOICES = [
        ('user', 'User Message'),
        ('ai', 'AI Response'),
        ('system', 'System Message'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(AIConversation, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True, help_text="Store intent, entities, confidence")
    timestamp = models.DateTimeField(default=timezone.now)
    is_flagged = models.BooleanField(default=False, help_text="Flagged for review")
    
    class Meta:
        db_table = 'ai_chat_messages'
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['conversation', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.message_type} - {self.content[:50]}"


class AIHealthInsight(models.Model):  # AI-generated health insights and recommendations
    INSIGHT_TYPE_CHOICES = [
        ('recommendation', 'Recommendation'),
        ('warning', 'Warning'),
        ('trend', 'Trend'),
        ('prediction', 'Prediction'),
        ('analysis', 'Analysis'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='ai_health_insights')
    insight_type = models.CharField(max_length=50, choices=INSIGHT_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField()
    recommendations = models.JSONField(default=list, blank=True)
    data_points_used = models.JSONField(default=dict, blank=True)
    confidence_score = models.FloatField(default=0.0, help_text="AI confidence 0-1")
    is_read = models.BooleanField(default=False)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    generated_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(DoctorData, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_insights')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        db_table = 'ai_health_insights'
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['patient', '-generated_at']),
            models.Index(fields=['priority', 'is_read']),
        ]

    def __str__(self):
        return f"{self.insight_type} - {self.title}"


class AISymptomChecker(models.Model):  # AI-powered symptom checking sessions
    URGENCY_LEVEL_CHOICES = [
        ('low', 'Low - Self Care'),
        ('medium', 'Medium - See Doctor Soon'),
        ('high', 'High - See Doctor Today'),
        ('emergency', 'Emergency - Seek Immediate Care'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='symptom_checks')
    symptoms = models.JSONField(default=list, help_text="List of reported symptoms")
    additional_info = models.JSONField(default=dict, blank=True, help_text="Age, gender, medical history")
    ai_analysis = models.TextField(blank=True)
    possible_conditions = models.JSONField(default=list, blank=True)
    urgency_level = models.CharField(max_length=20, choices=URGENCY_LEVEL_CHOICES, blank=True)
    recommendations = models.TextField(blank=True)
    confidence_score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(default=timezone.now)
    followed_up = models.BooleanField(default=False)

    class Meta:
        db_table = 'ai_symptom_checks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient', '-created_at']),
            models.Index(fields=['urgency_level']),
        ]

    def __str__(self):
        return f"Symptom Check - {self.patient.full_name} - {self.created_at.date()}"


class AIMedicationReminder(models.Model):  # AI-powered medication adherence tracking
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='ai_med_reminders')
    medication_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100, help_text="e.g., twice daily, every 8 hours")
    reminder_times = models.JSONField(default=list, help_text="List of reminder times")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    adherence_rate = models.FloatField(default=0.0, help_text="Percentage of doses taken on time")
    last_taken_at = models.DateTimeField(null=True, blank=True)
    missed_doses = models.IntegerField(default=0)
    ai_insights = models.TextField(blank=True, help_text="AI-generated adherence insights")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'ai_medication_reminders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient', 'is_active']),
            models.Index(fields=['-start_date']),
        ]

    def __str__(self):
        return f"{self.medication_name} - {self.patient.full_name}"


class AIHealthRiskAssessment(models.Model):  # AI-based health risk predictions
    RISK_CATEGORY_CHOICES = [
        ('cardiovascular', 'Cardiovascular Disease'),
        ('diabetes', 'Diabetes'),
        ('hypertension', 'Hypertension'),
        ('obesity', 'Obesity'),
        ('mental_health', 'Mental Health'),
        ('general', 'General Health'),
    ]

    RISK_LEVEL_CHOICES = [
        ('low', 'Low Risk'),
        ('moderate', 'Moderate Risk'),
        ('high', 'High Risk'),
        ('very_high', 'Very High Risk'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='health_risk_assessments')
    risk_category = models.CharField(max_length=50, choices=RISK_CATEGORY_CHOICES)
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES)
    risk_score = models.FloatField(help_text="Numerical risk score 0-100")
    risk_factors = models.JSONField(default=list, help_text="Contributing risk factors")
    prevention_recommendations = models.TextField()
    lifestyle_modifications = models.JSONField(default=list)
    follow_up_actions = models.TextField(blank=True)
    assessed_at = models.DateTimeField(default=timezone.now)
    next_assessment_date = models.DateField(null=True, blank=True)
    is_shared_with_doctor = models.BooleanField(default=False)

    class Meta:
        db_table = 'ai_health_risk_assessments'
        ordering = ['-assessed_at']
        indexes = [
            models.Index(fields=['patient', '-assessed_at']),
            models.Index(fields=['risk_level', 'risk_category']),
        ]

    def __str__(self):
        return f"{self.risk_category} - {self.patient.full_name} - {self.risk_level}"


class AIAppointmentSuggestion(models.Model):  # AI-suggested appointments based on health data
    SUGGESTION_REASON_CHOICES = [
        ('overdue_checkup', 'Overdue Checkup'),
        ('symptom_pattern', 'Symptom Pattern Detected'),
        ('preventive_care', 'Preventive Care'),
        ('follow_up', 'Follow-up Required'),
        ('medication_review', 'Medication Review'),
        ('health_risk', 'Health Risk Identified'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='ai_appointment_suggestions')
    suggested_doctor = models.ForeignKey(DoctorData, on_delete=models.SET_NULL, null=True, blank=True)
    suggested_specialty = models.CharField(max_length=100, blank=True)
    reason = models.CharField(max_length=50, choices=SUGGESTION_REASON_CHOICES)
    explanation = models.TextField()
    urgency = models.CharField(max_length=20, default='normal')
    confidence_score = models.FloatField(default=0.0)
    suggested_at = models.DateTimeField(default=timezone.now)
    is_accepted = models.BooleanField(default=False)
    is_dismissed = models.BooleanField(default=False)
    appointment_created = models.BooleanField(default=False)

    class Meta:
        db_table = 'ai_appointment_suggestions'
        ordering = ['-suggested_at']
        indexes = [
            models.Index(fields=['patient', '-suggested_at']),
            models.Index(fields=['is_dismissed', 'is_accepted']),
        ]

    def __str__(self):
        return f"Suggestion for {self.patient.full_name} - {self.reason}"


class AIFeedback(models.Model):  # User feedback on AI interactions for improvement
    FEEDBACK_TYPE_CHOICES = [
        ('helpful', 'Helpful'),
        ('not_helpful', 'Not Helpful'),
        ('inaccurate', 'Inaccurate'),
        ('inappropriate', 'Inappropriate'),
    ]

    FEATURE_TYPE_CHOICES = [
        ('chat', 'Chat Assistant'),
        ('symptom_checker', 'Symptom Checker'),
        ('health_insight', 'Health Insight'),
        ('medication_reminder', 'Medication Reminder'),
        ('risk_assessment', 'Risk Assessment'),
        ('appointment_suggestion', 'Appointment Suggestion'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='ai_feedback')
    feature_type = models.CharField(max_length=50, choices=FEATURE_TYPE_CHOICES)
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_TYPE_CHOICES)
    rating = models.IntegerField(null=True, blank=True, help_text="1-5 star rating")
    comment = models.TextField(blank=True)
    related_conversation = models.ForeignKey(AIConversation, on_delete=models.SET_NULL, null=True, blank=True)
    related_insight = models.ForeignKey(AIHealthInsight, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    is_reviewed = models.BooleanField(default=False)

    class Meta:
        db_table = 'ai_feedback'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['feature_type', '-created_at']),
            models.Index(fields=['feedback_type', 'rating']),
        ]

    def __str__(self):
        return f"{self.feature_type} - {self.feedback_type} - {self.participant.full_name}"


class AIMedicalDocumentAnalysis(models.Model):  # AI analysis of uploaded medical documents
    DOCUMENT_TYPE_CHOICES = [
        ('lab_result', 'Laboratory Result'),
        ('imaging_report', 'Imaging Report'),
        ('prescription', 'Prescription'),
        ('consultation_note', 'Consultation Note'),
        ('discharge_summary', 'Discharge Summary'),
        ('pathology_report', 'Pathology Report'),
        ('vaccination_record', 'Vaccination Record'),
        ('other', 'Other Medical Document'),
    ]
    
    ANALYSIS_STATUS_CHOICES = [
        ('pending', 'Pending Analysis'),
        ('processing', 'Processing'),
        ('completed', 'Analysis Completed'),
        ('failed', 'Analysis Failed'),
        ('needs_review', 'Needs Doctor Review'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='ai_document_analyses')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    document_reference = models.UUIDField(help_text="Reference to DocumentUpload in health_records")
    file_name = models.CharField(max_length=255)
    
    # Extracted Information
    extracted_text = models.TextField(blank=True, help_text="OCR/Extracted text from document")
    extracted_data = models.JSONField(default=dict, blank=True, help_text="Structured data extracted")
    
    # AI Analysis
    ai_summary = models.TextField(blank=True, help_text="AI-generated summary")
    key_findings = models.JSONField(default=list, blank=True, help_text="Key medical findings")
    identified_conditions = models.JSONField(default=list, blank=True)
    medications_identified = models.JSONField(default=list, blank=True)
    test_results = models.JSONField(default=list, blank=True, help_text="Lab test results with values")
    abnormal_flags = models.JSONField(default=list, blank=True, help_text="Abnormal or concerning values")
    
    # Recommendations
    recommendations = models.TextField(blank=True)
    follow_up_needed = models.BooleanField(default=False)
    urgency_level = models.CharField(max_length=20, default='normal')
    
    # Analysis metadata
    analysis_status = models.CharField(max_length=20, choices=ANALYSIS_STATUS_CHOICES, default='pending')
    confidence_score = models.FloatField(default=0.0)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    # Disclaimer
    disclaimer_shown = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'ai_medical_document_analyses'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient', '-created_at']),
            models.Index(fields=['analysis_status']),
        ]

    def __str__(self):
        return f"{self.document_type} Analysis - {self.patient.full_name}"


class AIEHRDataAnalysis(models.Model):  # Comprehensive EHR data analysis using PyHealth
    ANALYSIS_TYPE_CHOICES = [
        ('risk_prediction', 'Disease Risk Prediction'),
        ('readmission_risk', 'Hospital Readmission Risk'),
        ('medication_interaction', 'Medication Interaction Analysis'),
        ('disease_progression', 'Disease Progression Analysis'),
        ('treatment_recommendation', 'Treatment Recommendation'),
        ('outcome_prediction', 'Outcome Prediction'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='ai_ehr_analyses')
    analysis_type = models.CharField(max_length=50, choices=ANALYSIS_TYPE_CHOICES)
    
    # Input Data Summary
    data_sources_used = models.JSONField(default=list, help_text="List of data sources: demographics, vitals, labs, etc.")
    timeframe_analyzed = models.JSONField(default=dict, help_text="Start and end dates of data analyzed")
    
    # PyHealth Model Results
    model_used = models.CharField(max_length=100, help_text="PyHealth model name")
    predictions = models.JSONField(default=dict, help_text="Model predictions with probabilities")
    risk_scores = models.JSONField(default=dict, help_text="Risk scores for various conditions")
    
    # Clinical Interpretation
    interpretation = models.TextField(help_text="Clinical interpretation of results")
    risk_factors_identified = models.JSONField(default=list)
    protective_factors = models.JSONField(default=list)
    recommendations = models.TextField()
    
    # Model Metadata
    model_confidence = models.FloatField(default=0.0)
    model_version = models.CharField(max_length=50)
    feature_importance = models.JSONField(default=dict, blank=True)
    
    # Review and Validation
    reviewed_by_doctor = models.ForeignKey(DoctorData, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_ehr_analyses')
    doctor_notes = models.TextField(blank=True)
    is_validated = models.BooleanField(default=False)
    
    generated_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'ai_ehr_analyses'
        ordering = ['-generated_at']
        verbose_name = 'AI EHR Analysis'
        verbose_name_plural = 'AI EHR Analyses'
        indexes = [
            models.Index(fields=['patient', '-generated_at']),
            models.Index(fields=['analysis_type']),
        ]

    def __str__(self):
        return f"{self.analysis_type} - {self.patient.full_name}"


class AIConsolidatedHealthReport(models.Model):  # Comprehensive health report combining all patient data
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='ai_health_reports')
    
    # Report Metadata
    report_date = models.DateField(default=timezone.now)
    report_type = models.CharField(max_length=50, default='comprehensive')
    generated_for_doctor = models.ForeignKey(DoctorData, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Data Summary
    data_sources_count = models.IntegerField(default=0)
    records_analyzed = models.JSONField(default=dict, help_text="Count of each type of record analyzed")
    date_range_covered = models.JSONField(default=dict)
    
    # Health Status Overview
    overall_health_score = models.FloatField(null=True, blank=True, help_text="0-100 health score")
    health_status_summary = models.TextField()
    
    # Key Findings
    active_conditions = models.JSONField(default=list)
    current_medications = models.JSONField(default=list)
    recent_lab_results = models.JSONField(default=list)
    recent_vitals = models.JSONField(default=dict)
    allergies_and_contraindications = models.JSONField(default=list)
    
    # Risk Assessment
    high_risk_conditions = models.JSONField(default=list)
    medium_risk_conditions = models.JSONField(default=list)
    protective_factors = models.JSONField(default=list)
    
    # Trends and Patterns
    health_trends = models.JSONField(default=list, help_text="Identified trends over time")
    concerning_patterns = models.JSONField(default=list)
    positive_improvements = models.JSONField(default=list)
    
    # Recommendations
    priority_recommendations = models.JSONField(default=list)
    lifestyle_recommendations = models.JSONField(default=list)
    screening_recommendations = models.JSONField(default=list)
    follow_up_needed = models.JSONField(default=list)
    
    # Clinical Summary for Doctors
    doctor_summary = models.TextField(blank=True, help_text="Technical summary for healthcare providers")
    clinical_decision_support = models.JSONField(default=dict, blank=True)
    
    # Report Metadata
    confidence_level = models.FloatField(default=0.0)
    completeness_score = models.FloatField(default=0.0, help_text="How complete is the patient data")
    ai_models_used = models.JSONField(default=list)
    
    generated_at = models.DateTimeField(default=timezone.now)
    last_updated = models.DateTimeField(auto_now=True)
    
    # Sharing and Access
    shared_with_doctors = models.ManyToManyField(DoctorData, related_name='accessible_ai_reports', blank=True)
    is_patient_visible = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'ai_consolidated_health_reports'
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['patient', '-report_date']),
        ]

    def __str__(self):
        return f"Health Report - {self.patient.full_name} - {self.report_date}"


class AIDoctorAssistant(models.Model):  # AI assistant for doctors during diagnosis and treatment
    ASSISTANCE_TYPE_CHOICES = [
        ('diagnosis_support', 'Diagnosis Support'),
        ('treatment_plan', 'Treatment Plan Recommendation'),
        ('drug_interaction', 'Drug Interaction Check'),
        ('differential_diagnosis', 'Differential Diagnosis'),
        ('clinical_guideline', 'Clinical Guideline Recommendation'),
        ('lab_interpretation', 'Lab Result Interpretation'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(DoctorData, on_delete=models.CASCADE, related_name='ai_assistance_requests')
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='doctor_ai_consultations')
    assistance_type = models.CharField(max_length=50, choices=ASSISTANCE_TYPE_CHOICES)
    
    # Input Context
    clinical_question = models.TextField(help_text="Doctor's question or request")
    patient_context = models.JSONField(default=dict, help_text="Relevant patient information")
    symptoms_provided = models.JSONField(default=list, blank=True)
    current_findings = models.JSONField(default=dict, blank=True)
    
    # AI Analysis
    ai_response = models.TextField(help_text="AI-generated response")
    suggested_diagnoses = models.JSONField(default=list, blank=True)
    suggested_tests = models.JSONField(default=list, blank=True)
    suggested_treatments = models.JSONField(default=list, blank=True)
    drug_interactions_found = models.JSONField(default=list, blank=True)
    clinical_guidelines_referenced = models.JSONField(default=list, blank=True)
    
    # Evidence and References
    evidence_level = models.CharField(max_length=20, blank=True)
    medical_references = models.JSONField(default=list, blank=True, help_text="Research papers, guidelines")
    similar_cases = models.JSONField(default=list, blank=True)
    
    # Doctor Feedback
    was_helpful = models.BooleanField(null=True, blank=True)
    doctor_notes = models.TextField(blank=True)
    action_taken = models.TextField(blank=True, help_text="What action doctor took based on AI advice")
    
    confidence_score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'ai_doctor_assistant'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['doctor', '-created_at']),
            models.Index(fields=['patient', '-created_at']),
        ]

    def __str__(self):
        return f"{self.assistance_type} - Dr. {self.doctor.participant.full_name} - {self.patient.full_name}"


class AIInsight(models.Model):  # Organization-level AI insights (hospitals, pharmacies, insurance)
    CATEGORY_CHOICES = [
        ('patient_flow', 'Patient Flow'),
        ('resource_utilization', 'Resource Utilization'),
        ('revenue_optimization', 'Revenue Optimization'),
        ('quality_metrics', 'Quality Metrics'),
        ('hr_analytics', 'HR Analytics'),
        ('financial_analytics', 'Financial Analytics'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='ai_insights')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    insight_text = models.TextField()
    recommendation = models.TextField(blank=True)
    metric_name = models.CharField(max_length=100, blank=True)
    metric_value = models.CharField(max_length=100, blank=True)
    trend = models.CharField(max_length=50, blank=True)  # increasing, decreasing, stable
    confidence_score = models.FloatField(default=0.0)
    is_dismissed = models.BooleanField(default=False)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'ai_insights'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', '-created_at']),
            models.Index(fields=['category', 'priority']),
            models.Index(fields=['is_dismissed']),
        ]

    def __str__(self):
        return f"{self.category} - {self.organization.full_name}"


class AIFeature(models.Model):  # Track AI feature usage and status
    FEATURE_TYPE_CHOICES = [
        ('chat', 'Chat Assistant'),
        ('health_insights', 'Health Insights'),
        ('symptom_checker', 'Symptom Checker'),
        ('medication_reminder', 'Medication Reminder'),
        ('risk_assessment', 'Risk Assessment'),
        ('hr_analytics', 'HR Analytics'),
        ('financial_analytics', 'Financial Analytics'),
        ('diagnostic_analysis', 'Diagnostic Analysis'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=50, choices=FEATURE_TYPE_CHOICES)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    usage_count = models.IntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'ai_features'
        ordering = ['name']
        indexes = [
            models.Index(fields=['type', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.type})"


class AIModelPerformance(models.Model):  # Track AI model performance and accuracy
    model_name = models.CharField(max_length=100)
    model_version = models.CharField(max_length=50)
    model_type = models.CharField(max_length=100, help_text="PyHealth, Transformer, Custom, etc.")
    
    # Performance Metrics
    accuracy = models.FloatField(null=True, blank=True)
    precision = models.FloatField(null=True, blank=True)
    recall = models.FloatField(null=True, blank=True)
    f1_score = models.FloatField(null=True, blank=True)
    auc_roc = models.FloatField(null=True, blank=True, help_text="Area Under ROC Curve")
    
    # Usage Statistics
    total_predictions = models.IntegerField(default=0)
    successful_predictions = models.IntegerField(default=0)
    failed_predictions = models.IntegerField(default=0)
    average_confidence = models.FloatField(default=0.0)
    
    # Validation
    validated_by_doctors = models.IntegerField(default=0)
    doctor_agreement_rate = models.FloatField(null=True, blank=True)
    
    # Metadata
    last_evaluation_date = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'ai_model_performance'
        ordering = ['-last_evaluation_date']
        unique_together = ['model_name', 'model_version']
        indexes = [
            models.Index(fields=['is_active', '-last_evaluation_date']),
            models.Index(fields=['model_type']),
        ]

    def __str__(self):
        return f"{self.model_name} v{self.model_version}"
