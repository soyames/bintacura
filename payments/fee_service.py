from decimal import Decimal
from django.conf import settings

class FeeCalculationService:
    """Service for calculating fees and taxes for BINTACURA transactions"""
    
    # Fee Configuration
    PLATFORM_FEE_PERCENTAGE = Decimal('0.01')  # 1% platform fee
    TAX_RATE = Decimal('0.18')  # 18% VAT (adjust based on your country)
    
    # Transaction types that incur fees
    FEE_EXEMPT_TYPES = ['deposit']
    
    @staticmethod
    def calculate_fees(amount: Decimal, transaction_type: str, include_tax: bool = True) -> dict:
        """
        Calculate platform fees and taxes for a transaction
        
        Args:
            amount: Transaction amount
            transaction_type: Type of transaction
            include_tax: Whether to include tax calculation
            
        Returns:
            dict with fee breakdown:
            {
                'amount': original amount,
                'platform_fee': platform fee (1%),
                'tax': tax on platform fee,
                'total_fee': platform_fee + tax,
                'net_amount': amount - total_fee (what service provider receives),
                'gross_amount': amount (what patient pays),
                'fee_breakdown': detailed breakdown
            }
        """
        amount = Decimal(str(amount))
        
        # No fees for wallet top-ups
        if transaction_type in FeeCalculationService.FEE_EXEMPT_TYPES:
            return {
                'amount': amount,
                'platform_fee': Decimal('0'),
                'tax': Decimal('0'),
                'total_fee': Decimal('0'),
                'net_amount': amount,
                'gross_amount': amount,
                'fee_breakdown': {
                    'platform_fee_percentage': '0%',
                    'platform_fee': Decimal('0'),
                    'tax_rate': '0%',
                    'tax_on_fee': Decimal('0'),
                    'total_deducted': Decimal('0')
                }
            }
        
        # Calculate platform fee (1% of transaction amount)
        platform_fee = (amount * FeeCalculationService.PLATFORM_FEE_PERCENTAGE).quantize(Decimal('0.01'))
        
        # Calculate tax on platform fee if applicable
        tax_on_fee = Decimal('0')
        if include_tax:
            tax_on_fee = (platform_fee * FeeCalculationService.TAX_RATE).quantize(Decimal('0.01'))
        
        total_fee = platform_fee + tax_on_fee
        net_amount = amount - total_fee
        
        return {
            'amount': amount,
            'platform_fee': platform_fee,
            'tax': tax_on_fee,
            'total_fee': total_fee,
            'net_amount': net_amount,
            'gross_amount': amount,
            'fee_breakdown': {
                'platform_fee_percentage': f'{FeeCalculationService.PLATFORM_FEE_PERCENTAGE * 100}%',
                'platform_fee': platform_fee,
                'tax_rate': f'{FeeCalculationService.TAX_RATE * 100}%' if include_tax else '0%',
                'tax_on_fee': tax_on_fee,
                'total_deducted': total_fee
            }
        }
    
    @staticmethod
    def calculate_service_payment_fees(service_amount: Decimal, payment_method: str = 'wallet') -> dict:
        """
        Calculate fees for service payments (appointments, prescriptions, etc.)
        
        Args:
            service_amount: Amount charged for the service
            payment_method: 'wallet' or 'onsite'
            
        Returns:
            Fee breakdown dictionary
        """
        # 1% fee applies to both wallet and on-site payments
        fees = FeeCalculationService.calculate_fees(
            service_amount,
            transaction_type='service_payment',
            include_tax=True
        )
        
        fees['payment_method'] = payment_method
        fees['is_onsite'] = payment_method == 'onsite'
        
        return fees
    
    @staticmethod
    def calculate_payout_deductions(
        total_earnings: Decimal,
        wallet_transactions_count: int,
        onsite_transactions_count: int,
        wallet_transactions_total: Decimal,
        onsite_transactions_total: Decimal
    ) -> dict:
        """
        Calculate total deductions for provider payout
        
        Args:
            total_earnings: Total amount earned by provider
            wallet_transactions_count: Number of wallet payments received
            onsite_transactions_count: Number of on-site payments received
            wallet_transactions_total: Total from wallet payments
            onsite_transactions_total: Total from on-site payments
            
        Returns:
            dict with payout breakdown
        """
        # Calculate fees on wallet transactions (1% + tax)
        wallet_fees = FeeCalculationService.calculate_fees(
            wallet_transactions_total,
            'service_payment',
            include_tax=True
        )
        
        # Calculate fees on on-site transactions (1% + tax)
        onsite_fees = FeeCalculationService.calculate_fees(
            onsite_transactions_total,
            'service_payment',
            include_tax=True
        )
        
        total_platform_fees = wallet_fees['platform_fee'] + onsite_fees['platform_fee']
        total_tax = wallet_fees['tax'] + onsite_fees['tax']
        total_deductions = wallet_fees['total_fee'] + onsite_fees['total_fee']
        
        net_payout = total_earnings - total_deductions
        
        return {
            'total_earnings': total_earnings,
            'wallet_payments': {
                'count': wallet_transactions_count,
                'total': wallet_transactions_total,
                'platform_fee': wallet_fees['platform_fee'],
                'tax': wallet_fees['tax'],
                'total_fee': wallet_fees['total_fee']
            },
            'onsite_payments': {
                'count': onsite_transactions_count,
                'total': onsite_transactions_total,
                'platform_fee': onsite_fees['platform_fee'],
                'tax': onsite_fees['tax'],
                'total_fee': onsite_fees['total_fee']
            },
            'total_platform_fees': total_platform_fees,
            'total_tax': total_tax,
            'total_deductions': total_deductions,
            'net_payout_amount': net_payout,
            'fee_summary': {
                'platform_fee_rate': '1%',
                'tax_rate': f'{FeeCalculationService.TAX_RATE * 100}%',
                'total_transactions': wallet_transactions_count + onsite_transactions_count
            }
        }

