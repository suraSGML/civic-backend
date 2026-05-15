"""Duplicate detection utilities for reports."""
from difflib import SequenceMatcher
from django.db.models import Q
from .models import Report, ReportStatus


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts (0-1)."""
    if not text1 or not text2:
        return 0.0
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def find_potential_duplicates(report: Report, threshold: float = 0.65, limit: int = 5):
    """
    Find potentially duplicate reports based on location and content similarity.
    
    Args:
        report: The report to find duplicates for
        threshold: Similarity threshold (0-1), default 0.65
        limit: Maximum number of results to return
    
    Returns:
        List of dicts with 'report' and 'similarity' score
    """
    # Search for reports in same area with similar category
    # Using approximate bounding box (0.01 degrees ≈ 1.1 km)
    delta = 0.01
    
    similar_reports = Report.objects.filter(
        latitude__range=(
            float(report.latitude) - delta,
            float(report.latitude) + delta
        ),
        longitude__range=(
            float(report.longitude) - delta,
            float(report.longitude) + delta
        ),
        category=report.category,
        status__in=[
            ReportStatus.PENDING,
            ReportStatus.UNDER_REVIEW,
            ReportStatus.ASSIGNED,
        ],
    ).exclude(id=report.id).select_related('reporter')
    
    results = []
    
    for other in similar_reports:
        # Calculate similarity scores
        title_sim = calculate_similarity(report.title, other.title)
        desc_sim = calculate_similarity(report.description, other.description)
        
        # Weighted average (title more important)
        avg_sim = (title_sim * 0.4) + (desc_sim * 0.6)
        
        if avg_sim >= threshold:
            results.append({
                'id': other.id,
                'title': other.title,
                'description': other.description,
                'category': other.category,
                'status': other.status,
                'status_display': other.get_status_display(),
                'created_at': other.created_at.isoformat(),
                'reporter_name': other.reporter.get_full_name() if other.reporter else 'Anonymous',
                'similarity': round(avg_sim * 100, 1),
                'upvote_count': other.upvote_count,
            })
    
    # Sort by similarity descending
    results.sort(key=lambda x: x['similarity'], reverse=True)
    
    return results[:limit]


def merge_reports(primary_id: int, duplicate_id: int, user=None):
    """
    Merge a duplicate report into the primary report.
    
    Args:
        primary_id: ID of the primary report (keeps this one)
        duplicate_id: ID of the duplicate report (will be marked as duplicate)
        user: User performing the merge
    
    Returns:
        Dict with merge result
    """
    try:
        primary = Report.objects.get(id=primary_id)
        duplicate = Report.objects.get(id=duplicate_id)
    except Report.DoesNotExist:
        return {'success': False, 'error': 'Report not found'}
    
    # Mark duplicate as duplicate status
    old_status = duplicate.status
    duplicate.status = ReportStatus.DUPLICATE
    duplicate.duplicate_of = primary
    duplicate.save()
    
    # Merge upvotes
    primary.upvote_count += duplicate.upvote_count
    primary.save()
    
    # Create status history entry
    from .models import StatusHistory
    StatusHistory.objects.create(
        report=duplicate,
        changed_by=user,
        old_status=old_status,
        new_status=ReportStatus.DUPLICATE,
        notes=f'Merged with report #{primary_id}',
    )
    
    return {
        'success': True,
        'primary_id': primary_id,
        'duplicate_id': duplicate_id,
        'merged_upvotes': duplicate.upvote_count,
    }


def link_reports(report_id_1: int, report_id_2: int):
    """
    Link two related reports without marking one as duplicate.
    
    Args:
        report_id_1: First report ID
        report_id_2: Second report ID
    
    Returns:
        Dict with link result
    """
    try:
        report1 = Report.objects.get(id=report_id_1)
        report2 = Report.objects.get(id=report_id_2)
    except Report.DoesNotExist:
        return {'success': False, 'error': 'Report not found'}
    
    # Create bidirectional link
    if not report1.related_reports.filter(id=report_id_2).exists():
        report1.related_reports.add(report2)
    
    if not report2.related_reports.filter(id=report_id_1).exists():
        report2.related_reports.add(report1)
    
    return {
        'success': True,
        'report_1': report_id_1,
        'report_2': report_id_2,
        'linked': True,
    }
