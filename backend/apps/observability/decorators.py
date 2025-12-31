"""
Decorators for observability instrumentation.
"""
import functools
import time
from .services import log_event


def trace_step(step_name: str, source: str = 'workflow'):
    """
    Decorator to trace a workflow step.
    
    Usage:
        @trace_step('extract_skills', source='agent')
        def extract_skills(ctx, worklog):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(ctx, *args, **kwargs):
            log_event(ctx, f"{step_name} started", level='info', source=source)
            start_time = time.time()
            
            try:
                result = func(ctx, *args, **kwargs)
                duration = time.time() - start_time
                log_event(
                    ctx,
                    f"{step_name} completed",
                    level='info',
                    source=source,
                    duration_seconds=duration
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                log_event(
                    ctx,
                    f"{step_name} failed: {str(e)}",
                    level='error',
                    source=source,
                    duration_seconds=duration,
                    error=str(e)
                )
                raise
        
        return wrapper
    return decorator
