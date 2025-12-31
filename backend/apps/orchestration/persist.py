"""
Shared persistence utilities for workflows.
"""
from apps.observability.services import log_event


def persist_result(ctx, result: dict, description: str):
    """
    Persist a workflow result with logging.
    
    Args:
        ctx: Execution context
        result: Result data to persist
        description: Human-readable description
    """
    log_event(
        ctx,
        f"Persisted result: {description}",
        level='info',
        source='workflow',
        result_size=len(str(result))
    )
    
    return result
