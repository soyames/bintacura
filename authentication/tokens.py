from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.crypto import get_random_string


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):  # EmailVerificationTokenGenerator class implementation
    def _make_hash_value(self, user, timestamp):  # Make hash value
        return f"{user.uid}{timestamp}{user.is_email_verified}"


email_verification_token = EmailVerificationTokenGenerator()


def generate_activation_code():  # Generate activation code
    return get_random_string(length=6, allowed_chars="0123456789")
