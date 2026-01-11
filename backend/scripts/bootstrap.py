#!/usr/bin/env python
"""
Bootstrap script - initial setup and configuration.
Idempotent - safe to run multiple times.
"""
import os
import sys
import time

# Add parent directory to path so we can import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django

# Wait for database to be ready
def wait_for_db(max_retries=30):
    """Wait for database to be available."""
    from django.db import connection
    from django.db.utils import OperationalError
    
    print("Waiting for database...")
    retries = 0
    while retries < max_retries:
        try:
            connection.ensure_connection()
            print("✓ Database is ready")
            return True
        except OperationalError:
            retries += 1
            print(f"  Database not ready, retrying ({retries}/{max_retries})...")
            time.sleep(2)
    
    print("✗ Database connection failed")
    return False


def main():
    # Set up Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
    django.setup()
    
    print("\n=== AfterResume Backend Bootstrap ===\n")
    
    # Wait for database
    if not wait_for_db():
        sys.exit(1)
    
    # Import after Django setup
    from django.core.management import call_command
    from django.contrib.auth import get_user_model
    from apps.tenants.services import create_tenant_for_user
    
    User = get_user_model()
    
    # Run migrations
    # Optionally create migrations (useful in dev) before applying them.
    from django.conf import settings

    print("\nRunning migrations...")
    try:
        force_make = os.environ.get('FORCE_MAKEMIGRATIONS', '0').lower() in ('1', 'true', 'yes')
        if settings.DEBUG or force_make:
            try:
                print("-> Running makemigrations (dev/forced)...")
                call_command('makemigrations', '--no-input')
                print("-> makemigrations complete")
            except Exception:
                # Don't fail bootstrap if makemigrations has nothing to do or errors
                print("-> makemigrations skipped or failed (continuing)")

        call_command('migrate', '--no-input')
        print("✓ Migrations complete")
    except Exception as exc:
        print(f"✗ Migrations failed: {exc}")
        raise
    
    # Get admin credentials from environment (for display later)
    admin_user = os.environ.get('ADMIN_USERNAME', 'davmor')
    admin_email = os.environ.get('ADMIN_EMAIL', 'david@digimse.com')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'sl15op33')
    
    # Create superuser and profile using management command
    print(f"\nBootstrapping admin user...")
    try:
        call_command('bootstrap_admin')
        print(f"✓ Admin bootstrap complete")
    except Exception as exc:
        print(f"✗ Admin bootstrap failed: {exc}")
        # Try legacy method as fallback
        print(f"\nChecking for superuser: {admin_user}")
        user = None
        if not User.objects.filter(username=admin_user).exists():
            user = User.objects.create_superuser(
                username=admin_user,
                email=admin_email,
                password=admin_password
            )
            print(f"✓ Superuser created: {admin_user}")
        else:
            user = User.objects.get(username=admin_user)
            print(f"✓ Superuser already exists: {admin_user}")
        
        # Create tenant for admin user
        if user:
            print(f"\nCreating tenant for {admin_user}...")
            tenant = create_tenant_for_user(user)
            print(f"✓ Tenant created: {tenant.name}")
    
    # Create Site for allauth
    from django.contrib.sites.models import Site
    site, created = Site.objects.get_or_create(
        pk=1,
        defaults={'domain': 'localhost:8000', 'name': 'AfterResume'}
    )
    if created:
        print("✓ Site created for allauth")
    else:
        print("✓ Site already exists")
    
    # Create scheduled jobs
    print("\nSetting up scheduled jobs...")
    from apps.jobs.models import Schedule
    
    # Daily metrics computation
    metrics_schedule, created = Schedule.objects.get_or_create(
        name='daily_metrics_computation',
        defaults={
            'job_type': 'system.compute_metrics',
            'cron': '@daily',
            'payload': {'bucket': 'daily', 'lookback_days': 30},
            'enabled': True
        }
    )
    if created:
        print("✓ Daily metrics computation schedule created")
    else:
        print("✓ Daily metrics computation schedule already exists")
    
    print("\n=== Bootstrap Complete ===")
    print("\nServices ready:")
    print("  • Database: ✓")
    print(f"  • Admin user: {admin_user}")
    print(f"  • Admin email: {admin_email}")
    print("\nNext steps:")
    print("  1. Backend API: http://localhost:8000/api/healthz/")
    print("  2. Admin panel: http://localhost:8000/admin/")
    print("  3. Login: http://localhost:8000/accounts/login/")


if __name__ == '__main__':
    main()
