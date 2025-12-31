"""
Workflow chaining and composition utilities.
"""
from typing import List, Optional
from django.conf import settings


def should_auto_chain(job_type: str) -> bool:
    """Determine if a job type should trigger follow-up jobs."""
    auto_chain = getattr(settings, 'WORKFLOW_AUTO_CHAIN', True)
    return auto_chain


def get_follow_up_jobs(job_type: str) -> List[tuple]:
    """
    Get follow-up job types for automatic chaining.
    
    Returns list of (job_type, payload_builder) tuples.
    """
    chains = {
        'worklog.analyze': [
            ('skills.extract', lambda payload: {'user_id': payload.get('user_id')}),
            ('report.generate', lambda payload: {'user_id': payload.get('user_id'), 'kind': 'status'}),
        ],
    }
    
    return chains.get(job_type, [])


def enqueue_follow_ups(ctx, job_type: str, original_payload: dict, parent_job):
    """Enqueue follow-up jobs based on workflow rules."""
    if not should_auto_chain(job_type):
        return
    
    from apps.jobs.dispatcher import enqueue
    from apps.observability.services import log_event
    
    for follow_up_type, payload_builder in get_follow_up_jobs(job_type):
        payload = payload_builder(original_payload)
        
        job = enqueue(
            job_type=follow_up_type,
            payload=payload,
            trigger='system',
            user=parent_job.user,
            parent_job=parent_job
        )
        
        log_event(
            ctx,
            f"Enqueued follow-up job: {follow_up_type}",
            level='info',
            source='workflow',
            follow_up_job_id=str(job.id)
        )
