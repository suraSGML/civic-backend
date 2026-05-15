"""
Celery tasks for sending notifications.
Handles email, SMS, and in-app notifications.
"""
from celery import shared_task
import logging

logger = logging.getLogger('civic_system')


@shared_task(bind=True, max_retries=3)
def send_report_notification(self, report_id, event_type):
    """Send notifications when a report is created or updated."""
    try:
        from reports.models import Report
        from accounts.models import UserRole
        from .models import Notification, NotificationType
        from .services import send_email_notification, send_sms_notification

        report = Report.objects.select_related('reporter').get(pk=report_id)

        if event_type == 'new_report':
            # Notify authorities
            from accounts.models import User
            authorities = User.objects.filter(
                role__in=[UserRole.AUTHORITY, UserRole.SUPER_ADMIN],
                is_active=True,
            )
            for authority in authorities:
                Notification.objects.create(
                    recipient=authority,
                    notification_type=NotificationType.REPORT_SUBMITTED,
                    title=f'New Report: {report.title}',
                    message=f'A new {report.get_severity_display()} severity report has been submitted.',
                    data={'report_id': report.id, 'category': report.category},
                )

            # Notify reporter
            if report.reporter and report.reporter.notify_email:
                send_email_notification(
                    to_email=report.reporter.email,
                    subject='Report Submitted Successfully',
                    message=f'Your report "{report.title}" has been received and is under review.',
                )

        elif event_type == 'status_update':
            if report.reporter:
                Notification.objects.create(
                    recipient=report.reporter,
                    notification_type=NotificationType.REPORT_STATUS_UPDATE,
                    title=f'Report Update: {report.title}',
                    message=f'Your report status has been updated to: {report.get_status_display()}',
                    data={'report_id': report.id, 'status': report.status},
                )
                if report.reporter.notify_sms and report.reporter.phone:
                    send_sms_notification(
                        phone=str(report.reporter.phone),
                        message=f'Civic System: Your report "{report.title[:30]}" is now {report.get_status_display()}.',
                    )

    except Exception as exc:
        logger.error(f'Error sending report notification: {exc}')
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_assignment_notification(self, assignment_id):
    """Notify worker of new assignment."""
    try:
        from assignments.models import Assignment
        from .models import Notification, NotificationType
        from .services import send_email_notification, send_sms_notification

        assignment = Assignment.objects.select_related('worker', 'report').get(pk=assignment_id)
        worker = assignment.worker

        if worker:
            Notification.objects.create(
                recipient=worker,
                notification_type=NotificationType.ASSIGNMENT_RECEIVED,
                title=f'New Assignment: {assignment.report.title}',
                message=f'You have been assigned to resolve: {assignment.report.title}',
                data={
                    'assignment_id': assignment.id,
                    'report_id': assignment.report.id,
                },
            )
            if worker.notify_email:
                send_email_notification(
                    to_email=worker.email,
                    subject='New Task Assignment',
                    message=f'You have been assigned to: {assignment.report.title}\n\nInstructions: {assignment.instructions}',
                )
            if worker.notify_sms and worker.phone:
                send_sms_notification(
                    phone=str(worker.phone),
                    message=f'Civic System: New assignment - {assignment.report.title[:40]}',
                )

    except Exception as exc:
        logger.error(f'Error sending assignment notification: {exc}')
        raise self.retry(exc=exc, countdown=60)


@shared_task
def send_emergency_broadcast(report_id):
    """Broadcast emergency alert to all authorities and nearby workers."""
    try:
        from reports.models import Report
        from accounts.models import User, UserRole
        from .models import Notification, NotificationType
        from .services import send_sms_notification

        report = Report.objects.get(pk=report_id)
        responders = User.objects.filter(
            role__in=[UserRole.AUTHORITY, UserRole.SUPER_ADMIN, UserRole.FIELD_WORKER],
            is_active=True,
        )

        for responder in responders:
            Notification.objects.create(
                recipient=responder,
                notification_type=NotificationType.EMERGENCY_ALERT,
                title=f'🚨 EMERGENCY: {report.title}',
                message=f'Critical emergency reported at {report.address or "GPS coordinates"}. Immediate response required.',
                data={
                    'report_id': report.id,
                    'category': report.category,
                    'latitude': str(report.latitude),
                    'longitude': str(report.longitude),
                },
            )
            if responder.notify_sms and responder.phone:
                send_sms_notification(
                    phone=str(responder.phone),
                    message=f'🚨 EMERGENCY ALERT: {report.title} at {report.address or "see app"}. Respond immediately.',
                )

    except Exception as exc:
        logger.error(f'Error sending emergency broadcast: {exc}')
