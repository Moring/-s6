"""
YAML flow loader for declarative flow definitions.

Loads and validates flow definitions from YAML files.
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class FlowDefinition:
    """Represents a loaded flow definition."""
    
    def __init__(self, name: str, spec: Dict[str, Any], source_path: str):
        """
        Initialize flow definition.
        
        Args:
            name: Flow name
            spec: Flow specification dictionary
            source_path: Path to YAML file
        """
        self.name = name
        self.spec = spec
        self.source_path = source_path
        
        # Extract key metadata
        self.description = spec.get('description', '')
        self.entry_node = spec.get('entry_node', 'start')
        self.nodes = spec.get('nodes', {})
        self.metadata = spec.get('metadata', {})
        
        # Validate structure
        self._validate()
    
    def _validate(self):
        """Validate flow definition structure."""
        if not self.nodes:
            raise ValueError(f"Flow {self.name} has no nodes defined")
        
        if self.entry_node not in self.nodes:
            raise ValueError(f"Entry node '{self.entry_node}' not found in flow {self.name}")
        
        # Validate node structure
        for node_name, node_spec in self.nodes.items():
            if 'type' not in node_spec:
                raise ValueError(f"Node '{node_name}' in flow {self.name} missing 'type'")
            
            # Validate transitions reference existing nodes
            transitions = node_spec.get('transitions', [])
            for transition in transitions:
                target = transition.get('target')
                if target and target not in self.nodes and target != 'end':
                    raise ValueError(
                        f"Node '{node_name}' references non-existent target '{target}' in flow {self.name}"
                    )
    
    def get_node(self, node_name: str) -> Optional[Dict[str, Any]]:
        """Get node specification by name."""
        return self.nodes.get(node_name)
    
    def get_entry_node(self) -> Dict[str, Any]:
        """Get the entry node specification."""
        return self.nodes[self.entry_node]


class FlowLoader:
    """Loads flow definitions from YAML files."""
    
    def __init__(self, flows_dir: Optional[str] = None):
        """
        Initialize flow loader.
        
        Args:
            flows_dir: Directory containing flow definitions (defaults to apps/flows)
        """
        if flows_dir is None:
            from django.conf import settings
            base_dir = Path(settings.BASE_DIR)
            flows_dir = base_dir / 'apps' / 'flows'
        
        self.flows_dir = Path(flows_dir)
        self._loaded_flows: Dict[str, FlowDefinition] = {}
    
    def discover_flows(self) -> Dict[str, FlowDefinition]:
        """
        Discover and load all flows from the flows directory.
        
        Returns:
            Dictionary mapping flow names to FlowDefinition objects
        """
        self._loaded_flows = {}
        
        if not self.flows_dir.exists():
            logger.warning(f"Flows directory not found: {self.flows_dir}")
            return self._loaded_flows
        
        # Scan for flow.yaml files in subdirectories
        for flow_dir in self.flows_dir.iterdir():
            if not flow_dir.is_dir():
                continue
            
            # Skip special directories
            if flow_dir.name.startswith('_') or flow_dir.name == 'plugins':
                continue
            
            flow_file = flow_dir / 'flow.yaml'
            if flow_file.exists():
                try:
                    flow_def = self.load_flow(flow_file)
                    self._loaded_flows[flow_def.name] = flow_def
                    logger.info(f"Loaded flow: {flow_def.name} from {flow_file}")
                except Exception as e:
                    logger.error(f"Failed to load flow from {flow_file}: {e}")
        
        return self._loaded_flows
    
    def load_flow(self, flow_file: Path) -> FlowDefinition:
        """
        Load a single flow from a YAML file.
        
        Args:
            flow_file: Path to flow.yaml
            
        Returns:
            FlowDefinition object
        """
        with open(flow_file, 'r') as f:
            spec = yaml.safe_load(f)
        
        # Extract flow name from spec or directory name
        flow_name = spec.get('name', flow_file.parent.name)
        
        return FlowDefinition(flow_name, spec, str(flow_file))
    
    def get_flow(self, name: str) -> Optional[FlowDefinition]:
        """Get a loaded flow by name."""
        return self._loaded_flows.get(name)
    
    def list_flows(self) -> List[str]:
        """List all loaded flow names."""
        return list(self._loaded_flows.keys())
    
    def reload(self):
        """Reload all flows from disk."""
        return self.discover_flows()
