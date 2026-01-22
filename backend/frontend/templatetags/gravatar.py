"""
Gravatar template tags for Django.
"""
import hashlib
from urllib.parse import urlencode
from django import template

register = template.Library()


@register.simple_tag
def gravatar_url(email, size=80, default='identicon', rating='g'):
    """
    Generate a Gravatar URL for the given email.
    
    Args:
        email: User's email address
        size: Size of the avatar in pixels (1-2048)
        default: Default image if no Gravatar exists (404, mp, identicon, monsterid, wavatar, retro, robohash, blank)
        rating: Maximum rating (g, pg, r, x)
    
    Returns:
        Gravatar URL
    """
    if not email:
        email = 'guest@digimuse.ai'
    
    # Generate hash
    email_hash = hashlib.md5(email.lower().strip().encode('utf-8')).hexdigest()
    
    # Build URL
    params = urlencode({
        's': str(size),
        'd': default,
        'r': rating
    })
    
    return f"https://www.gravatar.com/avatar/{email_hash}?{params}"
