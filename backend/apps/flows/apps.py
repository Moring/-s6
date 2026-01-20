"""
Django app configuration for flows.
"""
from django.apps import AppConfig


class FlowsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.flows'
    verbose_name = 'Flow Engine'
    
    def ready(self):
        """Initialize flow engine on app ready."""
        from .engine import FlowEngine
        # Pre-load flows for faster first request
        try:
            engine = FlowEngine()
            engine.discover_flows()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to pre-load flows: {e}")
