"""
Notification service helpers for email and SMS.
"""
import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger('civic_system')


def send_email_notification(to_email: str, subject: str, message: str):
    """Send an email notification."""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
        logger.info(f'Email sent to {to_email}: {subject}')
    except Exception as e:
        logger.error(f'Failed to send email to {to_email}: {e}')


def send_sms_notification(phone: str, message: str):
    """
    Send SMS via Africa's Talking API.
    Falls back to logging if not configured.
    """
    try:
        import africastalking
        africastalking.initialize(
            username=settings.AT_USERNAME,
            api_key=settings.AT_API_KEY,
        )
        sms = africastalking.SMS
        response = sms.send(message, [phone])
        logger.info(f'SMS sent to {phone}: {response}')
    except ImportError:
        logger.warning(f'africastalking not installed. SMS to {phone}: {message}')
    except Exception as e:
        logger.error(f'Failed to send SMS to {phone}: {e}')


def create_in_app_notification(recipient, notification_type, title, message, data=None):
    """Create an in-app notification and push via WebSocket."""
    from .models import Notification
    notification = Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        data=data or {},
    )
    # Push via WebSocket
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{recipient.id}',
            {
                'type': 'notification_message',
                'notification': {
                    'id': notification.id,
                    'type': notification_type,
                    'title': title,
                    'message': message,
                    'data': data or {},
                },
            }
        )
    except Exception as e:
        logger.warning(f'WebSocket push failed: {e}')
    return notification
