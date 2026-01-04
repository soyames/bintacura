from django.apps import AppConfig


class HospitalConfig(AppConfig):  # HospitalConfig class implementation
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hospital'
    
    def ready(self):
        import hospital.signals  # Import signals to register them
