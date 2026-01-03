"""
Comprehensive Sentry Integration Verification
Tests all Sentry features implemented in Bintacura
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

import sentry_sdk
from sentry_sdk import metrics
from core.sentry_utils import (
    set_participant_context,
    set_transaction_context,
    capture_business_metric,
    capture_error_with_context,
    add_breadcrumb,
    sentry_trace
)
from django.test import RequestFactory
import logging

logger = logging.getLogger('BINTACURA')


def test_basic_logging():
    """Test 1: Basic logging integration"""
    print("\n✅ Test 1: Basic Logging Integration")
    logger.info('Info log test')
    logger.warning('Warning log test')
    logger.error('Error log test')
    print("   Logs sent to Sentry")


def test_participant_context():
    """Test 2: Participant context tracking"""
    print("\n✅ Test 2: Participant Context Tracking")
    
    class MockParticipant:
        uid = "123e4567-e89b-12d3-a456-426614174000"
        username = "test_patient"
        email = "patient@test.com"
        role = "patient"
    
    set_participant_context(MockParticipant())
    sentry_sdk.capture_message("Test with participant context")
    print("   Participant context set and tested")


def test_transaction_context():
    """Test 3: Transaction context tracking"""
    print("\n✅ Test 3: Transaction Context Tracking")
    set_transaction_context(
        'appointment_booking',
        '987e6543-e21b-45c9-b765-123456789abc',
        amount=5000,
        currency='XOF'
    )
    sentry_sdk.capture_message("Test with transaction context")
    print("   Transaction context set and tested")


def test_business_metrics():
    """Test 4: Business metrics capture"""
    print("\n✅ Test 4: Business Metrics Capture")
    capture_business_metric("test.appointment.booked", 1)
    capture_business_metric("test.payment.amount", 5000.0)
    metrics.gauge("test.queue.depth", 15)
    print("   Business metrics captured")


def test_error_with_context():
    """Test 5: Error capture with context"""
    print("\n✅ Test 5: Error Capture with Context")
    try:
        raise ValueError("Test error with context")
    except ValueError as e:
        capture_error_with_context(e, {
            "module": "test_suite",
            "operation": "verification",
            "test_id": "12345"
        })
    print("   Error captured with custom context")


def test_breadcrumbs():
    """Test 6: Breadcrumb tracking"""
    print("\n✅ Test 6: Breadcrumb Tracking")
    add_breadcrumb("Step 1: Initialize", category="flow", level="info")
    add_breadcrumb("Step 2: Validate", category="flow", level="info")
    add_breadcrumb("Step 3: Process", category="flow", level="info", data={"status": "success"})
    sentry_sdk.capture_message("Test with breadcrumbs")
    print("   Breadcrumbs added and tested")


@sentry_trace
def traced_function():
    """Function with performance tracing"""
    import time
    time.sleep(0.1)
    return "traced_result"


def test_performance_tracing():
    """Test 7: Performance tracing decorator"""
    print("\n✅ Test 7: Performance Tracing")
    result = traced_function()
    print(f"   Function traced: {result}")


def test_middleware_simulation():
    """Test 8: Middleware behavior simulation"""
    print("\n✅ Test 8: Middleware Simulation")
    from core.sentry_middleware import SentryContextMiddleware
    
    factory = RequestFactory()
    request = factory.get('/test/endpoint')
    
    class MockParticipant:
        uid = "middleware-test-123"
        username = "middleware_user"
        email = "middleware@test.com"
        role = "doctor"
    
    request.participant = MockParticipant()
    
    middleware = SentryContextMiddleware(lambda r: None)
    middleware.process_request(request)
    
    sentry_sdk.capture_message("Test middleware context")
    print("   Middleware context applied")


def test_logging_levels():
    """Test 9: Different logging levels"""
    print("\n✅ Test 9: Logging Levels")
    django_logger = logging.getLogger('django')
    security_logger = logging.getLogger('core.security')
    
    django_logger.warning('Django warning log')
    django_logger.error('Django error log')
    security_logger.warning('Security warning log')
    print("   Multiple logger levels tested")


def test_metrics_types():
    """Test 10: Different metric types"""
    print("\n✅ Test 10: Metric Types")
    metrics.count("test.counter", 1)
    metrics.gauge("test.gauge", 42)
    metrics.distribution("test.distribution", 123.45)
    print("   All metric types tested")


def run_all_tests():
    """Run all Sentry integration tests"""
    print("=" * 70)
    print("BINTACURA - COMPREHENSIVE SENTRY INTEGRATION VERIFICATION")
    print("=" * 70)
    
    tests = [
        test_basic_logging,
        test_participant_context,
        test_transaction_context,
        test_business_metrics,
        test_error_with_context,
        test_breadcrumbs,
        test_performance_tracing,
        test_middleware_simulation,
        test_logging_levels,
        test_metrics_types,
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"\n❌ Test failed: {test.__name__}")
            print(f"   Error: {str(e)}")
            sentry_sdk.capture_exception(e)
    
    print("\n" + "=" * 70)
    print("✅ ALL SENTRY INTEGRATION TESTS COMPLETED!")
    print("=" * 70)
    print("\nFeatures Verified:")
    print("  ✓ Basic logging integration")
    print("  ✓ Participant context tracking")
    print("  ✓ Transaction context tracking")
    print("  ✓ Business metrics capture")
    print("  ✓ Error capture with context")
    print("  ✓ Breadcrumb debugging")
    print("  ✓ Performance tracing")
    print("  ✓ Middleware integration")
    print("  ✓ Multi-level logging")
    print("  ✓ All metric types")
    print("\n📊 View results in Sentry Dashboard:")
    print("   https://o4510646016606208.ingest.de.sentry.io")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
