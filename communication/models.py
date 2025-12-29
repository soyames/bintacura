from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator
import uuid
from core.models import Participant
from core.sync_mixin import SyncMixin

class CommunityProfile(models.Model):  # Manages user profiles for the community forum
    participant = models.OneToOneField(Participant, on_delete=models.CASCADE, related_name='community_profile')
    handle = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=255)
    bio = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True)
    is_verified = models.BooleanField(default=False)
    is_private = models.BooleanField(default=False)
    followers_count = models.IntegerField(default=0)
    following_count = models.IntegerField(default=0)
    posts_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # Meta class implementation
        db_table = 'community_profiles'

class CommunityPost(SyncMixin):
    POST_TYPE_CHOICES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('textWithImage', 'Text with Image'),
        ('poll', 'Poll'),
        ('article', 'Article'),
    ]

    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('followers', 'Followers'),
        ('connections', 'Connections'),
        ('private', 'Private'),
    ]

    author = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='community_posts')
    author_handle = models.CharField(max_length=100, blank=True)
    content = models.TextField()
    image_url = models.URLField(blank=True)
    image = models.ImageField(
        upload_to='forum/posts/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp'])]
    )
    post_type = models.CharField(max_length=20, choices=POST_TYPE_CHOICES, default='text')
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    group = models.ForeignKey('CommunityGroup', on_delete=models.CASCADE, null=True, blank=True, related_name='posts')

    likes_count = models.IntegerField(default=0)
    dislikes_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)
    shares_count = models.IntegerField(default=0)

    hashtags = models.JSONField(default=list, blank=True)
    mentions = models.JSONField(default=list, blank=True)

    is_pinned = models.BooleanField(default=False)
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    region_code = models.CharField(max_length=50, default="global", db_index=True)

    class Meta:
        db_table = 'community_posts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['author', 'created_at']),
            models.Index(fields=['visibility', 'created_at']),
        ]

class CommunityComment(SyncMixin):
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='community_comments')
    content = models.TextField()
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    likes_count = models.IntegerField(default=0)
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    region_code = models.CharField(max_length=50, default="global", db_index=True)

    class Meta:
        db_table = 'community_comments'
        ordering = ['created_at']

class CommunityConnection(models.Model):  # Manages follower relationships and connections between users
    CONNECTION_TYPE_CHOICES = [
        ('follow', 'Follow'),
        ('friend', 'Friend'),
        ('blocked', 'Blocked'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='connections_from')
    to_participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='connections_to')
    connection_type = models.CharField(max_length=20, choices=CONNECTION_TYPE_CHOICES, default='follow')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='accepted')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # Meta class implementation
        db_table = 'community_connections'
        unique_together = ['from_participant', 'to_participant', 'connection_type']

class CommunityMessage(SyncMixin):
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('file', 'File'),
        ('voice', 'Voice'),
    ]

    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
    ]

    sender = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='text')
    attachment_url = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    read_at = models.DateTimeField(null=True, blank=True)
    is_deleted_by_sender = models.BooleanField(default=False)
    is_deleted_by_recipient = models.BooleanField(default=False)
    region_code = models.CharField(max_length=50, default="global", db_index=True)

    class Meta:
        db_table = 'community_messages'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sender', 'recipient', 'created_at']),
        ]

class Notification(SyncMixin):
    NOTIFICATION_TYPE_CHOICES = [
        ('appointment', 'Appointment'),
        ('prescription', 'Prescription'),
        ('payment', 'Payment'),
        ('message', 'Message'),
        ('community', 'Community'),
        ('insurance', 'Insurance'),
        ('health_alert', 'Health Alert'),
        ('system', 'System'),
    ]

    recipient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    action_url = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    region_code = models.CharField(max_length=50, default="global", db_index=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', 'created_at']),
        ]

class RideRequest(SyncMixin):
    STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    RIDE_TYPE_CHOICES = [
        ('ambulance', 'Ambulance'),
        ('medical_transport', 'Medical Transport'),
        ('wheelchair_accessible', 'Wheelchair Accessible'),
    ]

    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='ride_requests')
    provider = models.ForeignKey(Participant, on_delete=models.CASCADE, null=True, blank=True, related_name='assigned_rides')
    ride_type = models.CharField(max_length=50, choices=RIDE_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')
    pickup_location = models.TextField()
    pickup_latitude = models.FloatField()
    pickup_longitude = models.FloatField()
    destination_location = models.TextField()
    destination_latitude = models.FloatField()
    destination_longitude = models.FloatField()
    scheduled_time = models.DateTimeField()
    estimated_arrival_time = models.DateTimeField(null=True, blank=True)
    actual_pickup_time = models.DateTimeField(null=True, blank=True)
    actual_dropoff_time = models.DateTimeField(null=True, blank=True)
    distance_km = models.FloatField(null=True, blank=True)
    fare = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    driver_name = models.CharField(max_length=255, blank=True)
    driver_phone = models.CharField(max_length=20, blank=True)
    vehicle_number = models.CharField(max_length=50, blank=True)
    region_code = models.CharField(max_length=50, default="global", db_index=True)

    class Meta:
        db_table = 'ride_requests'
        ordering = ['-created_at']

# New models for forum features
class PostLike(models.Model):  # Tracks likes and dislikes on posts
    """Track likes and dislikes on posts"""
    REACTION_CHOICES = [
        ('like', 'Like'),
        ('dislike', 'Dislike'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='reactions')
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='post_reactions')
    reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:  # Meta class implementation
        db_table = 'post_likes'
        unique_together = ['post', 'participant']
        indexes = [
            models.Index(fields=['post', 'reaction_type']),
        ]

class CommentLike(models.Model):  # Tracks likes on comments
    """Track likes on comments"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    comment = models.ForeignKey(CommunityComment, on_delete=models.CASCADE, related_name='likes')
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='comment_likes')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:  # Meta class implementation
        db_table = 'comment_likes'
        unique_together = ['comment', 'participant']

class CommunityGroup(models.Model):  # Represents forum groups and communities
    """Forum groups/communities"""
    PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
        ('secret', 'Secret'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField()
    cover_image = models.ImageField(upload_to='forum/groups/', blank=True, null=True)
    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default='public')
    creator = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='created_groups')
    admins = models.ManyToManyField(Participant, related_name='admin_groups', blank=True)
    members_count = models.IntegerField(default=0)
    posts_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # Meta class implementation
        db_table = 'community_groups'
        ordering = ['-created_at']

class GroupMembership(models.Model):  # Tracks user memberships in community groups
    """Track group memberships"""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('member', 'Member'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(CommunityGroup, on_delete=models.CASCADE, related_name='memberships')
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='group_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved')
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:  # Meta class implementation
        db_table = 'group_memberships'
        unique_together = ['group', 'participant']

class OnlineStatus(models.Model):  # Tracks user online status and last activity
    """Track online users"""
    participant = models.OneToOneField(Participant, on_delete=models.CASCADE, related_name='online_status')
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(default=timezone.now)
    last_activity = models.DateTimeField(default=timezone.now)

    class Meta:  # Meta class implementation
        db_table = 'online_status'
