from django.contrib import admin
from .models import (
    AIConversation, AIChatMessage, AIHealthInsight, AISymptomChecker,
    AIMedicationReminder, AIHealthRiskAssessment, AIAppointmentSuggestion, AIFeedback,
    AIMedicalDocumentAnalysis, AIEHRDataAnalysis, AIConsolidatedHealthReport,
    AIDoctorAssistant, AIModelPerformance
)


@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):  # Admin for AI conversations
    list_display = ['id', 'participant', 'title', 'status', 'started_at', 'last_message_at', 'escalated_to_staff']
    list_filter = ['status', 'escalated_to_staff', 'started_at']
    search_fields = ['participant__email', 'participant__full_name', 'title']
    readonly_fields = ['id', 'started_at', 'last_message_at']
    date_hierarchy = 'started_at'


@admin.register(AIChatMessage)
class AIChatMessageAdmin(admin.ModelAdmin):  # Admin for chat messages
    list_display = ['id', 'conversation', 'message_type', 'content_preview', 'timestamp', 'is_flagged']
    list_filter = ['message_type', 'is_flagged', 'timestamp']
    search_fields = ['content', 'conversation__participant__email']
    readonly_fields = ['id', 'timestamp']
    date_hierarchy = 'timestamp'
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(AIHealthInsight)
class AIHealthInsightAdmin(admin.ModelAdmin):  # Admin for health insights
    list_display = ['id', 'patient', 'insight_type', 'title', 'priority', 'is_read', 'is_verified', 'generated_at']
    list_filter = ['insight_type', 'priority', 'is_read', 'is_verified', 'generated_at']
    search_fields = ['patient__email', 'patient__full_name', 'title', 'description']
    readonly_fields = ['id', 'generated_at']
    date_hierarchy = 'generated_at'
    list_editable = ['is_verified']


@admin.register(AISymptomChecker)
class AISymptomCheckerAdmin(admin.ModelAdmin):  # Admin for symptom checker
    list_display = ['id', 'patient', 'urgency_level', 'confidence_score', 'created_at', 'followed_up']
    list_filter = ['urgency_level', 'followed_up', 'created_at']
    search_fields = ['patient__email', 'patient__full_name']
    readonly_fields = ['id', 'created_at', 'ai_analysis', 'confidence_score']
    date_hierarchy = 'created_at'


@admin.register(AIMedicationReminder)
class AIMedicationReminderAdmin(admin.ModelAdmin):  # Admin for medication reminders
    list_display = ['id', 'patient', 'medication_name', 'frequency', 'is_active', 'adherence_rate', 'missed_doses']
    list_filter = ['is_active', 'created_at']
    search_fields = ['patient__email', 'patient__full_name', 'medication_name']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'


@admin.register(AIHealthRiskAssessment)
class AIHealthRiskAssessmentAdmin(admin.ModelAdmin):  # Admin for risk assessments
    list_display = ['id', 'patient', 'risk_category', 'risk_level', 'risk_score', 'assessed_at', 'is_shared_with_doctor']
    list_filter = ['risk_category', 'risk_level', 'is_shared_with_doctor', 'assessed_at']
    search_fields = ['patient__email', 'patient__full_name']
    readonly_fields = ['id', 'assessed_at']
    date_hierarchy = 'assessed_at'


@admin.register(AIAppointmentSuggestion)
class AIAppointmentSuggestionAdmin(admin.ModelAdmin):  # Admin for appointment suggestions
    list_display = ['id', 'patient', 'reason', 'urgency', 'is_accepted', 'is_dismissed', 'appointment_created', 'suggested_at']
    list_filter = ['reason', 'urgency', 'is_accepted', 'is_dismissed', 'suggested_at']
    search_fields = ['patient__email', 'patient__full_name', 'explanation']
    readonly_fields = ['id', 'suggested_at']
    date_hierarchy = 'suggested_at'


@admin.register(AIFeedback)
class AIFeedbackAdmin(admin.ModelAdmin):  # Admin for AI feedback
    list_display = ['id', 'participant', 'feature_type', 'feedback_type', 'rating', 'is_reviewed', 'created_at']
    list_filter = ['feature_type', 'feedback_type', 'rating', 'is_reviewed', 'created_at']
    search_fields = ['participant__email', 'participant__full_name', 'comment']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
    list_editable = ['is_reviewed']


@admin.register(AIMedicalDocumentAnalysis)
class AIMedicalDocumentAnalysisAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'document_type', 'analysis_status', 'urgency_level', 'created_at']
    list_filter = ['document_type', 'analysis_status', 'urgency_level', 'created_at']
    search_fields = ['patient__email', 'patient__full_name', 'file_name']
    readonly_fields = ['id', 'created_at', 'processed_at', 'extracted_text', 'confidence_score']
    date_hierarchy = 'created_at'


@admin.register(AIEHRDataAnalysis)
class AIEHRDataAnalysisAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'analysis_type', 'model_used', 'is_validated', 'generated_at']
    list_filter = ['analysis_type', 'is_validated', 'generated_at']
    search_fields = ['patient__email', 'patient__full_name']
    readonly_fields = ['id', 'generated_at', 'model_version', 'model_confidence']
    date_hierarchy = 'generated_at'


@admin.register(AIConsolidatedHealthReport)
class AIConsolidatedHealthReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'report_date', 'overall_health_score', 'completeness_score', 'is_patient_visible']
    list_filter = ['report_date', 'is_patient_visible']
    search_fields = ['patient__email', 'patient__full_name']
    readonly_fields = ['id', 'generated_at', 'last_updated']
    date_hierarchy = 'report_date'


@admin.register(AIDoctorAssistant)
class AIDoctorAssistantAdmin(admin.ModelAdmin):
    list_display = ['id', 'doctor', 'patient', 'assistance_type', 'was_helpful', 'confidence_score', 'created_at']
    list_filter = ['assistance_type', 'was_helpful', 'created_at']
    search_fields = ['doctor__participant__email', 'patient__email', 'clinical_question']
    readonly_fields = ['id', 'created_at', 'confidence_score']
    date_hierarchy = 'created_at'


@admin.register(AIModelPerformance)
class AIModelPerformanceAdmin(admin.ModelAdmin):
    list_display = ['model_name', 'model_version', 'accuracy', 'precision', 'recall', 'is_active', 'last_evaluation_date']
    list_filter = ['is_active', 'model_type', 'last_evaluation_date']
    search_fields = ['model_name', 'model_version']
    readonly_fields = ['last_evaluation_date']
    date_hierarchy = 'last_evaluation_date'
