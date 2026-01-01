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
        self.api_key = getattr(settings, 'FEDAPAY_API_KEY', os.getenv('FEDAPAY_SK_SANDBOX'))
        self.environment = getattr(settings, 'FEDAPAY_ENVIRONMENT', os.getenv('FEDAPAY_ENVIRONMENT', 'sandbox'))
        
        if not self.api_key:
            logger.error("FEDAPAY_API_KEY is not configured!")
            logger.error(f"Environment: {self.environment}")
            logger.error("Please set FEDAPAY_SK_SANDBOX or FEDAPAY_SK_LIVE in your .env file")
            raise ValueError("FedaPay API key is required")
        
        if self.environment == 'sandbox':
            self.base_url = 'https://sandbox-api.fedapay.com/v1'
        else:
            self.base_url = 'https://api.fedapay.com/v1'
        
        # FedaPay uses the Secret Key (SK) for API authentication
        # Format: Authorization: Bearer sk_sandbox_xxx or sk_live_xxx
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        logger.info(f"✅ FedaPay initialized in {self.environment} mode")
        logger.info(f"   Base URL: {self.base_url}")
        logger.info(f"   API Key: {self.api_key[:15]}... (masked)")
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make HTTP request to FedaPay API"""
        url = f'{self.base_url}/{endpoint}'
        
        try:
            logger.info(f"🔵 FedaPay {method} request to: {url}")
            logger.info(f"   Request data: {data}")
            logger.info(f"   Headers: Authorization: Bearer {self.api_key[:20]}...")
            
            if method == 'GET':
                response = requests.get(url, headers=self.headers, params=data, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, headers=self.headers, json=data, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=self.headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            logger.info(f"   ✅ Response status: {response.status_code}")
            
            # Check if request was successful
            if response.status_code >= 400:
                error_text = response.text
                logger.error(f"   ❌ Error response: {error_text}")
                response.raise_for_status()
            
            result = response.json() if response.text else {}
            logger.info(f"   ✅ Response data received successfully")
            return result
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ FedaPay HTTP Error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"   Error details: {error_data}")
                except:
                    logger.error(f"   Error text: {e.response.text}")
            raise Exception(f"FedaPay API error: {e.response.status_code} {e.response.reason}")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ FedaPay API request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"   Response text: {e.response.text}")
            raise Exception(f"FedaPay API error: {str(e)}")
    
    def _format_phone_for_fedapay(self, phone_number: str) -> Optional[Dict]:
        """
        Format phone number for FedaPay API
        FedaPay expects: {"number": "97000001", "country": "BJ"}
        - No + prefix
        - No country code
        - Just the local number digits
        
        Country code mapping:
        +229 -> BJ (Benin) - 8 digits
        +226 -> BF (Burkina Faso) - 8 digits
        +243 -> CD (DRC) - 9 digits
        +225 -> CI (Côte d'Ivoire) - 10 digits
        +228 -> TG (Togo) - 8 digits
        """
        if not phone_number:
            return None
        
        # Clean phone number - remove all non-digits
        phone = ''.join(filter(str.isdigit, phone_number))
        
        # Country code mapping
        country_codes = {
            '229': ('BJ', 8),  # Benin
            '226': ('BF', 8),  # Burkina Faso
            '243': ('CD', 9),  # DRC
            '225': ('CI', 10), # Côte d'Ivoire
            '228': ('TG', 8),  # Togo
        }
        
        country = 'BJ'  # Default to Benin
        expected_length = 8
        
        # Try to extract country code
        for code, (iso, length) in country_codes.items():
            if phone.startswith(code):
                country = iso
                expected_length = length
                phone = phone[len(code):]  # Remove country code
                break
        
        # Remove leading zeros
        phone = phone.lstrip('0')
        
        # Validate length
        if len(phone) == expected_length:
            return {
                'number': phone,
                'country': country
            }
        else:
            logger.warning(f"Invalid phone number: {phone_number} -> {phone} (expected {expected_length} digits for {country})")
            # Try to use it anyway if we have some digits
            if len(phone) >= 8:
                return {
                    'number': phone[:expected_length],
                    'country': country
                }
            return None
    
    def create_customer(self, participant) -> Dict:
        """Create or retrieve a FedaPay customer"""
        logger.error(f"🔍 =============== FEDAPAY CUSTOMER CREATION DEBUG ===============")
        logger.error(f"   Participant Type: {type(participant)}")
        logger.error(f"   Email: {participant.email}")
        logger.error(f"   Full name: {participant.full_name}")
        logger.error(f"   Role: {participant.role}")
        logger.error(f"   UID: {participant.uid}")
        logger.error(f"   Phone: {participant.phone_number}")
        logger.error(f"=================================================================")
        
        # Split full name into first and last name
        name_parts = participant.full_name.split() if participant.full_name else ['User']
        firstname = name_parts[0] if name_parts else 'User'
        lastname = ' '.join(name_parts[1:]) if len(name_parts) > 1 else 'BINTACURA'
        
        # Ensure we have valid names
        if not firstname or len(firstname.strip()) == 0:
            firstname = 'User'
        if not lastname or len(lastname.strip()) == 0:
            lastname = 'BINTACURA'
        
        data = {
            'firstname': firstname.strip(),
            'lastname': lastname.strip(),
            'email': participant.email,
        }
        
        # Add phone number if available
        phone_data = self._format_phone_for_fedapay(participant.phone_number)
        if phone_data:
            data['phone_number'] = phone_data
        
        try:
            logger.info(f"Creating FedaPay customer with data: {data}")
            response = self._make_request('POST', 'customers', data)
            logger.info(f"FedaPay customer creation response: {response}")
            
            # FedaPay returns: {"v1/customer": {...}}
            if 'v1/customer' in response:
                customer = response['v1/customer']
                logger.info(f"✅ Customer created successfully with ID: {customer.get('id')}")
                return customer
            
            # Fallback for different response format
            logger.info(f"✅ Customer created (alternate format)")
            return response
        except Exception as e:
            logger.error(f"❌ Failed to create FedaPay customer: {str(e)}")
            logger.error(f"   Participant: {participant.email} - {participant.full_name}")
            logger.error(f"   Phone: {participant.phone_number}")
            raise
    
    def create_transaction(
        self,
        amount: Decimal,
        currency: str,
        description: str,
        customer_id: int,
        callback_url: str,
        custom_metadata: Optional[Dict] = None,
        merchant_reference: Optional[str] = None
    ) -> Dict:
        """Create a payment transaction"""
        
        # FedaPay expects amount as integer (whole units)
        # For XOF: 3500 XOF = 3500 (no decimal places)
        amount_in_units = int(amount)
        
        data = {
            'description': description,
            'amount': amount_in_units,
            'currency': {'iso': currency.upper()},
            'callback_url': callback_url,
            'customer': {'id': customer_id}
        }
        
        if custom_metadata:
            data['custom_metadata'] = custom_metadata
        
        if merchant_reference:
            data['merchant_reference'] = merchant_reference
        
        try:
            response = self._make_request('POST', 'transactions', data)
            
            # FedaPay returns: {"v1/transaction": {...}}
            if 'v1/transaction' in response:
                return response['v1/transaction']
            
            return response
        except Exception as e:
            logger.error(f"Failed to create FedaPay transaction: {str(e)}")
            raise
    
    def generate_payment_token(self, transaction_id: int) -> Dict:
        """Generate payment token and URL for a transaction"""
        try:
            response = self._make_request('POST', f'transactions/{transaction_id}/token')
            
            # Response format: {"token": "...", "url": "..."}
            return response
        except Exception as e:
            logger.error(f"Failed to generate payment token: {str(e)}")
            raise
    
    def get_transaction(self, transaction_id: int) -> Dict:
        """Retrieve a transaction by ID"""
        try:
            response = self._make_request('GET', f'transactions/{transaction_id}')
            
            # FedaPay returns: {"v1/transaction": {...}}
            if 'v1/transaction' in response:
                return response['v1/transaction']
            
            return response
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
        payout_data = {'id': payout_id}
        
        if phone_number:
            phone_formatted = self._format_phone_for_fedapay(phone_number)
            if phone_formatted:
                payout_data['phone_number'] = phone_formatted
        
        data = {'payouts': [payout_data]}
        
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

