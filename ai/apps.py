from django.apps import AppConfig


class AiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai'
    verbose_name = 'AI Assistant & Health Intelligence'

    def ready(self):
        """
        Initialize AI app - set up logging and monitoring (Phase 11)
        """
        # Set up AI logging
        from ai.logging_utils import setup_ai_logging
        import logging

        try:
            setup_ai_logging(log_file='logs/ai.log', log_level=logging.INFO)
        except Exception as e:
            print(f"Warning: Could not set up AI logging: {e}")

        # Import signal handlers for cache invalidation
        # Uncomment when ready to use automatic cache invalidation
        # from ai.cache_utils import invalidate_health_cache_on_record_save, invalidate_org_cache_on_data_change
        # from django.db.models.signals import post_save
        # from health_records.models import HealthRecord
        # from hr.models import Employee
        # from financial.models import Transaction
        #
        # post_save.connect(invalidate_health_cache_on_record_save, sender=HealthRecord)
        # post_save.connect(invalidate_org_cache_on_data_change, sender=Employee)
        # post_save.connect(invalidate_org_cache_on_data_change, sender=Transaction)
