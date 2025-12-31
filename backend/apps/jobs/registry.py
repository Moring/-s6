"""
Job type registry - maps job types to workflow callables.
"""
from typing import Callable, Dict

# Registry of job_type -> workflow function
_REGISTRY: Dict[str, Callable] = {}


def register(job_type: str):
    """Decorator to register a workflow function."""
    def decorator(func: Callable):
        _REGISTRY[job_type] = func
        return func
    return decorator


def get_workflow(job_type: str) -> Callable:
    """Get workflow function for a job type."""
    if job_type not in _REGISTRY:
        raise ValueError(f"Unknown job type: {job_type}")
    return _REGISTRY[job_type]


def list_job_types():
    """List all registered job types."""
    return list(_REGISTRY.keys())


# Import workflows to register them
def _load_workflows():
    """Load all workflow modules to trigger registration."""
    try:
        from apps.orchestration.workflows import worklog_analyze
        from apps.orchestration.workflows import skills_extract
        from apps.orchestration.workflows import report_generate
        from apps.orchestration.workflows import resume_refresh
        from apps.orchestration.workflows import metrics_compute
        from apps.orchestration.workflows import reward_evaluate
    except ImportError:
        pass  # Workflows may not be available yet during initial setup


_load_workflows()
