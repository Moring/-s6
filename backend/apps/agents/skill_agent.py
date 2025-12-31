"""
Skill extraction agent.
"""
from .base import BaseAgent


class SkillAgent(BaseAgent):
    """Agent for extracting skills from work logs."""
    
    def extract_skills(self, ctx, worklogs) -> list:
        """
        Extract skills from work logs.
        
        Returns:
            skills: list of dicts with name, confidence, level, evidence
        """
        self._log(ctx, "Extracting skills", worklogs_count=len(worklogs))
        
        # Aggregate content
        content = "\n\n".join([wl.content for wl in worklogs[:10]])
        
        # Call LLM
        prompt = self._build_extraction_prompt(content)
        response = self._call_llm(ctx, prompt)
        
        # Parse response (MVP stub with deterministic output)
        skills = response.get('skills', [
            {
                'name': 'Python',
                'confidence': 0.9,
                'level': 'expert',
                'evidence': [{'worklog_id': wl.id, 'excerpt': 'Python development'} for wl in worklogs[:2]]
            },
            {
                'name': 'Django',
                'confidence': 0.85,
                'level': 'intermediate',
                'evidence': [{'worklog_id': wl.id, 'excerpt': 'Django REST framework'} for wl in worklogs[:2]]
            }
        ])
        
        self._log(ctx, "Skills extracted", skills_count=len(skills))
        
        return skills
    
    def _build_extraction_prompt(self, content: str) -> str:
        """Build extraction prompt."""
        from apps.llm.prompts import get_extraction_prompt
        return get_extraction_prompt(content)
