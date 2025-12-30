"""
Resend activation email to existing participants
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Participant
from authentication.email_service import send_verification_email
from authentication.tokens import generate_activation_code
from django.utils import timezone

def resend_activation_email(email):
    """Resend activation email to a participant"""
    try:
        participant = Participant.objects.get(email=email)
        print(f"\nParticipant: {participant.email}")
        print(f"  Role: {participant.role}")
        print(f"  Active: {participant.is_active}")
        print(f"  Email Verified: {participant.is_email_verified}")
        print(f"  Terms Accepted: {participant.terms_accepted}")
        
        # Generate new activation code
        activation_code = generate_activation_code()
        participant.activation_code = activation_code
        participant.activation_code_created_at = timezone.now()
        participant.save()
        
        print(f"\nActivation code generated: {activation_code}")
        
        # Send verification email
        result = send_verification_email(participant, activation_code)
        
        if result:
            print(f"SUCCESS: Verification email sent to {email}")
            print(f"  From: no-reply@bintacura.org")
            print(f"  Subject: Verification de votre compte - BINTACURA")
            print(f"  Code: {activation_code}")
            print(f"\nThe participant should check their inbox and spam folder.")
            return True
        else:
            print(f"FAILED: Could not send email to {email}")
            print("Check your email settings in .env file:")
            print("  - EMAIL_HOST_USER")
            print("  - EMAIL_HOST_PASSWORD")
            return False
            
    except Participant.DoesNotExist:
        print(f"ERROR: No participant found with email: {email}")
        return False
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("="*70)
    print("RESEND ACTIVATION EMAIL")
    print("="*70)
    
    # Resend to smartwork608@gmail.com
    email = 'smartwork608@gmail.com'
    result = resend_activation_email(email)
    
    if result:
        print("\n" + "="*70)
        print("EMAIL SENT SUCCESSFULLY!")
        print("="*70)
        print(f"\nNext steps:")
        print(f"1. Check email inbox for: {email}")
        print(f"2. Check spam/junk folder if not in inbox")
        print(f"3. Use activation code or click verification link")
        print(f"4. Login at /auth/login/")
    else:
        print("\n" + "="*70)
        print("EMAIL SENDING FAILED")
        print("="*70)
        print("\nManual verification option:")
        print(f"  python manage.py shell")
        print(f"  >>> from core.models import Participant")
        print(f"  >>> p = Participant.objects.get(email='{email}')")
        print(f"  >>> p.is_email_verified = True")
        print(f"  >>> p.terms_accepted = True")
        print(f"  >>> p.save()")
