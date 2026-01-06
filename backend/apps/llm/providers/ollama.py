"""
Ollama provider (stub for MVP).
"""
import requests


class OllamaProvider:
    """Ollama provider for local generation."""

    def __init__(self, endpoint: str, model: str):
        self.endpoint = endpoint.rstrip('/')
        self.model_name = model

    def complete(self, prompt: str, **kwargs) -> dict:
        """
        Call Ollama generate endpoint.

        Note: This is a stub. In production, implement:
        - Proper error handling
        - Retry logic
        - Response parsing
        - Token management
        """
        url = f"{self.endpoint}/api/generate"

        payload = {
            'model': self.model_name,
            'prompt': prompt,
            'stream': False,
        }

        options = {}
        if 'temperature' in kwargs:
            options['temperature'] = kwargs['temperature']
        if 'max_tokens' in kwargs:
            options['num_predict'] = kwargs['max_tokens']
        if options:
            payload['options'] = options

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            text = data.get('response', '')
            return {'response': text, 'raw': data}

        except Exception as e:
            return {
                'error': str(e),
                'response': 'Ollama unavailable, using fallback'
            }
