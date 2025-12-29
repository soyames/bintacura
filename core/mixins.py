from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib import messages


class RoleRequiredMixin(LoginRequiredMixin):  # Base mixin to restrict views to specific user roles
    allowed_roles = []
    login_url = '/auth/login/'

    def dispatch(self, request, *args, **kwargs):  # Check if user has required role before allowing access
        if not request.user.is_authenticated:
            messages.warning(request, 'Vous devez vous connecter pour accéder à cette page.')
            return redirect(f'{self.login_url}?next={request.path}')
        
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        
        user_role = request.user.role.lower() if hasattr(request.user, 'role') and request.user.role else None
        
        if not user_role or user_role not in self.allowed_roles:
            messages.error(request, "Vous n'avez pas l'autorisation d'accéder à cette page.")
            return redirect(self.get_redirect_url(user_role))
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_redirect_url(self, user_role):  # Get appropriate dashboard URL based on user role
        role_map = {
            'patient': '/patient/dashboard/',
            'doctor': '/doctor/dashboard/',
            'hospital': '/hospital/dashboard/',
            'pharmacy': '/pharmacy/dashboard/',
            'insurance_company': '/insurance/dashboard/',
            'lab': '/hospital/dashboard/',
            'admin': '/superadmin/dashboard/',
            'super_admin': '/superadmin/dashboard/',
        }
        return role_map.get(user_role, '/auth/login/')


class PatientRequiredMixin(RoleRequiredMixin):  # Restrict view access to patient role only
    allowed_roles = ['patient']


class DoctorRequiredMixin(RoleRequiredMixin):  # Restrict view access to doctor role only
    allowed_roles = ['doctor']


class HospitalRequiredMixin(RoleRequiredMixin):  # Restrict view access to hospital and lab roles
    allowed_roles = ['hospital', 'lab']


class PharmacyRequiredMixin(RoleRequiredMixin):  # Restrict view access to pharmacy role only
    allowed_roles = ['pharmacy']


class InsuranceRequiredMixin(RoleRequiredMixin):  # Restrict view access to insurance company role only
    allowed_roles = ['insurance_company']


# Synchronization Mixin for Offline-First Architecture
import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings


class SyncMixin(models.Model):
    """
    Abstract model mixin for offline-first synchronization

    Adds synchronization metadata to models that need to sync between
    local business instances (hospitals, pharmacies) and cloud database.

    Features:
    - UUID primary keys for global uniqueness across instances
    - Version tracking for optimistic locking
    - Instance tracking (which installation created/modified record)
    - Soft delete support (for sync purposes)
    - Last sync timestamp tracking

    Usage:
        class MyModel(SyncMixin):
            # Your fields here
            name = models.CharField(max_length=100)
    """

    # Global unique identifier (UUID instead of auto-increment for conflict-free merging)
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Global unique identifier"
    )

    # Timestamps
    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
        help_text="When this record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this record was last modified"
    )

    # Version for optimistic locking (conflict detection)
    version = models.IntegerField(
        default=1,
        help_text="Version number for conflict detection"
    )

    # Sync tracking
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this record was last synced with cloud"
    )

    # Instance tracking (which local installation created/modified this)
    created_by_instance = models.UUIDField(
        null=True,
        blank=True,
        help_text="UUID of instance that created this record"
    )
    modified_by_instance = models.UUIDField(
        null=True,
        blank=True,
        help_text="UUID of instance that last modified this record"
    )

    # Soft delete (for sync purposes - don't hard delete until synced)
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Soft delete flag for sync purposes"
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this record was marked as deleted"
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
            models.Index(fields=['is_deleted']),
        ]

    def save(self, *args, **kwargs):
        """
        Override save to:
        1. Increment version on every update (for conflict detection)
        2. Set instance tracking if available
        """
        # Increment version on update (not on create)
        if self.pk and not kwargs.get('force_insert'):
            self.version += 1

        # Set instance tracking if available
        try:
            if hasattr(settings, 'INSTANCE_ID') and settings.INSTANCE_ID:
                instance_id = str(settings.INSTANCE_ID).strip()
                if instance_id and instance_id != 'None':
                    if not self.created_by_instance:
                        self.created_by_instance = instance_id
                    self.modified_by_instance = instance_id
        except Exception:
            pass  # Ignore if settings not available (cloud instance)

        super().save(*args, **kwargs)

    def soft_delete(self):
        """Soft delete this record (mark as deleted without removing from database)"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
