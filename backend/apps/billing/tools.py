"""
Billing tools for Stripe integration.
These are callable tools used in DAG workflows and API endpoints.
"""
import stripe
from django.conf import settings
from apps.billing.models import BillingProfile, ReserveAccount, StripeEvent
from apps.observability.services import emit_event
import logging

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY if hasattr(settings, 'STRIPE_SECRET_KEY') else None


def stripe_get_or_create_customer(tenant):
    """
    Tool: Get or create Stripe customer for a tenant.
    
    Args:
        tenant: Tenant model instance
    
    Returns:
        dict with customer_id and created flag
    """
    emit_event(
        event_type='billing.customer_check',
        tenant_id=tenant.id,
        details={'action': 'get_or_create_customer'}
    )
    
    # Get or create billing profile
    billing_profile, profile_created = BillingProfile.objects.get_or_create(
        tenant=tenant,
        defaults={'plan_tier': 'free'}
    )
    
    # Check if customer already exists
    if billing_profile.stripe_customer_id:
        emit_event(
            event_type='billing.customer_exists',
            tenant_id=tenant.id,
            details={'customer_id': billing_profile.stripe_customer_id}
        )
        return {
            'customer_id': billing_profile.stripe_customer_id,
            'created': False,
        }
    
    # Create Stripe customer
    try:
        if not stripe.api_key:
            logger.warning('Stripe API key not configured, using mock customer ID')
            mock_customer_id = f'cus_mock_{tenant.id}'
            billing_profile.stripe_customer_id = mock_customer_id
            billing_profile.save()
            
            emit_event(
                event_type='billing.customer_created_mock',
                tenant_id=tenant.id,
                details={'customer_id': mock_customer_id}
            )
            
            return {
                'customer_id': mock_customer_id,
                'created': True,
                'mock': True,
            }
        
        customer = stripe.Customer.create(
            email=tenant.owner.email,
            name=tenant.name,
            metadata={
                'tenant_id': str(tenant.id),
                'tenant_name': tenant.name,
            }
        )
        
        billing_profile.stripe_customer_id = customer.id
        billing_profile.save()
        
        emit_event(
            event_type='billing.customer_created',
            tenant_id=tenant.id,
            details={'customer_id': customer.id}
        )
        
        return {
            'customer_id': customer.id,
            'created': True,
        }
        
    except Exception as e:
        logger.error(f'Failed to create Stripe customer for tenant {tenant.id}: {e}')
        emit_event(
            event_type='billing.customer_creation_failed',
            tenant_id=tenant.id,
            details={'error': str(e)}
        )
        raise


def stripe_create_checkout_session(tenant, amount_cents, success_url, cancel_url):
    """
    Tool: Create Stripe Checkout session for reserve top-up.
    
    Args:
        tenant: Tenant model instance
        amount_cents: Amount to charge in cents
        success_url: URL to redirect on success
        cancel_url: URL to redirect on cancel
    
    Returns:
        dict with checkout_url and session_id
    """
    # Ensure customer exists
    customer_info = stripe_get_or_create_customer(tenant)
    customer_id = customer_info['customer_id']
    
    emit_event(
        event_type='billing.checkout_session_create',
        tenant_id=tenant.id,
        details={
            'amount_cents': amount_cents,
            'customer_id': customer_id,
        }
    )
    
    try:
        if not stripe.api_key:
            logger.warning('Stripe API key not configured, returning mock checkout URL')
            mock_session_id = f'cs_mock_{tenant.id}_{amount_cents}'
            
            emit_event(
                event_type='billing.checkout_session_created_mock',
                tenant_id=tenant.id,
                details={'session_id': mock_session_id}
            )
            
            return {
                'checkout_url': f'/billing/mock-checkout/?session={mock_session_id}',
                'session_id': mock_session_id,
                'mock': True,
            }
        
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Reserve Balance Top-up',
                        'description': f'Add  to your reserve balance',
                    },
                    'unit_amount': amount_cents,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'tenant_id': str(tenant.id),
                'purpose': 'reserve_topup',
                'amount_cents': str(amount_cents),
            }
        )
        
        emit_event(
            event_type='billing.checkout_session_created',
            tenant_id=tenant.id,
            details={
                'session_id': session.id,
                'checkout_url': session.url,
            }
        )
        
        return {
            'checkout_url': session.url,
            'session_id': session.id,
        }
        
    except Exception as e:
        logger.error(f'Failed to create checkout session for tenant {tenant.id}: {e}')
        emit_event(
            event_type='billing.checkout_session_failed',
            tenant_id=tenant.id,
            details={'error': str(e)}
        )
        raise


def stripe_create_portal_session(tenant, return_url):
    """
    Tool: Create Stripe Customer Portal session.
    
    Args:
        tenant: Tenant model instance
        return_url: URL to return to after portal session
    
    Returns:
        dict with portal_url
    """
    # Ensure customer exists
    customer_info = stripe_get_or_create_customer(tenant)
    customer_id = customer_info['customer_id']
    
    billing_profile = BillingProfile.objects.get(tenant=tenant)
    
    if not billing_profile.allow_portal_access:
        raise ValueError('Portal access not enabled for this tenant')
    
    emit_event(
        event_type='billing.portal_session_create',
        tenant_id=tenant.id,
        details={'customer_id': customer_id}
    )
    
    try:
        if not stripe.api_key:
            logger.warning('Stripe API key not configured, returning mock portal URL')
            
            emit_event(
                event_type='billing.portal_session_created_mock',
                tenant_id=tenant.id,
                details={'mock': True}
            )
            
            return {
                'portal_url': f'/billing/mock-portal/?customer={customer_id}',
                'mock': True,
            }
        
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        
        emit_event(
            event_type='billing.portal_session_created',
            tenant_id=tenant.id,
            details={'portal_url': session.url}
        )
        
        return {
            'portal_url': session.url,
        }
        
    except Exception as e:
        logger.error(f'Failed to create portal session for tenant {tenant.id}: {e}')
        emit_event(
            event_type='billing.portal_session_failed',
            tenant_id=tenant.id,
            details={'error': str(e)}
        )
        raise


def get_or_create_reserve_account(tenant):
    """
    Tool: Get or create reserve account for a tenant.
    
    Args:
        tenant: Tenant model instance
    
    Returns:
        ReserveAccount instance
    """
    account, created = ReserveAccount.objects.get_or_create(
        tenant=tenant,
        defaults={
            'balance_cents': 0,
            'currency': 'USD',
            'low_balance_policy': 'warn',
        }
    )
    
    if created:
        emit_event(
            event_type='billing.reserve_account_created',
            tenant_id=tenant.id,
            details={'initial_balance_cents': 0}
        )
    
    return account
