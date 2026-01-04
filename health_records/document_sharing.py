"""
Document Sharing Service for Health Records
Handles secure document sharing between healthcare participants
"""
from django.db import models
from django.utils import timezone
from cryptography.fernet import Fernet
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class DocumentShare(models.Model):
    """Tracks document sharing between participants"""
    PERMISSION_CHOICES = [
        ('view', 'View Only'),
        ('download', 'View & Download'),
        ('edit', 'View, Download & Edit'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('revoked', 'Revoked'),
        ('expired', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey('DocumentUpload', on_delete=models.CASCADE, related_name='shares')
    shared_by = models.ForeignKey('core.Participant', on_delete=models.CASCADE, related_name='documents_shared')
    shared_with = models.ForeignKey('core.Participant', on_delete=models.CASCADE, related_name='documents_received')
    permission_level = models.CharField(max_length=20, choices=PERMISSION_CHOICES, default='view')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    message = models.TextField(blank=True, help_text="Optional message to recipient")
    expires_at = models.DateTimeField(null=True, blank=True, help_text="When this share expires")
    
    shared_at = models.DateTimeField(auto_now_add=True)
    accessed_at = models.DateTimeField(null=True, blank=True, help_text="When recipient first accessed")
    revoked_at = models.DateTimeField(null=True, blank=True)
    
    # Encryption
    encryption_key = models.CharField(max_length=255, blank=True, help_text="Per-share encryption key")
    
    class Meta:
        db_table = 'document_shares'
        ordering = ['-shared_at']
        unique_together = [['document', 'shared_with']]  # One share per document per recipient
        indexes = [
            models.Index(fields=['shared_by', 'status']),
            models.Index(fields=['shared_with', 'status']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.document.file_name} shared with {self.shared_with.full_name}"
    
    def is_active(self):
        """Check if share is still valid"""
        if self.status not in ['accepted', 'pending']:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            self.status = 'expired'
            self.save()
            return False
        return True
    
    def mark_accessed(self):
        """Record when recipient first accesses the document"""
        if not self.accessed_at:
            self.accessed_at = timezone.now()
            if self.status == 'pending':
                self.status = 'accepted'
            self.save()
    
    def revoke(self):
        """Revoke access to this share"""
        self.status = 'revoked'
        self.revoked_at = timezone.now()
        self.save()


class DocumentShareService:
    """Service for managing document sharing operations"""
    
    @staticmethod
    def share_document(document, shared_by, shared_with, permission_level='view', 
                      message='', expires_in_days=None):
        """
        Share a document with another participant
        
        Args:
            document: DocumentUpload instance
            shared_by: Participant sharing the document
            shared_with: Participant receiving the share
            permission_level: 'view', 'download', or 'edit'
            message: Optional message to recipient
            expires_in_days: Number of days until share expires (None for no expiration)
        
        Returns:
            DocumentShare instance
        """
        from communication.models import Notification
        
        # Check if share already exists
        existing_share = DocumentShare.objects.filter(
            document=document,
            shared_with=shared_with
        ).first()
        
        if existing_share and existing_share.status in ['pending', 'accepted']:
            # Update existing share
            existing_share.permission_level = permission_level
            existing_share.message = message
            existing_share.shared_at = timezone.now()
            if expires_in_days:
                existing_share.expires_at = timezone.now() + timezone.timedelta(days=expires_in_days)
            existing_share.save()
            share = existing_share
        else:
            # Create new share
            expires_at = None
            if expires_in_days:
                from datetime import timedelta
                expires_at = timezone.now() + timedelta(days=expires_in_days)
            
            share = DocumentShare.objects.create(
                document=document,
                shared_by=shared_by,
                shared_with=shared_with,
                permission_level=permission_level,
                message=message,
                expires_at=expires_at
            )
        
        # Send notification to recipient
        try:
            notification_message = f"{shared_by.full_name} a partagé un document avec vous: {document.file_name}"
            if message:
                notification_message += f"\n\nMessage: {message}"
            
            Notification.objects.create(
                user=shared_with,
                message=notification_message,
                notification_type='document_shared',
                link=f'/patient/health-records/shared-documents/{share.id}/'
            )
        except Exception as e:
            logger.error(f"Failed to send document share notification: {str(e)}")
        
        logger.info(f"Document {document.file_name} shared by {shared_by.uid} with {shared_with.uid}")
        return share
    
    @staticmethod
    def get_shared_documents(participant, as_sender=False):
        """
        Get documents shared with or by a participant
        
        Args:
            participant: Participant instance
            as_sender: If True, return documents shared BY this participant
        
        Returns:
            QuerySet of DocumentShare instances
        """
        if as_sender:
            return DocumentShare.objects.filter(
                shared_by=participant,
                status__in=['pending', 'accepted']
            ).select_related('document', 'shared_with')
        else:
            return DocumentShare.objects.filter(
                shared_with=participant,
                status__in=['pending', 'accepted']
            ).select_related('document', 'shared_by')
    
    @staticmethod
    def revoke_share(share, revoked_by):
        """
        Revoke access to a shared document
        
        Args:
            share: DocumentShare instance
            revoked_by: Participant revoking the share
        """
        from communication.models import Notification
        
        # Only the sharer can revoke
        if share.shared_by != revoked_by:
            raise PermissionError("Only the document owner can revoke access")
        
        share.revoke()
        
        # Notify recipient
        try:
            Notification.objects.create(
                user=share.shared_with,
                message=f"L'accès au document '{share.document.file_name}' a été révoqué",
                notification_type='document_revoked'
            )
        except Exception as e:
            logger.error(f"Failed to send revoke notification: {str(e)}")
        
        logger.info(f"Document share {share.id} revoked by {revoked_by.uid}")
    
    @staticmethod
    def can_access_document(document, participant):
        """
        Check if a participant can access a document
        
        Args:
            document: DocumentUpload instance
            participant: Participant requesting access
        
        Returns:
            tuple: (can_access: bool, permission_level: str or None)
        """
        # Owner always has full access
        if document.uploaded_by == participant:
            return True, 'edit'
        
        # Check for active share
        share = DocumentShare.objects.filter(
            document=document,
            shared_with=participant,
            status__in=['pending', 'accepted']
        ).first()
        
        if share and share.is_active():
            return True, share.permission_level
        
        return False, None
    
    @staticmethod
    def cleanup_expired_shares():
        """Mark expired shares as expired (run as periodic task)"""
        expired_count = DocumentShare.objects.filter(
            status__in=['pending', 'accepted'],
            expires_at__lt=timezone.now()
        ).update(status='expired')
        
        logger.info(f"Marked {expired_count} document shares as expired")
        return expired_count


import uuid
