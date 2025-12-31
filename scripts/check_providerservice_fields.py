#!/usr/bin/env python
"""Check ProviderService field names"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import ProviderService, ParticipantService

print("\n" + "=" * 60)
print("PROVIDERSERVICE FIELD CHECK")
print("=" * 60)

print(f"\nProviderService == ParticipantService: {ProviderService == ParticipantService}")
print(f"\nProviderService is ParticipantService: {ProviderService is ParticipantService}")

print("\nFields containing 'participant' or 'provider':")
for field in ProviderService._meta.fields:
    if 'participant' in field.name or 'provider' in field.name:
        print(f"  - {field.name}: {field.__class__.__name__}")

print("\nForeignKey fields:")
for field in ProviderService._meta.fields:
    if field.get_internal_type() == 'ForeignKey':
        print(f"  - {field.name} → {field.related_model.__name__}")

print("\n" + "=" * 60)
