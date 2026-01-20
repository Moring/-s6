"""
Unified flow engine - single entry point for all GUI prompts.

Orchestrates flow selection, context management, and execution.
"""
import logging
from typing import Dict, Any, Optional
from .context import FlowContext
from .selector import FlowSelector
from .executor import FlowExecutor
from .plugins.flow_loader import FlowLoader, FlowDefinition

logger = logging.getLogger(__name__)


class FlowEngine:
    """
    Unified entry point for all prompt processing.
    
    Responsibilities:
    - Normalize user context
    - Select appropriate flow using LLM
    - Initialize or resume flow execution
    - Manage stateful interactions
    """
    
    def __init__(self):
        """Initialize flow engine components."""
        self.loader = FlowLoader()
        self.selector = FlowSelector()
        self.executor = FlowExecutor()
        self._flows: Dict[str, FlowDefinition] = {}
        
        # Discover flows on initialization
        self.discover_flows()
    
    def discover_flows(self) -> Dict[str, FlowDefinition]:
        """Discover and load all available flows."""
        self._flows = self.loader.discover_flows()
        logger.info(f"Discovered {len(self._flows)} flows: {list(self._flows.keys())}")
        return self._flows
    
    def process_prompt(
        self,
        user_prompt: str,
        session_key: str,
        is_authenticated: bool = False,
        user_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        UNIFIED ENTRY POINT for all prompts from GUI.
        
        This is the single point where:
        - User context is normalized
        - Flow selection occurs
        - Execution state is initialized or resumed
        
        Args:
            user_prompt: User's input message
            session_key: Django session key or unique identifier
            is_authenticated: Whether user is logged in
            user_data: Additional user context (username, tenant, etc.)
            
        Returns:
            Dictionary with 'response', 'requires_input', 'flow_active', etc.
        """
        # 1. Normalize user context
        context = FlowContext(session_key)
        user_data = user_data or {}
        
        # Store user info and auth status in context metadata
        if is_authenticated and user_data:
            context.set_metadata('username', user_data.get('username'))
            context.set_metadata('tenant_id', user_data.get('tenant_id'))
            context.set_metadata('auth_status', 'authenticated')
        else:
            context.set_metadata('auth_status', 'not authenticated')
        
        # 2. Check if flow is already active
        if context.is_active():
            logger.info(f"Continuing active flow: {context.flow_name}")
            return self._continue_flow(context, user_prompt)
        
        # 3. Select flow using LLM
        selection = self.selector.select_flow(
            user_prompt=user_prompt,
            is_authenticated=is_authenticated,
            available_flows=list(self._flows.keys()),
            context_data=context.to_dict()
        )
        
        flow_name = selection['flow_name']
        logger.info(f"Selected flow: {flow_name} (confidence: {selection['confidence']})")
        
        # 4. Get flow definition
        flow_def = self._flows.get(flow_name)
        
        if not flow_def:
            logger.error(f"Flow '{flow_name}' not found, falling back to default")
            flow_def = self._flows.get('default')
        
        if not flow_def:
            # No flows available - fallback response
            return {
                'response': self._get_fallback_response(user_prompt, is_authenticated),
                'requires_input': False,
                'flow_active': False,
                'error': 'No flows available'
            }
        
        # 5. Execute flow
        return self._execute_flow(flow_def, context, user_prompt)
    
    def _continue_flow(self, context: FlowContext, user_prompt: str) -> Dict[str, Any]:
        """Continue executing an active flow."""
        flow_name = context.flow_name
        flow_def = self._flows.get(flow_name)
        
        if not flow_def:
            logger.error(f"Active flow '{flow_name}' not found, resetting")
            context.reset()
            return {
                'response': "Sorry, I lost track of where we were. Let's start over. How can I help you?",
                'requires_input': False,
                'flow_active': False
            }
        
        # Continue execution from current node
        result = self.executor.continue_flow(flow_def, context, user_prompt)
        
        return self._format_result(result, context)
    
    def _execute_flow(self, flow_def: FlowDefinition, context: FlowContext, user_prompt: str) -> Dict[str, Any]:
        """Execute a flow from the beginning."""
        result = self.executor.start_flow(flow_def, context, user_prompt)
        return self._format_result(result, context)
    
    def _format_result(self, execution_result: Dict[str, Any], context: FlowContext) -> Dict[str, Any]:
        """Format execution result for GUI response."""
        return {
            'response': execution_result.get('response', ''),
            'requires_input': execution_result.get('requires_input', False),
            'flow_active': context.is_active(),
            'flow_name': context.flow_name,
            'current_node': context.current_node,
            'error': execution_result.get('error', False),
            'metadata': execution_result
        }
    
    def _get_fallback_response(self, user_prompt: str, is_authenticated: bool) -> str:
        """Get fallback response when no flows available."""
        if is_authenticated:
            return (
                "I'm having trouble processing your request right now. "
                "Our system is being updated. Please try again in a moment, "
                "or contact support if the issue persists."
            )
        else:
            return (
                "Welcome to DigiMuse.ai! I'm currently being updated. "
                "Please try logging in, or check back shortly. "
                "Type 'login' to sign in or 'signup' to create an account."
            )
    
    def get_flow_info(self, flow_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific flow."""
        flow_def = self._flows.get(flow_name)
        if not flow_def:
            return None
        
        return {
            'name': flow_def.name,
            'description': flow_def.description,
            'entry_node': flow_def.entry_node,
            'nodes': list(flow_def.nodes.keys()),
            'metadata': flow_def.metadata
        }
    
    def list_flows(self) -> list:
        """List all available flows."""
        return [self.get_flow_info(name) for name in self._flows.keys()]
    
    def reload_flows(self):
        """Reload all flows from disk."""
        self._flows = self.loader.reload()
        logger.info(f"Reloaded {len(self._flows)} flows")
