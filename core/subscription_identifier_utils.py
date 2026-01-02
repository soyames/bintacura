import random
import string
from django.db import transaction


def generate_identifier(entity_type):
    """
    Generate human-readable unique identifier for subscription management.
    Format: {PREFIX}-{RANDOM_ALPHANUMERIC}
    
    Args:
        entity_type: 'hospital', 'pharmacy', or 'insurance'
    
    Returns:
        String like "HOSP-A3X9K2M7" or "PHRM-B5Y8L4N6" or "INSR-C7Z2P9Q4"
    """
    prefix_map = {
        'hospital': 'HOSP',
        'pharmacy': 'PHRM',
        'insurance': 'INSR'
    }
    
    prefix = prefix_map.get(entity_type, 'UNKN')
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    return f"{prefix}-{random_part}"


def generate_activation_code():
    """
    Generate 12-character activation code for local instance activation.
    Format: XXXX-XXXX-XXXX (12 alphanumeric characters: uppercase letters + digits)
    More secure than digits-only format.
    
    Returns:
        String like "A2Z9-5C83-4P5H"
    """
    characters = string.ascii_uppercase + string.digits
    part1 = ''.join(random.choices(characters, k=4))
    part2 = ''.join(random.choices(characters, k=4))
    part3 = ''.join(random.choices(characters, k=4))
    
    return f"{part1}-{part2}-{part3}"


def ensure_unique_identifier(model_class, entity_type, max_attempts=10):
    """
    Generate a unique identifier ensuring no collision in database.
    
    Args:
        model_class: HospitalData, PharmacyData, or InsuranceCompanyData
        entity_type: 'hospital', 'pharmacy', or 'insurance'
        max_attempts: Maximum generation attempts before raising error
    
    Returns:
        Unique identifier string
    """
    for _ in range(max_attempts):
        identifier = generate_identifier(entity_type)
        if not model_class.objects.filter(identifier=identifier).exists():
            return identifier
    
    raise ValueError(f"Failed to generate unique identifier after {max_attempts} attempts")


@transaction.atomic
def assign_identifier_and_activation_code(data_instance, entity_type, validity_years=None):
    """
    Assign identifier and activation code to a hospital, pharmacy, or insurance company.
    This should be called after verification and certification (blue checkmark).
    
    Args:
        data_instance: HospitalData, PharmacyData, or InsuranceCompanyData instance
        entity_type: 'hospital', 'pharmacy', or 'insurance'
        validity_years: Number of years the activation code is valid (default: uses instance's setting or 1 year)
    
    Returns:
        Tuple of (identifier, activation_code, expires_at)
    """
    from django.utils import timezone
    from dateutil.relativedelta import relativedelta
    
    if data_instance.identifier and data_instance.activation_code and data_instance.activation_code_expires_at:
        # Check if code is still valid
        if not data_instance.is_activation_code_expired():
            return data_instance.identifier, data_instance.activation_code, data_instance.activation_code_expires_at
    
    model_class = type(data_instance)
    
    # Generate new identifier only if doesn't exist
    if not data_instance.identifier:
        identifier = ensure_unique_identifier(model_class, entity_type)
        data_instance.identifier = identifier
    
    # Always generate new activation code
    activation_code = generate_activation_code()
    
    # Set validity period
    if validity_years is None:
        validity_years = data_instance.activation_code_validity_years or 1
    
    issued_at = timezone.now()
    expires_at = issued_at + relativedelta(years=validity_years)
    
    data_instance.activation_code = activation_code
    data_instance.activation_code_issued_at = issued_at
    data_instance.activation_code_expires_at = expires_at
    data_instance.activation_code_validity_years = validity_years
    
    data_instance.save(update_fields=[
        'identifier', 
        'activation_code', 
        'activation_code_issued_at', 
        'activation_code_expires_at',
        'activation_code_validity_years'
    ])
    
    return data_instance.identifier, activation_code, expires_at


def bulk_assign_identifiers_to_existing(model_class, entity_type):
    """
    Bulk assign identifiers and activation codes to existing verified entities.
    Use this for migrating existing hospitals, pharmacies, and insurance companies.
    
    Args:
        model_class: HospitalData, PharmacyData, or InsuranceCompanyData
        entity_type: 'hospital', 'pharmacy', or 'insurance'
    
    Returns:
        Number of records updated
    """
    instances_without_identifier = model_class.objects.filter(
        identifier__isnull=True
    ).filter(
        participant__is_verified=True
    )
    
    updated_count = 0
    
    for instance in instances_without_identifier:
        try:
            with transaction.atomic():
                assign_identifier_and_activation_code(instance, entity_type)
                updated_count += 1
        except Exception as e:
            print(f"Failed to assign identifier to {instance.participant.uid}: {e}")
            continue
    
    return updated_count


@transaction.atomic
def renew_activation_code(data_instance, entity_type, validity_years=None):
    """
    Renew activation code using the same identifier.
    This is used when a participant requests a new activation code.
    
    Args:
        data_instance: HospitalData, PharmacyData, or InsuranceCompanyData instance
        entity_type: 'hospital', 'pharmacy', or 'insurance'
        validity_years: Number of years for the new code (default: uses current validity_years setting)
    
    Returns:
        Tuple of (identifier, new_activation_code, new_expires_at)
    """
    from django.utils import timezone
    from dateutil.relativedelta import relativedelta
    
    if not data_instance.identifier:
        raise ValueError("Cannot renew activation code: No identifier found. Entity must be verified first.")
    
    # Keep the same identifier
    identifier = data_instance.identifier
    
    # Generate new activation code
    new_activation_code = generate_activation_code()
    
    # Set validity period
    if validity_years is None:
        validity_years = data_instance.activation_code_validity_years or 1
    
    issued_at = timezone.now()
    expires_at = issued_at + relativedelta(years=validity_years)
    
    data_instance.activation_code = new_activation_code
    data_instance.activation_code_issued_at = issued_at
    data_instance.activation_code_expires_at = expires_at
    data_instance.activation_code_validity_years = validity_years
    
    data_instance.save(update_fields=[
        'activation_code',
        'activation_code_issued_at',
        'activation_code_expires_at',
        'activation_code_validity_years'
    ])
    
    return identifier, new_activation_code, expires_at


@transaction.atomic
def update_activation_code_validity(data_instance, new_validity_years):
    """
    Update the validity period for activation code subscription.
    This extends or reduces the expiry date based on the new validity period.
    
    Args:
        data_instance: HospitalData, PharmacyData, or InsuranceCompanyData instance
        new_validity_years: New validity period (1, 2, 5 years, etc.)
    
    Returns:
        New expiry datetime
    """
    from django.utils import timezone
    from dateutil.relativedelta import relativedelta
    
    if not data_instance.activation_code_issued_at:
        raise ValueError("Cannot update validity: activation code has not been issued yet")
    
    # Calculate new expiry date from issue date
    new_expires_at = data_instance.activation_code_issued_at + relativedelta(years=new_validity_years)
    
    data_instance.activation_code_expires_at = new_expires_at
    data_instance.activation_code_validity_years = new_validity_years
    
    data_instance.save(update_fields=['activation_code_expires_at', 'activation_code_validity_years'])
    
    return new_expires_at


def get_activation_code_by_identifier(model_class, identifier):
    """
    Retrieve activation code information by identifier.
    Used for reactivation requests.
    
    Args:
        model_class: HospitalData, PharmacyData, or InsuranceCompanyData
        identifier: The unique identifier (e.g., 'HOSP-YTHIYIXN')
    
    Returns:
        Dict with activation code details or None if not found
    """
    try:
        instance = model_class.objects.select_related('participant').get(identifier=identifier)
        return {
            'identifier': instance.identifier,
            'activation_code': instance.activation_code,
            'issued_at': instance.activation_code_issued_at,
            'expires_at': instance.activation_code_expires_at,
            'validity_years': instance.activation_code_validity_years,
            'is_expired': instance.is_activation_code_expired(),
            'days_until_expiry': instance.days_until_expiry(),
            'participant_uid': instance.participant.uid,
            'entity_name': instance.participant.full_name,
        }
    except model_class.DoesNotExist:
        return None
