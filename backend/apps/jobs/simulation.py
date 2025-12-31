"""
Simulation mode for external integrations.
Allows CI/dev environments to run deterministically without external API keys.
"""
from typing import Optional, Dict, Any
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class SimulationMode:
    """
    Manages simulation mode for external integrations.
    
    When enabled, external API calls return simulated responses instead of
    making real calls. This allows:
    - Running tests without API keys
    - Deterministic CI/dev behavior
    - Cost savings in development
    - Safe testing of payment flows
    """
    
    def __init__(self, service_name: str):
        """
        Initialize simulation mode manager.
        
        Args:
            service_name: Name of the external service (stripe, openai, email, etc.)
        """
        self.service_name = service_name
        self.cache_key = f'simulation_mode:{service_name}'
    
    def is_enabled(self) -> bool:
        """
        Check if simulation mode is enabled for this service.
        
        Returns:
            True if simulation mode is enabled
        """
        # Check cache first (admin can toggle)
        cached = cache.get(self.cache_key)
        if cached is not None:
            return cached
        
        # Check settings
        setting_name = f'SIMULATE_{self.service_name.upper()}'
        return getattr(settings, setting_name, False)
    
    def enable(self, ttl: Optional[int] = None) -> None:
        """
        Enable simulation mode.
        
        Args:
            ttl: Optional time-to-live in seconds
        """
        cache.set(self.cache_key, True, ttl)
        logger.info(f'Simulation mode enabled for {self.service_name}')
    
    def disable(self, ttl: Optional[int] = None) -> None:
        """
        Disable simulation mode.
        
        Args:
            ttl: Optional time-to-live in seconds
        """
        cache.set(self.cache_key, False, ttl)
        logger.info(f'Simulation mode disabled for {self.service_name}')
    
    def simulate_or_execute(self, real_func: callable, simulated_response: Any) -> Any:
        """
        Execute function or return simulated response.
        
        Args:
            real_func: Function to execute if simulation mode is disabled
            simulated_response: Response to return if simulation mode is enabled
        
        Returns:
            Either real result or simulated response
        """
        if self.is_enabled():
            logger.info(f'[SIMULATION] {self.service_name}: returning simulated response')
            return simulated_response
        
        return real_func()


# Pre-configured simulation modes
STRIPE_SIMULATION = SimulationMode('stripe')
OPENAI_SIMULATION = SimulationMode('openai')
EMAIL_SIMULATION = SimulationMode('email')
SMS_SIMULATION = SimulationMode('sms')


# Simulated responses for common operations

SIMULATED_STRIPE_CHARGE = {
    'id': 'ch_simulated_test_charge',
    'object': 'charge',
    'amount': 1000,
    'currency': 'usd',
    'status': 'succeeded',
    'paid': True,
    'simulated': True
}

SIMULATED_STRIPE_CUSTOMER = {
    'id': 'cus_simulated_test_customer',
    'object': 'customer',
    'email': 'test@example.com',
    'simulated': True
}

SIMULATED_STRIPE_SUBSCRIPTION = {
    'id': 'sub_simulated_test_subscription',
    'object': 'subscription',
    'status': 'active',
    'simulated': True
}

SIMULATED_OPENAI_COMPLETION = {
    'id': 'chatcmpl_simulated',
    'object': 'chat.completion',
    'created': 1234567890,
    'model': 'gpt-4',
    'choices': [{
        'index': 0,
        'message': {
            'role': 'assistant',
            'content': 'This is a simulated response from OpenAI.'
        },
        'finish_reason': 'stop'
    }],
    'usage': {
        'prompt_tokens': 10,
        'completion_tokens': 20,
        'total_tokens': 30
    },
    'simulated': True
}

SIMULATED_EMAIL_SEND = {
    'message_id': '<simulated@test.com>',
    'status': 'sent',
    'simulated': True
}


# Helper decorators

def simulate_stripe(func):
    """
    Decorator to add Stripe simulation.
    
    Example:
        @simulate_stripe
        def charge_customer(amount):
            return stripe.Charge.create(amount=amount, ...)
    """
    def wrapper(*args, **kwargs):
        return STRIPE_SIMULATION.simulate_or_execute(
            real_func=lambda: func(*args, **kwargs),
            simulated_response=SIMULATED_STRIPE_CHARGE
        )
    return wrapper


def simulate_openai(func):
    """
    Decorator to add OpenAI simulation.
    
    Example:
        @simulate_openai
        def get_completion(prompt):
            return openai.ChatCompletion.create(...)
    """
    def wrapper(*args, **kwargs):
        return OPENAI_SIMULATION.simulate_or_execute(
            real_func=lambda: func(*args, **kwargs),
            simulated_response=SIMULATED_OPENAI_COMPLETION
        )
    return wrapper


def simulate_email(func):
    """
    Decorator to add email simulation.
    
    Example:
        @simulate_email
        def send_email(recipient, subject, body):
            return send_mail(...)
    """
    def wrapper(*args, **kwargs):
        return EMAIL_SIMULATION.simulate_or_execute(
            real_func=lambda: func(*args, **kwargs),
            simulated_response=SIMULATED_EMAIL_SEND
        )
    return wrapper


# Context manager for temporary simulation

class temporary_simulation:
    """
    Context manager for temporary simulation mode.
    
    Usage:
        with temporary_simulation('stripe', enabled=True):
            # Stripe calls will be simulated
            charge = create_charge()
    """
    
    def __init__(self, service_name: str, enabled: bool = True):
        self.service_name = service_name
        self.enabled = enabled
        self.simulation = SimulationMode(service_name)
        self.original_state = None
    
    def __enter__(self):
        self.original_state = self.simulation.is_enabled()
        if self.enabled:
            self.simulation.enable()
        else:
            self.simulation.disable()
        return self.simulation
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.original_state:
            self.simulation.enable()
        else:
            self.simulation.disable()


# Settings validation helper

def get_simulation_status() -> Dict[str, bool]:
    """
    Get simulation status for all services.
    
    Returns:
        Dictionary mapping service names to simulation enabled status
    """
    return {
        'stripe': STRIPE_SIMULATION.is_enabled(),
        'openai': OPENAI_SIMULATION.is_enabled(),
        'email': EMAIL_SIMULATION.is_enabled(),
        'sms': SMS_SIMULATION.is_enabled(),
    }


def validate_simulation_config():
    """
    Validate simulation configuration.
    Warns if production environment has simulation enabled.
    """
    if not settings.DEBUG:
        status = get_simulation_status()
        enabled_services = [k for k, v in status.items() if v]
        
        if enabled_services:
            logger.warning(
                f'Simulation mode enabled in production for: {", ".join(enabled_services)}. '
                f'This should only be used for staging/testing.'
            )
