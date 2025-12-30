"""
Quick script to test if login is working
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Participant
from django.contrib.auth import authenticate

print("="*70)
print("TESTING LOGIN FUNCTIONALITY")
print("="*70)

# Get all participants
participants = Participant.objects.all()
print(f"\nTotal participants in database: {participants.count()}\n")

for p in participants:
    print(f"Email: {p.email}")
    print(f"  Role: {p.role}")
    print(f"  Active: {'✅' if p.is_active else '❌'} {p.is_active}")
    print(f"  Email Verified: {'✅' if p.is_email_verified else '❌'} {p.is_email_verified}")
    print(f"  Superuser: {'✅' if p.is_superuser else '❌'} {p.is_superuser}")
    print(f"  Has Password: {'✅' if p.has_usable_password() else '❌'} {p.has_usable_password()}")
    print(f"  Can Login: {'✅ YES' if (p.is_active and p.has_usable_password()) else '❌ NO'}")
    print()

print("="*70)
print("AUTHENTICATION TEST")
print("="*70)
print("\nNote: I cannot test actual passwords for security reasons.")
print("But I can verify the accounts are ready to authenticate.\n")

for p in participants:
    print(f"Account: {p.email}")
    if p.is_active and p.has_usable_password():
        print(f"  ✅ Ready to login")
        print(f"  → Use this email with your password at /auth/login/")
    else:
        print(f"  ❌ Not ready to login")
        if not p.is_active:
            print(f"     Reason: Account not active")
        if not p.has_usable_password():
            print(f"     Reason: No password set")
    print()

print("="*70)
print("SUMMARY")
print("="*70)
print(f"\n✅ {participants.filter(is_active=True, is_email_verified=True).count()} accounts ready to login")
print(f"❌ {participants.filter(is_active=False).count()} accounts need activation")
print("\nIf you can't login, make sure:")
print("  1. You're using the correct password")
print("  2. You complete the hCaptcha")
print("  3. Cookies are enabled in your browser")
print("\nTo reset password:")
print("  python manage.py shell")
print("  >>> from core.models import Participant")
print("  >>> user = Participant.objects.get(email='your@email.com')")
print("  >>> user.set_password('new_password')")
print("  >>> user.save()")
