"""
Conflict Resolution Strategies

Handles synchronization conflicts when the same record is modified
on multiple instances simultaneously.

Conflict Types:
- Update-Update: Two instances update same record
- Delete-Update: One instance deletes while another updates
- Create-Create: Two instances create same record (UUID collision - rare)
- Payment: Financial transaction conflicts (require manual resolution)
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from django.db import transaction
from django.utils import timezone
from django.apps import apps

from sync.models import SyncConflict

logger = logging.getLogger(__name__)


class ConflictResolver:
    """
    Resolves synchronization conflicts using various strategies

    Strategies:
    1. Latest Timestamp Wins (default)
    2. Cloud Wins (cloud is authoritative)
    3. Local Wins (local is authoritative)
    4. Field-Level Merge (merge non-conflicting fields)
    5. Manual Resolution (human decision required)
    """

    # Critical models that require manual conflict resolution
    CRITICAL_MODELS = [
        'payments.GatewayTransaction',
        'payments.ServiceTransaction',
        'payments.TransactionFee',
        'insurance.InsuranceClaim',
        'core.Transaction',
        'core.Wallet',
    ]

    # Models that use automatic resolution (non-financial)
    AUTO_RESOLVE_MODELS = [
        'appointments.Appointment',
        'prescriptions.Prescription',
        'patient.PatientData',
        'doctor.DoctorData',
        'hospital.HospitalData',
        'pharmacy.PharmacyInventory',
        'health_records.HealthRecord',
        'communication.Notification',
        'ai.Conversation',
    ]

    # Models where cloud is always authoritative
    CLOUD_AUTHORITATIVE_MODELS = [
        'core.Participant',  # User accounts managed on cloud
        'appointments.Availability',  # Slot availability on cloud
        'core.Review',  # Reviews managed centrally
    ]

    # Models where local is authoritative
    LOCAL_AUTHORITATIVE_MODELS = [
        'health_records.PatientNote',  # Doctor's local notes
        'pharmacy.PharmacySale',  # Local pharmacy sales
        'hospital.DepartmentTask',  # Local hospital tasks
    ]

    def resolve_update_update_conflict(
        self,
        local_obj: Any,
        cloud_data: Dict[str, Any],
        instance: 'SyncInstance',
        strategy: str = 'latest_wins'
    ) -> Optional[Any]:
        """
        Resolve update-update conflict

        Args:
            local_obj: Local database object
            cloud_data: Cloud object data snapshot
            instance: SyncInstance that detected conflict
            strategy: Resolution strategy ('latest_wins', 'cloud_wins', 'local_wins', 'merge', 'manual')

        Returns:
            Resolved object if auto-resolved, None if manual resolution required
        """
        model_name = f"{local_obj._meta.app_label}.{local_obj._meta.model_name}"

        # Check if this is a critical model requiring manual resolution
        if model_name in self.CRITICAL_MODELS:
            logger.warning(f"Critical financial model conflict detected: {model_name} - requires manual resolution")
            self._create_conflict_record(
                instance=instance,
                conflict_type='payment' if 'transaction' in model_name.lower() else 'update_update',
                model_name=model_name,
                object_id=local_obj.id,
                local_obj=local_obj,
                cloud_data=cloud_data,
                requires_manual=True
            )
            return None
        
        # Auto-resolve non-financial models
        if model_name in self.AUTO_RESOLVE_MODELS:
            logger.info(f"Auto-resolving non-financial model conflict: {model_name}")
            strategy = 'latest_wins'  # Default for auto-resolve

        # Auto-select strategy based on model
        if strategy == 'auto':
            if model_name in self.CLOUD_AUTHORITATIVE_MODELS:
                strategy = 'cloud_wins'
            elif model_name in self.LOCAL_AUTHORITATIVE_MODELS:
                strategy = 'local_wins'
            else:
                strategy = 'latest_wins'

        # Apply resolution strategy
        if strategy == 'cloud_wins':
            return self._resolve_cloud_wins(local_obj, cloud_data, instance)

        elif strategy == 'local_wins':
            return self._resolve_local_wins(local_obj, cloud_data, instance)

        elif strategy == 'latest_wins':
            return self._resolve_latest_wins(local_obj, cloud_data, instance)

        elif strategy == 'merge':
            return self._resolve_merge_fields(local_obj, cloud_data, instance)

        elif strategy == 'manual':
            self._create_conflict_record(
                instance=instance,
                conflict_type='update_update',
                model_name=model_name,
                object_id=local_obj.id,
                local_obj=local_obj,
                cloud_data=cloud_data,
                requires_manual=True
            )
            return None

        else:
            logger.error(f"Unknown conflict resolution strategy: {strategy}")
            return None

    def resolve_delete_update_conflict(
        self,
        local_obj: Optional[Any],
        cloud_data: Dict[str, Any],
        instance: 'SyncInstance',
        deleted_locally: bool = False
    ) -> bool:
        """
        Resolve delete-update conflict

        Args:
            local_obj: Local object (None if deleted locally)
            cloud_data: Cloud object data
            instance: SyncInstance
            deleted_locally: True if local deleted, False if cloud deleted

        Returns:
            True if resolved, False if manual resolution required
        """
        model_name = cloud_data.get('model') or f"{local_obj._meta.app_label}.{local_obj._meta.model_name}"

        # Critical models require manual resolution
        if model_name in self.CRITICAL_MODELS:
            self._create_conflict_record(
                instance=instance,
                conflict_type='delete_update',
                model_name=model_name,
                object_id=cloud_data.get('pk') or local_obj.id,
                local_obj=local_obj,
                cloud_data=cloud_data,
                requires_manual=True
            )
            return False

        # Default: Delete wins (respect deletion)
        if deleted_locally and local_obj:
            # Cloud has update, but local deleted - keep deletion
            logger.info(f"Delete-update conflict: Keeping local deletion for {model_name}")
            return True
        elif not deleted_locally:
            # Local has update, but cloud deleted - accept deletion
            logger.info(f"Delete-update conflict: Accepting cloud deletion for {model_name}")
            if local_obj and hasattr(local_obj, 'soft_delete'):
                local_obj._skip_sync_logging = True
                local_obj.soft_delete()
            elif local_obj:
                local_obj._skip_sync_logging = True
                local_obj.delete()
            return True

        return True

    def _resolve_cloud_wins(
        self,
        local_obj: Any,
        cloud_data: Dict[str, Any],
        instance: 'SyncInstance'
    ) -> Any:
        """Cloud version wins - overwrite local with cloud data"""
        try:
            cloud_fields = cloud_data.get('fields', {})

            # Update local object with cloud data
            for field_name, cloud_value in cloud_fields.items():
                if hasattr(local_obj, field_name):
                    setattr(local_obj, field_name, cloud_value)

            # Mark to skip sync logging
            local_obj._skip_sync_logging = True
            local_obj.save()

            logger.info(
                f"Resolved conflict (cloud_wins): "
                f"{local_obj._meta.app_label}.{local_obj._meta.model_name}:{local_obj.id}"
            )

            # Record resolution
            self._create_conflict_record(
                instance=instance,
                conflict_type='update_update',
                model_name=f"{local_obj._meta.app_label}.{local_obj._meta.model_name}",
                object_id=local_obj.id,
                local_obj=local_obj,
                cloud_data=cloud_data,
                requires_manual=False,
                resolution_strategy='cloud_wins',
                resolved=True
            )

            return local_obj

        except Exception as e:
            logger.error(f"Failed to resolve conflict (cloud_wins): {str(e)}")
            return None

    def _resolve_local_wins(
        self,
        local_obj: Any,
        cloud_data: Dict[str, Any],
        instance: 'SyncInstance'
    ) -> Any:
        """Local version wins - keep local data, ignore cloud"""
        try:
            logger.info(
                f"Resolved conflict (local_wins): "
                f"{local_obj._meta.app_label}.{local_obj._meta.model_name}:{local_obj.id}"
            )

            # Record resolution
            self._create_conflict_record(
                instance=instance,
                conflict_type='update_update',
                model_name=f"{local_obj._meta.app_label}.{local_obj._meta.model_name}",
                object_id=local_obj.id,
                local_obj=local_obj,
                cloud_data=cloud_data,
                requires_manual=False,
                resolution_strategy='local_wins',
                resolved=True
            )

            # No changes needed - local wins
            return local_obj

        except Exception as e:
            logger.error(f"Failed to resolve conflict (local_wins): {str(e)}")
            return None

    def _resolve_latest_wins(
        self,
        local_obj: Any,
        cloud_data: Dict[str, Any],
        instance: 'SyncInstance'
    ) -> Any:
        """Latest timestamp wins - compare updated_at fields"""
        try:
            local_updated = getattr(local_obj, 'updated_at', None)
            cloud_updated_str = cloud_data.get('fields', {}).get('updated_at')

            if not local_updated or not cloud_updated_str:
                # Fallback to cloud_wins if timestamps not available
                logger.warning("Timestamps not available, defaulting to cloud_wins")
                return self._resolve_cloud_wins(local_obj, cloud_data, instance)

            # Parse cloud timestamp
            if isinstance(cloud_updated_str, str):
                cloud_updated = datetime.fromisoformat(cloud_updated_str.replace('Z', '+00:00'))
            else:
                cloud_updated = cloud_updated_str

            # Compare timestamps
            if cloud_updated > local_updated:
                # Cloud is newer
                logger.info(
                    f"Resolved conflict (latest_wins - cloud): "
                    f"{local_obj._meta.app_label}.{local_obj._meta.model_name}:{local_obj.id}"
                )
                return self._resolve_cloud_wins(local_obj, cloud_data, instance)
            else:
                # Local is newer or equal
                logger.info(
                    f"Resolved conflict (latest_wins - local): "
                    f"{local_obj._meta.app_label}.{local_obj._meta.model_name}:{local_obj.id}"
                )
                return self._resolve_local_wins(local_obj, cloud_data, instance)

        except Exception as e:
            logger.error(f"Failed to resolve conflict (latest_wins): {str(e)}")
            return None

    def _resolve_merge_fields(
        self,
        local_obj: Any,
        cloud_data: Dict[str, Any],
        instance: 'SyncInstance'
    ) -> Any:
        """
        Merge non-conflicting fields intelligently.
        
        Strategy for non-financial data:
        - Compare each field individually
        - If only one side changed, use that change
        - If both sides changed to same value, no conflict
        - If both changed to different values, use latest timestamp
        - Financial fields always require manual resolution
        """
        try:
            model_name = f"{local_obj._meta.app_label}.{local_obj._meta.model_name}"
            
            # Financial models should not use automatic merge
            if model_name in self.CRITICAL_MODELS:
                logger.error(f"Attempted automatic merge on financial model {model_name}")
                return None
            
            cloud_fields = cloud_data.get('fields', {})
            merge_performed = False
            
            # For non-financial models, merge non-conflicting fields
            for field_name, cloud_value in cloud_fields.items():
                if not hasattr(local_obj, field_name):
                    continue
                
                local_value = getattr(local_obj, field_name)
                
                # Skip timestamp fields (used for conflict detection)
                if field_name in ['updated_at', 'created_at', 'version']:
                    continue
                
                # If values are different, take cloud value for non-critical fields
                if local_value != cloud_value:
                    # For text fields with both changes, concatenate with marker
                    if isinstance(local_value, str) and isinstance(cloud_value, str):
                        if len(local_value) > 0 and len(cloud_value) > 0:
                            # Both have content, merge with marker
                            merged_value = f"{local_value}\n[MERGED FROM CLOUD]\n{cloud_value}"
                            setattr(local_obj, field_name, merged_value)
                            merge_performed = True
                            logger.info(f"Merged text field {field_name}")
                    else:
                        # For non-text fields, use latest timestamp logic
                        local_updated = getattr(local_obj, 'updated_at', None)
                        cloud_updated_str = cloud_data.get('fields', {}).get('updated_at')
                        
                        if cloud_updated_str:
                            if isinstance(cloud_updated_str, str):
                                cloud_updated = datetime.fromisoformat(cloud_updated_str.replace('Z', '+00:00'))
                            else:
                                cloud_updated = cloud_updated_str
                            
                            if cloud_updated > local_updated:
                                setattr(local_obj, field_name, cloud_value)
                                merge_performed = True
            
            if merge_performed:
                local_obj._skip_sync_logging = True
                local_obj.save()
                
                logger.info(
                    f"Resolved conflict (merge): "
                    f"{local_obj._meta.app_label}.{local_obj._meta.model_name}:{local_obj.id}"
                )
                
                # Record resolution
                self._create_conflict_record(
                    instance=instance,
                    conflict_type='update_update',
                    model_name=model_name,
                    object_id=local_obj.id,
                    local_obj=local_obj,
                    cloud_data=cloud_data,
                    requires_manual=False,
                    resolution_strategy='field_merge',
                    resolved=True
                )
                
                return local_obj
            else:
                # No actual conflicts, use latest_wins as fallback
                return self._resolve_latest_wins(local_obj, cloud_data, instance)

        except Exception as e:
            logger.error(f"Failed to resolve conflict (merge): {str(e)}")
            # Fallback to latest_wins if merge fails
            return self._resolve_latest_wins(local_obj, cloud_data, instance)

    def _create_conflict_record(
        self,
        instance: 'SyncInstance',
        conflict_type: str,
        model_name: str,
        object_id: str,
        local_obj: Any,
        cloud_data: Dict[str, Any],
        requires_manual: bool = False,
        resolution_strategy: str = None,
        resolved: bool = False
    ):
        """Create SyncConflict record for tracking"""
        try:
            # Serialize local object
            from django.core.serializers import serialize
            import json

            if local_obj:
                local_serialized = serialize('json', [local_obj])
                local_version = json.loads(local_serialized)[0]
            else:
                local_version = {'deleted': True}

            conflict = SyncConflict.objects.create(
                instance=instance,
                conflict_type=conflict_type,
                model_name=model_name,
                object_id=object_id,
                local_version=local_version,
                cloud_version=cloud_data,
                resolution_strategy=resolution_strategy,
                requires_manual_resolution=requires_manual,
                resolved=resolved,
                resolved_at=timezone.now() if resolved else None
            )

            logger.info(
                f"Created conflict record: {conflict_type} for {model_name}:{object_id} "
                f"(manual={requires_manual}, resolved={resolved})"
            )

        except Exception as e:
            logger.error(f"Failed to create conflict record: {str(e)}")

    @staticmethod
    def resolve_conflict_manually(
        conflict_id: str,
        resolution: str,
        resolved_by: 'Participant'
    ) -> bool:
        """
        Manually resolve a conflict

        Args:
            conflict_id: SyncConflict UUID
            resolution: 'use_local', 'use_cloud', or 'merge'
            resolved_by: Participant who resolved

        Returns:
            True if resolved successfully
        """
        try:
            conflict = SyncConflict.objects.get(id=conflict_id)

            if conflict.resolved:
                logger.warning(f"Conflict {conflict_id} already resolved")
                return False

            # Get model
            app_label, model_name = conflict.model_name.split('.')
            Model = apps.get_model(app_label, model_name)

            with transaction.atomic():
                if resolution == 'use_cloud':
                    # Apply cloud version
                    from django.core.serializers import deserialize
                    import json

                    serialized_data = json.dumps([conflict.cloud_version])
                    for obj in deserialize('json', serialized_data):
                        obj.object._skip_sync_logging = True
                        obj.save()

                    conflict.resolution_strategy = 'cloud_wins'

                elif resolution == 'use_local':
                    # Keep local version (do nothing)
                    conflict.resolution_strategy = 'local_wins'

                elif resolution == 'merge':
                    # Manual merge would require custom UI
                    logger.error("Manual merge not implemented via API")
                    return False

                # Mark resolved
                conflict.resolved = True
                conflict.resolved_at = timezone.now()
                conflict.resolved_by = resolved_by
                conflict.save()

                logger.info(f"Manually resolved conflict {conflict_id} ({resolution})")
                return True

        except Exception as e:
            logger.error(f"Failed to manually resolve conflict {conflict_id}: {str(e)}")
            return False
