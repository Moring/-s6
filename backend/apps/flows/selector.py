"""
LLM-based flow selector using Ollama with function calling.

Uses Gemma model to dynamically select the appropriate flow based on user prompt.
"""
import json
import logging
from typing import Dict, Any, Optional, List
from apps.llm.client import get_llm_client

logger = logging.getLogger(__name__)


class FlowSelector:
    """Selects flows using LLM function calling."""
    
    def __init__(self):
        """Initialize flow selector."""
        self.llm = get_llm_client()
    
    def select_flow(
        self,
        user_prompt: str,
        is_authenticated: bool,
        available_flows: List[str],
        context_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Select appropriate flow using LLM.
        
        Args:
            user_prompt: User's input message
            is_authenticated: Whether user is logged in
            available_flows: List of available flow names
            context_data: Current flow context (if any)
            
        Returns:
            Dictionary with 'flow_name', 'entry_node', 'params', 'confidence'
        """
        # Build prompt for flow selection
        prompt = self._build_selection_prompt(
            user_prompt,
            is_authenticated,
            available_flows,
            context_data
        )
        
        try:
            # Call LLM with function calling format
            response = self.llm.complete(prompt, temperature=0.3, max_tokens=200)
            
            # Parse response
            selection = self._parse_selection(response, available_flows)
            
            # Add token usage from LLM response
            selection['tokens_in'] = response.get('tokens_in', 0)
            selection['tokens_out'] = response.get('tokens_out', 0)
            
            logger.info(f"Flow selected: {selection['flow_name']} (confidence: {selection['confidence']})")
            return selection
            
        except Exception as e:
            logger.error(f"Error in flow selection: {e}")
            # Fallback to default
            return {
                'flow_name': 'default',
                'entry_node': None,
                'params': {},
                'confidence': 0.0,
                'error': str(e)
            }
    
    def _build_selection_prompt(
        self,
        user_prompt: str,
        is_authenticated: bool,
        available_flows: List[str],
        context_data: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for flow selection."""
        
        # Define available flows with descriptions
        flow_descriptions = {
            'default': 'General support and documentation Q&A',
            'support': 'Technical support and developer contact',
            'onboarding': 'User onboarding and account setup',
            'login': 'User authentication flow',
            'signup': 'New user registration',
            'worklog': 'Work log management and tracking',
            'skills': 'Skills analysis and extraction',
            'dashboard': 'Dashboard and statistics viewing'
        }
        
        flows_info = []
        for flow_name in available_flows:
            desc = flow_descriptions.get(flow_name, 'No description available')
            flows_info.append(f"- {flow_name}: {desc}")
        
        auth_status = "authenticated" if is_authenticated else "not authenticated"
        active_flow = context_data.get('flow_name') if context_data else None
        
        prompt = f"""You are a flow router for DigiMuse.ai, an AI-powered career intelligence platform.

User's message: "{user_prompt}"
User authentication: {auth_status}
Currently active flow: {active_flow or 'None'}

Available flows:
{chr(10).join(flows_info)}

Your task: Select the most appropriate flow to handle this user's request.

Rules:
1. If user is continuing an active flow, prefer to stay in that flow unless they explicitly want to exit
2. Authentication-required flows (worklog, skills, dashboard) should only be selected for authenticated users
3. If no specific flow matches, select 'default' for general questions
4. For login/signup requests, select those specific flows
5. For technical support or developer contact, select 'support'

Respond in JSON format:
{{
  "flow_name": "selected_flow_name",
  "reason": "brief explanation",
  "confidence": 0.95
}}"""
        
        return prompt
    
    def _parse_selection(self, llm_response: Dict[str, Any], available_flows: List[str]) -> Dict[str, Any]:
        """Parse LLM response and extract flow selection."""
        response_text = llm_response.get('response', '').strip()
        
        # Try to parse JSON from response
        try:
            # Extract JSON if wrapped in markdown code blocks
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            elif '```' in response_text:
                json_start = response_text.find('```') + 3
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            
            selection = json.loads(response_text)
            
            flow_name = selection.get('flow_name', 'default')
            
            # Validate flow exists
            if flow_name not in available_flows:
                logger.warning(f"Selected flow '{flow_name}' not available, using 'default'")
                flow_name = 'default'
            
            return {
                'flow_name': flow_name,
                'entry_node': selection.get('entry_node'),
                'params': selection.get('params', {}),
                'confidence': float(selection.get('confidence', 0.7)),
                'reason': selection.get('reason', '')
            }
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse LLM selection response: {e}")
            logger.debug(f"Response was: {response_text}")
            
            # Fallback: simple keyword matching
            return self._fallback_selection(llm_response, available_flows)
    
    def _fallback_selection(self, llm_response: Dict[str, Any], available_flows: List[str]) -> Dict[str, Any]:
        """Fallback selection using keyword matching."""
        response_text = llm_response.get('response', '').lower()
        
        # Simple keyword matching
        if 'login' in response_text and 'login' in available_flows:
            flow_name = 'login'
        elif 'signup' in response_text and 'signup' in available_flows:
            flow_name = 'signup'
        elif 'support' in response_text and 'support' in available_flows:
            flow_name = 'support'
        elif 'worklog' in response_text and 'worklog' in available_flows:
            flow_name = 'worklog'
        else:
            flow_name = 'default'
        
        return {
            'flow_name': flow_name,
            'entry_node': None,
            'params': {},
            'confidence': 0.5,
            'reason': 'Fallback keyword matching'
        }
