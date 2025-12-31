"""
Django management command to validate environment configuration.
"""
from django.core.management.base import BaseCommand
from apps.api.env_validation import check_env_or_exit, print_env_status


class Command(BaseCommand):
    help = 'Validate environment configuration'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--print-status',
            action='store_true',
            help='Print environment status',
        )
    
    def handle(self, *args, **options):
        if options['print_status']:
            print_env_status()
        else:
            check_env_or_exit()
            self.stdout.write(self.style.SUCCESS('✓ Environment validation passed'))
