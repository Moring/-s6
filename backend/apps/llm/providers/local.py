"""
Local fake LLM provider for testing.
"""
import json
import hashlib


class LocalProvider:
    """
    Fake LLM provider that returns deterministic responses.
    Useful for testing without real LLM.
    """
    
    model_name = "local-fake"
    
    def complete(self, prompt: str, **kwargs) -> dict:
        """Return deterministic fake response."""
        # Generate response based on prompt hash for determinism
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        
        # Parse intent from prompt
        if 'analyze' in prompt.lower() or 'worklog' in prompt.lower():
            return {
                'summary': f'Analysis result {prompt_hash}',
                'activities': ['Development', 'Testing', 'Documentation'],
                'technologies': ['Python', 'Django', 'PostgreSQL'],
                'sentiment': 'positive'
            }
        
        elif 'skill' in prompt.lower() or 'extract' in prompt.lower():
            return {
                'skills': [
                    {
                        'name': 'Python',
                        'confidence': 0.9,
                        'level': 'expert',
                        'evidence': []
                    },
                    {
                        'name': 'Django',
                        'confidence': 0.85,
                        'level': 'intermediate',
                        'evidence': []
                    }
                ]
            }
        
        elif 'report' in prompt.lower() or 'resume' in prompt.lower():
            return {
                'summary': [f'Professional summary {prompt_hash}'],
                'completed': ['Task A', 'Task B'],
                'in_progress': ['Task C'],
                'skills': ['Python', 'Django', 'REST APIs'],
                'experience': ['Built scalable systems', 'Led development teams']
            }
        
        # Default response
        return {
            'response': f'Processed prompt {prompt_hash}',
            'success': True
        }
