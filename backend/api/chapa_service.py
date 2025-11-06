"""
Chapa Payment Service Integration
Handles all Chapa payment operations for the book marketplace
"""
import hashlib
import hmac
import json
import requests
from datetime import datetime
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class ChapaService:
    """
    Chapa Payment Service for handling all payment operations
    """
    
    def __init__(self):
        # Chapa configuration from environment
        self.base_url = getattr(settings, 'CHAPA_BASE_URL', 'https://api.chapa.co/v1')
        self.test_mode = getattr(settings, 'CHAPA_TEST_MODE', True)  # Default to test mode for Ethiopian users
        self.public_key = getattr(settings, 'CHAPA_PUBLIC_KEY', 'CHAPUBK_TEST-v3JKhynQP4agIXoPDws1V5MNDSzfih9l')
        self.secret_key = getattr(settings, 'CHAPA_SECRET_KEY', 'CHASECK_TEST-Usww6shqQXig4c3yMe9H9VKN50iIhYMc')
        self.encryption_key = getattr(settings, 'CHAPA_ENCRYPTION_KEY', 's3c68Acs3dX1j6IGyROcqMvo')
        
    def _get_headers(self):
        """Get headers for Chapa API requests"""
        return {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def create_checkout(self, amount, currency='ETB', description='', callback_url='', return_url='', **kwargs):
        """
        Create a Chapa checkout session
        
        Args:
            amount (float): Payment amount
            currency (str): Currency code (default: ETB)
            description (str): Payment description
            callback_url (str): Webhook callback URL
            return_url (str): Return URL after payment
            **kwargs: Additional parameters
            
        Returns:
            dict: Checkout response data
        """
        try:
            # Generate unique transaction reference
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            tx_ref = f"TXN{timestamp}"
            
            # Check if we're in test mode and return mock response for Ethiopian testing
            if self.test_mode:
                logger.info(f"Creating test Chapa checkout: {tx_ref}")
                
                # Mock checkout URL for testing Ethiopian payment flows
                test_checkout_url = f"https://checkout.chapa.co/test-mode/{tx_ref}?amount={amount}&currency={currency}&country=ET&provider=test"
                
                # Add Ethiopian-specific test data
                test_data = {
                    'success': True,
                    'test_mode': True,
                    'checkout_url': test_checkout_url,
                    'tx_ref': tx_ref,
                    'payment_id': f"test_payment_{tx_ref}",
                    'amount': amount,
                    'currency': currency,
                    'test_info': {
                        'country': 'ET (Ethiopia)',
                        'payment_methods': ['telebir', 'cbe_bir', 'hellocash', 'amole'],
                        'network_providers': ['Ethio Telecom', 'CBE', 'Safaricom'],
                        'test_transaction': True,
                        'demo_transaction': True
                    }
                }
                
                return test_data
            
            # Production mode - make actual API call
            checkout_data = {
                'amount': f"{amount:.2f}",
                'currency': currency,
                'tx_ref': tx_ref,
                'redirect_url': return_url or kwargs.get('return_url', 'http://localhost:3000/payment/success'),
                'callback_url': callback_url or kwargs.get('callback_url', 'http://localhost:8000/api/payments/chapa/webhook'),
                'customization': {
                    'title': description or 'Book Purchase',
                    'description': 'Purchase books from our marketplace',
                    'logo': kwargs.get('logo', 'https://yourdomain.com/logo.png')
                },
                'customer': {
                    'email': kwargs.get('customer_email', 'customer@example.com'),
                    'name': kwargs.get('customer_name', 'Customer'),
                    'phone_number': kwargs.get('phone_number', '+251911234567')
                },
                'meta': {
                    'source': 'book_marketplace',
                    'integration_check': 'chapa',
                    **kwargs.get('meta', {})
                }
            }
            
            # Make request to Chapa API
            url = f"{self.base_url}/checkout"
            response = requests.post(url, json=checkout_data, headers=self._get_headers())
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Chapa checkout created successfully: {tx_ref}")
                return {
                    'success': True,
                    'checkout_url': data.get('data', {}).get('checkout_url'),
                    'tx_ref': tx_ref,
                    'payment_id': data.get('data', {}).get('payment_id'),
                    'amount': amount,
                    'currency': currency
                }
            else:
                error_msg = f"Chapa API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            error_msg = f"Failed to create Chapa checkout: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def verify_transaction(self, tx_ref):
        """
        Verify a Chapa transaction status
        
        Args:
            tx_ref (str): Transaction reference
            
        Returns:
            dict: Verification response data
        """
        try:
            # Check if we're in test mode - return mock verification for Ethiopian testing
            if self.test_mode and tx_ref.startswith('TXN'):
                logger.info(f"Test mode verification for Ethiopian user: {tx_ref}")
                
                # Simulate successful Ethiopian payment verification
                test_verification = {
                    'success': True,
                    'status': 'success',
                    'amount': '100.00',
                    'currency': 'ETB',
                    'tx_ref': tx_ref,
                    'reference': f'CHAP_REF_{tx_ref}',
                    'test_mode': True,
                    'ethiopian_payment': True,
                    'payment_details': {
                        'provider': 'telebir',  # Most popular Ethiopian mobile money
                        'network': 'Ethio Telecom',
                        'country': 'ET',
                        'test_transaction': True
                    },
                    'full_data': {
                        'status': 'success',
                        'amount': '100.00',
                        'currency': 'ETB',
                        'tx_ref': tx_ref,
                        'reference': f'CHAP_REF_{tx_ref}',
                        'customer': {
                            'name': 'Ethiopian Test Customer',
                            'email': 'test@ethiopia.et',
                            'phone_number': '+251911234567'
                        }
                    }
                }
                
                return test_verification
            
            # Production mode - make actual verification API call
            url = f"{self.base_url}/transaction/verify/{tx_ref}"
            response = requests.get(url, headers=self._get_headers())
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'status': data.get('data', {}).get('status'),
                    'amount': data.get('data', {}).get('amount'),
                    'currency': data.get('data', {}).get('currency'),
                    'tx_ref': data.get('data', {}).get('tx_ref'),
                    'reference': data.get('data', {}).get('reference'),
                    'full_data': data.get('data', {})
                }
            else:
                error_msg = f"Chapa verification error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            error_msg = f"Failed to verify Chapa transaction: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def generate_signature(self, data, secret_key=None):
        """
        Generate signature for webhook verification
        
        Args:
            data (dict): Data to sign
            secret_key (str): Secret key to use
            
        Returns:
            str: Generated signature
        """
        try:
            # Convert data to query string format
            query_string = '&'.join([f"{k}={v}" for k, v in sorted(data.items())])
            
            # Generate signature
            secret = secret_key or self.encryption_key
            signature = hmac.new(
                secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return signature
            
        except Exception as e:
            logger.error(f"Failed to generate signature: {str(e)}")
            return None
    
    def verify_webhook_signature(self, payload, signature, secret_key=None):
        """
        Verify webhook signature
        
        Args:
            payload (str): Raw webhook payload
            signature (str): Received signature
            secret_key (str): Secret key to use
            
        Returns:
            bool: True if signature is valid
        """
        try:
            expected_signature = self.generate_signature(payload, secret_key)
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"Failed to verify webhook signature: {str(e)}")
            return False
    
    def get_supported_currencies(self):
        """
        Get list of supported currencies
        
        Returns:
            list: List of supported currencies
        """
        return ['ETB', 'USD']
    
    def get_payment_methods(self):
        """
        Get available payment methods for Chapa
        
        Returns:
            dict: Payment methods configuration
        """
        return {
            'telebir': {
                'id': 'telebir',
                'name': 'Telebir',
                'type': 'mobile',
                'icon': '📱',
                'networks': ['Ethio Telecom'],
                'popular': True
            },
            'cbe_bir': {
                'id': 'cbe_bir', 
                'name': 'CBE Bir',
                'type': 'bank',
                'icon': '🏦',
                'networks': ['CBE'],
                'popular': True
            },
            'hellocash': {
                'id': 'hellocash',
                'name': 'HelloCash',
                'type': 'mobile',
                'icon': '💰',
                'networks': ['Ethio Telecom', 'Safaricom'],
                'popular': False
            },
            'dashen': {
                'id': 'dashen',
                'name': 'Dashen Bank',
                'type': 'bank',
                'icon': '🏛️',
                'networks': ['Dashen Bank'],
                'popular': False
            },
            'awash': {
                'id': 'awash',
                'name': 'Awash Bank',
                'type': 'bank',
                'icon': '🏦',
                'networks': ['Awash Bank'],
                'popular': False
            },
            'amole': {
                'id': 'amole',
                'name': 'Amole',
                'type': 'mobile',
                'icon': '💳',
                'networks': ['Ethio Telecom'],
                'popular': False
            }
        }
    
    def calculate_conversion_rate(self, from_currency, to_currency):
        """
        Calculate currency conversion rate
        
        Args:
            from_currency (str): Source currency
            to_currency (str): Target currency
            
        Returns:
            float: Conversion rate
        """
        try:
            # Cache rates for 1 hour
            cache_key = f"chapa_rates_{from_currency}_{to_currency}"
            cached_rate = cache.get(cache_key)
            
            if cached_rate:
                return cached_rate
            
            # Make API call to get current rates
            url = f"{self.base_url}/exchange-rate"
            response = requests.get(url, params={
                'from': from_currency,
                'to': to_currency
            }, headers=self._get_headers())
            
            if response.status_code == 200:
                data = response.json()
                rate = float(data.get('rate', 55.0))  # Default fallback rate
                cache.set(cache_key, rate, 3600)  # Cache for 1 hour
                return rate
            else:
                # Return default rate based on common conversions
                default_rates = {
                    ('USD', 'ETB'): 55.0,
                    ('ETB', 'USD'): 0.018,
                }
                return default_rates.get((from_currency, to_currency), 55.0)
                
        except Exception as e:
            logger.error(f"Failed to get conversion rate: {str(e)}")
            return 55.0  # Default ETB to USD rate
    
    def get_ethiopian_payment_methods(self):
        """
        Get Ethiopian-specific payment methods for testing
        
        Returns:
            dict: Ethiopian payment methods configuration
        """
        ethiopian_methods = {
            'telebir': {
                'id': 'telebir',
                'name': 'Telebir',
                'type': 'mobile_money',
                'icon': '📱',
                'network': 'Ethio Telecom',
                'popular': True,
                'country': 'ET',
                'test_available': self.test_mode
            },
            'cbe_bir': {
                'id': 'cbe_bir',
                'name': 'CBE Birr',
                'type': 'mobile_banking',
                'icon': '🏦',
                'network': 'Commercial Bank of Ethiopia',
                'popular': True,
                'country': 'ET',
                'test_available': self.test_mode
            },
            'hellocash': {
                'id': 'hellocash',
                'name': 'HelloCash',
                'type': 'mobile_money',
                'icon': '💰',
                'network': 'Ethio Telecom',
                'popular': False,
                'country': 'ET',
                'test_available': self.test_mode
            },
            'amole': {
                'id': 'amole',
                'name': 'Amole',
                'type': 'mobile_money',
                'icon': '💳',
                'network': 'Ethio Telecom',
                'popular': False,
                'country': 'ET',
                'test_available': self.test_mode
            },
            'dashen': {
                'id': 'dashen',
                'name': 'Dashen Bank',
                'type': 'bank_transfer',
                'icon': '🏛️',
                'network': 'Dashen Bank',
                'popular': False,
                'country': 'ET',
                'test_available': self.test_mode
            },
            'awash': {
                'id': 'awash',
                'name': 'Awash Bank',
                'type': 'bank_transfer',
                'icon': '🏦',
                'network': 'Awash Bank',
                'popular': False,
                'country': 'ET',
                'test_available': self.test_mode
            }
        }
        
        return ethiopian_methods
    
    def simulate_ethiopian_payment(self, method_id, amount, phone_number=None):
        """
        Simulate Ethiopian payment method for testing
        
        Args:
            method_id (str): Payment method ID
            amount (float): Payment amount
            phone_number (str): Optional phone number
            
        Returns:
            dict: Simulated payment result
        """
        if not self.test_mode:
            return {
                'success': False,
                'error': 'Test mode disabled'
            }
        
        try:
            methods = self.get_ethiopian_payment_methods()
            method = methods.get(method_id)
            
            if not method:
                return {
                    'success': False,
                    'error': f'Payment method {method_id} not found'
                }
            
            # Simulate Ethiopian payment processing
            import random
            transaction_id = f"ET{random.randint(100000, 999999)}"
            
            # Simulate success/failure (90% success rate for testing)
            is_success = random.random() > 0.1
            
            if is_success:
                return {
                    'success': True,
                    'test_mode': True,
                    'transaction_id': transaction_id,
                    'method': method['name'],
                    'network': method['network'],
                    'amount': amount,
                    'currency': 'ETB',
                    'phone_number': phone_number or '+251911234567',
                    'status': 'completed',
                    'ethiopian_payment': True,
                    'test_info': {
                        'country': 'ET',
                        'provider': method['name'],
                        'network': method['network'],
                        'simulated_transaction': True
                    }
                }
            else:
                return {
                    'success': False,
                    'error': 'Insufficient balance or network error',
                    'test_mode': True,
                    'transaction_id': transaction_id,
                    'method': method['name'],
                    'amount': amount,
                    'status': 'failed',
                    'ethiopian_payment': True
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Simulation error: {str(e)}',
                'test_mode': True
            }
    
    def enable_test_mode(self):
        """Enable test mode for Ethiopian payment testing"""
        self.test_mode = True
        logger.info("Chapa test mode enabled for Ethiopian payment testing")
    
    def disable_test_mode(self):
        """Disable test mode for production"""
        self.test_mode = False
        logger.info("Chapa test mode disabled for production")
    
    def is_test_mode(self):
        """Check if test mode is enabled"""
        return self.test_mode
    
    def process_refund(self, tx_ref, amount=None, reason=None):
        """
        Process a refund
        
        Args:
            tx_ref (str): Transaction reference
            amount (float): Refund amount (optional, defaults to full amount)
            reason (str): Refund reason
            
        Returns:
            dict: Refund response data
        """
        try:
            refund_data = {
                'tx_ref': tx_ref,
                'reason': reason or 'Customer request'
            }
            
            if amount:
                refund_data['amount'] = f"{amount:.2f}"
            
            url = f"{self.base_url}/refund"
            response = requests.post(url, json=refund_data, headers=self._get_headers())
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Refund processed successfully for {tx_ref}")
                return {
                    'success': True,
                    'refund_id': data.get('data', {}).get('id'),
                    'status': data.get('data', {}).get('status'),
                    'amount': data.get('data', {}).get('amount')
                }
            else:
                error_msg = f"Chapa refund error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            error_msg = f"Failed to process refund: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def get_transaction_report(self, start_date=None, end_date=None):
        """
        Get transaction report
        
        Args:
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            
        Returns:
            dict: Transaction report data
        """
        try:
            params = {}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
                
            url = f"{self.base_url}/transaction/report"
            response = requests.get(url, params=params, headers=self._get_headers())
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'data': data.get('data', {}),
                    'total_transactions': data.get('total_transactions', 0),
                    'total_amount': data.get('total_amount', 0),
                    'report_period': {
                        'start': start_date,
                        'end': end_date
                    }
                }
            else:
                error_msg = f"Chapa report error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            error_msg = f"Failed to get transaction report: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

# Create global instance
chapa_service = ChapaService()