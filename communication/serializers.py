from rest_framework import serializers
from .models import *

class CommunityPostSerializer(serializers.ModelSerializer):  # Serializer for CommunityPost data
    author_name = serializers.SerializerMethodField()
    user_reaction = serializers.SerializerMethodField()

    class Meta:  # Meta class implementation
        model = CommunityPost
        fields = [
            'id', 'author', 'author_handle', 'author_name', 'content',
            'image', 'image_url', 'post_type', 'visibility', 'group',
            'likes_count', 'dislikes_count', 'comments_count', 'shares_count',
            'hashtags', 'mentions', 'is_pinned', 'is_edited', 'edited_at',
            'created_at', 'updated_at', 'user_reaction'
        ]
        read_only_fields = ['author', 'author_handle', 'likes_count', 'dislikes_count',
                           'comments_count', 'shares_count', 'created_at', 'updated_at']

    def get_author_name(self, obj) -> str:  # Get author name
        return obj.author.full_name if hasattr(obj.author, 'full_name') else 'Unknown'

    def get_user_reaction(self, obj) -> str:  # Get user reaction
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            reaction = PostLike.objects.filter(post=obj, participant=request.user).first()
            return reaction.reaction_type if reaction else None
        return None

class CommentSerializer(serializers.ModelSerializer):  # Serializer for Comment data
    author_name = serializers.SerializerMethodField()
    replies_count = serializers.SerializerMethodField()
    user_liked = serializers.SerializerMethodField()

    class Meta:  # Meta class implementation
        model = CommunityComment
        fields = [
            'id', 'post', 'author', 'author_name', 'content', 'parent_comment',
            'likes_count', 'is_edited', 'edited_at', 'created_at', 'updated_at',
            'replies_count', 'user_liked'
        ]
        read_only_fields = ['author', 'likes_count', 'created_at', 'updated_at']

    def get_author_name(self, obj) -> str:  # Get author name
        return obj.author.full_name if hasattr(obj.author, 'full_name') else 'Unknown'

    def get_replies_count(self, obj) -> int:  # Get replies count
        return obj.replies.count()

    def get_user_liked(self, obj) -> bool:  # Get user liked
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return CommentLike.objects.filter(comment=obj, participant=request.user).exists()
        return False

class PostLikeSerializer(serializers.ModelSerializer):  # Serializer for PostLike data
    class Meta:  # Meta class implementation
        model = PostLike
        fields = ['id', 'post', 'participant', 'reaction_type', 'created_at']
        read_only_fields = ['participant', 'created_at']

class CommunityGroupSerializer(serializers.ModelSerializer):  # Serializer for CommunityGroup data
    is_member = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()

    class Meta:  # Meta class implementation
        model = CommunityGroup
        fields = [
            'id', 'name', 'slug', 'description', 'cover_image', 'privacy',
            'creator', 'members_count', 'posts_count', 'created_at', 'updated_at',
            'is_member', 'user_role'
        ]
        read_only_fields = ['creator', 'members_count', 'posts_count', 'created_at', 'updated_at']

    def get_is_member(self, obj) -> bool:  # Get is member
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return GroupMembership.objects.filter(
                group=obj, participant=request.user, status='approved'
            ).exists()
        return False

    def get_user_role(self, obj) -> str:  # Get user role
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            membership = GroupMembership.objects.filter(
                group=obj, participant=request.user, status='approved'
            ).first()
            return membership.role if membership else None
        return None

class GroupMembershipSerializer(serializers.ModelSerializer):  # Serializer for GroupMembership data
    participant_name = serializers.SerializerMethodField()

    class Meta:  # Meta class implementation
        model = GroupMembership
        fields = ['id', 'group', 'participant', 'participant_name', 'role', 'status', 'joined_at']
        read_only_fields = ['joined_at']

    def get_participant_name(self, obj) -> str:  # Get participant name
        return obj.participant.full_name if hasattr(obj.participant, 'full_name') else 'Unknown'

class OnlineStatusSerializer(serializers.ModelSerializer):  # Serializer for OnlineStatus data
    participant_name = serializers.SerializerMethodField()

    class Meta:  # Meta class implementation
        model = OnlineStatus
        fields = ['participant', 'participant_name', 'is_online', 'last_seen', 'last_activity']
        read_only_fields = ['last_seen', 'last_activity']

    def get_participant_name(self, obj) -> str:  # Get participant name
        return obj.participant.full_name if hasattr(obj.participant, 'full_name') else 'Unknown'

class NotificationSerializer(serializers.ModelSerializer):  # Serializer for Notification data
    class Meta:  # Meta class implementation
        model = Notification
        fields = '__all__'
