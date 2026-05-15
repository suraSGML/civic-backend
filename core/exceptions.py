"""
Custom exception handlers for DRF.
"""
import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response

logger = logging.getLogger('civic_system')


def custom_exception_handler(exc, context):
    """
    Custom exception handler that logs errors and returns detailed messages.
    """
    # Log the exception
    logger.error(f"Exception in {context['view'].__class__.__name__}: {str(exc)}", exc_info=True)
    
    # Call the default exception handler first
    response = exception_handler(exc, context)
    
    # If no response from DRF handler, create a 500 response
    if response is None:
        return Response(
            {'error': f'Internal server error: {str(exc)}'},
            status=500
        )
    
    return response
