"""
Custom exceptions for reports app.
"""
from rest_framework.exceptions import APIException
from rest_framework import status


class InvalidStatusTransition(APIException):
    """Raised when attempting an invalid status transition."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Invalid status transition.'
    default_code = 'invalid_status_transition'

    def __init__(self, from_status, to_status, detail=None):
        if detail is None:
            detail = f'Cannot transition from {from_status} to {to_status}'
        super().__init__(detail)


class ReportNotFound(APIException):
    """Raised when a report is not found."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'Report not found.'
    default_code = 'report_not_found'


class UnauthorizedStatusUpdate(APIException):
    """Raised when user is not authorized to update report status."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Only authorities can update report status.'
    default_code = 'unauthorized_status_update'


class InvalidBulkOperation(APIException):
    """Raised when bulk operation parameters are invalid."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Invalid bulk operation parameters.'
    default_code = 'invalid_bulk_operation'
