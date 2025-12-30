from django.core.management.base import BaseCommand
from django.utils import timezone
from currency_converter.services import CurrencyConverterService
from currency_converter.models import ExchangeRate


class Command(BaseCommand):
    help = 'Fetch and cache exchange rates from API. Rates are stored for 7 days.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--base-currency',
            type=str,
            default='XOF',
            help='Base currency to fetch rates for (default: XOF)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force fetch even if recent rates exist'
        )

    def handle(self, *args, **options):
        base_currency = options['base_currency']
        force = options['force']
        
        self.stdout.write(f"Fetching exchange rates for {base_currency}...")
        
        # Check if we have recent rates (last 24 hours)
        if not force:
            recent_rate = ExchangeRate.objects.filter(
                from_currency=base_currency,
                fetched_at__gte=timezone.now() - timezone.timedelta(hours=24)
            ).first()
            
            if recent_rate:
                self.stdout.write(
                    self.style.WARNING(
                        f"Recent rates exist (fetched at {recent_rate.fetched_at}). "
                        "Use --force to fetch anyway."
                    )
                )
                return
        
        # Fetch rates for all supported currencies
        supported_currencies = CurrencyConverterService.get_supported_currencies()
        success_count = 0
        
        for target_currency in supported_currencies:
            if target_currency == base_currency:
                continue
            
            try:
                rate = CurrencyConverterService._fetch_rate_from_api(
                    base_currency, 
                    target_currency
                )
                
                if rate:
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"[OK] {base_currency}/{target_currency}: {rate}"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[SKIP] {base_currency}/{target_currency}: Failed to fetch"
                        )
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"[ERROR] {base_currency}/{target_currency}: {str(e)}"
                    )
                )
        
        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully fetched {success_count} exchange rates"
            )
        )
        
        # Show total cached rates
        total_rates = ExchangeRate.objects.filter(
            from_currency=base_currency
        ).count()
        self.stdout.write(f"Total rates in database: {total_rates}")
        
        # Show oldest rate
        oldest_rate = ExchangeRate.objects.filter(
            from_currency=base_currency
        ).order_by('fetched_at').first()
        
        if oldest_rate:
            self.stdout.write(f"Oldest rate: {oldest_rate.fetched_at}")
        
        self.stdout.write("="*50)
