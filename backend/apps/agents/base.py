"""
Base agent class.
"""
from typing import Any
from apps.observability.services import log_event
from apps.observability.context import ExecutionContext


class BaseAgent:
    """Base class for all agents."""
    
    def __init__(self):
        self.name = self.__class__.__name__
    
    def _log(self, ctx: ExecutionContext, message: str, **data):
        """Log an agent event."""
        log_event(ctx, message, level='info', source='agent', agent=self.name, **data)
    
    def _call_llm(self, ctx: ExecutionContext, prompt: str, **kwargs) -> dict:
        """Call LLM with logging."""
        from apps.llm.client import get_llm_client
        
        self._log(ctx, f"Calling LLM", prompt_length=len(prompt))
        
        client = get_llm_client()
        response = client.complete(prompt, **kwargs)
        
        log_event(
            ctx,
            "LLM response received",
            level='info',
            source='llm',
            response_length=len(str(response)),
            model=client.model_name
        )
        
        return response
