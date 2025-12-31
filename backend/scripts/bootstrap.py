#!/usr/bin/env python
"""
Bootstrap script - initial setup and configuration.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.core.management import call_command


def main():
    print("=== AfterResume Backend Bootstrap ===\n")
    
    # Run migrations
    print("Running migrations...")
    call_command('migrate', '--no-input')
    
    # Create superuser if env vars provided
    admin_user = os.environ.get('ADMIN_USERNAME')
    admin_email = os.environ.get('ADMIN_EMAIL')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    
    if admin_user and admin_email and admin_password:
        print(f"\nCreating superuser: {admin_user}")
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if not User.objects.filter(username=admin_user).exists():
            User.objects.create_superuser(
                username=admin_user,
                email=admin_email,
                password=admin_password
            )
            print("✓ Superuser created")
        else:
            print("✓ Superuser already exists")
    
    print("\n=== Bootstrap Complete ===")
    print("\nNext steps:")
    print("  1. Run server: python manage.py runserver")
    print("  2. Run worker: python manage.py run_huey")
    print("  3. Visit: http://localhost:8000/api/healthz/")


if __name__ == '__main__':
    main()
