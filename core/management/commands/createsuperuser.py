from django.core.management.base import BaseCommand
from django.core.management import call_command
from core.models import Participant
import getpass


class Command(BaseCommand):
    help = 'Create a superuser with super_admin role'

    def handle(self, *args, **options):
        email = input('Email: ')

        if Participant.objects.filter(email=email).exists():
            self.stdout.write(self.style.ERROR(f'Error: User with email {email} already exists.'))
            return

        password = None
        while not password:
            password = getpass.getpass('Password: ')
            password2 = getpass.getpass('Password (again): ')

            if password != password2:
                self.stdout.write(self.style.ERROR("Error: Passwords don't match."))
                password = None
                continue

            if len(password.strip()) < 8:
                self.stdout.write(self.style.ERROR('Error: Password must be at least 8 characters.'))
                password = None
                continue

        try:
            user = Participant.objects.create_superuser(
                email=email,
                password=password,
                full_name='Super Administrator',
                is_verified=True,
                is_email_verified=True
            )

            self.stdout.write(self.style.SUCCESS(f'Superuser created successfully with email: {email}'))
            self.stdout.write(self.style.SUCCESS(f'Role: {user.role}'))
            self.stdout.write(self.style.SUCCESS(f'Admin access granted'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating superuser: {str(e)}'))
