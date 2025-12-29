"""
Synchronization Service

Core business logic for offline-first bidirectional synchronization.
Handles push/pull of SyncEvents between local instances and cloud.
"""

import json
import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from django.db import transaction
from django.apps import apps
from django.core.serializers import deserialize
from django.utils import timezone
from django.conf import settings

from sync.models import SyncEvent, SyncInstance, SyncInstanceLog, SyncConflict
from sync.conflict_resolver import ConflictResolver

logger = logging.getLogger(__name__)


class SyncService:
    """
    Service for synchronizing data between local instances and cloud

    Handles:
    - Pushing local changes to cloud
    - Pulling cloud changes to local
    - Applying events to local database
    - Conflict detection and resolution
    """

    def __init__(self, instance_id: str = None):
        """
        Initialize sync service

        Args:
            instance_id: UUID of the local instance (None for cloud)
        """
        self.instance_id = instance_id
        self.conflict_resolver = ConflictResolver()

        # Get instance object if ID provided
        self.instance = None
        if instance_id:
            try:
                self.instance = SyncInstance.objects.get(instance_id=instance_id)
            except SyncInstance.DoesNotExist:
                logger.error(f"SyncInstance {instance_id} not found")

    def push_events_to_cloud(
        self,
        cloud_api_url: str,
        jwt_token: str,
        batch_size: int = 100
    ) -> SyncInstanceLog:
        """
        Push unsynced local events to cloud

        This runs on LOCAL instances to send their changes to cloud.

        Args:
            cloud_api_url: Cloud API endpoint (e.g., https://api.vitacare.com/sync/push/)
            jwt_token: JWT token for authentication
            batch_size: Number of events to push per batch

        Returns:
            SyncInstanceLog with operation statistics
        """
        import requests

        # Create log entry
        log = SyncInstanceLog.objects.create(
            instance=self.instance,
            direction='push',
            status='in_progress'
        )

        try:
            # Get unsynced events (not yet pushed to cloud)
            unsynced_events = SyncEvent.objects.filter(
                instance_id=self.instance_id,
                synced_to_cloud=False
            ).order_by('timestamp')[:batch_size]

            if not unsynced_events.exists():
                log.status = 'success'
                log.completed_at = timezone.now()
                log.save()
                logger.info("No events to push")
                return log

            # Serialize events for API
            events_data = []
            for event in unsynced_events:
                events_data.append({
                    'id': str(event.id),
                    'model_name': event.model_name,
                    'object_id': str(event.object_id),
                    'event_type': event.event_type,
                    'timestamp': event.timestamp.isoformat(),
                    'instance_id': str(event.instance_id) if event.instance_id else None,
                    'data_snapshot': event.data_snapshot,
                    'changed_fields': event.changed_fields,
                    'data_hash': event.data_hash,
                })

            # Push to cloud API
            headers = {
                'Authorization': f'Bearer {jwt_token}',
                'Content-Type': 'application/json'
            }

            response = requests.post(
                cloud_api_url,
                json={'events': events_data},
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()

                # Mark events as synced
                synced_count = 0
                conflict_count = 0

                for event_id in result.get('synced_event_ids', []):
                    try:
                        event = SyncEvent.objects.get(id=event_id)
                        event.synced_to_cloud = True
                        event.synced_at = timezone.now()
                        event.save()
                        synced_count += 1
                    except SyncEvent.DoesNotExist:
                        logger.warning(f"Event {event_id} not found")

                # Record conflicts
                for conflict_data in result.get('conflicts', []):
                    SyncConflict.objects.create(
                        instance=self.instance,
                        conflict_type=conflict_data['conflict_type'],
                        model_name=conflict_data['model_name'],
                        object_id=conflict_data['object_id'],
                        local_version=conflict_data['local_version'],
                        cloud_version=conflict_data['cloud_version'],
                        requires_manual_resolution=conflict_data.get('requires_manual_resolution', False)
                    )
                    conflict_count += 1

                # Update log
                log.status = 'success'
                log.records_pushed = synced_count
                log.conflicts_detected = conflict_count
                log.completed_at = timezone.now()
                log.save()

                # Update instance last_sync
                self.instance.last_sync_at = timezone.now()
                self.instance.save()

                logger.info(f"Pushed {synced_count} events, {conflict_count} conflicts")
                return log

            else:
                # API error
                log.status = 'failed'
                log.error_message = f"API returned {response.status_code}: {response.text}"
                log.errors_count = 1
                log.completed_at = timezone.now()
                log.save()
                logger.error(log.error_message)
                return log

        except Exception as e:
            # Unexpected error
            log.status = 'failed'
            log.error_message = str(e)
            log.errors_count = 1
            log.completed_at = timezone.now()
            log.save()
            logger.exception("Failed to push events to cloud")
            return log

    def pull_events_from_cloud(
        self,
        cloud_api_url: str,
        jwt_token: str,
        since: datetime = None
    ) -> SyncInstanceLog:
        """
        Pull events from cloud and apply them locally

        This runs on LOCAL instances to get changes from cloud.

        Args:
            cloud_api_url: Cloud API endpoint (e.g., https://api.vitacare.com/sync/pull/)
            jwt_token: JWT token for authentication
            since: Only get events after this timestamp (None = get all)

        Returns:
            SyncInstanceLog with operation statistics
        """
        import requests

        # Create log entry
        log = SyncInstanceLog.objects.create(
            instance=self.instance,
            direction='pull',
            status='in_progress'
        )

        try:
            # Determine last sync time
            if since is None:
                # Get timestamp of last successful pull
                last_pull = SyncInstanceLog.objects.filter(
                    instance=self.instance,
                    direction='pull',
                    status='success'
                ).order_by('-completed_at').first()

                if last_pull and last_pull.completed_at:
                    since = last_pull.completed_at
                else:
                    # First sync - get events from last 7 days
                    since = timezone.now() - timedelta(days=7)

            # Request events from cloud
            headers = {
                'Authorization': f'Bearer {jwt_token}',
                'Content-Type': 'application/json'
            }

            params = {
                'since': since.isoformat(),
                'instance_id': str(self.instance_id)  # Don't send back our own events
            }

            response = requests.get(
                cloud_api_url,
                params=params,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                events_data = result.get('events', [])

                applied_count = 0
                conflict_count = 0
                error_count = 0

                # Apply each event
                for event_data in events_data:
                    try:
                        applied, conflict = self.apply_cloud_event(event_data)
                        if applied:
                            applied_count += 1
                        if conflict:
                            conflict_count += 1
                    except Exception as e:
                        logger.error(f"Failed to apply event {event_data.get('id')}: {str(e)}")
                        error_count += 1

                # Update log
                if error_count == 0:
                    log.status = 'success'
                elif applied_count > 0:
                    log.status = 'partial'
                else:
                    log.status = 'failed'

                log.records_pulled = applied_count
                log.conflicts_detected = conflict_count
                log.errors_count = error_count
                log.completed_at = timezone.now()
                log.save()

                # Update instance last_sync
                self.instance.last_sync_at = timezone.now()
                self.instance.save()

                logger.info(f"Pulled {applied_count} events, {conflict_count} conflicts, {error_count} errors")
                return log

            else:
                # API error
                log.status = 'failed'
                log.error_message = f"API returned {response.status_code}: {response.text}"
                log.errors_count = 1
                log.completed_at = timezone.now()
                log.save()
                logger.error(log.error_message)
                return log

        except Exception as e:
            # Unexpected error
            log.status = 'failed'
            log.error_message = str(e)
            log.errors_count = 1
            log.completed_at = timezone.now()
            log.save()
            logger.exception("Failed to pull events from cloud")
            return log

    def apply_cloud_event(self, event_data: Dict[str, Any]) -> Tuple[bool, bool]:
        """
        Apply a single cloud event to local database

        Args:
            event_data: Event data from cloud

        Returns:
            Tuple of (applied: bool, conflict_detected: bool)
        """
        try:
            # Verify data integrity
            data_snapshot = event_data['data_snapshot']
            data_hash = event_data['data_hash']

            computed_hash = hashlib.sha256(
                json.dumps(data_snapshot, sort_keys=True).encode()
            ).hexdigest()

            if computed_hash != data_hash:
                logger.error(f"Data integrity check failed for event {event_data['id']}")
                return False, False

            # Get model class
            model_name = event_data['model_name']
            app_label, model_class_name = model_name.split('.')
            Model = apps.get_model(app_label, model_class_name)

            # Check for conflicts
            object_id = event_data['object_id']
            event_type = event_data['event_type']

            conflict_detected = False

            try:
                local_obj = Model.objects.get(id=object_id)

                # Check for version conflict
                cloud_version = data_snapshot.get('fields', {}).get('version', 1)
                local_version = getattr(local_obj, 'version', 1)

                if local_version > cloud_version:
                    # Local is newer - potential conflict
                    conflict_detected = True

                    # Use conflict resolver
                    resolved_obj = self.conflict_resolver.resolve_update_update_conflict(
                        local_obj=local_obj,
                        cloud_data=data_snapshot,
                        instance=self.instance
                    )

                    if resolved_obj:
                        # Conflict auto-resolved
                        logger.info(f"Auto-resolved conflict for {model_name}:{object_id}")
                        return True, True
                    else:
                        # Manual resolution required
                        logger.warning(f"Manual resolution required for {model_name}:{object_id}")
                        return False, True

            except Model.DoesNotExist:
                # Object doesn't exist locally - safe to create
                pass

            # Apply the event
            with transaction.atomic():
                if event_type == 'create':
                    # Deserialize and create object
                    serialized_data = json.dumps([data_snapshot])

                    for obj in deserialize('json', serialized_data):
                        # Mark to skip sync logging (prevent circular sync)
                        obj.object._skip_sync_logging = True
                        obj.save()
                        logger.debug(f"Created {model_name}:{object_id}")

                elif event_type == 'update':
                    # Deserialize and update object
                    serialized_data = json.dumps([data_snapshot])

                    for obj in deserialize('json', serialized_data):
                        obj.object._skip_sync_logging = True
                        obj.save()
                        logger.debug(f"Updated {model_name}:{object_id}")

                elif event_type == 'delete':
                    # Soft delete or hard delete
                    try:
                        obj = Model.objects.get(id=object_id)

                        if hasattr(obj, 'soft_delete'):
                            # Use soft delete
                            obj._skip_sync_logging = True
                            obj.soft_delete()
                            logger.debug(f"Soft deleted {model_name}:{object_id}")
                        else:
                            # Hard delete
                            obj._skip_sync_logging = True
                            obj.delete()
                            logger.debug(f"Hard deleted {model_name}:{object_id}")
                    except Model.DoesNotExist:
                        # Already deleted locally - OK
                        pass

                # Record the cloud event locally (for tracking)
                SyncEvent.objects.create(
                    id=event_data['id'],  # Use same ID as cloud
                    model_name=model_name,
                    object_id=object_id,
                    event_type=event_type,
                    timestamp=datetime.fromisoformat(event_data['timestamp']),
                    instance_id=event_data.get('instance_id'),
                    data_snapshot=data_snapshot,
                    changed_fields=event_data.get('changed_fields'),
                    data_hash=data_hash,
                    synced_to_cloud=True,  # Already from cloud
                    synced_at=timezone.now()
                )

            return True, conflict_detected

        except Exception as e:
            logger.exception(f"Failed to apply event {event_data.get('id')}: {str(e)}")
            return False, False

    def bidirectional_sync(
        self,
        cloud_push_url: str,
        cloud_pull_url: str,
        jwt_token: str
    ) -> Dict[str, SyncInstanceLog]:
        """
        Perform full bidirectional sync (push then pull)

        Args:
            cloud_push_url: Cloud push endpoint
            cloud_pull_url: Cloud pull endpoint
            jwt_token: JWT token for authentication

        Returns:
            Dict with 'push' and 'pull' SyncInstanceLog objects
        """
        logger.info(f"Starting bidirectional sync for instance {self.instance_id}")

        # Step 1: Push local changes to cloud
        push_log = self.push_events_to_cloud(cloud_push_url, jwt_token)

        # Step 2: Pull cloud changes to local
        pull_log = self.pull_events_from_cloud(cloud_pull_url, jwt_token)

        logger.info(
            f"Bidirectional sync complete: "
            f"pushed {push_log.records_pushed}, "
            f"pulled {pull_log.records_pulled}, "
            f"conflicts {push_log.conflicts_detected + pull_log.conflicts_detected}"
        )

        return {
            'push': push_log,
            'pull': pull_log
        }

    @staticmethod
    def get_unsynced_count(instance_id: str = None) -> int:
        """
        Get count of unsynced events

        Args:
            instance_id: Instance ID (None = all instances)

        Returns:
            Count of unsynced events
        """
        query = SyncEvent.objects.filter(synced_to_cloud=False)

        if instance_id:
            query = query.filter(instance_id=instance_id)

        return query.count()

    @staticmethod
    def get_pending_conflicts(instance_id: str = None) -> int:
        """
        Get count of pending conflicts

        Args:
            instance_id: Instance ID (None = all instances)

        Returns:
            Count of unresolved conflicts
        """
        query = SyncConflict.objects.filter(resolved=False)

        if instance_id:
            query = query.filter(instance__instance_id=instance_id)

        return query.count()
