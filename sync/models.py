"""
Synchronization Models for Offline-First Architecture

These models enable bidirectional sync between local business instances
(hospitals, pharmacies) and the central cloud database.
"""

import uuid
import json
import hashlib
from django.db import models
from django.utils import timezone
from django.conf import settings


class SyncEvent(models.Model):
    """
    Event log for all data changes (create, update, delete)

    Enables efficient incremental synchronization by tracking every change
    to any SyncMixin model. Local instances push these events to cloud,
    and pull events from cloud created by other instances.
    """

    EVENT_TYPES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # What changed
    model_name = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Full model path (e.g., 'appointments.Appointment')"
    )
    object_id = models.UUIDField(
        db_index=True,
        help_text="UUID of the object that changed"
    )
    event_type = models.CharField(
        max_length=10,
        choices=EVENT_TYPES,
        help_text="Type of change: create, update, or delete"
    )

    # When and where
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When this event occurred"
    )
    instance_id = models.UUIDField(
        db_index=True,
        null=True,
        blank=True,
        help_text="Which local instance created this event (null for cloud)"
    )

    # Change data
    data_snapshot = models.JSONField(
        help_text="Full serialized object data"
    )
    changed_fields = models.JSONField(
        null=True,
        blank=True,
        help_text="List of changed field names (for updates)"
    )

    # Data integrity
    data_hash = models.CharField(
        max_length=64,
        help_text="SHA256 hash of data_snapshot for integrity verification"
    )

    # Sync status
    synced_to_cloud = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this event has been synced to cloud"
    )
    synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this event was synced to cloud"
    )

    # Conflict tracking
    conflict_detected = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether a conflict was detected for this event"
    )
    conflict_resolution = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="How the conflict was resolved"
    )

    class Meta:
        db_table = 'sync_events'
        indexes = [
            models.Index(fields=['model_name', 'timestamp']),
            models.Index(fields=['instance_id', 'synced_to_cloud']),
            models.Index(fields=['timestamp', 'synced_to_cloud']),
            models.Index(fields=['object_id', 'event_type']),
        ]
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.event_type} {self.model_name}:{self.object_id} at {self.timestamp}"

    def save(self, *args, **kwargs):
        """Auto-compute data hash on save"""
        if not self.data_hash:
            data_str = json.dumps(self.data_snapshot, sort_keys=True)
            self.data_hash = hashlib.sha256(data_str.encode()).hexdigest()
        super().save(*args, **kwargs)

    def verify_integrity(self):
        """Verify data hasn't been tampered with"""
        data_str = json.dumps(self.data_snapshot, sort_keys=True)
        computed_hash = hashlib.sha256(data_str.encode()).hexdigest()
        return computed_hash == self.data_hash


class SyncInstance(models.Model):
    """
    Represents a local installation (desktop EXE at hospital, pharmacy, etc.)

    Each business location that needs offline operation gets a unique instance
    registration with credentials for syncing to cloud.
    """

    INSTANCE_TYPES = [
        ('hospital', 'Hospital'),
        ('pharmacy', 'Pharmacy'),
        ('insurance', 'Insurance Company'),
        ('lab', 'Laboratory'),
        ('imaging', 'Imaging Center'),
    ]

    # Unique instance identifier
    instance_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this installation"
    )

    # Organization link
    organization = models.ForeignKey(
        'core.Participant',
        on_delete=models.CASCADE,
        related_name='sync_instances',
        help_text="The hospital, pharmacy, or insurance company this instance belongs to"
    )

    # Instance metadata
    instance_type = models.CharField(
        max_length=20,
        choices=INSTANCE_TYPES,
        help_text="Type of organization"
    )
    instance_name = models.CharField(
        max_length=200,
        help_text="Descriptive name (e.g., 'Hospital Yalgado Desktop 1')"
    )

    # Device info
    platform = models.CharField(
        max_length=20,
        help_text="Operating system: 'windows', 'linux', etc."
    )
    hardware_id = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Hardware identifier (MAC address, etc.)"
    )
    os_version = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="OS version string"
    )

    # Authentication (API key stored, secret is hashed)
    api_key = models.CharField(
        max_length=200,
        unique=True,
        db_index=True,
        help_text="API key for this instance (stored in plain text)"
    )
    api_secret_hash = models.CharField(
        max_length=200,
        help_text="Hashed API secret (use make_password/check_password)"
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this instance is allowed to sync"
    )
    registered_at = models.DateTimeField(
        default=timezone.now,
        help_text="When this instance was registered"
    )
    last_sync_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this instance last synced"
    )

    # Sync configuration
    sync_interval_minutes = models.IntegerField(
        default=15,
        help_text="How often to auto-sync (in minutes)"
    )
    sync_enabled = models.BooleanField(
        default=True,
        help_text="Whether automatic sync is enabled"
    )

    class Meta:
        db_table = 'sync_instances'
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['api_key']),
            models.Index(fields=['instance_type']),
        ]

    def __str__(self):
        return f"{self.instance_name} ({self.instance_id})"

    def generate_jwt_token(self, expiry_days=365):
        """Generate JWT token for this instance"""
        import jwt
        from datetime import timedelta

        payload = {
            'instance_id': str(self.instance_id),
            'organization_id': str(self.organization.uid),
            'instance_type': self.instance_type,
            'exp': timezone.now() + timedelta(days=expiry_days),
            'iat': timezone.now(),
        }

        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        return token


class SyncInstanceLog(models.Model):
    """
    Log of sync operations per instance

    Tracks each sync attempt (push or pull) with statistics and errors.
    Used for monitoring and debugging sync issues.
    """

    SYNC_DIRECTIONS = [
        ('push', 'Local → Cloud'),
        ('pull', 'Cloud → Local'),
    ]

    SYNC_STATUSES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('success', 'Success'),
        ('partial', 'Partial Success'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    instance = models.ForeignKey(
        SyncInstance,
        on_delete=models.CASCADE,
        related_name='sync_logs',
        help_text="Which instance performed this sync"
    )

    # Sync operation details
    direction = models.CharField(
        max_length=10,
        choices=SYNC_DIRECTIONS,
        help_text="Push to cloud or pull from cloud"
    )
    status = models.CharField(
        max_length=20,
        choices=SYNC_STATUSES,
        default='pending',
        help_text="Current status of sync operation"
    )

    # Timing
    started_at = models.DateTimeField(
        default=timezone.now,
        help_text="When sync started"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When sync completed"
    )

    # Statistics
    records_pushed = models.IntegerField(
        default=0,
        help_text="Number of records pushed to cloud"
    )
    records_pulled = models.IntegerField(
        default=0,
        help_text="Number of records pulled from cloud"
    )
    conflicts_detected = models.IntegerField(
        default=0,
        help_text="Number of conflicts detected"
    )
    errors_count = models.IntegerField(
        default=0,
        help_text="Number of errors encountered"
    )

    # Error details
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="Error message if sync failed"
    )

    # Additional metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional sync metadata"
    )

    class Meta:
        db_table = 'sync_instance_logs'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['instance', 'status']),
            models.Index(fields=['started_at']),
            models.Index(fields=['direction', 'status']),
        ]

    def __str__(self):
        return f"{self.instance.instance_name} - {self.direction} ({self.status})"


class SyncConflict(models.Model):
    """
    Tracks detected synchronization conflicts

    When two instances modify the same record simultaneously, a conflict
    is created. Some conflicts can be auto-resolved, others require manual
    intervention (especially payment-related conflicts).
    """

    CONFLICT_TYPES = [
        ('update_update', 'Update-Update Conflict'),
        ('delete_update', 'Delete-Update Conflict'),
        ('create_create', 'Create-Create Conflict'),
        ('payment', 'Payment Conflict (Critical)'),
        ('other', 'Other Conflict'),
    ]

    RESOLUTION_STRATEGIES = [
        ('cloud_wins', 'Cloud Version Wins'),
        ('local_wins', 'Local Version Wins'),
        ('latest_wins', 'Latest Timestamp Wins'),
        ('merge', 'Merge Changes'),
        ('manual', 'Manual Resolution Required'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Conflict details
    conflict_type = models.CharField(
        max_length=20,
        choices=CONFLICT_TYPES,
        help_text="Type of conflict detected"
    )
    model_name = models.CharField(
        max_length=100,
        help_text="Model that has conflicting versions"
    )
    object_id = models.UUIDField(
        help_text="ID of the object with conflict"
    )

    # Conflicting versions (full object snapshots)
    local_version = models.JSONField(
        help_text="Local instance's version of the object"
    )
    cloud_version = models.JSONField(
        help_text="Cloud database's version of the object"
    )

    # Resolution
    resolution_strategy = models.CharField(
        max_length=20,
        choices=RESOLUTION_STRATEGIES,
        null=True,
        blank=True,
        help_text="How this conflict was/will be resolved"
    )
    resolved = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether conflict has been resolved"
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When conflict was resolved"
    )
    resolved_by = models.ForeignKey(
        'core.Participant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who manually resolved the conflict"
    )

    # Metadata
    detected_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When conflict was detected"
    )
    instance = models.ForeignKey(
        SyncInstance,
        on_delete=models.CASCADE,
        help_text="Instance where conflict was detected"
    )
    requires_manual_resolution = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether auto-resolution failed and manual intervention needed"
    )

    # Additional notes
    notes = models.TextField(
        null=True,
        blank=True,
        help_text="Notes about conflict resolution"
    )

    class Meta:
        db_table = 'sync_conflicts'
        indexes = [
            models.Index(fields=['resolved', 'requires_manual_resolution']),
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['conflict_type']),
            models.Index(fields=['detected_at']),
        ]
        ordering = ['-detected_at']

    def __str__(self):
        status = "Resolved" if self.resolved else ("Manual Required" if self.requires_manual_resolution else "Pending")
        return f"{self.conflict_type} - {self.model_name}:{self.object_id} ({status})"
