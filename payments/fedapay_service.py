import os
import logging
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
import requests
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class FedaPayService:
    """Service for integrating with FedaPay payment gateway"""
    
    def __init__(self):  # Initialize instance
        self.api_key = getattr(settings, 'FEDAPAY_API_KEY', os.getenv('FEDAPAY_API_KEY'))
        self.environment = getattr(settings, 'FEDAPAY_ENVIRONMENT', os.getenv('FEDAPAY_ENVIRONMENT', 'sandbox'))
        
        if self.environment == 'sandbox':
            self.base_url = 'https://sandbox-api.fedapay.com/v1'
        else:
            self.base_url = 'https://api.fedapay.com/v1'
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make HTTP request to FedaPay API"""
        url = f'{self.base_url}/{endpoint}'
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers, params=data)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            elif method == 'PUT':
                response = requests.put(url, headers=self.headers, json=data)
            elif method == 'DELETE':
                response = requests.delete(url, headers=self.headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json() if response.text else {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"FedaPay API request failed: {str(e)}")
            raise Exception(f"FedaPay API error: {str(e)}")
    
    def create_customer(self, participant) -> Dict:
        """Create or retrieve a FedaPay customer"""
        data = {
            'firstname': participant.full_name.split()[0] if participant.full_name else 'User',
            'lastname': ' '.join(participant.full_name.split()[1:]) if participant.full_name and len(participant.full_name.split()) > 1 else 'BINTACURA',
            'email': participant.email,
        }
        
        if participant.phone_number:
            data['phone_number'] = {
                'number': participant.phone_number,
                'country': participant.country[:2] if participant.country else 'BJ'
            }
        
        try:
            return self._make_request('POST', 'customers', data)
        except Exception as e:
            logger.error(f"Failed to create FedaPay customer: {str(e)}")
            raise
    
    def create_transaction(
        self,
        amount: Decimal,
        currency: str,
        description: str,
        customer_id: int,
        callback_url: str,
        custom_metadata: Optional[Dict] = None
    ) -> Dict:
        """Create a payment transaction"""
        
        amount_in_minor_units = int(amount * 100)
        
        data = {
            'description': description,
            'amount': amount_in_minor_units,
            'currency': {'iso': currency},
            'callback_url': callback_url,
            'customer': {'id': customer_id}
        }
        
        if custom_metadata:
            data['custom_metadata'] = custom_metadata
        
        try:
            return self._make_request('POST', 'transactions', data)
        except Exception as e:
            logger.error(f"Failed to create FedaPay transaction: {str(e)}")
            raise
    
    def generate_payment_token(self, transaction_id: int) -> Dict:
        """Generate payment token for a transaction"""
        try:
            return self._make_request('POST', f'transactions/{transaction_id}/token')
        except Exception as e:
            logger.error(f"Failed to generate payment token: {str(e)}")
            raise
    
    def get_transaction(self, transaction_id: int) -> Dict:
        """Retrieve a transaction by ID"""
        try:
            return self._make_request('GET', f'transactions/{transaction_id}')
        except Exception as e:
            logger.error(f"Failed to retrieve transaction: {str(e)}")
            raise
    
    def create_payout(
        self,
        amount: Decimal,
        currency: str,
        customer_id: int,
        mode: str = 'mtn'
    ) -> Dict:
        """Create a payout to a provider"""
        
        amount_in_minor_units = int(amount * 100)
        
        data = {
            'amount': amount_in_minor_units,
            'currency': {'iso': currency},
            'customer': {'id': customer_id},
            'mode': mode
        }
        
        try:
            return self._make_request('POST', 'payouts', data)
        except Exception as e:
            logger.error(f"Failed to create payout: {str(e)}")
            raise
    
    def start_payout(self, payout_id: int, phone_number: Optional[str] = None) -> Dict:
        """Start/execute a payout"""
        data = [{'id': payout_id}]
        
        if phone_number:
            data[0]['phone_number'] = {
                'number': phone_number,
                'country': 'BJ'
            }
        
        try:
            return self._make_request('PUT', 'payouts/start', data)
        except Exception as e:
            logger.error(f"Failed to start payout: {str(e)}")
            raise
    
    def get_balance(self) -> Dict:
        """Get account balance"""
        try:
            return self._make_request('GET', 'balances')
        except Exception as e:
            logger.error(f"Failed to retrieve balance: {str(e)}")
            raise
    
    def list_transactions(self, params: Optional[Dict] = None) -> Dict:
        """List all transactions"""
        try:
            return self._make_request('GET', 'transactions/search', params)
        except Exception as e:
            logger.error(f"Failed to list transactions: {str(e)}")
            raise
    
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """Verify webhook signature for security"""
        import hmac
        import hashlib
        
        webhook_secret = getattr(settings, 'FEDAPAY_WEBHOOK_SECRET', os.getenv('FEDAPAY_WEBHOOK_SECRET', ''))
        
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)


fedapay_service = FedaPayService()

