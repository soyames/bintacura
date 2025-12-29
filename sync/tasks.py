"""
Celery Tasks for Offline-First Synchronization

Asynchronous tasks for bidirectional sync between local instances and cloud.
These tasks are scheduled by Celery Beat to run automatically.
"""

import logging
from typing import Dict, Any
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from sync.models import SyncInstance, SyncInstanceLog
from sync.services import SyncService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def push_changes_to_cloud(self, instance_id: str = None):
    """
    Push local changes to cloud (LOCAL → CLOUD)

    This task runs on LOCAL business instances to send their
    unsynced events to the cloud database.

    Args:
        instance_id: UUID of the local instance (uses settings.INSTANCE_ID if None)

    Returns:
        Dict with sync statistics
    """
    try:
        # Get instance ID
        if instance_id is None:
            instance_id = getattr(settings, 'INSTANCE_ID', None)

        if not instance_id:
            logger.error("No instance_id provided and settings.INSTANCE_ID not set")
            return {'error': 'No instance_id configured'}

        # Get instance
        try:
            instance = SyncInstance.objects.get(instance_id=instance_id)
        except SyncInstance.DoesNotExist:
            logger.error(f"SyncInstance {instance_id} not found")
            return {'error': 'Instance not found'}

        # Check if sync enabled
        if not instance.sync_enabled or not instance.is_active:
            logger.info(f"Sync disabled for instance {instance_id}")
            return {'skipped': 'Sync disabled or instance inactive'}

        # Get cloud URL and JWT token
        cloud_url = getattr(settings, 'SYNC_CLOUD_PUSH_URL', None)
        if not cloud_url:
            logger.error("settings.SYNC_CLOUD_PUSH_URL not configured")
            return {'error': 'Cloud URL not configured'}

        jwt_token = instance.generate_jwt_token()

        # Perform push
        sync_service = SyncService(instance_id=str(instance_id))
        log = sync_service.push_events_to_cloud(
            cloud_api_url=cloud_url,
            jwt_token=jwt_token,
            batch_size=getattr(settings, 'SYNC_BATCH_SIZE', 100)
        )

        logger.info(
            f"Push completed: {log.records_pushed} records pushed, "
            f"{log.conflicts_detected} conflicts, status={log.status}"
        )

        return {
            'instance_id': str(instance_id),
            'direction': 'push',
            'status': log.status,
            'records_pushed': log.records_pushed,
            'conflicts_detected': log.conflicts_detected,
            'errors_count': log.errors_count,
            'log_id': str(log.id)
        }

    except Exception as e:
        logger.exception(f"Failed to push changes to cloud: {str(e)}")

        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def pull_changes_from_cloud(self, instance_id: str = None):
    """
    Pull changes from cloud to local (CLOUD → LOCAL)

    This task runs on LOCAL business instances to retrieve
    changes from other instances via the cloud.

    Args:
        instance_id: UUID of the local instance (uses settings.INSTANCE_ID if None)

    Returns:
        Dict with sync statistics
    """
    try:
        # Get instance ID
        if instance_id is None:
            instance_id = getattr(settings, 'INSTANCE_ID', None)

        if not instance_id:
            logger.error("No instance_id provided and settings.INSTANCE_ID not set")
            return {'error': 'No instance_id configured'}

        # Get instance
        try:
            instance = SyncInstance.objects.get(instance_id=instance_id)
        except SyncInstance.DoesNotExist:
            logger.error(f"SyncInstance {instance_id} not found")
            return {'error': 'Instance not found'}

        # Check if sync enabled
        if not instance.sync_enabled or not instance.is_active:
            logger.info(f"Sync disabled for instance {instance_id}")
            return {'skipped': 'Sync disabled or instance inactive'}

        # Get cloud URL and JWT token
        cloud_url = getattr(settings, 'SYNC_CLOUD_PULL_URL', None)
        if not cloud_url:
            logger.error("settings.SYNC_CLOUD_PULL_URL not configured")
            return {'error': 'Cloud URL not configured'}

        jwt_token = instance.generate_jwt_token()

        # Perform pull
        sync_service = SyncService(instance_id=str(instance_id))
        log = sync_service.pull_events_from_cloud(
            cloud_api_url=cloud_url,
            jwt_token=jwt_token
        )

        logger.info(
            f"Pull completed: {log.records_pulled} records pulled, "
            f"{log.conflicts_detected} conflicts, status={log.status}"
        )

        return {
            'instance_id': str(instance_id),
            'direction': 'pull',
            'status': log.status,
            'records_pulled': log.records_pulled,
            'conflicts_detected': log.conflicts_detected,
            'errors_count': log.errors_count,
            'log_id': str(log.id)
        }

    except Exception as e:
        logger.exception(f"Failed to pull changes from cloud: {str(e)}")

        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def bidirectional_sync(self, instance_id: str = None):
    """
    Perform full bidirectional sync (push then pull)

    This is the main sync task that should be scheduled periodically.
    It pushes local changes to cloud, then pulls cloud changes to local.

    Args:
        instance_id: UUID of the local instance (uses settings.INSTANCE_ID if None)

    Returns:
        Dict with sync statistics for both push and pull
    """
    try:
        # Get instance ID
        if instance_id is None:
            instance_id = getattr(settings, 'INSTANCE_ID', None)

        if not instance_id:
            logger.error("No instance_id provided and settings.INSTANCE_ID not set")
            return {'error': 'No instance_id configured'}

        # Get instance
        try:
            instance = SyncInstance.objects.get(instance_id=instance_id)
        except SyncInstance.DoesNotExist:
            logger.error(f"SyncInstance {instance_id} not found")
            return {'error': 'Instance not found'}

        # Check if sync enabled
        if not instance.sync_enabled or not instance.is_active:
            logger.info(f"Sync disabled for instance {instance_id}")
            return {'skipped': 'Sync disabled or instance inactive'}

        # Get cloud URLs and JWT token
        cloud_push_url = getattr(settings, 'SYNC_CLOUD_PUSH_URL', None)
        cloud_pull_url = getattr(settings, 'SYNC_CLOUD_PULL_URL', None)

        if not cloud_push_url or not cloud_pull_url:
            logger.error("Cloud URLs not configured in settings")
            return {'error': 'Cloud URLs not configured'}

        jwt_token = instance.generate_jwt_token()

        # Perform bidirectional sync
        sync_service = SyncService(instance_id=str(instance_id))
        logs = sync_service.bidirectional_sync(
            cloud_push_url=cloud_push_url,
            cloud_pull_url=cloud_pull_url,
            jwt_token=jwt_token
        )

        push_log = logs['push']
        pull_log = logs['pull']

        logger.info(
            f"Bidirectional sync completed: "
            f"pushed {push_log.records_pushed}, "
            f"pulled {pull_log.records_pulled}, "
            f"total conflicts {push_log.conflicts_detected + pull_log.conflicts_detected}"
        )

        return {
            'instance_id': str(instance_id),
            'push': {
                'status': push_log.status,
                'records_pushed': push_log.records_pushed,
                'conflicts': push_log.conflicts_detected,
                'errors': push_log.errors_count,
                'log_id': str(push_log.id)
            },
            'pull': {
                'status': pull_log.status,
                'records_pulled': pull_log.records_pulled,
                'conflicts': pull_log.conflicts_detected,
                'errors': pull_log.errors_count,
                'log_id': str(pull_log.id)
            }
        }

    except Exception as e:
        logger.exception(f"Failed to perform bidirectional sync: {str(e)}")

        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task
def sync_all_active_instances():
    """
    Sync all active instances

    This task can be scheduled on CLOUD to trigger sync for all
    registered instances, or run on local instance manager.

    Returns:
        Dict with sync results for all instances
    """
    try:
        active_instances = SyncInstance.objects.filter(
            is_active=True,
            sync_enabled=True
        )

        results = []
        for instance in active_instances:
            try:
                result = bidirectional_sync.delay(str(instance.instance_id))
                results.append({
                    'instance_id': str(instance.instance_id),
                    'instance_name': instance.instance_name,
                    'task_id': result.id,
                    'status': 'queued'
                })
            except Exception as e:
                logger.error(f"Failed to queue sync for {instance.instance_name}: {str(e)}")
                results.append({
                    'instance_id': str(instance.instance_id),
                    'instance_name': instance.instance_name,
                    'error': str(e)
                })

        logger.info(f"Queued sync for {len(results)} instances")
        return {
            'total_instances': len(results),
            'results': results
        }

    except Exception as e:
        logger.exception(f"Failed to sync all active instances: {str(e)}")
        return {'error': str(e)}


@shared_task
def cleanup_old_sync_logs(days_to_keep: int = 30):
    """
    Clean up old sync logs to prevent database bloat

    Args:
        days_to_keep: Number of days to keep logs (default: 30)

    Returns:
        Number of logs deleted
    """
    try:
        from datetime import timedelta

        cutoff_date = timezone.now() - timedelta(days=days_to_keep)

        # Delete old successful logs (keep failed logs longer)
        deleted_count, _ = SyncInstanceLog.objects.filter(
            completed_at__lt=cutoff_date,
            status='success'
        ).delete()

        logger.info(f"Cleaned up {deleted_count} old sync logs")
        return {'deleted_count': deleted_count}

    except Exception as e:
        logger.exception(f"Failed to cleanup old sync logs: {str(e)}")
        return {'error': str(e)}


@shared_task
def cleanup_synced_events(days_to_keep: int = 7):
    """
    Clean up old synced events to save disk space

    Keep unsynced events forever, but delete old synced events
    as they're safely stored on cloud.

    Args:
        days_to_keep: Number of days to keep synced events (default: 7)

    Returns:
        Number of events deleted
    """
    try:
        from datetime import timedelta

        cutoff_date = timezone.now() - timedelta(days=days_to_keep)

        # Only delete events that are synced to cloud
        deleted_count, _ = SyncEvent.objects.filter(
            synced_at__lt=cutoff_date,
            synced_to_cloud=True
        ).delete()

        logger.info(f"Cleaned up {deleted_count} old synced events")
        return {'deleted_count': deleted_count}

    except Exception as e:
        logger.exception(f"Failed to cleanup synced events: {str(e)}")
        return {'error': str(e)}


# Celery Beat Schedule (add to settings.py)
"""
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Bidirectional sync every 15 minutes
    'bidirectional-sync': {
        'task': 'sync.tasks.bidirectional_sync',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
        'options': {'expires': 60 * 10}  # Expire after 10 minutes if not executed
    },

    # Cleanup old logs daily at 2 AM
    'cleanup-sync-logs': {
        'task': 'sync.tasks.cleanup_old_sync_logs',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
        'kwargs': {'days_to_keep': 30}
    },

    # Cleanup synced events daily at 3 AM
    'cleanup-synced-events': {
        'task': 'sync.tasks.cleanup_synced_events',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
        'kwargs': {'days_to_keep': 7}
    },
}
"""
