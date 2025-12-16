"""
Emergency command to create or promote a user to admin status.
Usage: python manage.py create_admin <username>
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from accounts.models import UserProfile


class Command(BaseCommand):
    help = 'Create or promote a user to admin status (emergency recovery)'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to create or promote')
        parser.add_argument(
            '--password',
            type=str,
            help='Password for new user (required if creating new user)',
            default=None
        )
        parser.add_argument(
            '--superuser',
            action='store_true',
            help='Also grant Django superuser status',
        )

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        make_superuser = options['superuser']
        
        # Check if user exists
        try:
            user = User.objects.get(username=username)
            self.stdout.write(f'Found existing user: {username}')
            created_user = False
        except User.DoesNotExist:
            if not password:
                raise CommandError(
                    f'User "{username}" does not exist. '
                    'Provide --password to create a new user.'
                )
            user = User.objects.create_user(
                username=username,
                password=password,
                is_staff=True,
                is_superuser=make_superuser
            )
            self.stdout.write(self.style.SUCCESS(f'Created new user: {username}'))
            created_user = True
        
        # Ensure staff status
        if not user.is_staff:
            user.is_staff = True
            user.save(update_fields=['is_staff'])
            self.stdout.write('  → Granted staff status')
        
        # Superuser if requested
        if make_superuser and not user.is_superuser:
            user.is_superuser = True
            user.save(update_fields=['is_superuser'])
            self.stdout.write('  → Granted superuser status')
        
        # Get or create profile
        profile, profile_created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'company_name': f'{username} (Admin)',
                'technical_email': user.email or f'{username}@admin.local',
                'user_functionality': 'admin',
                'admin_role': 'full_admin',
            }
        )
        
        if not profile_created:
            # Update existing profile
            profile.user_functionality = 'admin'
            profile.admin_role = 'full_admin'
            profile.set_default_permissions()
            profile.save()
            self.stdout.write('  → Updated profile to admin with full permissions')
        else:
            self.stdout.write('  → Created admin profile with full permissions')
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✓ {username} is now a full admin with all permissions.'
        ))
        if created_user:
            self.stdout.write(f'  Login: {username} / {password}')
        self.stdout.write(f'  Django Admin: {"Yes (superuser)" if user.is_superuser else "Yes (staff)"}')
        self.stdout.write(f'  Portal Admin: Yes (full_admin)')

