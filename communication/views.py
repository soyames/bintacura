from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q, F
from .models import *
from .serializers import *


class CommunityPostViewSet(viewsets.ModelViewSet):  # View for CommunityPostSet operations
    serializer_class = CommunityPostSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):  # Get queryset
        queryset = CommunityPost.objects.filter(visibility="public").order_by("-created_at")
        group_id = self.request.query_params.get('group', None)
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        return queryset

    def get_serializer_context(self):  # Get serializer context
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):  # Perform create
        # Automatically set the author and author_handle
        participant = self.request.user
        author_handle = getattr(participant, 'username', None) or getattr(participant, 'email', '').split('@')[0]

        serializer.save(
            author=participant,
            author_handle=author_handle,
            visibility='public'  # Ensure posts are public by default
        )

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):  # Like
        post = self.get_object()
        participant = request.user

        # Remove any existing reaction
        PostLike.objects.filter(post=post, participant=participant).delete()

        # Add new like
        PostLike.objects.create(post=post, participant=participant, reaction_type='like')

        # Update counts
        post.likes_count = PostLike.objects.filter(post=post, reaction_type='like').count()
        post.dislikes_count = PostLike.objects.filter(post=post, reaction_type='dislike').count()
        post.save()

        return Response({
            'status': 'liked',
            'likes_count': post.likes_count,
            'dislikes_count': post.dislikes_count
        })

    @action(detail=True, methods=['post'])
    def dislike(self, request, pk=None):  # Dislike
        post = self.get_object()
        participant = request.user

        # Remove any existing reaction
        PostLike.objects.filter(post=post, participant=participant).delete()

        # Add new dislike
        PostLike.objects.create(post=post, participant=participant, reaction_type='dislike')

        # Update counts
        post.likes_count = PostLike.objects.filter(post=post, reaction_type='like').count()
        post.dislikes_count = PostLike.objects.filter(post=post, reaction_type='dislike').count()
        post.save()

        return Response({
            'status': 'disliked',
            'likes_count': post.likes_count,
            'dislikes_count': post.dislikes_count
        })

    @action(detail=True, methods=['post'])
    def unlike(self, request, pk=None):  # Unlike
        post = self.get_object()
        participant = request.user

        # Remove reaction
        PostLike.objects.filter(post=post, participant=participant).delete()

        # Update counts
        post.likes_count = PostLike.objects.filter(post=post, reaction_type='like').count()
        post.dislikes_count = PostLike.objects.filter(post=post, reaction_type='dislike').count()
        post.save()

        return Response({
            'status': 'unliked',
            'likes_count': post.likes_count,
            'dislikes_count': post.dislikes_count
        })

    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):  # Comments
        post = self.get_object()
        comments = CommunityComment.objects.filter(post=post, parent_comment=None)
        serializer = CommentSerializer(comments, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def comment(self, request, pk=None):  # Comment
        post = self.get_object()
        content = request.data.get('content')
        parent_id = request.data.get('parent_comment')

        if not content:
            return Response({'error': 'Content is required'}, status=status.HTTP_400_BAD_REQUEST)

        parent_comment = None
        if parent_id:
            try:
                parent_comment = CommunityComment.objects.get(id=parent_id)
            except CommunityComment.DoesNotExist:
                pass

        comment = CommunityComment.objects.create(
            post=post,
            author=request.user,
            content=content,
            parent_comment=parent_comment
        )

        # Update comment count
        post.comments_count = CommunityComment.objects.filter(post=post).count()
        post.save()

        serializer = CommentSerializer(comment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CommentViewSet(viewsets.ModelViewSet):  # View for CommentSet operations
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        return CommunityComment.objects.all()

    def get_serializer_context(self):  # Get serializer context
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):  # Perform create
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):  # Like
        comment = self.get_object()
        participant = request.user

        # Toggle like
        like, created = CommentLike.objects.get_or_create(comment=comment, participant=participant)
        if not created:
            like.delete()
            liked = False
        else:
            liked = True

        # Update count
        comment.likes_count = CommentLike.objects.filter(comment=comment).count()
        comment.save()

        return Response({
            'status': 'liked' if liked else 'unliked',
            'likes_count': comment.likes_count
        })

    @action(detail=True, methods=['get'])
    def replies(self, request, pk=None):  # Replies
        comment = self.get_object()
        replies = comment.replies.all()
        serializer = self.get_serializer(replies, many=True)
        return Response(serializer.data)


class CommunityGroupViewSet(viewsets.ModelViewSet):  # View for CommunityGroupSet operations
    serializer_class = CommunityGroupSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return CommunityGroup.objects.none()
        participant = self.request.user
        # Show public groups and groups user is a member of
        return CommunityGroup.objects.filter(
            Q(privacy='public') | Q(memberships__participant=participant, memberships__status='approved')
        ).distinct()

    def get_serializer_context(self):  # Get serializer context
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):  # Perform create
        group = serializer.save(creator=self.request.user)
        # Automatically add creator as admin member
        GroupMembership.objects.create(
            group=group,
            participant=self.request.user,
            role='admin',
            status='approved'
        )
        group.members_count = 1
        group.save()

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):  # Join
        group = self.get_object()
        participant = request.user

        # Check if already a member
        membership = GroupMembership.objects.filter(group=group, participant=participant).first()
        if membership:
            if membership.status == 'approved':
                return Response({'error': 'Already a member'}, status=status.HTTP_400_BAD_REQUEST)
            elif membership.status == 'pending':
                return Response({'error': 'Request pending'}, status=status.HTTP_400_BAD_REQUEST)

        # Create membership
        status_val = 'approved' if group.privacy == 'public' else 'pending'
        GroupMembership.objects.create(
            group=group,
            participant=participant,
            role='member',
            status=status_val
        )

        if status_val == 'approved':
            group.members_count = GroupMembership.objects.filter(
                group=group, status='approved'
            ).count()
            group.save()

        return Response({'status': status_val})

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):  # Leave
        group = self.get_object()
        participant = request.user

        # Can't leave if creator
        if group.creator == participant:
            return Response({'error': 'Creator cannot leave group'}, status=status.HTTP_400_BAD_REQUEST)

        # Delete membership
        GroupMembership.objects.filter(group=group, participant=participant).delete()

        # Update count
        group.members_count = GroupMembership.objects.filter(
            group=group, status='approved'
        ).count()
        group.save()

        return Response({'status': 'left'})

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):  # Members
        group = self.get_object()
        memberships = GroupMembership.objects.filter(group=group, status='approved')
        serializer = GroupMembershipSerializer(memberships, many=True)
        return Response(serializer.data)


@extend_schema(
    responses={200: OnlineStatusSerializer(many=True)},
    description="Get list of currently online users"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def online_users(request):
    """Get list of online users"""
    # Update current user's online status
    online_status, created = OnlineStatus.objects.get_or_create(participant=request.user)
    online_status.is_online = True
    online_status.last_activity = timezone.now()
    online_status.save()

    # Get users online in last 5 minutes
    cutoff_time = timezone.now() - timezone.timedelta(minutes=5)
    online_users = OnlineStatus.objects.filter(
        is_online=True,
        last_activity__gte=cutoff_time
    ).select_related('participant')

    serializer = OnlineStatusSerializer(online_users, many=True)
    return Response({
        'count': online_users.count(),
        'users': serializer.data
    })


@extend_schema(
    responses={200: dict},
    description="Update participant's last activity timestamp"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_activity(request):
    """Update user's last activity timestamp"""
    online_status, created = OnlineStatus.objects.get_or_create(participant=request.user)
    online_status.is_online = True
    online_status.last_activity = timezone.now()
    online_status.save()
    return Response({'status': 'updated'})


@extend_schema(
    responses={200: dict},
    description="Mark participant as offline"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def go_offline(request):
    """Mark user as offline"""
    try:
        online_status = OnlineStatus.objects.get(participant=request.user)
        online_status.is_online = False
        online_status.last_seen = timezone.now()
        online_status.save()
    except OnlineStatus.DoesNotExist:
        pass
    return Response({'status': 'offline'})


class NotificationViewSet(viewsets.ModelViewSet):  # View for NotificationSet operations
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()
        participant = self.request.user
        return Notification.objects.filter(recipient=participant)

    @action(detail=False, methods=["get"])
    def unread(self, request):  # Unread
        notifications = self.get_queryset().filter(is_read=False)
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def unread_count(self, request):  # Unread count
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"count": count})

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):  # Mark read
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        return Response({"status": "notification marked as read"})

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):  # Mark all read
        self.get_queryset().filter(is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return Response({"status": "all notifications marked as read"})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unread_count(request):  # Get unread count
    participant = request.user
    count = Notification.objects.filter(recipient=participant, is_read=False).count()
    return Response({'unread_count': count})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request):  # Mark notification read
    notification_id = request.data.get('notification_id')
    participant = request.user
    Notification.objects.filter(id=notification_id, recipient=participant).update(
        is_read=True, read_at=timezone.now()
    )
    return Response({'status': 'success'})


@extend_schema(
    responses={200: dict},
    description="Proxy endpoint for AI chat - redirects to AI app"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_chat_proxy(request):
    """Proxy endpoint for AI chat - redirects to AI app"""
    from ai.views import AIChatAPIView
    view = AIChatAPIView.as_view()
    return view(request._request)
