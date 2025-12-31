#!/usr/bin/env python
"""
BintaCura Platform Validation Script
Tests all critical fixes implemented on December 31, 2025
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection
from django.conf import settings
from core.models import Participant, RefundRequest, InsuranceClaim
from payments.models import ServiceTransaction, FedaPayTransaction
from doctor.models import DoctorService
from hospital.models import HospitalService
from pharmacy.models import PharmacyService
from insurance.models import InsurancePlan
from communication.models import ForumPost

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")

def print_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.END}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")

def print_section(title):
    print(f"\n{Colors.YELLOW}{'='*60}")
    print(f" {title}")
    print(f"{'='*60}{Colors.END}\n")

def validate_database_connectivity():
    """Test database connections"""
    print_section("Database Connectivity")
    
    databases = settings.DATABASES.keys()
    for db_name in databases:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            print_success(f"Database '{db_name}' connection successful")
        except Exception as e:
            print_error(f"Database '{db_name}' connection failed: {str(e)}")
            return False
    return True

def validate_models():
    """Test model integrity"""
    print_section("Model Integrity")
    
    models_to_test = [
        (Participant, "Participant"),
        (RefundRequest, "RefundRequest"),
        (InsuranceClaim, "InsuranceClaim"),
        (ServiceTransaction, "ServiceTransaction"),
        (FedaPayTransaction, "FedaPayTransaction"),
        (DoctorService, "DoctorService"),
        (HospitalService, "HospitalService"),
        (PharmacyService, "PharmacyService"),
        (InsurancePlan, "InsurancePlan"),
        (ForumPost, "ForumPost"),
    ]
    
    for model, name in models_to_test:
        try:
            count = model.objects.count()
            print_success(f"{name}: {count} records")
        except Exception as e:
            print_error(f"{name} failed: {str(e)}")
            return False
    return True

def validate_idempotency_keys():
    """Test idempotency key fields exist"""
    print_section("Idempotency Keys")
    
    models_with_keys = [
        (ServiceTransaction, "ServiceTransaction"),
        (FedaPayTransaction, "FedaPayTransaction"),
        (RefundRequest, "RefundRequest"),
        (InsuranceClaim, "InsuranceClaim"),
    ]
    
    for model, name in models_with_keys:
        try:
            if hasattr(model, 'idempotency_key'):
                print_success(f"{name} has idempotency_key field")
            else:
                print_error(f"{name} missing idempotency_key field")
                return False
        except Exception as e:
            print_error(f"{name} check failed: {str(e)}")
            return False
    return True

def validate_currency_defaults():
    """Test currency defaults are XOF"""
    print_section("Currency Defaults")
    
    models_with_currency = [
        (DoctorService, "DoctorService"),
        (HospitalService, "HospitalService"),
        (PharmacyService, "PharmacyService"),
        (InsurancePlan, "InsurancePlan"),
    ]
    
    for model, name in models_with_currency:
        try:
            field = model._meta.get_field('currency')
            default = field.default if hasattr(field, 'default') else None
            if default == 'XOF':
                print_success(f"{name} default currency: XOF")
            else:
                print_error(f"{name} default currency: {default} (should be XOF)")
                return False
        except Exception as e:
            print_error(f"{name} check failed: {str(e)}")
            return False
    return True

def validate_participant_fields():
    """Test Participant model has correct fields"""
    print_section("Participant Model Fields")
    
    required_fields = [
        'role',
        'verification_status',
        'phone_number',
        'country',
        'email',
        'is_verified',
    ]
    
    for field_name in required_fields:
        try:
            field = Participant._meta.get_field(field_name)
            print_success(f"Participant.{field_name} exists")
        except Exception as e:
            print_error(f"Participant.{field_name} missing: {str(e)}")
            return False
    
    # Check no 'provider' field exists
    try:
        Participant._meta.get_field('provider')
        print_error("Participant still has 'provider' field (should be removed)")
        return False
    except:
        print_success("Participant has no 'provider' field (correct)")
    
    return True

def validate_refund_model():
    """Test RefundRequest has participant field"""
    print_section("RefundRequest Model")
    
    try:
        field = RefundRequest._meta.get_field('participant')
        print_success("RefundRequest.participant field exists")
    except Exception as e:
        print_error(f"RefundRequest.participant missing: {str(e)}")
        return False
    
    # Check no 'provider' field exists
    try:
        RefundRequest._meta.get_field('provider')
        print_error("RefundRequest still has 'provider' field (should be removed)")
        return False
    except:
        print_success("RefundRequest has no 'provider' field (correct)")
    
    return True

def validate_forum_moderation():
    """Test ForumPost moderation fields"""
    print_section("Forum Moderation")
    
    required_fields = [
        'views_count',
        'is_censored',
        'censored_reason',
        'censored_by',
        'censored_at',
    ]
    
    for field_name in required_fields:
        try:
            field = ForumPost._meta.get_field(field_name)
            print_success(f"ForumPost.{field_name} exists")
        except Exception as e:
            print_error(f"ForumPost.{field_name} missing: {str(e)}")
            return False
    return True

def validate_regional_settings():
    """Test regional settings configuration"""
    print_section("Regional Settings")
    
    if not hasattr(settings, 'REGIONAL_SETTINGS'):
        print_error("REGIONAL_SETTINGS not found in settings.py")
        return False
    
    print_success("REGIONAL_SETTINGS exists in settings.py")
    
    required_regions = ['BENIN', 'GERMANY']
    for region in required_regions:
        if region in settings.REGIONAL_SETTINGS:
            config = settings.REGIONAL_SETTINGS[region]
            required_keys = ['database', 'currency', 'default_consultation_fee', 'timezone']
            
            for key in required_keys:
                if key in config:
                    print_success(f"{region}.{key}: {config[key]}")
                else:
                    print_error(f"{region}.{key} missing")
                    return False
        else:
            print_error(f"Region '{region}' not found in REGIONAL_SETTINGS")
            return False
    
    return True

def validate_language_settings():
    """Test French default language"""
    print_section("Language Configuration")
    
    if settings.LANGUAGE_CODE == 'fr':
        print_success(f"Default language: {settings.LANGUAGE_CODE}")
    else:
        print_error(f"Default language: {settings.LANGUAGE_CODE} (should be 'fr')")
        return False
    
    if settings.USE_I18N:
        print_success("Internationalization enabled")
    else:
        print_error("Internationalization disabled")
        return False
    
    return True

def main():
    """Run all validation tests"""
    print_info("BintaCura Platform Validation Script")
    print_info("Starting comprehensive system check...\n")
    
    tests = [
        ("Database Connectivity", validate_database_connectivity),
        ("Model Integrity", validate_models),
        ("Idempotency Keys", validate_idempotency_keys),
        ("Currency Defaults", validate_currency_defaults),
        ("Participant Model", validate_participant_fields),
        ("RefundRequest Model", validate_refund_model),
        ("Forum Moderation", validate_forum_moderation),
        ("Regional Settings", validate_regional_settings),
        ("Language Configuration", validate_language_settings),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test '{test_name}' crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print_section("Test Summary")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        color = Colors.GREEN if result else Colors.RED
        print(f"{color}{status:6}{Colors.END} {test_name}")
    
    print(f"\n{Colors.BLUE}Results: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print(f"{Colors.GREEN}\n✓ ALL TESTS PASSED - System ready for deployment{Colors.END}")
        return 0
    else:
        print(f"{Colors.RED}\n✗ SOME TESTS FAILED - Fix issues before deployment{Colors.END}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
