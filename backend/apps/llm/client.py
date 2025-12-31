"""
LLM client factory and interface.
"""
from django.conf import settings
from typing import Protocol


class LLMProvider(Protocol):
    """LLM provider interface."""
    
    model_name: str
    
    def complete(self, prompt: str, **kwargs) -> dict:
        """Complete a prompt and return structured response."""
        ...


def get_llm_client() -> LLMProvider:
    """Get configured LLM client."""
    provider = settings.LLM_PROVIDER
    
    if provider == 'local':
        from .providers.local import LocalProvider
        return LocalProvider()
    elif provider == 'vllm':
        from .providers.vllm import VLLMProvider
        return VLLMProvider(
            endpoint=settings.LLM_VLLM_ENDPOINT,
            model=settings.LLM_MODEL_NAME
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
