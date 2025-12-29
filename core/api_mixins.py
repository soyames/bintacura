# -*- coding: utf-8 -*-
"""
API Mixins for Multi-Region Support
Provides base functionality for ViewSets in multi-region architecture
"""
from rest_framework import status
from rest_framework.response import Response
from django.conf import settings
from .region_middleware import get_current_region


class MultiRegionMixin:
    """
    Mixin for ViewSets to support multi-region architecture.
    
    Features:
    - Automatic region-aware queryset filtering
    - Region information in API responses
    - Database routing support
    """
    
    def get_queryset(self):
        """
        Override to add region-aware filtering if needed.
        Subclasses should call super().get_queryset() and add their filters.
        """
        queryset = super().get_queryset()
        
        # If model has region field, filter by current region
        if hasattr(queryset.model, 'region'):
            current_region = get_current_region()
            queryset = queryset.filter(region=current_region)
        
        return queryset
    
    def finalize_response(self, request, response, *args, **kwargs):
        """Add region information to API response headers."""
        response = super().finalize_response(request, response, *args, **kwargs)
        
        # Add region header for debugging and monitoring
        if hasattr(request, 'BINTACURA_region'):
            response['X-BINTACURA-Region'] = request.BINTACURA_region
        
        return response


class ParticipantScopedMixin:
    """
    Mixin to automatically scope querysets to current authenticated participant.

    Determines the appropriate field based on participant role:
    - patient -> filter by patient field
    - doctor -> filter by doctor field
    - pharmacy -> filter by pharmacy field
    - pharmacy_staff -> filter by pharmacy field (via affiliated_provider_id)
    - hospital -> filter by hospital field
    - hospital_staff -> filter by hospital field (via affiliated_provider_id)
    - insurance_company -> filter by insurance_company field
    - insurance_company_staff -> filter by insurance_company field (via affiliated_provider_id)
    """
    
    # Override in subclass if needed
    participant_field_map = {
        'patient': 'patient',
        'doctor': 'doctor',
        'pharmacy': 'pharmacy',
        'pharmacy_staff': 'pharmacy',
        'hospital': 'hospital',
        'hospital_staff': 'hospital',
        'insurance_company': 'insurance_company',
        'insurance_company_staff': 'insurance_company',
    }
    
    def get_queryset(self):
        """Filter queryset based on current participant role."""
        queryset = super().get_queryset()
        participant = self.request.user
        
        if not participant or not participant.is_authenticated:
            return queryset.none()
        
        # Get the field name for filtering based on role
        field_name = self.participant_field_map.get(participant.role)
        
        if field_name and hasattr(queryset.model, field_name):
            # For staff roles, get related entity through affiliated_provider_id
            if participant.role in ['pharmacy_staff', 'hospital_staff', 'insurance_company_staff']:
                if participant.affiliated_provider_id:
                    try:
                        # Get the parent entity (pharmacy, hospital, or insurance company)
                        parent_entity = Participant.objects.get(uid=participant.affiliated_provider_id)
                        queryset = queryset.filter(**{field_name: parent_entity})
                    except Participant.DoesNotExist:
                        return queryset.none()
                else:
                    return queryset.none()
            else:
                # Direct filtering for patient, doctor, pharmacy, hospital, insurance_company
                queryset = queryset.filter(**{field_name: participant})

        return queryset


class RegionValidationMixin:
    """
    Mixin to validate that data operations are within the correct region.
    Prevents cross-region data leakage.
    """
    
    def perform_create(self, serializer):
        """Add region to created objects if model supports it."""
        instance = serializer.save()
        
        # If model has region field, set it to current region
        if hasattr(instance, 'region'):
            current_region = get_current_region()
            instance.region = current_region
            instance.save(update_fields=['region'])
        
        return instance
    
    def perform_update(self, serializer):
        """Ensure updates don't change region."""
        instance = serializer.instance
        
        # Prevent region changes
        if hasattr(instance, 'region'):
            current_region = get_current_region()
            if instance.region != current_region:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied(
                    "Cannot modify data from a different region."
                )
        
        return super().perform_update(serializer)


class PaymentRegionMixin:
    """
    Mixin for payment-related ViewSets to handle region-specific payment providers.
    
    Each region may have different payment providers (e.g., FedaPay in Mali, Stripe elsewhere).
    """
    
    def get_payment_provider(self):
        """Get the payment provider for the current region."""
        current_region = get_current_region()
        region_config = settings.REGIONAL_DATABASE_MAP.get(current_region, {})
        
        # Default to region's configured provider or FedaPay
        return region_config.get('payment_provider', 'fedapay')
    
    def get_payment_service(self):
        """Get the appropriate payment service based on region."""
        provider = self.get_payment_provider()
        
        if provider == 'stripe':
            from core.stripe_service import StripeService
            return StripeService()
        elif provider == 'fedapay':
            # Import FedaPay service when implemented
            from payments.services import FedaPayService
            return FedaPayService()
        else:
            raise ValueError(f"Unknown payment provider: {provider}")


class MultiRegionViewSetBase(
    MultiRegionMixin,
    ParticipantScopedMixin,
    RegionValidationMixin
):
    """
    Base ViewSet combining all multi-region mixins.
    
    Use this as a base class for ViewSets that need:
    - Multi-region support
    - Participant scoping
    - Region validation
    
    Example:
        class AppointmentViewSet(MultiRegionViewSetBase, viewsets.ModelViewSet):
            queryset = Appointment.objects.all()
            serializer_class = AppointmentSerializer
    """
    pass

