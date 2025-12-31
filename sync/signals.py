"""
Signal Handlers for Automatic SyncEvent Logging

Automatically creates SyncEvent records whenever a SyncMixin model
is created, updated, or deleted. This enables event sourcing for
offline-first synchronization.
"""

import json
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.core.serializers import serialize
from django.conf import settings

from sync.models import SyncEvent
from core.mixins import SyncMixin


def get_current_instance_id():
    """Get the current instance's UUID from settings or environment"""
    instance_id = getattr(settings, 'INSTANCE_ID', None)
    
    # Validate and clean the instance_id
    if instance_id:
        instance_id_str = str(instance_id).strip()
        # Check if it's empty, 'None', or just whitespace
        if not instance_id_str or instance_id_str == 'None' or instance_id_str.isspace():
            return None
        # Try to validate it's a valid UUID
        try:
            import uuid
            uuid.UUID(instance_id_str)
            return instance_id_str
        except (ValueError, AttributeError):
            return None
    
    return None


@receiver(post_save)
def log_sync_event_on_save(sender, instance, created, **kwargs):
    """
    Auto-create SyncEvent when any SyncMixin model is saved

    This runs AFTER every model save that inherits from SyncMixin.
    Creates an event log with the full object data for later sync.
    """

    # Only track models that inherit from SyncMixin
    if not isinstance(instance, SyncMixin):
        return

    # Don't log SyncEvent changes themselves (prevent recursion)
    if isinstance(instance, SyncEvent):
        return

    # Don't log changes during sync operations (would cause circular sync)
    if getattr(instance, '_skip_sync_logging', False):
        return

    # Serialize the object to JSON
    try:
        serialized = serialize('json', [instance])
        data_snapshot = json.loads(serialized)[0]

        event_type = 'create' if created else 'update'

        # Create sync event
        SyncEvent.objects.create(
            model_name=f"{instance._meta.app_label}.{instance._meta.model_name}",
            object_id=instance.id,
            event_type=event_type,
            instance_id=get_current_instance_id(),
            data_snapshot=data_snapshot,
            synced_to_cloud=False,
        )

    except Exception as e:
        # Log error but don't break the save operation
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create SyncEvent for {sender.__name__}: {str(e)}")


# Store objects about to be deleted (needed for post_delete)
_objects_to_delete = {}


@receiver(pre_delete)
def store_object_before_delete(sender, instance, **kwargs):
    """
    Store object data before deletion (for SyncEvent logging)

    We need this because post_delete doesn't have access to the object's data.
    """
    if not isinstance(instance, SyncMixin):
        return

    if isinstance(instance, SyncEvent):
        return

    # Serialize and store for post_delete
    try:
        serialized = serialize('json', [instance])
        _objects_to_delete[str(instance.id)] = json.loads(serialized)[0]
    except Exception:
        pass


@receiver(post_delete)
def log_sync_event_on_delete(sender, instance, **kwargs):
    """
    Auto-create SyncEvent when any SyncMixin model is deleted

    Uses data stored in pre_delete signal to create event log.
    """
    if not isinstance(instance, SyncMixin):
        return

    if isinstance(instance, SyncEvent):
        return

    if getattr(instance, '_skip_sync_logging', False):
        return

    try:
        # Retrieve stored object data
        object_id_str = str(instance.id)
        data_snapshot = _objects_to_delete.pop(object_id_str, {'id': str(instance.id)})

        # Create sync event
        SyncEvent.objects.create(
            model_name=f"{instance._meta.app_label}.{instance._meta.model_name}",
            object_id=instance.id,
            event_type='delete',
            instance_id=get_current_instance_id(),
            data_snapshot=data_snapshot,
            synced_to_cloud=False,
        )

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create delete SyncEvent for {sender.__name__}: {str(e)}")
