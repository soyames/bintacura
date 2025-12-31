#!/usr/bin/env python
"""Check insurance company data"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Participant, InsuranceCompanyData

print("\nChecking Insurance Company Data:")
print("=" * 60)

companies = Participant.objects.filter(role='insurance_company')
for company in companies:
    print(f"\n{company.full_name}:")
    try:
        if hasattr(company, 'insurance_company_data'):
            data = company.insurance_company_data
            print(f"  ✅ Has InsuranceCompanyData")
            print(f"     Company Name: {data.company_name}")
            print(f"     License: {data.license_number}")
            print(f"     Country: {data.country}")
        else:
            print(f"  ❌ No InsuranceCompanyData")
    except InsuranceCompanyData.DoesNotExist:
        print(f"  ❌ InsuranceCompanyData does not exist")

print("\n" + "=" * 60)
print(f"\nTotal Companies: {companies.count()}")
print(f"With Data: {companies.filter(insurance_company_data__isnull=False).count()}")
