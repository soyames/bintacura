from django.utils import timezone
from datetime import timedelta
import random
from .models import (
    AIConversation, AIChatMessage, AIHealthInsight, AISymptomChecker,
    AI_DISCLAIMER, AI_SHORT_DISCLAIMER
)


class AIAssistantService:
    """Service for AI-powered healthcare assistant functionality"""
    
    @staticmethod
    def process_chat_message(participant, message, conversation_id=None):
        """
        Process user message and generate AI response with context retention (Phase 9)
        Maintains conversation history and context across multiple messages
        """

        # Get or create conversation
        if conversation_id:
            try:
                conversation = AIConversation.objects.get(id=conversation_id, participant=participant)
            except AIConversation.DoesNotExist:
                conversation = AIConversation.objects.create(
                    participant=participant,
                    title=message[:50] + "..." if len(message) > 50 else message
                )
        else:
            conversation = AIConversation.objects.create(
                participant=participant,
                title=message[:50] + "..." if len(message) > 50 else message
            )

        # Build conversation context from recent messages (last 5 messages)
        recent_messages = AIChatMessage.objects.filter(
            conversation=conversation
        ).order_by('-created_at')[:5]

        conversation_context = {
            'message_count': conversation.messages.count(),
            'last_intent': None,
            'recent_topics': [],
            'conversation_history': []
        }

        # Extract context from recent messages
        for msg in reversed(list(recent_messages)):  # Chronological order
            if msg.message_type == 'ai' and msg.metadata:
                if not conversation_context['last_intent']:
                    conversation_context['last_intent'] = msg.metadata.get('intent')

                intent = msg.metadata.get('intent')
                if intent and intent not in conversation_context['recent_topics']:
                    conversation_context['recent_topics'].append(intent)

            conversation_context['conversation_history'].append({
                'type': msg.message_type,
                'content': msg.content[:100],  # Truncate for context
                'timestamp': msg.created_at
            })

        # Save user message
        user_message = AIChatMessage.objects.create(
            conversation=conversation,
            message_type='user',
            content=message
        )

        # Analyze intent with conversation context
        intent, entities, confidence = AIAssistantService._analyze_intent(message, conversation_context)

        # Generate context-aware response
        response_text = AIAssistantService._generate_response(
            participant, message, intent, entities, conversation_context
        )

        # Save AI response with enriched metadata
        ai_message = AIChatMessage.objects.create(
            conversation=conversation,
            message_type='ai',
            content=response_text,
            metadata={
                'intent': intent,
                'entities': entities,
                'confidence': confidence,
                'context_used': {
                    'last_intent': conversation_context.get('last_intent'),
                    'message_count': conversation_context.get('message_count'),
                    'has_context': len(conversation_context['recent_topics']) > 0
                }
            }
        )

        # Update conversation
        conversation.last_message_at = timezone.now()
        conversation.save()

        return {
            'response': response_text,
            'conversation_id': str(conversation.id),
            'message_id': str(ai_message.id),
            'intent': intent,
            'confidence': confidence,
            'context_aware': len(conversation_context['recent_topics']) > 0
        }
    
    @staticmethod
    def _analyze_intent(message, conversation_context=None):
        """
        Enhanced intent analysis with comprehensive keyword patterns (Phase 9)
        Supports French and English with multi-pattern matching and context awareness
        """
        message_lower = message.lower()

        # Enhanced intent mapping with more keywords and variations
        intents = {
            'appointment': {
                'keywords': ['rendez-vous', 'appointment', 'rdv', 'consulter', 'voir docteur',
                           'doctor visit', 'consultation', 'booking', 'réserver', 'schedule',
                           'médecin', 'physician', 'checkup', 'bilan'],
                'patterns': ['quand puis-je', 'when can i', 'je veux voir', 'i want to see',
                           'prendre rdv', 'make appointment', 'book', 'réserver un']
            },
            'prescription': {
                'keywords': ['ordonnance', 'prescription', 'médicament', 'medication', 'medicine',
                           'drug', 'pilule', 'pill', 'traitement', 'treatment', 'pharmacie', 'pharmacy'],
                'patterns': ['mes médicaments', 'my medications', 'besoin de', 'need prescription',
                           'renouveler', 'refill', 'commander', 'order']
            },
            'symptom': {
                'keywords': ['symptôme', 'symptom', 'douleur', 'pain', 'mal', 'sick', 'malade',
                           'ill', 'fièvre', 'fever', 'toux', 'cough', 'fatigue', 'tired',
                           'nausée', 'nausea', 'vomit', 'headache', 'migraine'],
                'patterns': ['je me sens', 'i feel', 'j\'ai mal', 'i have pain', 'ça fait mal',
                           'it hurts', 'je souffre', 'i suffer', 'je suis malade', 'i am sick']
            },
            'insurance': {
                'keywords': ['assurance', 'insurance', 'couverture', 'coverage', 'remboursement',
                           'reimbursement', 'claim', 'réclamation', 'mutuelle', 'policy'],
                'patterns': ['mon assurance', 'my insurance', 'suis-je couvert', 'am i covered',
                           'combien coûte', 'how much cost']
            },
            'billing': {
                'keywords': ['facture', 'paiement', 'payment', 'bill', 'invoice', 'pay', 'payer',
                           'coût', 'cost', 'prix', 'price', 'tarif', 'fee', 'charge'],
                'patterns': ['combien dois-je', 'how much do i', 'payer ma facture', 'pay my bill',
                           'montant', 'amount', 'solde', 'balance']
            },
            'health_record': {
                'keywords': ['dossier', 'record', 'historique', 'history', 'medical record',
                           'dossier médical', 'mes résultats', 'my results', 'rapport', 'report'],
                'patterns': ['voir mon dossier', 'see my records', 'mes analyses', 'my tests',
                           'résultats de', 'results of', 'historique médical', 'medical history']
            },
            'lab_results': {
                'keywords': ['analyse', 'lab', 'laboratoire', 'test', 'résultat', 'result',
                           'blood test', 'prise de sang', 'examen', 'examination'],
                'patterns': ['résultats d\'analyse', 'lab results', 'mes tests', 'my tests']
            },
            'emergency': {
                'keywords': ['urgence', 'emergency', 'urgent', 'grave', 'serious', 'critical',
                           'critique', 'danger', 'help me', 'aidez-moi', 'au secours'],
                'patterns': ['c\'est urgent', 'it\'s urgent', 'j\'ai besoin d\'aide', 'i need help']
            },
            'greeting': {
                'keywords': ['bonjour', 'hello', 'salut', 'hi', 'hey', 'bonsoir', 'good morning',
                           'good evening', 'coucou'],
                'patterns': ['comment allez-vous', 'how are you', 'ça va']
            },
            'gratitude': {
                'keywords': ['merci', 'thank', 'thanks', 'grateful', 'reconnaissant'],
                'patterns': ['merci beaucoup', 'thank you', 'thanks a lot']
            },
            'farewell': {
                'keywords': ['au revoir', 'goodbye', 'bye', 'adieu', 'see you', 'à bientôt'],
                'patterns': ['je dois y aller', 'i have to go', 'à plus tard']
            },
            'help': {
                'keywords': ['aide', 'help', 'support', 'comment', 'how', 'question'],
                'patterns': ['comment puis-je', 'how can i', 'j\'ai besoin d\'aide', 'i need help']
            },
        }

        detected_intent = 'general'
        confidence = 0.5
        entities = []
        max_confidence = 0.0

        # Check keywords and patterns for each intent
        for intent, intent_data in intents.items():
            intent_score = 0.0
            intent_entities = []

            # Check keywords (base score)
            for keyword in intent_data['keywords']:
                if keyword in message_lower:
                    intent_score += 0.3
                    intent_entities.append(keyword)

            # Check patterns (higher score)
            for pattern in intent_data.get('patterns', []):
                if pattern in message_lower:
                    intent_score += 0.5
                    intent_entities.append(pattern)

            # Context boost: if previous message had same intent, boost confidence
            if conversation_context and conversation_context.get('last_intent') == intent:
                intent_score += 0.2

            # Update if this intent has higher confidence
            if intent_score > max_confidence:
                max_confidence = intent_score
                detected_intent = intent
                entities = intent_entities
                confidence = min(0.95, 0.5 + intent_score)  # Cap at 95%

        return detected_intent, entities, confidence
    
    @staticmethod
    def _generate_response(participant, message, intent, entities, conversation_context=None):
        """
        Generate contextual response based on intent with conversation context (Phase 9)
        Provides context-aware, personalized responses
        """

        # Context-aware greeting
        greeting_text = f"Bonjour {participant.full_name}! Je suis votre assistant santé virtuel."
        if conversation_context and conversation_context.get('message_count', 0) > 0:
            greeting_text = f"Content de vous revoir, {participant.full_name}!"

        responses = {
            'greeting': f"{greeting_text} Comment puis-je vous aider aujourd'hui?",

            'appointment': f"Je peux vous aider avec vos rendez-vous! Vous avez les options suivantes:\n\n"
                          f"📅 Voir vos prochains rendez-vous\n"
                          f"➕ Prendre un nouveau rendez-vous\n"
                          f"📝 Modifier un rendez-vous existant\n\n"
                          f"Visitez la page 'Mes Rendez-vous' pour plus de détails.",

            'prescription': "Je peux vous aider avec vos ordonnances! Vous pouvez:\n\n"
                           "💊 Consulter vos prescriptions actives\n"
                           "📋 Voir l'historique de vos médicaments\n"
                           "🏪 Commander vos médicaments en pharmacie\n\n"
                           "Allez dans 'Mes Prescriptions' pour plus d'informations.",

            'symptom': "Je comprends que vous avez des symptômes. Pour votre sécurité:\n\n"
                      "⚠️ Si c'est une urgence, contactez immédiatement les urgences!\n\n"
                      "Pour les symptômes non urgents:\n"
                      "• Utilisez notre vérificateur de symptômes\n"
                      "• Prenez rendez-vous avec un médecin\n"
                      "• Consultez vos dossiers médicaux\n\n"
                      "Décrivez vos symptômes et je vous orienterai.",

            'emergency': "🚨 URGENCE DÉTECTÉE 🚨\n\n"
                        "Si vous faites face à une urgence médicale:\n\n"
                        "1️⃣ Appelez le 911 / 112 / Services d'urgence IMMÉDIATEMENT\n"
                        "2️⃣ Rendez-vous à l'hôpital le plus proche\n"
                        "3️⃣ Ne perdez pas de temps avec l'assistant virtuel\n\n"
                        "Votre sécurité est prioritaire. Agissez maintenant!",

            'insurance': "Pour vos questions d'assurance:\n\n"
                        "📋 Consultez vos polices actives\n"
                        "💰 Vérifiez votre couverture\n"
                        "📄 Soumettez une réclamation\n"
                        "📊 Suivez vos remboursements\n\n"
                        "Visitez la section 'Assurance' pour gérer vos polices.",

            'billing': "Pour les questions de paiement:\n\n"
                      "💳 Consultez vos factures\n"
                      "💰 Vérifiez votre portefeuille\n"
                      "📊 Voir l'historique des transactions\n"
                      "✅ Effectuer un paiement\n\n"
                      "Allez dans 'Portefeuille' pour plus de détails.",

            'health_record': "Accédez à vos dossiers de santé:\n\n"
                            "📋 Consultations passées\n"
                            "🔬 Résultats d'analyses\n"
                            "💊 Historique des prescriptions\n"
                            "📊 Rapports médicaux\n\n"
                            "Visitez 'Dossiers Médicaux' pour voir vos informations.",

            'lab_results': "Pour vos résultats d'analyse:\n\n"
                          "🔬 Consultez vos résultats de laboratoire\n"
                          "📊 Analyses de sang, urine, etc.\n"
                          "📈 Tendances et historique\n"
                          "🤖 Interprétation AI disponible\n\n"
                          "Visitez 'Mes Résultats' pour voir vos analyses.",

            'gratitude': "Je vous en prie! C'est un plaisir de vous aider. 😊\n\n"
                        "N'hésitez pas à me contacter si vous avez d'autres questions.\n"
                        "Je suis toujours là pour vous accompagner dans votre parcours santé!",

            'farewell': f"Au revoir, {participant.full_name}! 👋\n\n"
                       "Prenez soin de vous. N'hésitez pas à revenir si vous avez besoin d'aide.\n"
                       "À bientôt!",

            'help': "Je suis là pour vous aider! Voici ce que je peux faire:\n\n"
                   "✅ Répondre à vos questions sur la santé\n"
                   "✅ Vous aider à prendre rendez-vous\n"
                   "✅ Gérer vos prescriptions\n"
                   "✅ Suivre votre assurance\n"
                   "✅ Accéder à vos dossiers médicaux\n"
                   "✅ Interpréter vos résultats (AI)\n\n"
                   "Posez-moi n'importe quelle question!",

            'general': f"Merci pour votre message! Je suis votre assistant santé virtuel.\n\n"
                      f"Je peux vous aider avec:\n"
                      f"• Rendez-vous médicaux\n"
                      f"• Prescriptions et médicaments\n"
                      f"• Assurance santé\n"
                      f"• Dossiers médicaux\n"
                      f"• Questions générales de santé\n\n"
                      f"Comment puis-je vous aider aujourd'hui?"
        }
        
        # Add disclaimer to all responses
        base_response = responses.get(intent, responses['general'])
        return f"{base_response}\n\n{AI_SHORT_DISCLAIMER}"
    
    @staticmethod
    def create_health_insight(patient, insight_type, title, description, data_points=None, priority='normal'):
        """Create AI-generated health insight"""
        insight = AIHealthInsight.objects.create(
            patient=patient,
            insight_type=insight_type,
            title=title,
            description=description,
            data_points_used=data_points or {},
            confidence_score=random.uniform(0.7, 0.95),
            priority=priority,
            expires_at=timezone.now() + timedelta(days=30)
        )
        return insight
    
    @staticmethod
    def check_symptoms(patient, symptoms, additional_info=None):
        """AI-powered symptom checker (simplified version)"""
        
        # Create symptom check record
        symptom_check = AISymptomChecker.objects.create(
            patient=patient,
            symptoms=symptoms,
            additional_info=additional_info or {}
        )
        
        # Simple rule-based analysis (in production, use ML model)
        emergency_symptoms = ['chest pain', 'difficulty breathing', 'severe bleeding', 
                             'loss of consciousness', 'douleur thoracique', 'difficulté à respirer']
        
        has_emergency = any(sym.lower() in ' '.join(symptoms).lower() for sym in emergency_symptoms)
        
        if has_emergency:
            symptom_check.urgency_level = 'emergency'
            symptom_check.recommendations = f"⚠️ URGENCE: Contactez immédiatement les services d'urgence ou rendez-vous aux urgences les plus proches.\n\n{AI_SHORT_DISCLAIMER}"
            symptom_check.confidence_score = 0.95
        else:
            symptom_check.urgency_level = 'medium'
            symptom_check.recommendations = f"Nous vous recommandons de consulter un médecin dans les prochains jours pour évaluer vos symptômes.\n\n{AI_SHORT_DISCLAIMER}"
            symptom_check.confidence_score = 0.75
        
        symptom_check.ai_analysis = f"Analyse basée sur {len(symptoms)} symptôme(s) rapporté(s).\n\n{AI_SHORT_DISCLAIMER}"
        symptom_check.possible_conditions = ["Consultation médicale recommandée pour diagnostic précis"]
        symptom_check.save()
        
        return symptom_check
    
    @staticmethod
    def generate_personalized_recommendations(patient):
        """Generate personalized health recommendations"""
        recommendations = []
        
        # Check for overdue appointments
        from appointments.models import Appointment
        last_appointment = Appointment.objects.filter(
            patient=patient,
            status='completed'
        ).order_by('-appointment_date').first()
        
        if not last_appointment or (timezone.now().date() - last_appointment.appointment_date).days > 365:
            recommendations.append({
                'type': 'appointment',
                'title': 'Bilan de santé annuel',
                'description': 'Il est temps de planifier votre bilan de santé annuel.',
                'priority': 'normal'
            })
        
        # Check medication adherence
        from ai.models import AIMedicationReminder
        active_meds = AIMedicationReminder.objects.filter(
            patient=patient,
            is_active=True,
            adherence_rate__lt=80
        )
        
        if active_meds.exists():
            recommendations.append({
                'type': 'medication',
                'title': 'Améliorer l\'observance médicamenteuse',
                'description': 'Certains de vos médicaments ne sont pas pris régulièrement.',
                'priority': 'high'
            })
        
        # Create insights for recommendations
        for rec in recommendations:
            AIAssistantService.create_health_insight(
                patient=patient,
                insight_type='recommendation',
                title=rec['title'],
                description=rec['description'],
                priority=rec['priority']
            )
        
        return recommendations

    @staticmethod
    def get_unified_insights(organization):
        """
        Central AI Coordinator - Aggregates insights from all modules

        Combines insights from:
        - HR Module (HRAnalytics)
        - Financial Module (FinancialAI)
        - Hospital Module (HospitalAI)
        - Patient Module (AIHealthInsight, existing)

        Returns:
            dict: Unified insights with priority-based sorting
        """
        all_insights = []

        # 1. Get HR insights (if organization has HR module)
        try:
            from hr.ai_insights import HRAnalytics
            from hr.models import Employee

            employees = Employee.objects.filter(organization=organization, status='active')

            if employees.exists():
                # Aggregate department-level insights
                high_churn = 0
                declining_perf = 0
                attendance_problems = 0

                # Sample employees to avoid performance issues (max 50)
                sample_size = min(50, employees.count())
                for employee in employees[:sample_size]:
                    try:
                        churn = HRAnalytics.calculate_churn_risk(employee.user)
                        if churn.get('risk_level') == 'high':
                            high_churn += 1

                        perf = HRAnalytics.analyze_performance_trend(employee.user)
                        if perf and perf.get('trend') == 'declining':
                            declining_perf += 1

                        attendance = HRAnalytics.analyze_attendance_patterns(employee.user)
                        if attendance.get('patterns'):
                            attendance_problems += 1
                    except:
                        continue

                if high_churn > 0 or declining_perf > 0 or attendance_problems > 0:
                    all_insights.append({
                        'type': 'hr_summary',
                        'priority': 'high' if high_churn > 5 else 'medium',
                        'title': f'HR Insights: {high_churn + declining_perf + attendance_problems} Issues Detected',
                        'description': f'{high_churn} high churn risk, {declining_perf} declining performance, {attendance_problems} attendance issues',
                        'data': {
                            'high_churn_risk': high_churn,
                            'declining_performance': declining_perf,
                            'attendance_issues': attendance_problems,
                            'employees_analyzed': sample_size
                        },
                        'module': 'hr'
                    })
        except (ImportError, Exception):
            pass  # HR module not available or error occurred

        # 2. Get Financial insights
        try:
            from financial.ai_insights import FinancialAI
            financial_insights = FinancialAI.get_financial_insights(organization)
            all_insights.extend(financial_insights)
        except (ImportError, Exception):
            pass  # Financial module not available or error occurred

        # 3. Get Hospital insights (if organization is a hospital)
        if organization.role == 'hospital':
            try:
                from hospital.ai_insights import HospitalAI
                hospital_insights = HospitalAI.get_hospital_insights(organization)
                all_insights.extend(hospital_insights)
            except (ImportError, Exception):
                pass  # Hospital module not available or error occurred

        # 4. Get existing Patient AI insights
        try:
            recent_insights = AIHealthInsight.objects.filter(
                patient__affiliated_provider=organization,
                is_active=True,
                expires_at__gte=timezone.now()
            ).order_by('-created_at')[:10]

            for insight in recent_insights:
                priority = 'high' if insight.priority == 'high' else 'medium' if insight.priority == 'normal' else 'low'
                all_insights.append({
                    'type': 'health_insight',
                    'priority': priority,
                    'title': insight.title,
                    'description': insight.description,
                    'data': {
                        'insight_type': insight.insight_type,
                        'confidence_score': float(insight.confidence_score),
                        'patient_id': str(insight.patient_id)
                    },
                    'module': 'patient'
                })
        except Exception:
            pass

        # 5. Get Analytics predictive insights (only for super_admin)
        if organization.is_superuser or organization.role == 'super_admin':
            try:
                from analytics.predictive_analytics import PredictiveAnalytics
                analytics_insights = PredictiveAnalytics.get_predictive_insights()
                all_insights.extend(analytics_insights)
            except (ImportError, Exception):
                pass  # Analytics module not available or error occurred

        # Sort insights by priority (high > medium > low)
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        all_insights.sort(key=lambda x: priority_order.get(x.get('priority', 'low'), 3))

        # Count by priority
        high_priority = len([i for i in all_insights if i.get('priority') == 'high'])
        medium_priority = len([i for i in all_insights if i.get('priority') == 'medium'])
        low_priority = len([i for i in all_insights if i.get('priority') == 'low'])

        # Count by module
        module_counts = {}
        for insight in all_insights:
            module = insight.get('module', 'unknown')
            module_counts[module] = module_counts.get(module, 0) + 1

        return {
            'organization': organization.full_name,
            'organization_role': organization.role,
            'total_insights': len(all_insights),
            'priority_breakdown': {
                'high': high_priority,
                'medium': medium_priority,
                'low': low_priority
            },
            'module_breakdown': module_counts,
            'insights': all_insights,
            'generated_at': timezone.now()
        }
