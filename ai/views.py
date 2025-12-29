from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import render
from django.views.generic import TemplateView
from django.utils import timezone
from core.mixins import PatientRequiredMixin
from .models import (
    AIConversation, AIChatMessage, AIHealthInsight, AISymptomChecker,
    AIMedicationReminder, AIHealthRiskAssessment, AIAppointmentSuggestion, AIFeedback
)
from .serializers import (
    AIConversationSerializer, AIChatMessageSerializer, AIHealthInsightSerializer,
    AISymptomCheckerSerializer, AIMedicationReminderSerializer, AIHealthRiskAssessmentSerializer,
    AIAppointmentSuggestionSerializer, AIFeedbackSerializer, AIChatRequestSerializer,
    AIChatResponseSerializer
)
from .services import AIAssistantService


class AIAssistantPageView(PatientRequiredMixin, TemplateView):  # AI Assistant chat interface
    template_name = "patient/ai_assistant.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        participant = self.request.user
        # Use existing AIHealthInsight model instead of missing AIConversation
        context['recent_insights'] = AIHealthInsight.objects.filter(
            patient=participant,
            is_read=False
        ).order_by('-generated_at')[:5]
        return context


class AIChatAPIView(APIView):  # API endpoint for AI chat functionality
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = AIChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        message = serializer.validated_data['message']
        conversation_id = serializer.validated_data.get('conversation_id')
        
        try:
            result = AIAssistantService.process_chat_message(
                participant=request.user,
                message=message,
                conversation_id=conversation_id
            )
            
            response_serializer = AIChatResponseSerializer(data=result)
            if response_serializer.is_valid():
                return Response(response_serializer.data, status=status.HTTP_200_OK)
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': 'Une erreur s\'est produite lors du traitement de votre message.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AIConversationViewSet(viewsets.ModelViewSet):  # ViewSet for AI conversations
    serializer_class = AIConversationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return AIConversation.objects.filter(participant=self.request.user)
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        conversation = self.get_object()
        conversation.status = 'archived'
        conversation.save()
        return Response({'status': 'archived'})
    
    @action(detail=True, methods=['post'])
    def escalate(self, request, pk=None):
        conversation = self.get_object()
        conversation.status = 'escalated'
        conversation.escalated_to_staff = True
        conversation.escalated_at = timezone.now()
        conversation.save()
        return Response({'status': 'escalated to human support'})


class AIHealthInsightViewSet(viewsets.ModelViewSet):  # ViewSet for AI health insights
    serializer_class = AIHealthInsightSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return AIHealthInsight.objects.filter(patient=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        insight = self.get_object()
        insight.is_read = True
        insight.save()
        return Response({'status': 'marked as read'})
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        insights = self.get_queryset().filter(is_read=False)
        serializer = self.get_serializer(insights, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def high_priority(self, request):
        insights = self.get_queryset().filter(priority__in=['high', 'urgent'], is_read=False)
        serializer = self.get_serializer(insights, many=True)
        return Response(serializer.data)


class AISymptomCheckerViewSet(viewsets.ModelViewSet):  # ViewSet for symptom checker
    serializer_class = AISymptomCheckerSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return AISymptomChecker.objects.filter(patient=self.request.user)
    
    def create(self, request, *args, **kwargs):
        symptoms = request.data.get('symptoms', [])
        additional_info = request.data.get('additional_info', {})
        
        if not symptoms:
            return Response(
                {'error': 'Veuillez fournir au moins un symptôme'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        symptom_check = AIAssistantService.check_symptoms(
            patient=request.user,
            symptoms=symptoms,
            additional_info=additional_info
        )
        
        serializer = self.get_serializer(symptom_check)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def mark_followed_up(self, request, pk=None):
        symptom_check = self.get_object()
        symptom_check.followed_up = True
        symptom_check.save()
        return Response({'status': 'marked as followed up'})


class AIMedicationReminderViewSet(viewsets.ModelViewSet):  # ViewSet for medication reminders
    serializer_class = AIMedicationReminderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return AIMedicationReminder.objects.filter(patient=self.request.user)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        reminders = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(reminders, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def log_dose(self, request, pk=None):
        reminder = self.get_object()
        reminder.last_taken_at = timezone.now()
        reminder.save()
        return Response({'status': 'dose logged', 'taken_at': reminder.last_taken_at})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        reminder = self.get_object()
        reminder.is_active = False
        reminder.save()
        return Response({'status': 'deactivated'})


class AIHealthRiskAssessmentViewSet(viewsets.ModelViewSet):  # ViewSet for health risk assessments
    serializer_class = AIHealthRiskAssessmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return AIHealthRiskAssessment.objects.filter(patient=self.request.user)
    
    @action(detail=False, methods=['get'])
    def high_risk(self, request):
        assessments = self.get_queryset().filter(risk_level__in=['high', 'very_high'])
        serializer = self.get_serializer(assessments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def share_with_doctor(self, request, pk=None):
        assessment = self.get_object()
        assessment.is_shared_with_doctor = True
        assessment.save()
        return Response({'status': 'shared with doctor'})


class AIAppointmentSuggestionViewSet(viewsets.ModelViewSet):  # ViewSet for appointment suggestions
    serializer_class = AIAppointmentSuggestionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return AIAppointmentSuggestion.objects.filter(patient=self.request.user)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        suggestions = self.get_queryset().filter(
            is_accepted=False,
            is_dismissed=False
        )
        serializer = self.get_serializer(suggestions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        suggestion = self.get_object()
        suggestion.is_accepted = True
        suggestion.save()
        return Response({'status': 'accepted'})
    
    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        suggestion = self.get_object()
        suggestion.is_dismissed = True
        suggestion.save()
        return Response({'status': 'dismissed'})


class AIFeedbackViewSet(viewsets.ModelViewSet):  # ViewSet for AI feedback
    serializer_class = AIFeedbackSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return AIFeedback.objects.filter(participant=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(participant=self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_health_recommendations(request):
    """Generate personalized health recommendations"""
    try:
        recommendations = AIAssistantService.generate_personalized_recommendations(request.user)
        return Response({
            'recommendations': recommendations,
            'count': len(recommendations)
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': 'Une erreur s\'est produite lors de la génération des recommandations.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class SymptomCheckerPageView(PatientRequiredMixin, TemplateView):
    '''Symptom checker interface page'''
    template_name = 'patient/symptom_checker.html'


class HealthInsightsPageView(PatientRequiredMixin, TemplateView):
    '''Health insights dashboard page'''
    template_name = 'patient/health_insights.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['insights'] = AIHealthInsight.objects.filter(
            patient=self.request.user
        ).order_by('-generated_at')[:20]
        context['unread_count'] = AIHealthInsight.objects.filter(
            patient=self.request.user,
            is_read=False
        ).count()
        return context


class AIAnalyticsViewSet(viewsets.ViewSet):
    """
    Central AI Analytics ViewSet
    Provides unified insights from all modules (HR, Financial, Hospital, Patient)
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def unified_insights(self, request):
        """
        GET /api/ai/analytics/unified_insights/

        Aggregates AI insights from all modules:
        - HR Module (employee churn, performance, attendance)
        - Financial Module (budget variance, cash flow, anomalies)
        - Hospital Module (bed occupancy, staffing, maintenance)
        - Patient Module (health insights)

        Returns unified dashboard data sorted by priority
        """
        user = request.user

        # Verify user is an organization
        if not hasattr(user, 'role') or user.role not in ['hospital', 'pharmacy', 'insurance_company', 'clinic']:
            return Response(
                {'error': 'This endpoint is only accessible to organizations'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            insights_data = AIAssistantService.get_unified_insights(user)
            return Response(insights_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {
                    'error': 'An error occurred while generating unified insights',
                    'detail': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def diagnostic_analysis(self, request):
        """
        GET /api/ai/analytics/diagnostic_analysis/?days_back=365

        ML-powered diagnostic interpretation for patients (Phase 5)
        Analyzes diagnosis patterns, severity, and health risks
        """
        user = request.user

        # Only patients can access their own diagnostic analysis
        if user.role != 'patient':
            return Response(
                {'error': 'This endpoint is only accessible to patients'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            from ml_models.diagnostic_analyzer import DiagnosticAnalyzer

            days_back = int(request.query_params.get('days_back', 365))
            if days_back < 30 or days_back > 1095:  # 30 days to 3 years
                return Response(
                    {'error': 'days_back must be between 30 and 1095'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            analysis = DiagnosticAnalyzer.analyze_patient_diagnostics(user, days_back)
            return Response(analysis, status=status.HTTP_200_OK)

        except ImportError:
            return Response(
                {'error': 'ML diagnostic analyzer not available'},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        except Exception as e:
            return Response(
                {
                    'error': 'Diagnostic analysis failed',
                    'detail': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def lab_interpretation(self, request):
        """
        GET /api/ai/analytics/lab_interpretation/?days_back=90

        ML-powered lab result interpretation (Phase 5)
        Detects abnormal patterns and provides health insights
        """
        user = request.user

        if user.role != 'patient':
            return Response(
                {'error': 'This endpoint is only accessible to patients'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            from ml_models.diagnostic_analyzer import DiagnosticAnalyzer

            days_back = int(request.query_params.get('days_back', 90))
            if days_back < 30 or days_back > 365:
                return Response(
                    {'error': 'days_back must be between 30 and 365'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            interpretation = DiagnosticAnalyzer.interpret_lab_results(user, days_back)
            return Response(interpretation, status=status.HTTP_200_OK)

        except ImportError:
            return Response(
                {'error': 'ML diagnostic analyzer not available'},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        except Exception as e:
            return Response(
                {
                    'error': 'Lab interpretation failed',
                    'detail': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def health_risk_prediction(self, request):
        """
        GET /api/ai/analytics/health_risk_prediction/

        ML-powered health risk prediction (Phase 5)
        Predicts future health risks based on diagnostic and lab history
        """
        user = request.user

        if user.role != 'patient':
            return Response(
                {'error': 'This endpoint is only accessible to patients'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            from ml_models.diagnostic_analyzer import DiagnosticAnalyzer

            prediction = DiagnosticAnalyzer.predict_health_risks(user)
            return Response(prediction, status=status.HTTP_200_OK)

        except ImportError:
            return Response(
                {'error': 'ML diagnostic analyzer not available'},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        except Exception as e:
            return Response(
                {
                    'error': 'Health risk prediction failed',
                    'detail': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def comprehensive_health_analysis(self, request):
        """
        GET /api/ai/analytics/comprehensive_health_analysis/?days_back=365

        ML-powered comprehensive health record analysis (Phase 5)
        Analyzes all health record types for complete health picture
        """
        user = request.user

        if user.role != 'patient':
            return Response(
                {'error': 'This endpoint is only accessible to patients'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            from ml_models.health_record_analyzer import HealthRecordAnalyzer

            days_back = int(request.query_params.get('days_back', 365))
            if days_back < 90 or days_back > 1095:  # 90 days to 3 years
                return Response(
                    {'error': 'days_back must be between 90 and 1095'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            analysis = HealthRecordAnalyzer.comprehensive_health_analysis(user, days_back)
            return Response(analysis, status=status.HTTP_200_OK)

        except ImportError:
            return Response(
                {'error': 'ML health record analyzer not available'},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        except Exception as e:
            return Response(
                {
                    'error': 'Health record analysis failed',
                    'detail': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def predict_healthcare_needs(self, request):
        """
        GET /api/ai/analytics/predict_healthcare_needs/?months_forward=6

        ML-powered healthcare needs prediction (Phase 5)
        Predicts upcoming healthcare needs and appointments
        """
        user = request.user

        if user.role != 'patient':
            return Response(
                {'error': 'This endpoint is only accessible to patients'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            from ml_models.health_record_analyzer import HealthRecordAnalyzer

            months_forward = int(request.query_params.get('months_forward', 6))
            if months_forward < 1 or months_forward > 12:
                return Response(
                    {'error': 'months_forward must be between 1 and 12'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            prediction = HealthRecordAnalyzer.predict_healthcare_needs(user, months_forward)
            return Response(prediction, status=status.HTTP_200_OK)

        except ImportError:
            return Response(
                {'error': 'ML health record analyzer not available'},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        except Exception as e:
            return Response(
                {
                    'error': 'Healthcare needs prediction failed',
                    'detail': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
