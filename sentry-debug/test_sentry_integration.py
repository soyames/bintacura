"""
Test Sentry Integration
Run this script to verify Sentry monitoring is working correctly.
"""
import os
import sys
import django
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

import sentry_sdk
from sentry_sdk import metrics

logger = logging.getLogger(__name__)

def test_sentry_logging():
    """Test Sentry logging integration"""
    print("\n=== Testing Sentry Logging ===")
    
    sentry_sdk.logger.info('✅ Sentry direct info log')
    sentry_sdk.logger.warning('⚠️ Sentry direct warning log')
    sentry_sdk.logger.error('❌ Sentry direct error log')
    
    logger.info('✅ Python logger info - should be sent to Sentry')
    logger.warning('⚠️ Python logger warning - should be sent to Sentry')
    logger.error('❌ Python logger error - should be sent to Sentry')
    
    print("Logs sent to Sentry successfully!")

def test_sentry_metrics():
    """Test Sentry metrics integration"""
    print("\n=== Testing Sentry Metrics ===")
    
    metrics.count("test.checkout.failed", 1)
    metrics.gauge("test.queue.depth", 42)
    metrics.distribution("test.cart.amount_usd", 187.5)
    
    print("Metrics sent to Sentry successfully!")

def test_sentry_error():
    """Test Sentry error tracking"""
    print("\n=== Testing Sentry Error Tracking ===")
    
    try:
        result = 1 / 0
    except ZeroDivisionError as e:
        sentry_sdk.capture_exception(e)
        print(f"Error captured and sent to Sentry: {e}")

def test_sentry_message():
    """Test Sentry message capture"""
    print("\n=== Testing Sentry Message Capture ===")
    
    sentry_sdk.capture_message("Test message from Bintacura health platform", level="info")
    print("Message sent to Sentry successfully!")

if __name__ == "__main__":
    print("=" * 60)
    print("BINTACURA - SENTRY INTEGRATION TEST")
    print("=" * 60)
    
    test_sentry_logging()
    test_sentry_metrics()
    test_sentry_error()
    test_sentry_message()
    
    print("\n" + "=" * 60)
    print("✅ All Sentry tests completed!")
    print("Check your Sentry dashboard at:")
    print("https://o4510646016606208.ingest.de.sentry.io")
    print("=" * 60)
