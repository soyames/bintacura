"""
Management Command: register_instance

Registers a new local business instance for offline-first synchronization.
Generates API credentials and JWT token for desktop EXE configuration.

Usage:
    python manage.py register_instance \\
        --organization-id=<uuid> \\
        --instance-name="Hospital Yalgado Desktop 1" \\
        --instance-type=hospital \\
        --platform=windows

Example:
    python manage.py register_instance \\
        --organization-id=123e4567-e89b-12d3-a456-426614174000 \\
        --instance-name="Hospital Yalgado Desktop 1" \\
        --instance-type=hospital \\
        --platform=windows \\
        --hardware-id="00-1A-2B-3C-4D-5E"
"""

import secrets
import uuid
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.hashers import make_password
from django.db import transaction
from sync.models import SyncInstance
from core.models import Participant


class Command(BaseCommand):
    help = 'Register a new local business instance for offline-first sync'

    def add_arguments(self, parser):
        parser.add_argument(
            '--organization-id',
            type=str,
            required=True,
            help='UUID of the organization (Participant) this instance belongs to'
        )
        parser.add_argument(
            '--instance-name',
            type=str,
            required=True,
            help='Descriptive name for this instance (e.g., "Hospital Yalgado Desktop 1")'
        )
        parser.add_argument(
            '--instance-type',
            type=str,
            required=True,
            choices=['hospital', 'pharmacy', 'insurance', 'lab', 'imaging'],
            help='Type of organization'
        )
        parser.add_argument(
            '--platform',
            type=str,
            required=True,
            choices=['windows', 'linux', 'macos'],
            help='Operating system platform'
        )
        parser.add_argument(
            '--hardware-id',
            type=str,
            required=False,
            default=None,
            help='Hardware identifier (MAC address, etc.) - optional'
        )
        parser.add_argument(
            '--os-version',
            type=str,
            required=False,
            default=None,
            help='OS version string - optional'
        )
        parser.add_argument(
            '--sync-interval',
            type=int,
            required=False,
            default=15,
            help='Auto-sync interval in minutes (default: 15)'
        )

    def handle(self, *args, **options):
        """Register new instance and generate credentials"""

        organization_id = options['organization_id']
        instance_name = options['instance_name']
        instance_type = options['instance_type']
        platform = options['platform']
        hardware_id = options.get('hardware_id')
        os_version = options.get('os_version')
        sync_interval = options.get('sync_interval', 15)

        # Validate organization exists
        try:
            organization = Participant.objects.get(uid=organization_id)
        except Participant.DoesNotExist:
            raise CommandError(f'Organization with ID {organization_id} does not exist')

        # Validate organization role matches instance type
        valid_roles = {
            'hospital': ['hospital', 'lab'],
            'pharmacy': ['pharmacy'],
            'insurance': ['insurance_company'],
            'lab': ['hospital', 'lab'],
            'imaging': ['hospital'],
        }

        if organization.role.lower() not in valid_roles.get(instance_type, []):
            raise CommandError(
                f'Organization role "{organization.role}" does not match instance type "{instance_type}". '
                f'Valid roles for {instance_type}: {", ".join(valid_roles[instance_type])}'
            )

        self.stdout.write(self.style.SUCCESS(f'\n{"="*80}'))
        self.stdout.write(self.style.SUCCESS('REGISTERING NEW SYNC INSTANCE'))
        self.stdout.write(self.style.SUCCESS(f'{"="*80}\n'))

        # Generate API credentials
        api_key = f"instance_{uuid.uuid4().hex[:16]}"
        api_secret = secrets.token_urlsafe(32)  # 32 bytes = 256 bits
        api_secret_hash = make_password(api_secret)

        self.stdout.write(f'Organization: {organization.name} ({organization.uid})')
        self.stdout.write(f'Instance Name: {instance_name}')
        self.stdout.write(f'Instance Type: {instance_type}')
        self.stdout.write(f'Platform: {platform}')
        if hardware_id:
            self.stdout.write(f'Hardware ID: {hardware_id}')
        if os_version:
            self.stdout.write(f'OS Version: {os_version}')
        self.stdout.write(f'Sync Interval: {sync_interval} minutes\n')

        # Create instance record
        try:
            with transaction.atomic():
                instance = SyncInstance.objects.create(
                    organization=organization,
                    instance_name=instance_name,
                    instance_type=instance_type,
                    platform=platform,
                    hardware_id=hardware_id,
                    os_version=os_version,
                    api_key=api_key,
                    api_secret_hash=api_secret_hash,
                    sync_interval_minutes=sync_interval,
                    is_active=True,
                    sync_enabled=True,
                )

                # Generate JWT token
                jwt_token = instance.generate_jwt_token(expiry_days=365)

                self.stdout.write(self.style.SUCCESS(f'\n{"="*80}'))
                self.stdout.write(self.style.SUCCESS('✓ INSTANCE REGISTERED SUCCESSFULLY'))
                self.stdout.write(self.style.SUCCESS(f'{"="*80}\n'))

                self.stdout.write(self.style.WARNING('IMPORTANT: Save these credentials securely!\n'))
                self.stdout.write(self.style.WARNING('They will NOT be shown again.\n'))

                self.stdout.write(f'{"─"*80}\n')
                self.stdout.write(self.style.SUCCESS('INSTANCE CONFIGURATION'))
                self.stdout.write(f'{"─"*80}\n')

                self.stdout.write(f'Instance ID:        {instance.instance_id}')
                self.stdout.write(f'API Key:            {api_key}')
                self.stdout.write(f'API Secret:         {api_secret}')
                self.stdout.write(f'\n{"─"*80}\n')
                self.stdout.write(self.style.SUCCESS('JWT TOKEN (365-day expiry)'))
                self.stdout.write(f'{"─"*80}\n')
                self.stdout.write(f'{jwt_token}\n')

                self.stdout.write(f'{"─"*80}\n')
                self.stdout.write(self.style.SUCCESS('DESKTOP EXE CONFIGURATION'))
                self.stdout.write(f'{"─"*80}\n')

                # Generate desktop config file content
                config_content = f"""# VitaCare Desktop Instance Configuration
# Generated for: {instance_name}
# Organization: {organization.name}
# Date: {instance.registered_at.strftime('%Y-%m-%d %H:%M:%S')}

[instance]
instance_id = {instance.instance_id}
instance_name = {instance_name}
instance_type = {instance_type}
organization_id = {organization.uid}

[authentication]
api_key = {api_key}
api_secret = {api_secret}
jwt_token = {jwt_token}

[sync]
cloud_url = https://your-cloud-server.com/api/sync/
sync_interval_minutes = {sync_interval}
sync_enabled = true

[database]
db_name = vitacare_{instance_type}_{instance.instance_id.hex[:8]}
db_user = vitacare
db_password = <generate-secure-password>
db_host = localhost
db_port = 5432
"""

                self.stdout.write('Create a file named "instance_config.ini" with the following content:\n')
                self.stdout.write(self.style.WARNING(config_content))

                self.stdout.write(f'\n{"─"*80}\n')
                self.stdout.write(self.style.SUCCESS('NEXT STEPS'))
                self.stdout.write(f'{"─"*80}\n')
                self.stdout.write('1. Copy the configuration above to instance_config.ini')
                self.stdout.write('2. Install the desktop EXE on the target computer')
                self.stdout.write('3. Place instance_config.ini in the EXE directory')
                self.stdout.write('4. Run the desktop application')
                self.stdout.write('5. The app will automatically sync with cloud every 15 minutes\n')

                self.stdout.write(f'{"="*80}\n')

                return f'Instance {instance.instance_id} registered successfully'

        except Exception as e:
            raise CommandError(f'Failed to register instance: {str(e)}')
