"""
Resume generation agent.
"""
from .base import BaseAgent


class ResumeAgent(BaseAgent):
    """Agent for generating resumes."""
    
    def generate_resume(self, ctx, user) -> dict:
        """
        Generate a resume.
        
        Returns:
            resume content as structured dict
        """
        self._log(ctx, "Generating resume")
        
        # Gather all relevant data
        data = self._gather_resume_data(user)
        
        # Call LLM
        prompt = self._build_resume_prompt(data)
        response = self._call_llm(ctx, prompt)
        
        # Structure resume (MVP stub)
        content = {
            'name': user.get_full_name() if user else 'User',
            'sections': [
                {
                    'title': 'Professional Summary',
                    'items': response.get('summary', [
                        'Experienced software engineer with expertise in Python and Django'
                    ])
                },
                {
                    'title': 'Skills',
                    'items': response.get('skills', [
                        'Python, Django, REST APIs',
                        'PostgreSQL, Redis',
                        'Distributed systems'
                    ])
                },
                {
                    'title': 'Experience',
                    'items': response.get('experience', [
                        'Built scalable backend systems',
                        'Implemented async job processing'
                    ])
                }
            ]
        }
        
        self._log(ctx, "Resume generated", sections_count=len(content['sections']))
        
        return content
    
    def _gather_resume_data(self, user) -> dict:
        """Gather all data for resume."""
        from apps.worklog.selectors import list_worklogs
        from apps.skills.selectors import list_skills
        
        return {
            'worklogs': list_worklogs(user=user, limit=100),
            'skills': list_skills(user=user),
        }
    
    def _build_resume_prompt(self, data: dict) -> str:
        """Build resume prompt."""
        # Use generic report prompt for MVP
        from apps.llm.prompts import get_report_prompt
        return get_report_prompt('resume', data)
