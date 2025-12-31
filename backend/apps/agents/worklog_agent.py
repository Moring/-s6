"""
Worklog analysis agent.
"""
from .base import BaseAgent


class WorklogAgent(BaseAgent):
    """Agent for analyzing work log entries."""
    
    def analyze(self, ctx, content: str) -> dict:
        """
        Analyze a work log entry.
        
        Returns:
            analysis: dict with extracted information
        """
        self._log(ctx, "Analyzing worklog", content_length=len(content))
        
        # Call LLM with worklog analysis prompt
        prompt = self._build_analysis_prompt(content)
        response = self._call_llm(ctx, prompt)
        
        # Parse response (for MVP, return structured stub)
        analysis = {
            'summary': response.get('summary', 'Work completed'),
            'key_activities': response.get('activities', ['Development', 'Testing']),
            'technologies': response.get('technologies', ['Python', 'Django']),
            'sentiment': response.get('sentiment', 'positive')
        }
        
        self._log(ctx, "Worklog analysis complete", activities_count=len(analysis['key_activities']))
        
        return analysis
    
    def _build_analysis_prompt(self, content: str) -> str:
        """Build analysis prompt."""
        from apps.llm.prompts import get_analysis_prompt
        return get_analysis_prompt(content)
