from django.core.management.base import BaseCommand
from django.conf import settings
import uuid
import json


class Command(BaseCommand):
    help = 'Request admin access for local instance (use this instead of createsuperuser)'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, required=True, help='Email for the admin account')
        parser.add_argument('--full-name', type=str, required=True, help='Full name of the admin')
        parser.add_argument('--phone', type=str, required=False, help='Phone number (optional)')

    def handle(self, *args, **options):
        instance_type = getattr(settings, 'INSTANCE_TYPE', 'CLOUD')
        instance_id = getattr(settings, 'INSTANCE_ID', None)

        if instance_type == 'CLOUD':
            self.stdout.write(
                self.style.WARNING(
                    "\n========================================================\n"
                    "Cette commande est pour les instances locales seulement.\n"
                    "This command is for local instances only.\n\n"
                    "Utilisez: python manage.py createsuperuser\n"
                    "Use: python manage.py createsuperuser\n"
                    "========================================================\n"
                )
            )
            return

        email = options['email']
        full_name = options['full_name']
        phone = options.get('phone', '')

        if not instance_id:
            instance_id = str(uuid.uuid4())
            self.stdout.write(
                self.style.WARNING(
                    f"\nAUCUN INSTANCE_ID CONFIGURÉ!\n"
                    f"NO INSTANCE_ID CONFIGURED!\n\n"
                    f"ID d'instance généré / Generated instance ID:\n"
                    f"{instance_id}\n\n"
                    f"IMPORTANT: Ajoutez ceci à votre fichier .env:\n"
                    f"IMPORTANT: Add this to your .env file:\n"
                    f"INSTANCE_ID={instance_id}\n"
                )
            )

        request_data = {
            'instance_id': instance_id,
            'email': email,
            'full_name': full_name,
            'phone_number': phone,
            'instance_type': instance_type,
        }

        self.stdout.write(
            self.style.SUCCESS(
                "\n========================================================\n"
                "DEMANDE D'ACCÈS ADMINISTRATEUR\n"
                "ADMIN ACCESS REQUEST\n"
                "========================================================\n\n"
                "Informations de la demande / Request information:\n"
                f"{json.dumps(request_data, indent=2)}\n\n"
                "PROCHAINES ÉTAPES / NEXT STEPS:\n"
                "========================================================\n\n"
                "1. Copiez les informations ci-dessus\n"
                "   Copy the information above\n\n"
                "2. Envoyez un email à: support@bintacura.com\n"
                "   Send an email to: support@bintacura.com\n\n"
                "3. Sujet: Demande d'accès administrateur - Instance locale\n"
                "   Subject: Admin access request - Local instance\n\n"
                "4. Incluez les informations JSON dans votre email\n"
                "   Include the JSON information in your email\n\n"
                "5. Notre équipe créera un compte administrateur pour vous\n"
                "   Our team will create an admin account for you\n\n"
                "6. Vous recevrez les identifiants par email sécurisé\n"
                "   You will receive credentials via secure email\n\n"
                "========================================================\n"
                "SÉCURITÉ / SECURITY\n"
                "========================================================\n\n"
                "Cette restriction protège l'intégrité de l'écosystème\n"
                "BintaCura en empêchant les accès non autorisés au système\n"
                "central depuis les instances locales.\n\n"
                "This restriction protects the integrity of the BintaCura\n"
                "ecosystem by preventing unauthorized access to the central\n"
                "system from local instances.\n\n"
                "Merci de votre compréhension.\n"
                "Thank you for your understanding.\n"
                "========================================================\n"
            )
        )
