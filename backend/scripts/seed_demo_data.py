#!/usr/bin/env python
"""
Seed demo data for testing.
"""
import os
import sys
from datetime import date, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.contrib.auth import get_user_model
from apps.worklog.services import create_worklog
from apps.jobs.scheduler import create_schedule


def main():
    User = get_user_model()
    
    print("=== Seeding Demo Data ===\n")
    
    # Create demo user
    print("Creating demo user...")
    user, created = User.objects.get_or_create(
        username='demo',
        defaults={
            'email': 'demo@example.com',
            'first_name': 'Demo',
            'last_name': 'User'
        }
    )
    if created:
        user.set_password('demo')
        user.save()
        print("✓ Demo user created")
    else:
        print("✓ Demo user already exists")
    
    # Create sample work logs
    print("\nCreating sample work logs...")
    sample_logs = [
        {
            'date': date.today() - timedelta(days=2),
            'content': 'Implemented job execution system with Huey. Added retry logic and error handling.',
        },
        {
            'date': date.today() - timedelta(days=1),
            'content': 'Built REST API endpoints for worklogs and skills. Integrated DRF serializers.',
        },
        {
            'date': date.today(),
            'content': 'Created observability layer with event timeline. Added structured logging.',
        }
    ]
    
    for log_data in sample_logs:
        create_worklog(
            date=log_data['date'],
            content=log_data['content'],
            source='manual',
            user=user
        )
    print(f"✓ Created {len(sample_logs)} sample work logs")
    
    # Create sample schedule
    print("\nCreating sample schedules...")
    try:
        create_schedule(
            name='daily_skills_refresh',
            job_type='skills.extract',
            cron='@daily',
            payload={'window_days': 30},
            enabled=False  # Disabled by default
        )
        print("✓ Created daily skills refresh schedule")
    except:
        print("✓ Schedule already exists")
    
    print("\n=== Demo Data Seeded ===")
    print(f"\nDemo user credentials:")
    print(f"  Username: demo")
    print(f"  Password: demo")


if __name__ == '__main__':
    main()
