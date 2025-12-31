"""
Skills extraction workflow.
"""
from apps.jobs.registry import register
from apps.observability.services import log_event
from apps.agents.skill_agent import SkillAgent
from apps.orchestration.persist import persist_result


@register('skills.extract')
def extract_skills(ctx, payload: dict) -> dict:
    """
    Extract skills from work logs.
    
    Payload:
        user_id: User ID (optional)
        window_days: Number of days to analyze (default 30)
    
    Returns:
        skills: list of extracted skills
        evidence: list of evidence records
    """
    from apps.worklog.selectors import list_worklogs
    from apps.skills.services import create_skill, add_skill_evidence
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    user_id = payload.get('user_id')
    window_days = payload.get('window_days', 30)
    
    user = User.objects.get(id=user_id) if user_id else None
    
    log_event(ctx, f"Extracting skills for user {user_id}", source='workflow')
    
    # Get recent work logs
    worklogs = list_worklogs(user=user, limit=100)
    
    # Run agent
    agent = SkillAgent()
    extracted_skills = agent.extract_skills(ctx, worklogs)
    
    # Persist skills
    created_skills = []
    for skill_data in extracted_skills:
        skill = create_skill(
            name=skill_data['name'],
            user=user,
            confidence=skill_data.get('confidence', 0.5),
            level=skill_data.get('level')
        )
        
        # Add evidence
        for evidence_data in skill_data.get('evidence', []):
            add_skill_evidence(
                skill=skill,
                source_type='worklog',
                source_id=evidence_data['worklog_id'],
                excerpt=evidence_data.get('excerpt', ''),
                weight=evidence_data.get('weight', 1.0)
            )
        
        created_skills.append({
            'id': skill.id,
            'name': skill.name,
            'normalized': skill.normalized
        })
    
    result = {
        'user_id': user_id,
        'skills_count': len(created_skills),
        'skills': created_skills
    }
    
    return persist_result(ctx, result, f"extracted {len(created_skills)} skills")
