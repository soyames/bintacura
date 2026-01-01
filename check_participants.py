import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Participant

print(f"Total participants: {Participant.objects.count()}")
print(f"Roles: {list(Participant.objects.values_list('role', flat=True).distinct())}")

if Participant.objects.exists():
    p = Participant.objects.first()
    print(f"\nFirst participant:")
    print(f"  UID: {p.uid}")
    print(f"  Role: {p.role}")
    print(f"  Email: {p.email}")
    print(f"  Phone: {p.phone_number}")
    print(f"  Name: {p.full_name}")
