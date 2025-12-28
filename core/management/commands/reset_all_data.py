"""
Management command to completely reset and reload all data.
Safe to run on both local and production environments.

This command:
1. Clears all transactional data (FAs, Lots, Evaluations, Notifications)
2. Loads reference data (Camouflage types)
3. Creates test users (Partners, Inspectors, Staff)
4. Creates a superuser (mcadmin)
5. Creates test FA and Lot data

Usage:
    python manage.py reset_all_data
    
For production via prod_run.sh:
    ./scripts/prod_run.sh reset_all_data
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth.models import User
from django.db import connection
from accounts.models import UserProfile, PartnerCompany
from inspections.models import (
    FirstArticleInspection, LotAcceptance, MonthlyReport,
    FAEvaluation, FAColorEvaluation,
    LotEvaluation, LotSampleEvaluation, LotSampleColorEvaluation
)
from notifications.models import Notification
from core.models import CamouflageType


class Command(BaseCommand):
    help = 'Reset and reload all data - safe for local and production'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-superuser',
            action='store_true',
            help='Skip creating mcadmin superuser (if it already exists)',
        )
        parser.add_argument(
            '--skip-test-data',
            action='store_true',
            help='Skip creating test FA/Lot data (users and reference data only)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('RESETTING ALL DATA'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write('')

        # Step 1: Clear all transactional data
        self.clear_all_data()

        # Step 2: Load reference data
        self.stdout.write(self.style.HTTP_INFO('\n[Step 2] Loading reference data...'))
        call_command('load_initial_data')
        call_command('load_variant_colors')

        # Step 3: Create superuser
        if not options['skip_superuser']:
            self.create_superuser()
        else:
            self.stdout.write(self.style.HTTP_INFO('\n[Step 3] Skipping superuser creation'))

        # Step 4: Create test users
        self.create_test_users()

        # Step 5: Create test data
        if not options['skip_test_data']:
            self.stdout.write(self.style.HTTP_INFO('\n[Step 5] Creating test FA/Lot data...'))
            call_command('create_test_data')
        else:
            self.stdout.write(self.style.HTTP_INFO('\n[Step 5] Skipping test data creation'))

        # Summary
        self.print_summary()

    def clear_all_data(self):
        """Clear all transactional data while preserving reference data"""
        self.stdout.write(self.style.HTTP_INFO('[Step 1] Clearing existing data...'))

        # Clear evaluations first (FK dependencies)
        LotSampleColorEvaluation.objects.all().delete()
        self.stdout.write('  ✓ LotSampleColorEvaluation cleared')

        LotSampleEvaluation.objects.all().delete()
        self.stdout.write('  ✓ LotSampleEvaluation cleared')

        LotEvaluation.objects.all().delete()
        self.stdout.write('  ✓ LotEvaluation cleared')

        FAColorEvaluation.objects.all().delete()
        self.stdout.write('  ✓ FAColorEvaluation cleared')

        FAEvaluation.objects.all().delete()
        self.stdout.write('  ✓ FAEvaluation cleared')

        # Clear lots and FAs
        lot_count = LotAcceptance.objects.count()
        LotAcceptance.objects.all().delete()
        self.stdout.write(f'  ✓ {lot_count} LotAcceptance records cleared')

        fa_count = FirstArticleInspection.objects.count()
        FirstArticleInspection.objects.all().delete()
        self.stdout.write(f'  ✓ {fa_count} FirstArticleInspection records cleared')

        # Clear reports
        report_count = MonthlyReport.objects.count()
        MonthlyReport.objects.all().delete()
        self.stdout.write(f'  ✓ {report_count} MonthlyReport records cleared')

        # Clear notifications
        notif_count = Notification.objects.count()
        Notification.objects.all().delete()
        self.stdout.write(f'  ✓ {notif_count} Notification records cleared')

        # Clear non-superuser users (keep superusers)
        user_count = User.objects.filter(is_superuser=False).count()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write(f'  ✓ {user_count} non-superuser User records cleared')

        # Clear partner companies
        company_count = PartnerCompany.objects.count()
        PartnerCompany.objects.all().delete()
        self.stdout.write(f'  ✓ {company_count} PartnerCompany records cleared')

        self.stdout.write(self.style.SUCCESS('  All transactional data cleared!'))

    def create_superuser(self):
        """Create or update mcadmin superuser"""
        self.stdout.write(self.style.HTTP_INFO('\n[Step 3] Creating superuser...'))

        # mcadmin also uses Resend test email for dev/testing
        user, created = User.objects.get_or_create(
            username='mcadmin',
            defaults={
                'email': 'delivered+mcadmin@resend.dev',
                'first_name': 'Multicam',
                'last_name': 'Admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )

        if created:
            user.set_password('mcadmin123')
            user.save()
            self.stdout.write(self.style.SUCCESS('  ✓ Created superuser: mcadmin'))
        else:
            # Ensure superuser status and update email
            user.is_staff = True
            user.is_superuser = True
            user.email = 'delivered+mcadmin@resend.dev'
            user.set_password('mcadmin123')
            user.save()
            self.stdout.write(self.style.WARNING('  ↻ Updated superuser: mcadmin'))

        # Set up profile for full_admin
        profile = user.profile
        profile.user_functionality = 'admin'
        profile.admin_role = 'full_admin'
        profile.company_name = 'Multicam'
        profile.technical_email = 'delivered+mcadmin@resend.dev'
        profile.save()
        self.stdout.write('  → Profile: Full Admin')

    def create_test_users(self):
        """Create test users and partner companies"""
        self.stdout.write(self.style.HTTP_INFO('\n[Step 4] Creating test users...'))

        # Create partner companies
        company1, _ = PartnerCompany.objects.get_or_create(
            code='ACME',
            defaults={
                'name': 'ACME Corp',
                'contact_name': 'John Acme',
                'contact_email': 'contact@acmecorp.com',
                'status': 'active',
            }
        )
        self.stdout.write(f'  ✓ Company: {company1.name} ({company1.code})')

        company2, _ = PartnerCompany.objects.get_or_create(
            code='GLOBEX',
            defaults={
                'name': 'Globex Industries',
                'contact_name': 'Jane Globex',
                'contact_email': 'contact@globex.com',
                'status': 'active',
            }
        )
        self.stdout.write(f'  ✓ Company: {company2.name} ({company2.code})')

        # Test users - using Resend test emails (delivered+username@resend.dev)
        # These emails always succeed in Resend for testing purposes
        test_users = [
            # ACME Partners
            {
                'username': 'partner1a',
                'email': 'delivered+partner1a@resend.dev',
                'password': 'partner1a123',
                'first_name': 'Alice',
                'last_name': 'Anderson',
                'is_staff': False,
                'profile': {
                    'user_functionality': 'partner',
                    'company': company1,
                    'company_name': 'ACME Corp',
                    'technical_email': 'delivered+partner1a@resend.dev',
                }
            },
            {
                'username': 'partner1b',
                'email': 'delivered+partner1b@resend.dev',
                'password': 'partner1b123',
                'first_name': 'Bob',
                'last_name': 'Baker',
                'is_staff': False,
                'profile': {
                    'user_functionality': 'partner',
                    'company': company1,
                    'company_name': 'ACME Corp',
                    'technical_email': 'delivered+partner1b@resend.dev',
                }
            },
            # GLOBEX Partners
            {
                'username': 'partner2a',
                'email': 'delivered+partner2a@resend.dev',
                'password': 'partner2a123',
                'first_name': 'Charlie',
                'last_name': 'Chen',
                'is_staff': False,
                'profile': {
                    'user_functionality': 'partner',
                    'company': company2,
                    'company_name': 'Globex Industries',
                    'technical_email': 'delivered+partner2a@resend.dev',
                }
            },
            {
                'username': 'partner2b',
                'email': 'delivered+partner2b@resend.dev',
                'password': 'partner2b123',
                'first_name': 'Diana',
                'last_name': 'Davis',
                'is_staff': False,
                'profile': {
                    'user_functionality': 'partner',
                    'company': company2,
                    'company_name': 'Globex Industries',
                    'technical_email': 'delivered+partner2b@resend.dev',
                }
            },
            # Inspectors
            {
                'username': 'primary_inspector',
                'email': 'delivered+primary_inspector@resend.dev',
                'password': 'primary123',
                'first_name': 'Primary',
                'last_name': 'Inspector',
                'is_staff': True,
                'profile': {
                    'user_functionality': 'admin',
                    'admin_role': 'primary_inspector',
                    'company_name': 'Multicam QC',
                    'technical_email': 'delivered+primary_inspector@resend.dev',
                }
            },
            {
                'username': 'final_inspector',
                'email': 'delivered+final_inspector@resend.dev',
                'password': 'final123',
                'first_name': 'Final',
                'last_name': 'Inspector',
                'is_staff': True,
                'profile': {
                    'user_functionality': 'admin',
                    'admin_role': 'final_inspector',
                    'company_name': 'Multicam QC',
                    'technical_email': 'delivered+final_inspector@resend.dev',
                }
            },
            # Staff
            {
                'username': 'staff',
                'email': 'delivered+staff@resend.dev',
                'password': 'staff123',
                'first_name': 'Executive',
                'last_name': 'Staff',
                'is_staff': True,
                'profile': {
                    'user_functionality': 'admin',
                    'admin_role': 'staff_executive',
                    'company_name': 'Multicam Executive',
                    'technical_email': 'delivered+staff@resend.dev',
                }
            },
        ]

        for user_data in test_users:
            profile_data = user_data.pop('profile')
            password = user_data.pop('password')

            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults=user_data
            )

            if created:
                user.set_password(password)
                user.save()

            # Update profile
            profile = user.profile
            for key, value in profile_data.items():
                setattr(profile, key, value)
            profile.save()

            role = profile.get_admin_role_display() or 'Partner'
            company = profile_data.get('company')
            company_str = f" ({company.code})" if company else ""
            self.stdout.write(f'  ✓ {user.username}: {role}{company_str}')

    def print_summary(self):
        """Print summary of all created data"""
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('DATA RESET COMPLETE'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        self.stdout.write('TEST CREDENTIALS:')
        self.stdout.write('-' * 70)
        self.stdout.write('')
        self.stdout.write('SUPERUSER:')
        self.stdout.write('  mcadmin / mcadmin123  (Full Admin)')
        self.stdout.write('')
        self.stdout.write('PARTNERS:')
        self.stdout.write('  ACME Corp:')
        self.stdout.write('    partner1a / partner1a123  (Alice Anderson)')
        self.stdout.write('    partner1b / partner1b123  (Bob Baker)')
        self.stdout.write('  Globex Industries:')
        self.stdout.write('    partner2a / partner2a123  (Charlie Chen)')
        self.stdout.write('    partner2b / partner2b123  (Diana Davis)')
        self.stdout.write('')
        self.stdout.write('INSPECTORS:')
        self.stdout.write('  primary_inspector / primary123  (Primary Inspector)')
        self.stdout.write('  final_inspector / final123      (Final Inspector)')
        self.stdout.write('')
        self.stdout.write('STAFF:')
        self.stdout.write('  staff / staff123  (Executive Staff)')
        self.stdout.write('')
        self.stdout.write('-' * 70)
        self.stdout.write(f'FAs: {FirstArticleInspection.objects.count()} | Lots: {LotAcceptance.objects.count()}')
        self.stdout.write('')

