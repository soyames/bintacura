#!/usr/bin/env python
"""Test insurance company API endpoint"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Participant
from core.serializers import InsuranceCompanySerializer

print("\n" + "=" * 70)
print("TESTING INSURANCE COMPANY API")
print("=" * 70)

# Get insurance companies
companies = Participant.objects.filter(
    role='insurance_company',
    is_active=True
).select_related('insurance_company_data')

print(f"\nTotal Insurance Companies: {companies.count()}")

if companies.exists():
    print("\nSerializing insurance companies:")
    print("-" * 70)
    
    serializer = InsuranceCompanySerializer(companies, many=True)
    
    for company_data in serializer.data:
        print(f"\n✅ {company_data['name']}")
        print(f"   Email: {company_data['email']}")
        print(f"   Phone: {company_data['phone']}")
        if company_data.get('company_info'):
            info = company_data['company_info']
            print(f"   Company: {info.get('company_name')}")
            print(f"   License: {info.get('license_number')}")
            print(f"   Country: {info.get('country')}")
        print(f"   Packages: {len(company_data.get('packages', []))}")
        print(f"   Verified: {'Yes' if company_data.get('is_verified') else 'No'}")
else:
    print("\n❌ No insurance companies found!")

print("\n" + "=" * 70)
print("\nAPI Endpoints Available:")
print("  GET /api/v1/participants/?role=insurance_company")
print("  GET /api/v1/participants/insurance-companies/")
print("=" * 70)
