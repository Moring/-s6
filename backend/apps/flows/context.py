"""
Flow context management for stateful user interactions.

Tracks active flow, current node, and session state across multiple prompts.
"""
import json
from typing import Any, Dict, Optional
from django.core.cache import cache


class FlowContext:
    """Manages stateful flow context for a user session."""
    
    def __init__(self, session_key: str):
        """
        Initialize flow context.
        
        Args:
            session_key: Django session key or unique identifier
        """
        self.session_key = session_key
        self.cache_key = f"flow_context:{session_key}"
        self._data = self._load()
    
    def _load(self) -> Dict[str, Any]:
        """Load context from cache."""
        data = cache.get(self.cache_key)
        if data:
            try:
                return json.loads(data)
            except (json.JSONDecodeError, TypeError):
                pass
        return self._default_context()
    
    def _save(self):
        """Save context to cache (30 minute TTL)."""
        cache.set(self.cache_key, json.dumps(self._data), timeout=1800)
    
    def _default_context(self) -> Dict[str, Any]:
        """Return default empty context."""
        return {
            'flow_name': None,
            'current_node': None,
            'state': {},
            'history': [],
            'metadata': {}
        }
    
    @property
    def flow_name(self) -> Optional[str]:
        """Get active flow name."""
        return self._data.get('flow_name')
    
    @flow_name.setter
    def flow_name(self, value: Optional[str]):
        """Set active flow name."""
        self._data['flow_name'] = value
        self._save()
    
    @property
    def current_node(self) -> Optional[str]:
        """Get current node in flow."""
        return self._data.get('current_node')
    
    @current_node.setter
    def current_node(self, value: Optional[str]):
        """Set current node."""
        self._data['current_node'] = value
        self._save()
    
    def get_state(self, key: str, default=None) -> Any:
        """Get value from flow state."""
        return self._data.get('state', {}).get(key, default)
    
    def set_state(self, key: str, value: Any):
        """Set value in flow state."""
        if 'state' not in self._data:
            self._data['state'] = {}
        self._data['state'][key] = value
        self._save()
    
    def clear_state(self, key: str):
        """Remove key from state."""
        if 'state' in self._data and key in self._data['state']:
            del self._data['state'][key]
            self._save()
    
    def add_history(self, entry: Dict[str, Any]):
        """Add entry to interaction history."""
        if 'history' not in self._data:
            self._data['history'] = []
        self._data['history'].append(entry)
        # Keep only last 20 entries
        if len(self._data['history']) > 20:
            self._data['history'] = self._data['history'][-20:]
        self._save()
    
    def get_history(self) -> list:
        """Get interaction history."""
        return self._data.get('history', [])
    
    def set_metadata(self, key: str, value: Any):
        """Set metadata value."""
        if 'metadata' not in self._data:
            self._data['metadata'] = {}
        self._data['metadata'][key] = value
        self._save()
    
    def get_metadata(self, key: str, default=None) -> Any:
        """Get metadata value."""
        return self._data.get('metadata', {}).get(key, default)
    
    def is_active(self) -> bool:
        """Check if a flow is currently active."""
        return self.flow_name is not None
    
    def reset(self):
        """Reset context to default state."""
        self._data = self._default_context()
        self._save()
    
    def to_dict(self) -> Dict[str, Any]:
        """Export context as dictionary."""
        return self._data.copy()
