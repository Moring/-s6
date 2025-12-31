"""
Signal handlers for account events.
"""
from django.dispatch import receiver
from allauth.account.signals import user_logged_in
import logging

logger = logging.getLogger(__name__)


# Note: Token retrieval is handled in the custom allauth adapter
# See apps.accounts.adapters
