from django.apps import AppConfig


class TransportConfig(AppConfig):  # TransportConfig class implementation
    name = 'transport'
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        """Import signals when app is ready"""
        import transport.signals
