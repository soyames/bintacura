import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Notification


class NotificationConsumer(AsyncWebsocketConsumer):  # NotificationConsumer class implementation
    async def connect(self):  # Connect
        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            self.user_id = str(self.scope["user"].id)
            self.room_group_name = f"user_{self.user_id}"

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)

            await self.accept()

            unread_count = await self.get_unread_count()
            await self.send(
                text_data=json.dumps(
                    {"type": "connection_established", "unread_count": unread_count}
                )
            )

    async def disconnect(self, close_code):  # Disconnect
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    async def receive(self, text_data):  # Receive
        data = json.loads(text_data)
        message_type = data.get("type")

        if message_type == "mark_read":
            notification_id = data.get("notification_id")
            await self.mark_notification_read(notification_id)
        elif message_type == "get_unread_count":
            count = await self.get_unread_count()
            await self.send(
                text_data=json.dumps({"type": "unread_count", "count": count})
            )

    async def notification_message(self, event):  # Notification message
        await self.send(
            text_data=json.dumps(
                {"type": "notification", "notification": event["notification"]}
            )
        )

    @database_sync_to_async
    def get_unread_count(self):  # Get unread count
        return Notification.objects.filter(
            recipient_id=self.user_id, is_read=False
        ).count()

    @database_sync_to_async
    def mark_notification_read(self, notification_id):  # Mark notification read
        from django.utils import timezone

        Notification.objects.filter(
            id=notification_id, recipient_id=self.user_id
        ).update(is_read=True, read_at=timezone.now())
