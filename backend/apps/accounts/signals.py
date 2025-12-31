from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create a UserProfile when a new User is created.
    Links to the user's tenant (assumes tenant already exists).
    """
    if created:
        # Get or create tenant for this user
        from apps.tenants.models import Tenant
        
        tenant, _ = Tenant.objects.get_or_create(
            owner=instance,
            defaults={
                'name': f"{instance.username}'s Organization",
                'is_active': True
            }
        )
        
        # Create profile
        UserProfile.objects.create(
            user=instance,
            tenant=tenant,
            settings={}
        )


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Ensure profile exists and save it when user is saved.
    """
    if not hasattr(instance, 'profile'):
        # Profile doesn't exist, create it
        from apps.tenants.models import Tenant
        tenant, _ = Tenant.objects.get_or_create(
            owner=instance,
            defaults={
                'name': f"{instance.username}'s Organization",
                'is_active': True
            }
        )
        UserProfile.objects.create(
            user=instance,
            tenant=tenant,
            settings={}
        )
    else:
        instance.profile.save()
