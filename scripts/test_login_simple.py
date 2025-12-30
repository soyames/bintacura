import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Participant

# Test smartwork608 account
email = 'smartwork608@gmail.com'
participant = Participant.objects.using('default').filter(email=email).first()

if participant:
    print(f"\n✅ Found participant: {participant.first_name} {participant.last_name}")
    print(f"   Email: {participant.email}")
    print(f"   Role: {participant.role}")
    print(f"   Active: {participant.is_active}")
    print(f"   Email Verified: {participant.is_email_verified}")
    print(f"   UID: {participant.uid}")
else:
    print(f"\n❌ No participant found with email: {email}")

# Test super admin
super_admin = Participant.objects.using('default').filter(email='support@bintacura.org').first()
if super_admin:
    print(f"\n✅ Super Admin found: {super_admin.first_name}")
    print(f"   Email: {super_admin.email}")
    print(f"   Is Superuser: {super_admin.is_superuser}")
    print(f"   Is Staff: {super_admin.is_staff}")
else:
    print(f"\n❌ Super admin not found")

print(f"\n📊 Total participants in AWS: {Participant.objects.using('default').count()}")
