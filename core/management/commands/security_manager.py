from django.core.management.base import BaseCommand
from django.core.cache import cache
from core.security_config import SecurityConfig
import json


class Command(BaseCommand):
    help = 'Manage security settings and view/clear security blocks'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            type=str,
            choices=['show-profile', 'clear-blocks', 'clear-ip', 'list-blocks'],
            help='Action to perform'
        )
        parser.add_argument(
            '--ip',
            type=str,
            help='IP address (for clear-ip action)'
        )
        parser.add_argument(
            '--profile',
            type=str,
            choices=['development', 'lenient', 'moderate', 'strict'],
            help='Security profile to show'
        )

    def handle(self, *args, **options):
        action = options['action']

        if action == 'show-profile':
            self.show_profile(options.get('profile'))
        elif action == 'clear-blocks':
            self.clear_all_blocks()
        elif action == 'clear-ip':
            ip = options.get('ip')
            if not ip:
                self.stdout.write(self.style.ERROR('Please provide --ip argument'))
                return
            self.clear_ip_blocks(ip)
        elif action == 'list-blocks':
            self.list_blocks()

    def show_profile(self, profile_name=None):
        """Show current security profile settings"""
        if profile_name:
            profile = SecurityConfig.get_profile(profile_name)
            self.stdout.write(self.style.SUCCESS(f'\nSecurity Profile: {profile_name}'))
        else:
            from django.conf import settings
            from decouple import config
            current_profile = config('SECURITY_PROFILE', default='moderate' if not settings.DEBUG else 'development')
            profile = SecurityConfig.get_profile()
            self.stdout.write(self.style.SUCCESS(f'\nCurrent Security Profile: {current_profile}'))
        
        self.stdout.write('\nSettings:')
        self.stdout.write('-' * 60)
        for key, value in profile.items():
            self.stdout.write(f'{key:40} : {value}')
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('Exempt Paths:')
        for category, paths in SecurityConfig.EXEMPT_PATHS.items():
            self.stdout.write(f'\n{category}:')
            for path in paths:
                self.stdout.write(f'  - {path}')
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('Whitelisted IPs:')
        for ip in SecurityConfig.WHITELISTED_IPS:
            self.stdout.write(f'  - {ip}')

    def clear_all_blocks(self):
        """Clear all security blocks"""
        cache.clear()
        self.stdout.write(self.style.SUCCESS('All security blocks cleared!'))

    def clear_ip_blocks(self, ip):
        """Clear blocks for a specific IP"""
        block_types = [
            f'ddos_block_{ip}',
            f'login_block_{ip}',
            f'sql_injection_attempt_{ip}',
            f'ip_block_{ip}',
            f'ddos_log_{ip}'
        ]
        
        cleared = []
        for block_key in block_types:
            if cache.get(block_key):
                cache.delete(block_key)
                cleared.append(block_key)
        
        if cleared:
            self.stdout.write(self.style.SUCCESS(f'Cleared blocks for IP {ip}:'))
            for key in cleared:
                self.stdout.write(f'  - {key}')
        else:
            self.stdout.write(self.style.WARNING(f'No blocks found for IP {ip}'))

    def list_blocks(self):
        """List all current security blocks (limited functionality with local cache)"""
        self.stdout.write(self.style.WARNING(
            '\nNote: Local cache backend does not support key listing.'
        ))
        self.stdout.write(self.style.WARNING(
            'To list blocks, you need to use Redis cache backend.'
        ))
        self.stdout.write('\nTo clear specific IP, use: python manage.py security_manager clear-ip --ip=<IP_ADDRESS>')
        self.stdout.write('To clear all blocks, use: python manage.py security_manager clear-blocks')
