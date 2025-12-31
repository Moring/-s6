"""
Report generation agent.
"""
from .base import BaseAgent


class ReportAgent(BaseAgent):
    """Agent for generating reports."""
    
    def generate_report(self, ctx, user, kind: str, window_days: int) -> dict:
        """
        Generate a report.
        
        Returns:
            report content as structured dict
        """
        self._log(ctx, f"Generating {kind} report", window_days=window_days)
        
        # Gather data
        data = self._gather_report_data(user, kind, window_days)
        
        # Call LLM
        prompt = self._build_report_prompt(kind, data)
        response = self._call_llm(ctx, prompt)
        
        # Structure content (MVP stub)
        content = {
            'sections': [
                {
                    'title': 'Completed This Week',
                    'items': response.get('completed', [
                        'Implemented job execution system',
                        'Added event logging and observability'
                    ])
                },
                {
                    'title': 'In Progress',
                    'items': response.get('in_progress', [
                        'Building API endpoints',
                        'Writing tests'
                    ])
                }
            ]
        }
        
        self._log(ctx, "Report generated", sections_count=len(content['sections']))
        
        return content
    
    def _gather_report_data(self, user, kind: str, window_days: int) -> dict:
        """Gather data for report."""
        from datetime import timedelta
        from django.utils import timezone
        from apps.worklog.selectors import list_worklogs
        
        cutoff = timezone.now() - timedelta(days=window_days)
        worklogs = list_worklogs(user=user, limit=50)
        
        return {
            'worklogs': [
                {
                    'date': str(wl.date),
                    'content': wl.content[:200]
                }
                for wl in worklogs
            ]
        }
    
    def _build_report_prompt(self, kind: str, data: dict) -> str:
        """Build report prompt."""
        from apps.llm.prompts import get_report_prompt
        return get_report_prompt(kind, data)
