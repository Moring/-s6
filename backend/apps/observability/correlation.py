"""
Correlation ID middleware for distributed tracing.
Ensures requests, jobs, and DAG runs share trace context.
"""
import uuid
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class CorrelationIDMiddleware(MiddlewareMixin):
    """
    Add correlation ID to all requests for distributed tracing.
    """
    
    def process_request(self, request):
        # Get correlation ID from header or generate new one
        correlation_id = request.headers.get('X-Correlation-ID')
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Store on request
        request.correlation_id = correlation_id
        
        # Add to thread-local for logging
        logger_adapter = logging.LoggerAdapter(
            logger,
            {'correlation_id': correlation_id}
        )
        request.logger = logger_adapter
        
        return None
    
    def process_response(self, request, response):
        # Add correlation ID to response headers
        if hasattr(request, 'correlation_id'):
            response['X-Correlation-ID'] = request.correlation_id
        
        return response


def get_correlation_id(request=None) -> str:
    """
    Get correlation ID from request or generate new one.
    
    Args:
        request: Django request object (optional)
    
    Returns:
        Correlation ID string
    """
    if request and hasattr(request, 'correlation_id'):
        return request.correlation_id
    return str(uuid.uuid4())


class CorrelationIDFilter(logging.Filter):
    """
    Logging filter to add correlation ID to log records.
    """
    
    def filter(self, record):
        # Add correlation_id if not already present
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = 'n/a'
        return True
