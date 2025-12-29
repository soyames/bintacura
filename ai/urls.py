from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'ai'

router = DefaultRouter()
router.register(r'conversations', views.AIConversationViewSet, basename='conversation')
router.register(r'insights', views.AIHealthInsightViewSet, basename='insight')
router.register(r'symptom-checker', views.AISymptomCheckerViewSet, basename='symptom-checker')
router.register(r'medication-reminders', views.AIMedicationReminderViewSet, basename='medication-reminder')
router.register(r'risk-assessments', views.AIHealthRiskAssessmentViewSet, basename='risk-assessment')
router.register(r'appointment-suggestions', views.AIAppointmentSuggestionViewSet, basename='appointment-suggestion')
router.register(r'feedback', views.AIFeedbackViewSet, basename='feedback')
router.register(r'analytics', views.AIAnalyticsViewSet, basename='analytics')

urlpatterns = [
    path('', include(router.urls)),
    path('chat/', views.AIChatAPIView.as_view(), name='ai-chat'),
    path('assistant/', views.AIAssistantPageView.as_view(), name='assistant-page'),
    path('symptom-checker-page/', views.SymptomCheckerPageView.as_view(), name='symptom-checker-page'),
    path('health-insights-page/', views.HealthInsightsPageView.as_view(), name='health-insights-page'),
    path('recommendations/generate/', views.generate_health_recommendations, name='generate-recommendations'),
]
