"""
Execution context for tracking job execution.
"""
from dataclasses import dataclass
from typing import Optional
import uuid


@dataclass
class ExecutionContext:
    """Context passed through job execution."""
    job_id: str
    trace_id: str
    user_id: Optional[int] = None
    parent_job_id: Optional[str] = None
    
    @classmethod
    def from_job(cls, job):
        """Create context from a Job instance."""
        return cls(
            job_id=str(job.id),
            trace_id=str(uuid.uuid4()),
            user_id=job.user_id,
            parent_job_id=str(job.parent_job_id) if job.parent_job_id else None
        )
