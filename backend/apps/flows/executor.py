"""
DAG-based flow executor.

Executes flow nodes as a directed acyclic graph with state management.
"""
import logging
from typing import Dict, Any, Optional, Callable
from .context import FlowContext
from .plugins.flow_loader import FlowDefinition

logger = logging.getLogger(__name__)


class NodeExecutor:
    """Executes individual flow nodes."""
    
    def __init__(self):
        """Initialize node executor with registered handlers."""
        self._handlers: Dict[str, Callable] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register built-in node type handlers."""
        self.register_handler('prompt', self._execute_prompt)
        self.register_handler('action', self._execute_action)
        self.register_handler('condition', self._execute_condition)
        self.register_handler('llm_call', self._execute_llm_call)
        self.register_handler('end', self._execute_end)
    
    def register_handler(self, node_type: str, handler: Callable):
        """Register a custom node type handler."""
        self._handlers[node_type] = handler
    
    def execute(self, node_spec: Dict[str, Any], context: FlowContext, user_input: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a single node.
        
        Args:
            node_spec: Node specification from YAML
            context: Flow context
            user_input: User's input (if applicable)
            
        Returns:
            Dictionary with execution result including 'next_node' and 'response'
        """
        node_type = node_spec.get('type')
        handler = self._handlers.get(node_type)
        
        if not handler:
            logger.error(f"No handler registered for node type: {node_type}")
            return {
                'next_node': 'end',
                'response': f"Error: Unknown node type '{node_type}'",
                'error': True
            }
        
        try:
            return handler(node_spec, context, user_input)
        except Exception as e:
            logger.exception(f"Error executing node: {e}")
            return {
                'next_node': 'end',
                'response': f"Error executing flow: {str(e)}",
                'error': True
            }
    
    def _execute_prompt(self, node_spec: Dict[str, Any], context: FlowContext, user_input: Optional[str]) -> Dict[str, Any]:
        """Execute a prompt node (display message, wait for input)."""
        message = node_spec.get('message', '')
        
        # Template message with context variables
        for key, value in context.to_dict().get('state', {}).items():
            message = message.replace(f'{{{{{key}}}}}', str(value))
        
        # Store user input in context if provided
        if user_input:
            state_key = node_spec.get('store_as')
            if state_key:
                context.set_state(state_key, user_input)
        
        # Determine next node
        next_node = self._evaluate_transitions(node_spec, context, user_input)
        
        return {
            'next_node': next_node,
            'response': message,
            'requires_input': node_spec.get('requires_input', False)
        }
    
    def _execute_action(self, node_spec: Dict[str, Any], context: FlowContext, user_input: Optional[str]) -> Dict[str, Any]:
        """Execute an action node (perform operation)."""
        action_type = node_spec.get('action')
        
        # Execute registered action
        # For now, just log and continue
        logger.info(f"Executing action: {action_type}")
        
        next_node = self._evaluate_transitions(node_spec, context, user_input)
        
        return {
            'next_node': next_node,
            'response': node_spec.get('message', ''),
            'action_executed': action_type
        }
    
    def _execute_condition(self, node_spec: Dict[str, Any], context: FlowContext, user_input: Optional[str]) -> Dict[str, Any]:
        """Execute a condition node (branch based on state)."""
        condition = node_spec.get('condition')
        
        # Simple condition evaluation
        result = self._evaluate_condition(condition, context)
        
        # Choose transition based on result
        transitions = node_spec.get('transitions', [])
        for trans in transitions:
            if trans.get('condition') == result or (result and trans.get('when') == 'true'):
                return {
                    'next_node': trans.get('target', 'end'),
                    'response': trans.get('message', ''),
                    'condition_result': result
                }
        
        # Default fallback
        return {
            'next_node': 'end',
            'response': '',
            'condition_result': result
        }
    
    def _execute_llm_call(self, node_spec: Dict[str, Any], context: FlowContext, user_input: Optional[str]) -> Dict[str, Any]:
        """Execute an LLM call node."""
        from apps.llm.client import get_llm_client
        
        prompt = node_spec.get('prompt', '')
        
        # Template prompt with context state
        for key, value in context.to_dict().get('state', {}).items():
            prompt = prompt.replace(f'{{{{{key}}}}}', str(value))
        
        # Template with metadata (auth_status, etc.)
        metadata = context.to_dict().get('metadata', {})
        for key, value in metadata.items():
            prompt = prompt.replace(f'{{{{{key}}}}}', str(value))
        
        # Always replace user_input
        if user_input:
            prompt = prompt.replace('{{user_input}}', user_input)
        
        # Call LLM
        llm = get_llm_client()
        response = llm.complete(prompt, temperature=0.7, max_tokens=500)
        
        # Store response if specified
        store_as = node_spec.get('store_as')
        if store_as:
            response_text = response.get('response', '')
            context.set_state(store_as, response_text)
        
        next_node = self._evaluate_transitions(node_spec, context, user_input)
        
        # Get the actual response text
        response_text = response.get('response', '')
        
        # If empty or error, provide fallback
        if not response_text or 'error' in response:
            response_text = "I'm having trouble generating a response. Please try again or rephrase your question."
        
        return {
            'next_node': next_node,
            'response': response_text,
            'llm_called': True
        }
    
    def _execute_end(self, node_spec: Dict[str, Any], context: FlowContext, user_input: Optional[str]) -> Dict[str, Any]:
        """Execute an end node (terminate flow)."""
        message = node_spec.get('message', 'Flow complete.')
        
        # Clear flow context
        context.reset()
        
        return {
            'next_node': None,
            'response': message,
            'flow_complete': True
        }
    
    def _evaluate_transitions(self, node_spec: Dict[str, Any], context: FlowContext, user_input: Optional[str]) -> str:
        """Evaluate transitions to determine next node."""
        transitions = node_spec.get('transitions', [])
        
        if not transitions:
            return 'end'
        
        # For now, take first transition (can be enhanced with conditions)
        return transitions[0].get('target', 'end')
    
    def _evaluate_condition(self, condition: str, context: FlowContext) -> bool:
        """Evaluate a condition expression."""
        # Simple condition evaluation (can be enhanced)
        # Format: "key == value" or "key exists"
        if ' == ' in condition:
            key, value = condition.split(' == ')
            return str(context.get_state(key.strip())) == value.strip()
        elif ' exists' in condition:
            key = condition.replace(' exists', '').strip()
            return context.get_state(key) is not None
        return False


class FlowExecutor:
    """Executes flows as DAGs."""
    
    def __init__(self):
        """Initialize flow executor."""
        self.node_executor = NodeExecutor()
    
    def execute_node(self, flow_def: FlowDefinition, node_name: str, context: FlowContext, user_input: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a single node in the flow.
        
        Args:
            flow_def: Flow definition
            node_name: Name of node to execute
            context: Flow context
            user_input: User input (if any)
            
        Returns:
            Execution result with next_node and response
        """
        node_spec = flow_def.get_node(node_name)
        
        if not node_spec:
            logger.error(f"Node '{node_name}' not found in flow '{flow_def.name}'")
            return {
                'next_node': 'end',
                'response': f"Error: Node '{node_name}' not found",
                'error': True
            }
        
        # Execute node
        result = self.node_executor.execute(node_spec, context, user_input)
        
        # Update context
        next_node = result.get('next_node')
        if next_node and next_node != 'end':
            context.current_node = next_node
        else:
            context.reset()  # Flow complete
        
        # Add to history
        context.add_history({
            'node': node_name,
            'input': user_input,
            'output': result.get('response'),
            'next': next_node
        })
        
        return result
    
    def start_flow(self, flow_def: FlowDefinition, context: FlowContext, user_input: Optional[str] = None) -> Dict[str, Any]:
        """
        Start executing a flow from its entry node.
        
        Args:
            flow_def: Flow definition
            context: Flow context
            user_input: Initial user input
            
        Returns:
            Execution result
        """
        # Set flow in context
        context.flow_name = flow_def.name
        context.current_node = flow_def.entry_node
        
        # Execute entry node
        return self.execute_node(flow_def, flow_def.entry_node, context, user_input)
    
    def continue_flow(self, flow_def: FlowDefinition, context: FlowContext, user_input: str) -> Dict[str, Any]:
        """
        Continue executing a flow from the current node.
        
        Args:
            flow_def: Flow definition
            context: Flow context
            user_input: User's input
            
        Returns:
            Execution result
        """
        current_node = context.current_node
        
        if not current_node:
            logger.warning("No current node in context, starting from entry")
            return self.start_flow(flow_def, context, user_input)
        
        return self.execute_node(flow_def, current_node, context, user_input)
