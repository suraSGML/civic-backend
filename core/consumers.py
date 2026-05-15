"""
WebSocket consumers for real-time features.
- User notifications
- Live report updates
- Emergency broadcasts
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Personal notification channel for each authenticated user.
    Group name: user_{user_id}
    """
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return

        self.user_id = user.id
        self.group_name = f'user_{self.user_id}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send unread count on connect
        unread = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'unread_count': unread,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get('type') == 'mark_read':
            notification_id = data.get('notification_id')
            if notification_id:
                await self.mark_notification_read(notification_id)

    async def notification_message(self, event):
        """Receive notification from channel layer and forward to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification'],
        }))

    @database_sync_to_async
    def get_unread_count(self):
        from notifications.models import Notification
        return Notification.objects.filter(
            recipient_id=self.user_id, is_read=False
        ).count()

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        from notifications.models import Notification
        try:
            n = Notification.objects.get(pk=notification_id, recipient_id=self.user_id)
            n.mark_read()
        except Notification.DoesNotExist:
            pass


class ReportUpdatesConsumer(AsyncWebsocketConsumer):
    """
    Broadcast channel for live report updates.
    All authenticated users can subscribe.
    Group name: report_updates
    """
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return

        self.group_name = 'report_updates'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def report_update(self, event):
        """Forward report update to WebSocket client."""
        await self.send(text_data=json.dumps({
            'type': 'report_update',
            'report': event['report'],
        }))


class EmergencyConsumer(AsyncWebsocketConsumer):
    """
    Emergency broadcast channel for authorities and workers.
    Group name: emergency_alerts
    """
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return

        # Only authorities and workers get emergency alerts
        if user.role not in ['authority', 'super_admin', 'field_worker']:
            await self.close()
            return

        self.group_name = 'emergency_alerts'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def emergency_alert(self, event):
        await self.send(text_data=json.dumps({
            'type': 'emergency_alert',
            'alert': event['alert'],
        }))
