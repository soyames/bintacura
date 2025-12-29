from django.db import transaction
from .models import *

from django.db import transaction
from .models import *

class CommunityPostService:  # Service class for CommunityPost operations
    @staticmethod
    def create_communitypost(data):  # Create communitypost
        return CommunityPost.objects.create(**data)

    @staticmethod
    def get_communitypost(pk):  # Get communitypost
        try:
            return CommunityPost.objects.get(pk=pk)
        except CommunityPost.DoesNotExist:
            return None

    @staticmethod
    def update_communitypost(pk, data):  # Update communitypost
        obj = CommunityPostService.get_communitypost(pk)
        if obj:
            for key, value in data.items():
                setattr(obj, key, value)
            obj.save()
        return obj

    @staticmethod
    def delete_communitypost(pk):  # Delete communitypost
        obj = CommunityPostService.get_communitypost(pk)
        if obj:
            obj.delete()
            return True
        return False
from django.db import transaction
from .models import *

class NotificationService:  # Service class for Notification operations
    @staticmethod
    def create_notification(data):  # Create notification
        return Notification.objects.create(**data)

    @staticmethod
    def get_notification(pk):  # Get notification
        try:
            return Notification.objects.get(pk=pk)
        except Notification.DoesNotExist:
            return None

    @staticmethod
    def update_notification(pk, data):  # Update notification
        obj = NotificationService.get_notification(pk)
        if obj:
            for key, value in data.items():
                setattr(obj, key, value)
            obj.save()
        return obj

    @staticmethod
    def delete_notification(pk):  # Delete notification
        obj = NotificationService.get_notification(pk)
        if obj:
            obj.delete()
            return True
        return False
