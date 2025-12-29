"""
Custom validators for BINTACURA application
"""
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import date


def validate_date_of_birth(value):
    """
    Validate that date of birth is not in the future.
    ISSUE-PAT-005: Date of birth validation (allows future dates)
    """
    if value is None:
        return

    today = date.today()

    # Check if date is in the future
    if value > today:
        raise ValidationError(
            _("La date de naissance ne peut pas être dans le futur."),
            code='future_date'
        )

    # Check if date is too far in the past (more than 150 years ago)
    min_date = date(today.year - 150, today.month, today.day)
    if value < min_date:
        raise ValidationError(
            _("La date de naissance semble incorrecte (plus de 150 ans)."),
            code='too_old'
        )


def validate_profile_picture_size(file):
    """
    Validate profile picture file size.
    ISSUE-PAT-003: Profile picture upload size limit (1MB too small)

    Maximum file size: 5MB (increased from 1MB)
    """
    if file:
        max_size_mb = 5
        max_size_bytes = max_size_mb * 1024 * 1024

        if file.size > max_size_bytes:
            raise ValidationError(
                _(f"La taille du fichier ne doit pas dépasser {max_size_mb}MB. Taille actuelle: {file.size / (1024*1024):.2f}MB"),
                code='file_too_large'
            )


def validate_profile_picture_format(file):
    """
    Validate profile picture file format.
    Only allow common image formats: JPG, JPEG, PNG, GIF, WEBP
    """
    if file:
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        file_name = file.name.lower()

        if not any(file_name.endswith(ext) for ext in allowed_extensions):
            raise ValidationError(
                _("Format de fichier non supporté. Formats acceptés: JPG, JPEG, PNG, GIF, WEBP"),
                code='invalid_format'
            )


def validate_phone_number_format(phone_number):
    """
    Validate phone number format for international numbers.
    ISSUE-PAT-049: Phone number validation doesn't properly validate international formats
    """
    if not phone_number:
        return

    # Remove spaces and dashes
    cleaned = phone_number.replace(' ', '').replace('-', '')

    # Must start with +
    if not cleaned.startswith('+'):
        raise ValidationError(
            _("Le numéro de téléphone doit commencer par un indicatif international (ex: +228)"),
            code='missing_country_code'
        )

    # Must have between 8 and 15 digits after the +
    digits_only = cleaned[1:]
    if not digits_only.isdigit():
        raise ValidationError(
            _("Le numéro de téléphone ne doit contenir que des chiffres après l'indicatif"),
            code='invalid_characters'
        )

    if len(digits_only) < 8 or len(digits_only) > 15:
        raise ValidationError(
            _("Le numéro de téléphone doit contenir entre 8 et 15 chiffres"),
            code='invalid_length'
        )

