"""
AI Monitoring and Logging Utilities (Phase 11)
Comprehensive logging, monitoring, and performance tracking for AI services
"""
import logging
import time
from functools import wraps
from django.utils import timezone
from datetime import timedelta
import json

# Configure AI-specific logger
ai_logger = logging.getLogger('BINTACURA.ai')
ai_logger.setLevel(logging.INFO)


class AIPerformanceMonitor:
    """
    Monitor and log AI model performance metrics
    """

    @staticmethod
    def log_prediction(model_name, participant_id, execution_time, success=True, error=None, metadata=None):
        """
        Log AI prediction/analysis execution

        Args:
            model_name: Name of the AI model/analyzer
            participant_id: UUID of participant
            execution_time: Time taken in seconds
            success: Whether execution was successful
            error: Error message if failed
            metadata: Additional metadata (e.g., result stats)
        """
        log_data = {
            'model': model_name,
            'participant_id': str(participant_id),
            'execution_time_ms': round(execution_time * 1000, 2),
            'success': success,
            'timestamp': timezone.now().isoformat()
        }

        if metadata:
            log_data['metadata'] = metadata

        if success:
            ai_logger.info(f"AI_PREDICTION_SUCCESS | {json.dumps(log_data)}")
        else:
            log_data['error'] = str(error)
            ai_logger.error(f"AI_PREDICTION_ERROR | {json.dumps(log_data)}")

    @staticmethod
    def log_cache_hit(prefix, participant_id):
        """Log cache hit event"""
        ai_logger.debug(f"AI_CACHE_HIT | prefix={prefix} | participant={participant_id}")

    @staticmethod
    def log_cache_miss(prefix, participant_id):
        """Log cache miss event"""
        ai_logger.debug(f"AI_CACHE_MISS | prefix={prefix} | participant={participant_id}")

    @staticmethod
    def log_model_training(model_name, dataset_size, training_time, metrics=None):
        """
        Log ML model training event

        Args:
            model_name: Name of the ML model
            dataset_size: Number of training samples
            training_time: Training duration in seconds
            metrics: Training metrics (accuracy, etc.)
        """
        log_data = {
            'model': model_name,
            'dataset_size': dataset_size,
            'training_time_ms': round(training_time * 1000, 2),
            'timestamp': timezone.now().isoformat()
        }

        if metrics:
            log_data['metrics'] = metrics

        ai_logger.info(f"AI_MODEL_TRAINING | {json.dumps(log_data)}")

    @staticmethod
    def log_chatbot_interaction(conversation_id, intent, confidence, response_time):
        """
        Log chatbot interaction

        Args:
            conversation_id: UUID of conversation
            intent: Detected intent
            confidence: Confidence score
            response_time: Response generation time in seconds
        """
        log_data = {
            'conversation_id': str(conversation_id),
            'intent': intent,
            'confidence': round(confidence, 3),
            'response_time_ms': round(response_time * 1000, 2),
            'timestamp': timezone.now().isoformat()
        }

        ai_logger.info(f"AI_CHATBOT_INTERACTION | {json.dumps(log_data)}")

    @staticmethod
    def log_error(operation, error, participant_id=None, details=None):
        """
        Log AI operation error

        Args:
            operation: Operation being performed
            error: Exception or error message
            participant_id: UUID of participant (if applicable)
            details: Additional error details
        """
        log_data = {
            'operation': operation,
            'error': str(error),
            'error_type': type(error).__name__,
            'timestamp': timezone.now().isoformat()
        }

        if participant_id:
            log_data['participant_id'] = str(participant_id)

        if details:
            log_data['details'] = details

        ai_logger.error(f"AI_OPERATION_ERROR | {json.dumps(log_data)}")


def monitor_ai_performance(model_name, log_metadata=True):
    """
    Decorator to monitor AI model/analyzer performance

    Args:
        model_name: Name of the AI model
        log_metadata: Whether to log result metadata

    Usage:
        @monitor_ai_performance('diagnostic_analyzer')
        def analyze_diagnostics(patient, days_back=365):
            # ... analysis logic ...
            return result
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract participant from args or kwargs
            participant = kwargs.get('patient') or kwargs.get('organization')
            if not participant and len(args) > 0:
                participant = args[0]

            participant_id = str(participant.uid) if participant else 'unknown'

            # Start timer
            start_time = time.time()
            success = True
            error = None
            result = None
            metadata = None

            try:
                result = func(*args, **kwargs)

                # Extract metadata from result if it's a dict
                if log_metadata and isinstance(result, dict):
                    metadata = {
                        'status': result.get('status'),
                        'record_count': result.get('total_records') or result.get('total_diagnostic_records'),
                        'model_trained': result.get('model_trained')
                    }
                    # Remove None values
                    metadata = {k: v for k, v in metadata.items() if v is not None}

                return result

            except Exception as e:
                success = False
                error = e
                raise

            finally:
                # Calculate execution time
                execution_time = time.time() - start_time

                # Log performance
                AIPerformanceMonitor.log_prediction(
                    model_name=model_name,
                    participant_id=participant_id,
                    execution_time=execution_time,
                    success=success,
                    error=error,
                    metadata=metadata
                )

        return wrapper
    return decorator


def monitor_chatbot_interaction(func):
    """
    Decorator to monitor chatbot interactions

    Usage:
        @monitor_chatbot_interaction
        def process_chat_message(participant, message, conversation_id=None):
            # ... processing logic ...
            return response_data
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = func(*args, **kwargs)

            # Calculate response time
            response_time = time.time() - start_time

            # Log interaction
            if isinstance(result, dict):
                AIPerformanceMonitor.log_chatbot_interaction(
                    conversation_id=result.get('conversation_id'),
                    intent=result.get('intent'),
                    confidence=result.get('confidence', 0.0),
                    response_time=response_time
                )

            return result

        except Exception as e:
            AIPerformanceMonitor.log_error(
                operation='chatbot_interaction',
                error=e,
                details={'response_time': time.time() - start_time}
            )
            raise

    return wrapper


class AIUsageTracker:
    """
    Track AI feature usage for analytics
    """

    @staticmethod
    def log_feature_usage(feature_name, participant_id, feature_type='general'):
        """
        Log AI feature usage

        Args:
            feature_name: Name of the AI feature
            participant_id: UUID of participant
            feature_type: Type of feature (chat, health_insights, etc.)
        """
        from ai.models import AIFeature

        try:
            # Get or create feature
            feature, created = AIFeature.objects.get_or_create(
                name=feature_name,
                defaults={
                    'type': feature_type,
                    'description': f'AI feature: {feature_name}',
                    'is_active': True
                }
            )

            # Update usage count and last used timestamp
            feature.usage_count += 1
            feature.last_used_at = timezone.now()
            feature.save(update_fields=['usage_count', 'last_used_at'])

            ai_logger.debug(f"AI_FEATURE_USAGE | feature={feature_name} | participant={participant_id}")

        except Exception as e:
            ai_logger.error(f"Failed to track feature usage: {e}")

    @staticmethod
    def get_usage_stats(days_back=30):
        """
        Get AI usage statistics

        Args:
            days_back: Number of days to look back

        Returns:
            dict: Usage statistics
        """
        from ai.models import AIFeature, AIChatMessage, AIHealthInsight

        cutoff_date = timezone.now() - timedelta(days=days_back)

        # Get feature usage
        features = AIFeature.objects.filter(last_used_at__gte=cutoff_date)

        # Get chatbot usage
        chat_messages = AIChatMessage.objects.filter(timestamp__gte=cutoff_date).count()

        # Get health insights generated
        health_insights = AIHealthInsight.objects.filter(generated_at__gte=cutoff_date).count()

        return {
            'period_days': days_back,
            'active_features': features.count(),
            'total_feature_usages': sum(f.usage_count for f in features),
            'chat_messages': chat_messages,
            'health_insights_generated': health_insights,
            'top_features': [
                {
                    'name': f.name,
                    'type': f.type,
                    'usage_count': f.usage_count,
                    'last_used': f.last_used_at.isoformat() if f.last_used_at else None
                }
                for f in features.order_by('-usage_count')[:10]
            ]
        }


class AIModelHealthCheck:
    """
    Health check utilities for AI models and services
    """

    @staticmethod
    def check_ml_models():
        """
        Check if ML models are available and working

        Returns:
            dict: Health check results
        """
        health_status = {
            'overall_status': 'healthy',
            'checks': []
        }

        # Check scikit-learn availability
        try:
            import sklearn
            health_status['checks'].append({
                'component': 'scikit-learn',
                'status': 'healthy',
                'version': sklearn.__version__
            })
        except ImportError as e:
            health_status['overall_status'] = 'degraded'
            health_status['checks'].append({
                'component': 'scikit-learn',
                'status': 'unavailable',
                'error': str(e)
            })

        # Check cache availability
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 10)
            cache_value = cache.get('health_check')

            health_status['checks'].append({
                'component': 'cache',
                'status': 'healthy' if cache_value == 'ok' else 'degraded'
            })
        except Exception as e:
            health_status['overall_status'] = 'degraded'
            health_status['checks'].append({
                'component': 'cache',
                'status': 'unhealthy',
                'error': str(e)
            })

        # Check database connectivity for AI models
        try:
            from ai.models import AIFeature
            AIFeature.objects.count()

            health_status['checks'].append({
                'component': 'database',
                'status': 'healthy'
            })
        except Exception as e:
            health_status['overall_status'] = 'unhealthy'
            health_status['checks'].append({
                'component': 'database',
                'status': 'unhealthy',
                'error': str(e)
            })

        health_status['timestamp'] = timezone.now().isoformat()

        return health_status

    @staticmethod
    def get_model_performance_summary():
        """
        Get summary of AI model performance

        Returns:
            dict: Performance summary from AIModelPerformance records
        """
        from ai.models import AIModelPerformance

        active_models = AIModelPerformance.objects.filter(is_active=True)

        return {
            'active_models_count': active_models.count(),
            'models': [
                {
                    'name': model.model_name,
                    'version': model.model_version,
                    'type': model.model_type,
                    'total_predictions': model.total_predictions,
                    'success_rate': round((model.successful_predictions / model.total_predictions * 100), 2)
                    if model.total_predictions > 0 else 0,
                    'average_confidence': round(model.average_confidence, 3)
                }
                for model in active_models
            ]
        }


# Utility function to set up AI logging
def setup_ai_logging(log_file='logs/ai.log', log_level=logging.INFO):
    """
    Set up AI logging configuration

    Args:
        log_file: Path to AI log file
        log_level: Logging level

    Call this in ai/apps.py ready() method
    """
    import os

    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # File handler for AI logs
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)

    # Add handler to AI logger
    ai_logger.addHandler(file_handler)

    # Also log to console in development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
    console_handler.setFormatter(formatter)
    ai_logger.addHandler(console_handler)

    ai_logger.info("AI logging initialized")

