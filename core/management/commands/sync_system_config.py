from django.core.management.base import BaseCommand
from django.conf import settings
from core.system_config import SystemConfiguration


class Command(BaseCommand):
    help = 'Sync SystemConfiguration with settings.py values'

    def handle(self, *args, **options):
        default_currency = getattr(settings, 'DEFAULT_CURRENCY', 'XOF')
        default_fee_setting = f'DEFAULT_CONSULTATION_FEE_{default_currency}'
        default_fee = getattr(settings, default_fee_setting, 3500)
        
        config, created = SystemConfiguration.objects.get_or_create(
            is_active=True,
            defaults={
                'default_consultation_fee': default_fee,
                'default_consultation_currency': default_currency,
                'platform_fee_percentage': 1.00,
                'tax_percentage': 18.00,
                'wallet_topup_fee_percentage': 0.00,
            }
        )
        
        if not created:
            config.default_consultation_fee = default_fee
            config.default_consultation_currency = default_currency
            config.save()
            self.stdout.write(self.style.SUCCESS(f'✅ Updated SystemConfiguration: {default_fee} {default_currency}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ Created SystemConfiguration: {default_fee} {default_currency}'))
