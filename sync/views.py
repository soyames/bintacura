"""
API Views for Cloud Sync Endpoints

These views run on the CLOUD server and handle:
1. Receiving events from local instances (push)
2. Sending events to local instances (pull)
"""

import jwt
import json
import logging
import hashlib
from datetime import datetime
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
from django.apps import apps
from django.core.serializers import deserialize, serialize as django_serialize

from sync.models import SyncEvent, SyncInstance, SyncConflict
from sync.conflict_resolver import ConflictResolver

logger = logging.getLogger(__name__)


def verify_jwt_token(request):
    """
    Verify JWT token from Authorization header

    Returns:
        SyncInstance if valid, None if invalid
    """
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')

    if not auth_header.startswith('Bearer '):
        return None

    token = auth_header[7:]  # Remove 'Bearer ' prefix

    try:
        # Decode JWT
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])

        # Get instance
        instance_id = payload.get('instance_id')
        instance = SyncInstance.objects.get(instance_id=instance_id, is_active=True)

        return instance

    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid JWT token")
        return None
    except SyncInstance.DoesNotExist:
        logger.warning(f"SyncInstance not found or inactive")
        return None
    except Exception as e:
        logger.error(f"JWT verification error: {str(e)}")
        return None


def _serialize_object(obj):
    """Helper to serialize object to dict"""
    serialized = django_serialize('json', [obj])
    return json.loads(serialized)[0]


@csrf_exempt
@require_http_methods(["POST"])
def push_events(request):
    """
    Receive events from local instance (LOCAL → CLOUD)

    Endpoint: POST /api/sync/push/
    Authentication: JWT Bearer token

    Request Body:
    {
        "events": [
            {
                "id": "uuid",
                "model_name": "appointments.Appointment",
                "object_id": "uuid",
                "event_type": "create|update|delete",
                "timestamp": "2024-01-01T12:00:00Z",
                "instance_id": "uuid",
                "data_snapshot": {...},
                "changed_fields": [...],
                "data_hash": "sha256..."
            },
            ...
        ]
    }

    Response:
    {
        "status": "success|partial|failed",
        "synced_event_ids": ["uuid", ...],
        "conflicts": [
            {
                "event_id": "uuid",
                "conflict_type": "update_update",
                "model_name": "...",
                "object_id": "uuid",
                "local_version": {...},
                "cloud_version": {...},
                "requires_manual_resolution": true|false
            },
            ...
        ],
        "errors": [
            {"event_id": "uuid", "error": "..."},
            ...
        ]
    }
    """
    # Verify authentication
    instance = verify_jwt_token(request)
    if not instance:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        # Parse request body
        data = json.loads(request.body)
        events_data = data.get('events', [])

        if not events_data:
            return JsonResponse({'error': 'No events provided'}, status=400)

        synced_event_ids = []
        conflicts = []
        errors = []

        conflict_resolver = ConflictResolver()

        # Process each event
        for event_data in events_data:
            event_id = event_data.get('id')

            try:
                # Verify data integrity
                data_snapshot = event_data['data_snapshot']
                data_hash = event_data['data_hash']

                computed_hash = hashlib.sha256(
                    json.dumps(data_snapshot, sort_keys=True).encode()
                ).hexdigest()

                if computed_hash != data_hash:
                    errors.append({
                        'event_id': event_id,
                        'error': 'Data integrity check failed'
                    })
                    continue

                # Check if event already exists (idempotency)
                if SyncEvent.objects.filter(id=event_id).exists():
                    logger.info(f"Event {event_id} already exists (idempotent)")
                    synced_event_ids.append(event_id)
                    continue

                # Get model
                model_name = event_data['model_name']
                app_label, model_class_name = model_name.split('.')
                Model = apps.get_model(app_label, model_class_name)

                # Check for conflicts
                object_id = event_data['object_id']
                event_type = event_data['event_type']

                conflict_detected = False

                if event_type in ['update', 'delete']:
                    try:
                        cloud_obj = Model.objects.get(id=object_id)

                        # Check version
                        local_version = data_snapshot.get('fields', {}).get('version', 1)
                        cloud_version = getattr(cloud_obj, 'version', 1)

                        if cloud_version >= local_version:
                            # Cloud has newer or equal version - conflict
                            conflict_detected = True

                            conflicts.append({
                                'event_id': event_id,
                                'conflict_type': 'update_update' if event_type == 'update' else 'delete_update',
                                'model_name': model_name,
                                'object_id': str(object_id),
                                'local_version': data_snapshot,
                                'cloud_version': _serialize_object(cloud_obj),
                                'requires_manual_resolution': model_name in ConflictResolver.CRITICAL_MODELS
                            })

                            # Create conflict record
                            SyncConflict.objects.create(
                                instance=instance,
                                conflict_type='update_update' if event_type == 'update' else 'delete_update',
                                model_name=model_name,
                                object_id=object_id,
                                local_version=data_snapshot,
                                cloud_version=_serialize_object(cloud_obj),
                                requires_manual_resolution=model_name in ConflictResolver.CRITICAL_MODELS
                            )

                            # For critical models, don't apply - require manual resolution
                            if model_name in ConflictResolver.CRITICAL_MODELS:
                                logger.warning(f"Critical conflict detected for {model_name}:{object_id}")
                                continue

                    except Model.DoesNotExist:
                        # Object doesn't exist on cloud - safe to apply
                        pass

                # Apply the event to cloud database
                with transaction.atomic():
                    if event_type == 'create':
                        serialized_data = json.dumps([data_snapshot])
                        for obj in deserialize('json', serialized_data):
                            obj.object._skip_sync_logging = True  # Prevent circular sync
                            obj.save()

                    elif event_type == 'update':
                        serialized_data = json.dumps([data_snapshot])
                        for obj in deserialize('json', serialized_data):
                            obj.object._skip_sync_logging = True
                            obj.save()

                    elif event_type == 'delete':
                        try:
                            obj = Model.objects.get(id=object_id)
                            if hasattr(obj, 'soft_delete'):
                                obj._skip_sync_logging = True
                                obj.soft_delete()
                            else:
                                obj._skip_sync_logging = True
                                obj.delete()
                        except Model.DoesNotExist:
                            pass  # Already deleted

                    # Store the sync event
                    SyncEvent.objects.create(
                        id=event_id,
                        model_name=model_name,
                        object_id=object_id,
                        event_type=event_type,
                        timestamp=datetime.fromisoformat(event_data['timestamp']),
                        instance_id=event_data.get('instance_id'),
                        data_snapshot=data_snapshot,
                        changed_fields=event_data.get('changed_fields'),
                        data_hash=data_hash,
                        synced_to_cloud=True,
                        synced_at=timezone.now(),
                        conflict_detected=conflict_detected
                    )

                synced_event_ids.append(event_id)
                logger.debug(f"Synced event {event_id} from {instance.instance_name}")

            except Exception as e:
                logger.error(f"Failed to process event {event_id}: {str(e)}")
                errors.append({
                    'event_id': event_id,
                    'error': str(e)
                })

        # Determine overall status
        if len(synced_event_ids) == len(events_data):
            status = 'success'
        elif len(synced_event_ids) > 0:
            status = 'partial'
        else:
            status = 'failed'

        # Update instance last sync
        instance.last_sync_at = timezone.now()
        instance.save()

        return JsonResponse({
            'status': status,
            'synced_event_ids': synced_event_ids,
            'conflicts': conflicts,
            'errors': errors
        })

    except Exception as e:
        logger.exception("Failed to process push request")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def pull_events(request):
    """
    Send events to local instance (CLOUD → LOCAL)

    Endpoint: GET /api/sync/pull/?since=<timestamp>&instance_id=<uuid>
    Authentication: JWT Bearer token

    Query Parameters:
    - since: ISO timestamp (only get events after this time)
    - instance_id: UUID of requesting instance (exclude their own events)

    Response:
    {
        "status": "success",
        "events": [
            {
                "id": "uuid",
                "model_name": "appointments.Appointment",
                "object_id": "uuid",
                "event_type": "create|update|delete",
                "timestamp": "2024-01-01T12:00:00Z",
                "instance_id": "uuid",
                "data_snapshot": {...},
                "changed_fields": [...],
                "data_hash": "sha256..."
            },
            ...
        ],
        "count": 10
    }
    """
    # Verify authentication
    instance = verify_jwt_token(request)
    if not instance:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        # Get query parameters
        since_str = request.GET.get('since')
        instance_id = request.GET.get('instance_id', str(instance.instance_id))

        # Parse since timestamp
        if since_str:
            try:
                since = datetime.fromisoformat(since_str.replace('Z', '+00:00'))
            except ValueError:
                return JsonResponse({'error': 'Invalid since timestamp'}, status=400)
        else:
            # Default to last 7 days
            from datetime import timedelta
            since = timezone.now() - timedelta(days=7)

        # Query events
        events_query = SyncEvent.objects.filter(
            timestamp__gte=since
        ).exclude(
            instance_id=instance_id  # Don't send back their own events
        ).order_by('timestamp')[:1000]  # Limit to 1000 events per pull

        # Serialize events
        events_data = []
        for event in events_query:
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

        # Update instance last sync
        instance.last_sync_at = timezone.now()
        instance.save()

        return JsonResponse({
            'status': 'success',
            'events': events_data,
            'count': len(events_data)
        })

    except Exception as e:
        logger.exception("Failed to process pull request")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def sync_status(request):
    """
    Get sync status for an instance

    Endpoint: GET /api/sync/status/
    Authentication: JWT Bearer token

    Response:
    {
        "instance_id": "uuid",
        "instance_name": "...",
        "is_active": true,
        "last_sync_at": "2024-01-01T12:00:00Z",
        "unsynced_events_count": 0,
        "pending_conflicts_count": 0
    }
    """
    # Verify authentication
    instance = verify_jwt_token(request)
    if not instance:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        # Get unsynced events count
        unsynced_count = SyncEvent.objects.filter(
            instance_id=instance.instance_id,
            synced_to_cloud=False
        ).count()

        # Get pending conflicts count
        conflicts_count = SyncConflict.objects.filter(
            instance=instance,
            resolved=False
        ).count()

        return JsonResponse({
            'instance_id': str(instance.instance_id),
            'instance_name': instance.instance_name,
            'is_active': instance.is_active,
            'sync_enabled': instance.sync_enabled,
            'last_sync_at': instance.last_sync_at.isoformat() if instance.last_sync_at else None,
            'unsynced_events_count': unsynced_count,
            'pending_conflicts_count': conflicts_count
        })

    except Exception as e:
        logger.exception("Failed to get sync status")
        return JsonResponse({'error': str(e)}, status=500)
