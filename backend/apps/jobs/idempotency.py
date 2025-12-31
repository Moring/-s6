"""
Idempotency key management for preventing duplicate side effects.
Ensures external operations (Stripe, emails, AI calls, file writes) are not duplicated on retries.
"""
from typing import Optional, Tuple, Any
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from dataclasses import dataclass
import hashlib
import json


@dataclass
class IdempotencyResult:
    """Result of idempotency check."""
    is_duplicate: bool
    cached_result: Optional[Any] = None
    key: Optional[str] = None


class IdempotencyManager:
    """
    Manages idempotency keys to prevent duplicate side effects.
    
    Use this for:
    - Stripe charge creation
    - Email sending
    - AI API calls
    - File writes/uploads
    - External API calls
    
    Usage:
        manager = IdempotencyManager('stripe_charge')
        idempotency_key = manager.generate_key(user_id=user.id, amount=100)
        
        result = manager.check(idempotency_key)
        if result.is_duplicate:
            return result.cached_result
        
        # Perform operation
        charge = stripe.Charge.create(...)
        
        # Store result
        manager.store(idempotency_key, charge, ttl=86400)
    """
    
    def __init__(self, operation_type: str, ttl: int = 86400):
        """
        Initialize idempotency manager.
        
        Args:
            operation_type: Type of operation (e.g., 'stripe_charge', 'email_send')
            ttl: Time-to-live for idempotency keys in seconds (default: 24 hours)
        """
        self.operation_type = operation_type
        self.ttl = ttl
        self.prefix = f'idempotency:{operation_type}'
    
    def generate_key(self, **kwargs) -> str:
        """
        Generate idempotency key from parameters.
        
        Args:
            **kwargs: Parameters that uniquely identify the operation
        
        Returns:
            Idempotency key string
        
        Example:
            key = manager.generate_key(user_id=123, charge_amount=1000, timestamp='2025-12-31')
        """
        # Sort keys for consistency
        sorted_params = json.dumps(kwargs, sort_keys=True)
        
        # Hash parameters
        hash_obj = hashlib.sha256(sorted_params.encode())
        hash_hex = hash_obj.hexdigest()[:16]
        
        return f'{self.prefix}:{hash_hex}'
    
    def check(self, idempotency_key: str) -> IdempotencyResult:
        """
        Check if operation with this key has already been performed.
        
        Args:
            idempotency_key: The idempotency key
        
        Returns:
            IdempotencyResult with is_duplicate and cached_result
        """
        cached = cache.get(idempotency_key)
        
        if cached is not None:
            return IdempotencyResult(
                is_duplicate=True,
                cached_result=cached.get('result'),
                key=idempotency_key
            )
        
        return IdempotencyResult(
            is_duplicate=False,
            key=idempotency_key
        )
    
    def store(self, idempotency_key: str, result: Any, ttl: Optional[int] = None) -> None:
        """
        Store operation result for idempotency checking.
        
        Args:
            idempotency_key: The idempotency key
            result: Result to cache (must be JSON-serializable)
            ttl: Optional custom TTL (uses instance default if not provided)
        """
        ttl = ttl or self.ttl
        
        cache.set(idempotency_key, {
            'result': result,
            'stored_at': timezone.now().isoformat()
        }, ttl)
    
    def invalidate(self, idempotency_key: str) -> None:
        """
        Invalidate an idempotency key (force operation to be re-executed).
        
        Args:
            idempotency_key: The idempotency key to invalidate
        """
        cache.delete(idempotency_key)


# Pre-configured managers for common operations
STRIPE_IDEMPOTENCY = IdempotencyManager('stripe_charge', ttl=86400)  # 24 hours
EMAIL_IDEMPOTENCY = IdempotencyManager('email_send', ttl=3600)  # 1 hour
AI_CALL_IDEMPOTENCY = IdempotencyManager('ai_call', ttl=7200)  # 2 hours
FILE_WRITE_IDEMPOTENCY = IdempotencyManager('file_write', ttl=86400)  # 24 hours


def with_idempotency(operation_type: str, ttl: int = 86400):
    """
    Decorator to add idempotency to a function.
    
    Args:
        operation_type: Type of operation for idempotency key prefix
        ttl: Time-to-live for idempotency keys
    
    Example:
        @with_idempotency('stripe_charge')
        def create_charge(user_id, amount):
            # Function will only execute once per unique (user_id, amount) combination
            return stripe.Charge.create(...)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            manager = IdempotencyManager(operation_type, ttl)
            
            # Generate key from all arguments
            key_params = {
                'func': func.__name__,
                'args': args,
                **kwargs
            }
            idempotency_key = manager.generate_key(**key_params)
            
            # Check for duplicate
            result = manager.check(idempotency_key)
            if result.is_duplicate:
                return result.cached_result
            
            # Execute function
            func_result = func(*args, **kwargs)
            
            # Store result
            manager.store(idempotency_key, func_result, ttl)
            
            return func_result
        
        return wrapper
    return decorator


# Helper functions for common patterns

def ensure_idempotent_stripe_charge(
    user_id: int,
    amount: int,
    currency: str,
    description: str,
    charge_func: callable
) -> Tuple[bool, Any]:
    """
    Ensure Stripe charge is idempotent.
    
    Args:
        user_id: User ID
        amount: Charge amount in cents
        currency: Currency code
        description: Charge description
        charge_func: Function that creates the charge
    
    Returns:
        (was_duplicate, result)
    """
    key = STRIPE_IDEMPOTENCY.generate_key(
        user_id=user_id,
        amount=amount,
        currency=currency,
        description=description
    )
    
    result = STRIPE_IDEMPOTENCY.check(key)
    if result.is_duplicate:
        return True, result.cached_result
    
    charge_result = charge_func()
    STRIPE_IDEMPOTENCY.store(key, charge_result)
    
    return False, charge_result


def ensure_idempotent_email(
    recipient: str,
    subject: str,
    template: str,
    send_func: callable
) -> Tuple[bool, Any]:
    """
    Ensure email is sent only once.
    
    Args:
        recipient: Email recipient
        subject: Email subject
        template: Email template name
        send_func: Function that sends the email
    
    Returns:
        (was_duplicate, result)
    """
    key = EMAIL_IDEMPOTENCY.generate_key(
        recipient=recipient,
        subject=subject,
        template=template,
        date=timezone.now().date().isoformat()  # Same email can be sent on different days
    )
    
    result = EMAIL_IDEMPOTENCY.check(key)
    if result.is_duplicate:
        return True, result.cached_result
    
    email_result = send_func()
    EMAIL_IDEMPOTENCY.store(key, email_result)
    
    return False, email_result


def ensure_idempotent_ai_call(
    provider: str,
    model: str,
    prompt_hash: str,
    ai_func: callable
) -> Tuple[bool, Any]:
    """
    Ensure AI API call is idempotent (prevents duplicate charges).
    
    Args:
        provider: AI provider (openai, anthropic, etc.)
        model: Model name
        prompt_hash: Hash of the prompt
        ai_func: Function that makes the AI call
    
    Returns:
        (was_duplicate, result)
    """
    key = AI_CALL_IDEMPOTENCY.generate_key(
        provider=provider,
        model=model,
        prompt_hash=prompt_hash
    )
    
    result = AI_CALL_IDEMPOTENCY.check(key)
    if result.is_duplicate:
        return True, result.cached_result
    
    ai_result = ai_func()
    AI_CALL_IDEMPOTENCY.store(key, ai_result)
    
    return False, ai_result
