# Tool Context: Flow Engine System

## Overview

The Flow Engine is a unified, extensible system for routing and executing user prompts through declarative YAML-defined workflows. It provides:

- **Unified Entry Point**: Single location where all GUI prompts are processed
- **LLM-Based Selection**: Uses Ollama/Gemma to intelligently select flows
- **YAML-Defined Flows**: Declarative flow definitions with human-readable syntax
- **DAG Execution**: Flows execute as directed acyclic graphs with state management
- **Stateful Context**: User interactions maintain state across multiple prompts
- **Plugin Architecture**: Extensible system for custom node types and flows

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       GUI Frontend                          │
│                  (Django + HTMX)                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              ChatSendView (Unified Entry Point)             │
│  - Normalizes user context                                  │
│  - Creates/retrieves session key                            │
│  - Calls FlowEngine.process_prompt()                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                      FlowEngine                              │
│  ┌────────────────────────────────────────────────┐         │
│  │ 1. Load FlowContext (session-based)            │         │
│  │ 2. Check if flow active → continue OR          │         │
│  │ 3. Call FlowSelector (LLM-based)               │         │
│  │ 4. Get FlowDefinition from FlowLoader          │         │
│  │ 5. Execute via FlowExecutor                     │         │
│  └────────────────────────────────────────────────┘         │
└─────────────────┬────────────────────────────────────────────┘
                  │
        ┌─────────┴──────────┬──────────────┬─────────────┐
        ▼                    ▼              ▼             ▼
┌──────────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────┐
│ FlowContext  │  │ FlowSelector │  │FlowLoader│  │FlowExec. │
│  (Cache)     │  │   (LLM)      │  │  (YAML)  │  │  (DAG)   │
└──────────────┘  └──────────────┘  └──────────┘  └──────────┘
```

## Core Components

### 1. FlowEngine (`apps/flows/engine.py`)

**Purpose**: Unified entry point and orchestrator

**Key Methods**:
- `process_prompt(user_prompt, session_key, is_authenticated, user_data)`: Main entry point
- `discover_flows()`: Load all available flows from disk
- `reload_flows()`: Reload flows without restart

**Workflow**:
1. Normalize user context (auth status, metadata)
2. Load or create FlowContext for session
3. Check if flow already active:
   - Yes → Continue from current node
   - No → Select flow via LLM
4. Execute flow and return formatted response

**Configuration**: None required

**Dependencies**:
- FlowContext (context management)
- FlowSelector (LLM-based routing)
- FlowLoader (YAML parsing)
- FlowExecutor (DAG execution)

### 2. FlowContext (`apps/flows/context.py`)

**Purpose**: Stateful context management for user sessions

**Storage**: Django cache (default: 30-minute TTL)

**Structure**:
```python
{
    'flow_name': 'default',  # Active flow
    'current_node': 'start',  # Current DAG node
    'state': {               # Flow-specific state
        'username': 'alice',
        'step': 2
    },
    'history': [            # Interaction history (last 20)
        {'node': 'start', 'input': 'help', 'output': '...'}
    ],
    'metadata': {           # System metadata
        'auth_status': 'authenticated',
        'username': 'alice'
    }
}
```

**Key Methods**:
- `is_active()`: Check if flow in progress
- `get_state(key)` / `set_state(key, value)`: Manage flow state
- `add_history(entry)`: Track interactions
- `reset()`: Clear context (flow complete)

**Cache Key Format**: `flow_context:{session_key}`

### 3. FlowSelector (`apps/flows/selector.py`)

**Purpose**: LLM-based intelligent flow routing

**LLM Integration**: Uses Ollama (Gemma model for function calling)

**Selection Process**:
1. Build prompt with:
   - User's message
   - Authentication status
   - Available flows with descriptions
   - Active flow (if any)
2. Call LLM with function-calling format
3. Parse JSON response:
   ```json
   {
     "flow_name": "default",
     "reason": "User asking general question",
     "confidence": 0.95
   }
   ```
4. Validate flow exists
5. Fallback to keyword matching if LLM parse fails

**Flow Descriptions** (built-in):
- `default`: General support and documentation Q&A
- `support`: Technical support and developer contact
- `onboarding`: User onboarding and account setup
- `login/signup`: Authentication flows
- `worklog/skills/dashboard`: Feature-specific flows

**Configuration**:
- Temperature: 0.3 (deterministic selection)
- Max tokens: 200

### 4. FlowLoader (`apps/flows/plugins/flow_loader.py`)

**Purpose**: Load and validate YAML flow definitions

**Discovery**:
- Scans `apps/flows/` directory
- Looks for `flow.yaml` in each subdirectory
- Skips directories starting with `_` or named `plugins`

**FlowDefinition Structure**:
```yaml
name: my_flow
description: Flow description
metadata:
  version: "1.0"
  author: "..."
entry_node: start
nodes:
  start:
    type: prompt | action | condition | llm_call | end
    message: "..."
    transitions:
      - target: next_node
```

**Validation**:
- Entry node must exist
- All nodes must have `type`
- Transitions must reference valid nodes or 'end'

**Key Methods**:
- `discover_flows()`: Scan and load all flows
- `load_flow(path)`: Load single YAML file
- `get_flow(name)`: Retrieve loaded flow

### 5. FlowExecutor (`apps/flows/executor.py`)

**Purpose**: Execute flows as DAGs with state management

**Node Types**:

#### `prompt`
Display message and wait for user input
```yaml
type: prompt
message: "Enter your name:"
requires_input: true
store_as: username
transitions:
  - target: next_node
```

#### `action`
Perform operation (logged, no side effects yet)
```yaml
type: action
action: send_email
message: "Email sent!"
transitions:
  - target: next_node
```

#### `condition`
Branch based on state
```yaml
type: condition
condition: "username exists"
transitions:
  - when: "true"
    target: authenticated_node
  - when: "false"
    target: login_node
```

#### `llm_call`
Call LLM with templated prompt
```yaml
type: llm_call
prompt: "User said: {{user_input}}\nAuth: {{auth_status}}"
store_as: ai_response
transitions:
  - target: next_node
```

#### `end`
Terminate flow and reset context
```yaml
type: end
message: "Flow complete!"
```

**Templating**:
- `{{key}}`: Replaced with `context.get_state(key)`
- `{{auth_status}}`: From context metadata
- `{{user_input}}`: Current user input

**Execution**:
1. Get node from flow definition
2. Execute via registered handler
3. Update context with next node
4. Add to history
5. Return result

**Key Methods**:
- `start_flow(flow_def, context, input)`: Begin flow
- `continue_flow(flow_def, context, input)`: Resume flow
- `execute_node(flow_def, node_name, context, input)`: Run single node

### 6. NodeExecutor (`apps/flows/executor.py`)

**Purpose**: Execute individual flow nodes

**Handler Registration**:
```python
node_executor.register_handler('custom_type', handler_function)
```

**Handler Signature**:
```python
def handler(node_spec: Dict, context: FlowContext, user_input: str) -> Dict:
    return {
        'next_node': 'target_node' | 'end' | None,
        'response': 'Message to user',
        'error': False,
        # ... custom fields
    }
```

**Built-in Handlers**:
- `_execute_prompt`: Handle prompt nodes
- `_execute_action`: Handle action nodes
- `_execute_condition`: Handle condition nodes
- `_execute_llm_call`: Handle LLM call nodes
- `_execute_end`: Handle end nodes

## Directory Structure

```
backend/apps/flows/
├── __init__.py
├── apps.py                    # Django app config
├── engine.py                  # FlowEngine (unified entry point)
├── context.py                 # FlowContext (state management)
├── selector.py                # FlowSelector (LLM routing)
├── executor.py                # FlowExecutor + NodeExecutor (DAG)
├── plugins/
│   ├── __init__.py
│   └── flow_loader.py         # YAML loader
├── default/
│   └── flow.yaml              # Default support flow
└── support/
    └── flow.yaml              # Technical support flow
```

## YAML Flow Definition Schema

```yaml
name: flow_name                # Required: unique flow name
description: "..."             # Optional: flow description

metadata:                      # Optional: arbitrary metadata
  version: "1.0"
  author: "..."
  category: "..."

entry_node: start              # Required: initial node name

nodes:                         # Required: node definitions
  node_name:
    type: prompt | action | condition | llm_call | end
    
    # For prompt nodes:
    message: "Text with {{variables}}"
    requires_input: true | false
    store_as: state_key        # Store user input
    
    # For action nodes:
    action: action_name
    
    # For condition nodes:
    condition: "key == value" | "key exists"
    
    # For llm_call nodes:
    prompt: "Prompt with {{variables}}"
    store_as: state_key        # Store LLM response
    
    # For end nodes:
    message: "Final message"
    
    # Transitions (all node types)
    transitions:
      - target: next_node_name
        message: "Optional message"
        when: "true" | "false"   # For conditions
        condition: "..."          # Alternative condition syntax
```

## Adding New Flows

### 1. Create Flow Directory
```bash
mkdir -p backend/apps/flows/my_flow
```

### 2. Create flow.yaml
```yaml
name: my_flow
description: My custom flow
entry_node: start

nodes:
  start:
    type: llm_call
    prompt: "Handle user request: {{user_input}}"
    store_as: response
    transitions:
      - target: end
  
  end:
    type: end
    message: "{{response}}"
```

### 3. Reload Flows (optional)
Flows are auto-discovered on startup. For hot-reload:
```python
from apps.flows.engine import FlowEngine
engine = FlowEngine()
engine.reload_flows()
```

### 4. Test Flow
Send message matching flow intent:
```bash
curl -X POST http://localhost:8000/chat/send/ \
  -d "message=trigger my flow"
```

## Extending the System

### Custom Node Types

1. Create handler function:
```python
def my_handler(node_spec, context, user_input):
    # Custom logic here
    return {
        'next_node': 'next',
        'response': 'Done!',
        'custom_field': 'value'
    }
```

2. Register in FlowExecutor:
```python
from apps.flows.executor import FlowExecutor
executor = FlowExecutor()
executor.node_executor.register_handler('my_type', my_handler)
```

3. Use in YAML:
```yaml
nodes:
  custom:
    type: my_type
    # ... custom fields
```

### Custom Flow Selection Logic

Subclass FlowSelector:
```python
from apps.flows.selector import FlowSelector

class CustomSelector(FlowSelector):
    def select_flow(self, user_prompt, is_authenticated, available_flows, context_data):
        # Custom selection logic
        return {
            'flow_name': 'selected_flow',
            'confidence': 0.9
        }
```

Update FlowEngine:
```python
engine = FlowEngine()
engine.selector = CustomSelector()
```

## DAG Examples

### Simple Linear Flow
```yaml
nodes:
  start:
    type: prompt
    message: "Step 1"
    transitions:
      - target: middle
  
  middle:
    type: prompt
    message: "Step 2"
    transitions:
      - target: end
  
  end:
    type: end
    message: "Complete"
```

### Branching Flow
```yaml
nodes:
  start:
    type: prompt
    message: "Are you authenticated? (yes/no)"
    store_as: auth
    transitions:
      - target: check_auth
  
  check_auth:
    type: condition
    condition: "auth == yes"
    transitions:
      - when: "true"
        target: authenticated
      - when: "false"
        target: login
  
  authenticated:
    type: prompt
    message: "Welcome back!"
    transitions:
      - target: end
  
  login:
    type: prompt
    message: "Please login first"
    transitions:
      - target: end
  
  end:
    type: end
    message: "Done"
```

### Interactive Multi-Step Flow
```yaml
nodes:
  start:
    type: prompt
    message: "What's your name?"
    requires_input: true
    store_as: username
    transitions:
      - target: ask_age
  
  ask_age:
    type: prompt
    message: "Hi {{username}}! What's your age?"
    requires_input: true
    store_as: age
    transitions:
      - target: summarize
  
  summarize:
    type: llm_call
    prompt: "Generate greeting for {{username}}, age {{age}}"
    store_as: greeting
    transitions:
      - target: end
  
  end:
    type: end
    message: "{{greeting}}"
```

## Testing

### Unit Tests
```python
import pytest
from apps.flows.engine import FlowEngine
from apps.flows.context import FlowContext

def test_flow_execution():
    engine = FlowEngine()
    result = engine.process_prompt(
        user_prompt="help",
        session_key="test123",
        is_authenticated=False
    )
    assert result['response']
    assert not result['error']
```

### Integration Tests
```bash
cd backend
python -m pytest frontend/tests.py::TestChatSendView -v
```

### Manual Testing
```bash
# Start server
python manage.py runserver

# Test via browser
# Open: http://localhost:8000/
# Type message in chat

# Test via API
curl -X POST http://localhost:8000/chat/send/ \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "message=help" \
  --cookie "sessionid=..."
```

## Performance

- **Flow Discovery**: O(n) where n = number of flow directories
- **Flow Selection**: ~1-2 seconds (LLM call)
- **Flow Execution**: O(m) where m = number of nodes traversed
- **Context Storage**: Redis/cache (fast lookup)

**Optimization Tips**:
- Pre-load flows on app startup (done automatically)
- Cache flow selection results (not implemented)
- Use shorter LLM prompts for faster selection
- Limit history size (current: 20 entries)

## Debugging

### Enable Debug Logging
```python
# backend/config/settings/base.py
LOGGING = {
    'loggers': {
        'apps.flows': {
            'level': 'DEBUG',
            'handlers': ['console']
        }
    }
}
```

### Inspect Flow Context
```python
from apps.flows.context import FlowContext
context = FlowContext('session_key')
print(context.to_dict())
```

### View Available Flows
```python
from apps.flows.engine import FlowEngine
engine = FlowEngine()
print(engine.list_flows())
```

### Reload Flows Without Restart
```python
engine.reload_flows()
```

## Migration from Old System

**Old**: Hardcoded command handlers in views.py
**New**: Flow engine with YAML definitions

**Backward Compatibility**:
- Login/signup/logout/dashboard commands still handled directly
- Flow engine handles all other messages
- Tests updated to work with both systems

**Migration Path**:
1. Create YAML flows for remaining commands
2. Update command handlers to route through flow engine
3. Remove old handler methods
4. Update tests

## Future Enhancements

- [ ] Persistent context (database storage)
- [ ] Flow versioning and rollback
- [ ] A/B testing flows
- [ ] Flow analytics (completion rates, drop-off)
- [ ] Visual flow editor
- [ ] Flow templates library
- [ ] Conditional node execution based on user roles
- [ ] Async node execution (long-running operations)
- [ ] Flow composition (call flows from flows)
- [ ] External API integration nodes
- [ ] Webhook trigger nodes
