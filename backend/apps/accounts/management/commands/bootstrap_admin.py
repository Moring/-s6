import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.tenants.models import Tenant
from apps.accounts.models import UserProfile


class Command(BaseCommand):
    help = 'Bootstrap admin user with tenant and profile'
    
    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin')
        
        # Check if user already exists
        user, user_created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        if user_created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created superuser: {username}'))
        else:
            self.stdout.write(self.style.WARNING(f'Superuser already exists: {username}'))
        
        # Ensure tenant exists
        tenant, tenant_created = Tenant.objects.get_or_create(
            owner=user,
            defaults={
                'name': f"{username}'s Organization",
                'is_active': True
            }
        )
        
        if tenant_created:
            self.stdout.write(self.style.SUCCESS(f'Created tenant: {tenant.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'Tenant already exists: {tenant.name}'))
        
        # Ensure profile exists
        profile, profile_created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'tenant': tenant,
                'settings': {}
            }
        )
        
        if profile_created:
            self.stdout.write(self.style.SUCCESS(f'Created profile for: {username}'))
        else:
            # Ensure tenant is set
            if not profile.tenant:
                profile.tenant = tenant
                profile.save()
            self.stdout.write(self.style.WARNING(f'Profile already exists for: {username}'))
        
        self.stdout.write(self.style.SUCCESS('Bootstrap complete!'))
        self.stdout.write(f'Username: {username}')
        self.stdout.write(f'Email: {email}')
        self.stdout.write(f'Tenant: {tenant.name}')
