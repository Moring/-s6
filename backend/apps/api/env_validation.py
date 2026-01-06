"""
Environment variable validation and startup checks.
Ensures required configuration is present before starting the application.
"""
import os
import sys
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass


@dataclass
class EnvVar:
    """Environment variable specification."""
    name: str
    required: bool
    default: Optional[str] = None
    description: str = ""
    example: Optional[str] = None
    secret: bool = False  # If True, never log the value
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate this environment variable."""
        value = os.environ.get(self.name)
        
        if value is None:
            if self.required and self.default is None:
                return False, f"Missing required environment variable: {self.name}"
            return True, None
        
        # Basic validation passed
        return True, None


# Environment variable contract
ENV_VARS: List[EnvVar] = [
    # Core Django settings
    EnvVar(
        name='SECRET_KEY',
        required=True,
        description='Django secret key for cryptographic signing',
        example='django-insecure-dev-key-change-in-production',
        secret=True
    ),
    EnvVar(
        name='DEBUG',
        required=False,
        default='False',
        description='Enable debug mode (True/False)',
        example='False'
    ),
    EnvVar(
        name='DJANGO_ALLOWED_HOSTS',
        required=False,
        default='localhost,127.0.0.1',
        description='Comma-separated list of allowed hosts',
        example='example.com,www.example.com'
    ),
    
    # Database
    EnvVar(
        name='DATABASE_URL',
        required=False,  # Can use individual vars instead
        description='PostgreSQL connection URL',
        example='postgresql://user:pass@localhost:5432/dbname',
        secret=True
    ),
    EnvVar(
        name='POSTGRES_DB',
        required=False,
        default='afterresume',
        description='PostgreSQL database name',
        example='afterresume'
    ),
    EnvVar(
        name='POSTGRES_USER',
        required=False,
        default='afterresume',
        description='PostgreSQL username',
        example='afterresume'
    ),
    EnvVar(
        name='POSTGRES_PASSWORD',
        required=False,
        description='PostgreSQL password',
        example='secure-password',
        secret=True
    ),
    EnvVar(
        name='POSTGRES_HOST',
        required=False,
        default='localhost',
        description='PostgreSQL host',
        example='postgres'
    ),
    EnvVar(
        name='POSTGRES_PORT',
        required=False,
        default='5432',
        description='PostgreSQL port',
        example='5432'
    ),
    
    # Redis/Valkey
    EnvVar(
        name='REDIS_URL',
        required=False,
        default='redis://localhost:6379/0',
        description='Redis/Valkey connection URL',
        example='redis://valkey:6379/0'
    ),
    
    # MinIO/S3
    EnvVar(
        name='MINIO_ENDPOINT',
        required=False,
        default='minio:9000',
        description='MinIO endpoint',
        example='minio:9000'
    ),
    EnvVar(
        name='MINIO_ACCESS_KEY',
        required=False,
        default='minioadmin',
        description='MinIO access key',
        example='minioadmin',
        secret=True
    ),
    EnvVar(
        name='MINIO_SECRET_KEY',
        required=False,
        default='minioadmin',
        description='MinIO secret key',
        example='minioadmin',
        secret=True
    ),
    EnvVar(
        name='MINIO_BUCKET',
        required=False,
        default='artifacts',
        description='MinIO bucket name',
        example='artifacts'
    ),

    # Tika
    EnvVar(
        name='TIKA_ENDPOINT',
        required=False,
        default='http://tika:9998',
        description='Apache Tika endpoint',
        example='http://tika:9998'
    ),
    
    # Service auth
    EnvVar(
        name='SERVICE_TO_SERVICE_SECRET',
        required=False,
        description='Shared secret for service-to-service auth (falls back to SECRET_KEY)',
        example='service-secret-key-here',
        secret=True
    ),
    
    # LLM Provider
    EnvVar(
        name='LLM_PROVIDER',
        required=False,
        default='local',
        description='LLM provider (local/vllm/ollama)',
        example='local'
    ),
    EnvVar(
        name='LLM_VLLM_ENDPOINT',
        required=False,
        description='vLLM endpoint URL (required if LLM_PROVIDER=vllm)',
        example='http://vllm:8000'
    ),
    EnvVar(
        name='LLM_MODEL_NAME',
        required=False,
        default='local-fake',
        description='LLM model name',
        example='meta-llama/Llama-2-7b-chat-hf'
    ),
    EnvVar(
        name='OLLAMA_ENDPOINT',
        required=False,
        default='http://ollama:11434',
        description='Ollama endpoint URL (required if LLM_PROVIDER=ollama)',
        example='http://ollama:11434'
    ),
    
    # Email (optional)
    EnvVar(
        name='EMAIL_HOST',
        required=False,
        description='SMTP host',
        example='smtp.gmail.com'
    ),
    EnvVar(
        name='EMAIL_PORT',
        required=False,
        default='587',
        description='SMTP port',
        example='587'
    ),
    EnvVar(
        name='EMAIL_HOST_USER',
        required=False,
        description='SMTP username',
        example='noreply@example.com'
    ),
    EnvVar(
        name='EMAIL_HOST_PASSWORD',
        required=False,
        description='SMTP password',
        example='app-specific-password',
        secret=True
    ),
    EnvVar(
        name='EMAIL_USE_TLS',
        required=False,
        default='True',
        description='Use TLS for email',
        example='True'
    ),
    
    # Stripe (optional)
    EnvVar(
        name='STRIPE_SECRET_KEY',
        required=False,
        description='Stripe secret key',
        example='sk_test_...',
        secret=True
    ),
    EnvVar(
        name='STRIPE_PUBLISHABLE_KEY',
        required=False,
        description='Stripe publishable key',
        example='pk_test_...'
    ),
    EnvVar(
        name='STRIPE_WEBHOOK_SECRET',
        required=False,
        description='Stripe webhook signing secret',
        example='whsec_...',
        secret=True
    ),
    
    # Feature flags
    EnvVar(
        name='MAINTENANCE_MODE',
        required=False,
        default='False',
        description='Enable maintenance mode (True/False)',
        example='False'
    ),
    EnvVar(
        name='DISABLE_SHARING',
        required=False,
        default='False',
        description='Disable share link creation (True/False)',
        example='False'
    ),
    EnvVar(
        name='SKIP_SERVICE_AUTH',
        required=False,
        default='False',
        description='Skip service-to-service auth in dev (True/False)',
        example='False'
    ),
    
    # Security
    EnvVar(
        name='ADMIN_IP_ALLOWLIST',
        required=False,
        description='Comma-separated IP addresses allowed for admin access',
        example='192.168.1.1,10.0.0.1'
    ),
]


def validate_env() -> Tuple[bool, List[str]]:
    """
    Validate all environment variables.
    
    Returns:
        Tuple of (all_valid, error_messages)
    """
    errors = []
    
    for var in ENV_VARS:
        is_valid, error = var.validate()
        if not is_valid:
            errors.append(error)
    
    # Additional validation: LLM endpoint required if provider is vllm
    llm_provider = os.environ.get('LLM_PROVIDER', 'local')
    if llm_provider == 'vllm' and not os.environ.get('LLM_VLLM_ENDPOINT'):
        errors.append("LLM_VLLM_ENDPOINT is required when LLM_PROVIDER=vllm")
    if llm_provider == 'ollama' and not os.environ.get('OLLAMA_ENDPOINT'):
        errors.append("OLLAMA_ENDPOINT is required when LLM_PROVIDER=ollama")
    
    return len(errors) == 0, errors


def print_env_status():
    """Print environment variable status (for debugging)."""
    print("\n" + "="*70)
    print("ENVIRONMENT CONFIGURATION")
    print("="*70)
    
    for var in ENV_VARS:
        value = os.environ.get(var.name)
        status = "✓" if value else ("?" if not var.required else "✗")
        
        # Never print secret values
        if var.secret and value:
            display_value = "***REDACTED***"
        elif value:
            display_value = value
        else:
            display_value = var.default or "(not set)"
        
        required_str = "REQUIRED" if var.required else "optional"
        print(f"{status} {var.name:<30} [{required_str:8}] = {display_value}")
    
    print("="*70 + "\n")


def check_env_or_exit():
    """
    Validate environment and exit if invalid.
    Called during Django startup.
    """
    is_valid, errors = validate_env()
    
    if not is_valid:
        print("\n" + "="*70, file=sys.stderr)
        print("ENVIRONMENT VALIDATION FAILED", file=sys.stderr)
        print("="*70, file=sys.stderr)
        for error in errors:
            print(f"✗ {error}", file=sys.stderr)
        print("\nPlease check .env file and ensure all required variables are set.", file=sys.stderr)
        print("See .env.example for reference.", file=sys.stderr)
        print("="*70 + "\n", file=sys.stderr)
        sys.exit(1)
    
    # Print status in debug mode
    if os.environ.get('DEBUG') == 'True':
        print_env_status()


def get_env_example() -> str:
    """Generate .env.example content from contract."""
    lines = [
        "# AfterResume Environment Configuration",
        "# Copy this file to .env and fill in the values",
        ""
    ]
    
    for var in ENV_VARS:
        lines.append(f"# {var.description}")
        if var.example:
            lines.append(f"# Example: {var.example}")
        
        if var.default:
            lines.append(f"{var.name}={var.default}")
        else:
            lines.append(f"# {var.name}=")
        lines.append("")
    
    return "\n".join(lines)
