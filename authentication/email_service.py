from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from .tokens import email_verification_token, generate_activation_code
import logging

logger = logging.getLogger(__name__)


def send_verification_email(participant, activation_code):  # Send verification email
    """
    Send email verification using no-reply@bintacura.org with professional HTML template
    """
    try:
        token = email_verification_token.make_token(participant)
        uid = urlsafe_base64_encode(force_bytes(participant.uid))

        verification_link = f"{settings.FRONTEND_URL}/auth/verify-email/{uid}/{token}/"

        context = {
            "user_name": participant.full_name or participant.email,
            "verification_link": verification_link,
            "activation_code": activation_code,
        }

        # Render HTML email from template
        html_content = render_to_string("emails/email_verification.html", context)

        # Create email with HTML content
        email = EmailMultiAlternatives(
            subject="Vérification de votre compte - BINTACURA",
            body=html_content,
            from_email=settings.NO_REPLY_EMAIL,  # Use no-reply email
            to=[participant.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        logger.info(f"Verification email sent successfully to {participant.email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send verification email to {participant.email}: {str(e)}")
        return False

