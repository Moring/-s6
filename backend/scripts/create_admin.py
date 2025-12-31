#!/usr/bin/env python
"""
Create admin user interactively.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.contrib.auth import get_user_model


def main():
    User = get_user_model()
    
    print("=== Create Admin User ===\n")
    
    username = input("Username: ")
    email = input("Email: ")
    password = input("Password: ")
    
    if User.objects.filter(username=username).exists():
        print(f"\nError: User '{username}' already exists")
        sys.exit(1)
    
    User.objects.create_superuser(
        username=username,
        email=email,
        password=password
    )
    
    print(f"\n✓ Admin user '{username}' created successfully")


if __name__ == '__main__':
    main()
