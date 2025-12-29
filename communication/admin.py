from django.contrib import admin
from .models import CommunityProfile, CommunityPost, CommunityComment, CommunityConnection, CommunityMessage, Notification, RideRequest

@admin.register(CommunityProfile)
class CommunityProfileAdmin(admin.ModelAdmin):  # Admin configuration for CommunityProfile model
    list_display = ('participant', 'handle', 'display_name', 'is_verified', 'is_private', 'followers_count', 'posts_count')
    list_filter = ('is_verified', 'is_private')
    search_fields = ('handle', 'display_name', 'participant__email')

@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):  # Admin configuration for CommunityPost model
    list_display = ('id', 'author', 'author_handle', 'post_type', 'visibility', 'likes_count', 'comments_count', 'created_at')
    list_filter = ('post_type', 'visibility')
    search_fields = ('author__email', 'author_handle', 'content')
    date_hierarchy = 'created_at'

@admin.register(CommunityComment)
class CommunityCommentAdmin(admin.ModelAdmin):  # Admin configuration for CommunityComment model
    list_display = ('id', 'post', 'author', 'likes_count', 'is_edited', 'created_at')
    search_fields = ('author__email', 'content')
    date_hierarchy = 'created_at'

@admin.register(CommunityConnection)
class CommunityConnectionAdmin(admin.ModelAdmin):  # Admin configuration for CommunityConnection model
    list_display = ('id', 'from_participant', 'to_participant', 'connection_type', 'status', 'created_at')
    list_filter = ('connection_type', 'status')
    search_fields = ('from_participant__email', 'to_participant__email')

@admin.register(CommunityMessage)
class CommunityMessageAdmin(admin.ModelAdmin):  # Admin configuration for CommunityMessage model
    list_display = ('id', 'sender', 'recipient', 'message_type', 'status', 'created_at')
    list_filter = ('message_type', 'status')
    search_fields = ('sender__email', 'recipient__email')
    date_hierarchy = 'created_at'

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):  # Admin configuration for Notification model
    list_display = ('id', 'recipient', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('recipient__email', 'title')
    date_hierarchy = 'created_at'

@admin.register(RideRequest)
class RideRequestAdmin(admin.ModelAdmin):  # Admin configuration for RideRequest model
    list_display = ('id', 'patient', 'provider', 'ride_type', 'status', 'scheduled_time', 'fare')
    list_filter = ('ride_type', 'status')
    search_fields = ('patient__email', 'provider__email')
    date_hierarchy = 'scheduled_time'
