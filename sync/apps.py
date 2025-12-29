from django.apps import AppConfig


class SyncConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sync'
    verbose_name = 'Synchronization'

    def ready(self):
        """
        Register signal handlers when app is ready

        This ensures SyncEvent logging happens automatically
        for all SyncMixin models.
        """
        import sync.signals  # noqa: F401
