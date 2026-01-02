from rest_framework import serializers
from .models import (
    AIConversation, AIChatMessage, AIHealthInsight, AISymptomChecker,
    AIMedicationReminder, AIHealthRiskAssessment, AIAppointmentSuggestion, AIFeedback,
    AIMedicalDocumentAnalysis, AIEHRDataAnalysis, AIConsolidatedHealthReport,
    AIDoctorAssistant, AIModelPerformance
)


class AIChatMessageSerializer(serializers.ModelSerializer):  # Serializer for AI chat messages
    class Meta:
        model = AIChatMessage
        fields = ['id', 'conversation', 'message_type', 'content', 'metadata', 'timestamp', 'is_flagged']
        read_only_fields = ['id', 'timestamp']


class AIConversationSerializer(serializers.ModelSerializer):  # Serializer for AI conversations
    messages = AIChatMessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AIConversation
        fields = ['id', 'participant', 'title', 'status', 'started_at', 'last_message_at', 
                  'escalated_to_staff', 'escalated_at', 'sentiment_score', 'messages', 'message_count']
        read_only_fields = ['id', 'started_at', 'last_message_at']
    
    def get_message_count(self, obj) -> int:
        return obj.messages.count()


class AIHealthInsightSerializer(serializers.ModelSerializer):  # Serializer for AI health insights
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.participant.full_name', read_only=True)
    
    class Meta:
        model = AIHealthInsight
        fields = ['id', 'patient', 'patient_name', 'insight_type', 'title', 'description', 
                  'recommendations', 'data_points_used', 'confidence_score', 'is_read', 'priority',
                  'generated_at', 'expires_at', 'reviewed_by', 'reviewed_by_name', 'reviewed_at', 'is_verified']
        read_only_fields = ['id', 'generated_at']


class AISymptomCheckerSerializer(serializers.ModelSerializer):  # Serializer for symptom checker
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    
    class Meta:
        model = AISymptomChecker
        fields = ['id', 'patient', 'patient_name', 'symptoms', 'additional_info', 'ai_analysis', 
                  'possible_conditions', 'urgency_level', 'recommendations', 'confidence_score',
                  'created_at', 'followed_up']
        read_only_fields = ['id', 'created_at', 'ai_analysis', 'possible_conditions', 
                            'urgency_level', 'recommendations', 'confidence_score']


class AIMedicationReminderSerializer(serializers.ModelSerializer):  # Serializer for medication reminders
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    
    class Meta:
        model = AIMedicationReminder
        fields = ['id', 'patient', 'patient_name', 'medication_name', 'dosage', 'frequency', 
                  'reminder_times', 'start_date', 'end_date', 'is_active', 'adherence_rate',
                  'last_taken_at', 'missed_doses', 'ai_insights', 'created_at']
        read_only_fields = ['id', 'created_at', 'adherence_rate', 'missed_doses', 'ai_insights']


class AIHealthRiskAssessmentSerializer(serializers.ModelSerializer):  # Serializer for health risk assessments
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    
    class Meta:
        model = AIHealthRiskAssessment
        fields = ['id', 'patient', 'patient_name', 'risk_category', 'risk_level', 'risk_score',
                  'risk_factors', 'prevention_recommendations', 'lifestyle_modifications',
                  'follow_up_actions', 'assessed_at', 'next_assessment_date', 'is_shared_with_doctor']
        read_only_fields = ['id', 'assessed_at', 'risk_level', 'risk_score', 'risk_factors',
                            'prevention_recommendations', 'lifestyle_modifications', 'follow_up_actions']


class AIAppointmentSuggestionSerializer(serializers.ModelSerializer):  # Serializer for appointment suggestions
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    doctor_name = serializers.CharField(source='suggested_doctor.participant.full_name', read_only=True)
    
    class Meta:
        model = AIAppointmentSuggestion
        fields = ['id', 'patient', 'patient_name', 'suggested_doctor', 'doctor_name', 
                  'suggested_specialty', 'reason', 'explanation', 'urgency', 'confidence_score',
                  'suggested_at', 'is_accepted', 'is_dismissed', 'appointment_created']
        read_only_fields = ['id', 'suggested_at', 'explanation', 'confidence_score']


class AIFeedbackSerializer(serializers.ModelSerializer):  # Serializer for AI feedback
    participant_name = serializers.CharField(source='participant.full_name', read_only=True)
    
    class Meta:
        model = AIFeedback
        fields = ['id', 'participant', 'participant_name', 'feature_type', 'feedback_type', 
                  'rating', 'comment', 'related_conversation', 'related_insight', 
                  'created_at', 'is_reviewed']
        read_only_fields = ['id', 'created_at']


class AIChatRequestSerializer(serializers.Serializer):  # Serializer for chat requests
    message = serializers.CharField(max_length=2000, required=True)
    conversation_id = serializers.UUIDField(required=False, allow_null=True)


class AIChatResponseSerializer(serializers.Serializer):  # Serializer for chat responses
    response = serializers.CharField()
    conversation_id = serializers.UUIDField()
    message_id = serializers.UUIDField()
    intent = serializers.CharField(required=False)
    confidence = serializers.FloatField(required=False)


class AIMedicalDocumentAnalysisSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    
    class Meta:
        model = AIMedicalDocumentAnalysis
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'processed_at', 'extracted_text', 
                            'extracted_data', 'ai_summary', 'key_findings', 'confidence_score']


class AIEHRDataAnalysisSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by_doctor.participant.full_name', read_only=True)
    
    class Meta:
        model = AIEHRDataAnalysis
        fields = '__all__'
        read_only_fields = ['id', 'generated_at']


class AIConsolidatedHealthReportSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    
    class Meta:
        model = AIConsolidatedHealthReport
        fields = '__all__'
        read_only_fields = ['id', 'generated_at', 'last_updated']


class AIDoctorAssistantSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.participant.full_name', read_only=True)
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    
    class Meta:
        model = AIDoctorAssistant
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'ai_response', 'suggested_diagnoses', 
                            'suggested_tests', 'confidence_score']


class AIModelPerformanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIModelPerformance
        fields = '__all__'
