"""
Utility functions for assignment management.
"""
from django.db.models import Count, Q, F, Case, When, IntegerField
from accounts.models import User, UserRole
from reports.models import Report


def get_assignment_suggestions(report, limit=5):
    """
    Get ranked list of suitable workers for a report.
    
    Ranking criteria:
    1. Active assignment count (prefer less busy workers)
    2. Specialization match (prefer specialized workers)
    3. Completion rate (prefer reliable workers)
    """
    workers = User.objects.filter(
        role=UserRole.FIELD_WORKER,
        is_active=True,
        is_banned=False,
    ).annotate(
        # Count active assignments
        active_count=Count(
            'assignments',
            filter=Q(assignments__status__in=['pending', 'accepted', 'in_progress'])
        ),
        # Calculate specialization match (0-100)
        specialization_match=Case(
            When(specialization__icontains=report.category, then=100),
            default=50,
            output_field=IntegerField(),
        ),
        # Calculate completion rate
        total_assignments=Count('assignments'),
        completed_assignments=Count(
            'assignments',
            filter=Q(assignments__status='completed')
        ),
    ).order_by(
        'active_count',  # Prefer less busy workers
        '-specialization_match',  # Prefer specialized workers
        '-completed_assignments',  # Prefer reliable workers
    )

    suggestions = []
    for worker in workers[:limit]:
        completion_rate = (
            (worker.completed_assignments / worker.total_assignments * 100)
            if worker.total_assignments > 0
            else 0
        )
        
        suggestions.append({
            'worker_id': worker.id,
            'name': worker.get_full_name(),
            'email': worker.email,
            'phone': str(worker.phone) if worker.phone else None,
            'department': worker.department,
            'specialization': worker.specialization,
            'active_count': worker.active_count,
            'completion_rate': round(completion_rate, 1),
            'specialization_match': worker.specialization_match,
        })

    return suggestions


# Alias for backward compatibility
get_worker_suggestions = get_assignment_suggestions


def get_worker_performance_metrics(worker):
    """
    Get performance metrics for a worker.
    
    Returns:
        Dict with completion_rate, average_response_time, etc.
    """
    from assignments.models import Assignment
    
    assignments = Assignment.objects.filter(worker=worker)
    
    total = assignments.count()
    completed = assignments.filter(status='completed').count()
    in_progress = assignments.filter(status='in_progress').count()
    
    completion_rate = (completed / total * 100) if total > 0 else 0
    
    # Calculate average response time
    from django.db.models import Avg, F
    from django.utils import timezone
    from datetime import timedelta
    
    avg_response = assignments.filter(
        status='in_progress'
    ).aggregate(
        avg_time=Avg(F('updated_at') - F('created_at'))
    )['avg_time']
    
    avg_response_hours = (
        avg_response.total_seconds() / 3600
        if avg_response
        else 0
    )
    
    return {
        'total_assignments': total,
        'completed': completed,
        'in_progress': in_progress,
        'completion_rate': round(completion_rate, 1),
        'average_response_time_hours': round(avg_response_hours, 1),
    }
