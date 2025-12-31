"""
Stripe webhook handlers for processing payment events.
Implements idempotent event processing.
"""
import stripe
from django.conf import settings
from django.db import transaction
from apps.billing.models import StripeEvent, BillingProfile
from apps.billing.services import credit_reserve
from apps.billing.tools import get_or_create_reserve_account
from apps.tenants.models import Tenant
from apps.observability.services import emit_event
import logging

logger = logging.getLogger(__name__)


def verify_webhook_signature(payload, sig_header, webhook_secret):
    """
    Verify Stripe webhook signature.
    
    Args:
        payload: Raw request body
        sig_header: Stripe-Signature header value
        webhook_secret: Webhook signing secret from Stripe
    
    Returns:
        stripe.Event instance
    
    Raises:
        ValueError, stripe.error.SignatureVerificationError
    """
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        return event
    except ValueError as e:
        logger.error(f'Invalid webhook payload: {e}')
        raise
    except stripe.error.SignatureVerificationError as e:
        logger.error(f'Invalid webhook signature: {e}')
        raise


@transaction.atomic
def process_webhook_event(event_data):
    """
    Process a Stripe webhook event idempotently.
    
    Args:
        event_data: Stripe event dict
    
    Returns:
        dict with processing result
    """
    event_id = event_data['id']
    event_type = event_data['type']
    
    # Check if already processed (idempotency)
    payload_hash = StripeEvent.compute_payload_hash(event_data)
    
    existing_event = StripeEvent.objects.filter(event_id=event_id).first()
    if existing_event:
        logger.info(f'Webhook event {event_id} already processed, skipping')
        return {
            'status': 'skipped',
            'reason': 'already_processed',
            'event_id': event_id,
        }
    
    # Create event record
    stripe_event = StripeEvent.objects.create(
        event_id=event_id,
        event_type=event_type,
        payload_hash=payload_hash,
        processing_result='processing',
    )
    
    try:
        # Route to appropriate handler
        if event_type == 'checkout.session.completed':
            result = handle_checkout_completed(event_data)
        elif event_type == 'payment_intent.succeeded':
            result = handle_payment_succeeded(event_data)
        elif event_type == 'customer.subscription.created':
            result = handle_subscription_created(event_data)
        elif event_type == 'customer.subscription.updated':
            result = handle_subscription_updated(event_data)
        elif event_type == 'customer.subscription.deleted':
            result = handle_subscription_deleted(event_data)
        elif event_type == 'invoice.payment_failed':
            result = handle_invoice_payment_failed(event_data)
        else:
            result = {'status': 'ignored', 'reason': 'unhandled_event_type'}
        
        # Update event record
        stripe_event.processing_result = 'success'
        stripe_event.tenant_id = result.get('tenant_id')
        stripe_event.save()
        
        emit_event(
            event_type=f'billing.webhook_{event_type.replace(".", "_")}',
            tenant_id=result.get('tenant_id'),
            details={
                'stripe_event_id': event_id,
                'result': result,
            }
        )
        
        return result
        
    except Exception as e:
        logger.error(f'Failed to process webhook event {event_id}: {e}', exc_info=True)
        
        stripe_event.processing_result = 'failed'
        stripe_event.error_message = str(e)
        stripe_event.save()
        
        emit_event(
            event_type='billing.webhook_processing_failed',
            details={
                'stripe_event_id': event_id,
                'event_type': event_type,
                'error': str(e),
            }
        )
        
        raise


def handle_checkout_completed(event_data):
    """
    Handle checkout.session.completed event - credit reserve balance.
    """
    session = event_data['data']['object']
    
    # Extract metadata
    tenant_id = session['metadata'].get('tenant_id')
    purpose = session['metadata'].get('purpose')
    amount_cents = int(session['metadata'].get('amount_cents', 0))
    
    if not tenant_id or purpose != 'reserve_topup':
        return {'status': 'ignored', 'reason': 'not_reserve_topup'}
    
    # Get tenant
    try:
        tenant = Tenant.objects.get(id=tenant_id)
    except Tenant.DoesNotExist:
        raise ValueError(f'Tenant {tenant_id} not found')
    
    # Ensure reserve account exists
    get_or_create_reserve_account(tenant)
    
    # Credit reserve
    entry = credit_reserve(
        tenant=tenant,
        amount_cents=amount_cents,
        entry_type='topup',
        stripe_event_id=event_data['id'],
        notes=f'Checkout session {session["id"]} completed'
    )
    
    logger.info(f'Credited {amount_cents} cents to tenant {tenant_id} from checkout session {session["id"]}')
    
    return {
        'status': 'processed',
        'tenant_id': tenant.id,
        'amount_cents': amount_cents,
        'ledger_entry_id': entry.id,
    }


def handle_payment_succeeded(event_data):
    """
    Handle payment_intent.succeeded event.
    """
    payment_intent = event_data['data']['object']
    
    # Check if this is part of a checkout session (already handled)
    if payment_intent.get('metadata', {}).get('purpose') == 'reserve_topup':
        return {'status': 'deferred', 'reason': 'handled_by_checkout_session'}
    
    return {'status': 'ignored', 'reason': 'not_reserve_related'}


def handle_subscription_created(event_data):
    """
    Handle customer.subscription.created event.
    """
    subscription = event_data['data']['object']
    customer_id = subscription['customer']
    
    # Find billing profile
    try:
        billing_profile = BillingProfile.objects.get(stripe_customer_id=customer_id)
    except BillingProfile.DoesNotExist:
        logger.warning(f'Billing profile not found for customer {customer_id}')
        return {'status': 'ignored', 'reason': 'customer_not_found'}
    
    # Update subscription info
    billing_profile.stripe_subscription_id = subscription['id']
    billing_profile.subscription_status = subscription['status']
    billing_profile.subscription_current_period_start = timezone.datetime.fromtimestamp(
        subscription['current_period_start'], tz=timezone.utc
    )
    billing_profile.subscription_current_period_end = timezone.datetime.fromtimestamp(
        subscription['current_period_end'], tz=timezone.utc
    )
    billing_profile.save()
    
    logger.info(f'Subscription {subscription["id"]} created for customer {customer_id}')
    
    return {
        'status': 'processed',
        'tenant_id': billing_profile.tenant.id,
        'subscription_id': subscription['id'],
    }


def handle_subscription_updated(event_data):
    """
    Handle customer.subscription.updated event.
    """
    subscription = event_data['data']['object']
    subscription_id = subscription['id']
    
    # Find billing profile
    try:
        billing_profile = BillingProfile.objects.get(stripe_subscription_id=subscription_id)
    except BillingProfile.DoesNotExist:
        logger.warning(f'Billing profile not found for subscription {subscription_id}')
        return {'status': 'ignored', 'reason': 'subscription_not_found'}
    
    # Update status
    billing_profile.subscription_status = subscription['status']
    billing_profile.subscription_current_period_start = timezone.datetime.fromtimestamp(
        subscription['current_period_start'], tz=timezone.utc
    )
    billing_profile.subscription_current_period_end = timezone.datetime.fromtimestamp(
        subscription['current_period_end'], tz=timezone.utc
    )
    billing_profile.save()
    
    logger.info(f'Subscription {subscription_id} updated: status={subscription["status"]}')
    
    return {
        'status': 'processed',
        'tenant_id': billing_profile.tenant.id,
        'subscription_id': subscription_id,
        'new_status': subscription['status'],
    }


def handle_subscription_deleted(event_data):
    """
    Handle customer.subscription.deleted event.
    """
    subscription = event_data['data']['object']
    subscription_id = subscription['id']
    
    # Find billing profile
    try:
        billing_profile = BillingProfile.objects.get(stripe_subscription_id=subscription_id)
    except BillingProfile.DoesNotExist:
        return {'status': 'ignored', 'reason': 'subscription_not_found'}
    
    # Update status
    billing_profile.subscription_status = 'canceled'
    billing_profile.save()
    
    logger.info(f'Subscription {subscription_id} canceled')
    
    return {
        'status': 'processed',
        'tenant_id': billing_profile.tenant.id,
        'subscription_id': subscription_id,
    }


def handle_invoice_payment_failed(event_data):
    """
    Handle invoice.payment_failed event.
    """
    invoice = event_data['data']['object']
    customer_id = invoice['customer']
    
    # Find billing profile
    try:
        billing_profile = BillingProfile.objects.get(stripe_customer_id=customer_id)
    except BillingProfile.DoesNotExist:
        return {'status': 'ignored', 'reason': 'customer_not_found'}
    
    # Emit event for notification system
    emit_event(
        event_type='billing.payment_failed',
        tenant_id=billing_profile.tenant.id,
        details={
            'invoice_id': invoice['id'],
            'amount_due': invoice['amount_due'],
            'attempt_count': invoice['attempt_count'],
        }
    )
    
    logger.warning(f'Payment failed for invoice {invoice["id"]}, customer {customer_id}')
    
    return {
        'status': 'processed',
        'tenant_id': billing_profile.tenant.id,
        'invoice_id': invoice['id'],
    }
