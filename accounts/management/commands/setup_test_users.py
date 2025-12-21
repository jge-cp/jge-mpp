"""
Management command to set up test users for MVP testing.
Creates: partner, primary_inspector, final_inspector, staff users.
Creates: Test Partner Company with partner users linked.
Clears existing test data (except specified users).
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile, PartnerCompany
from inspections.models import FirstArticleInspection, LotAcceptance, MonthlyReport


class Command(BaseCommand):
    help = 'Set up test users for MVP testing and clear FA/Lot data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-user',
            type=str,
            default='llepore',
            help='Username to keep (default: llepore)'
        )

    def handle(self, *args, **options):
        keep_user = options['keep_user']
        
        self.stdout.write(self.style.WARNING(f'Keeping user: {keep_user}'))
        
        # Clear FA and Lot data
        fa_count = FirstArticleInspection.objects.count()
        lot_count = LotAcceptance.objects.count()
        report_count = MonthlyReport.objects.count()
        
        FirstArticleInspection.objects.all().delete()
        LotAcceptance.objects.all().delete()
        MonthlyReport.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS(f'Cleared {fa_count} First Article Inspections'))
        self.stdout.write(self.style.SUCCESS(f'Cleared {lot_count} Lot Acceptances'))
        self.stdout.write(self.style.SUCCESS(f'Cleared {report_count} Monthly Reports'))
        
        # Create test Partner Companies
        company1, created1 = PartnerCompany.objects.get_or_create(
            code='ACME',
            defaults={
                'name': 'Acme Fabrics Inc',
                'contact_name': 'John Acme',
                'contact_email': 'contact@acmefabrics.com',
                'status': 'active',
            }
        )
        if created1:
            self.stdout.write(self.style.SUCCESS(f'Created Partner Company: {company1.name} ({company1.code})'))
        else:
            self.stdout.write(self.style.WARNING(f'Partner Company already exists: {company1.name}'))
        
        company2, created2 = PartnerCompany.objects.get_or_create(
            code='GLOBEX',
            defaults={
                'name': 'Globex Textiles Ltd',
                'contact_name': 'Jane Globex',
                'contact_email': 'contact@globextextiles.com',
                'status': 'active',
            }
        )
        if created2:
            self.stdout.write(self.style.SUCCESS(f'Created Partner Company: {company2.name} ({company2.code})'))
        else:
            self.stdout.write(self.style.WARNING(f'Partner Company already exists: {company2.name}'))
        
        # Delete users except the keep_user and superusers
        users_to_delete = User.objects.exclude(username=keep_user).exclude(is_superuser=True)
        user_count = users_to_delete.count()
        users_to_delete.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {user_count} users (kept {keep_user} and superusers)'))
        
        # Create test users (4 partners: 2 per company, 3 inspectors/staff)
        test_users = [
            # Company 1: ACME
            {
                'username': 'partner1a',
                'email': 'partner1a@acmefabrics.com',
                'password': 'partner1a123',
                'first_name': 'Alice',
                'last_name': 'Anderson',
                'is_staff': False,
                'profile': {
                    'user_functionality': 'partner',
                    'company': company1,
                    'company_name': 'Acme Fabrics Inc',
                    'technical_email': 'partner1a@acmefabrics.com',
                }
            },
            {
                'username': 'partner1b',
                'email': 'partner1b@acmefabrics.com',
                'password': 'partner1b123',
                'first_name': 'Bob',
                'last_name': 'Baker',
                'is_staff': False,
                'profile': {
                    'user_functionality': 'partner',
                    'company': company1,
                    'company_name': 'Acme Fabrics Inc',
                    'technical_email': 'partner1b@acmefabrics.com',
                }
            },
            # Company 2: GLOBEX
            {
                'username': 'partner2a',
                'email': 'partner2a@globextextiles.com',
                'password': 'partner2a123',
                'first_name': 'Charlie',
                'last_name': 'Chen',
                'is_staff': False,
                'profile': {
                    'user_functionality': 'partner',
                    'company': company2,
                    'company_name': 'Globex Textiles Ltd',
                    'technical_email': 'partner2a@globextextiles.com',
                }
            },
            {
                'username': 'partner2b',
                'email': 'partner2b@globextextiles.com',
                'password': 'partner2b123',
                'first_name': 'Diana',
                'last_name': 'Davis',
                'is_staff': False,
                'profile': {
                    'user_functionality': 'partner',
                    'company': company2,
                    'company_name': 'Globex Textiles Ltd',
                    'technical_email': 'partner2b@globextextiles.com',
                }
            },
            {
                'username': 'primary_inspector',
                'email': 'primary@test.com',
                'password': 'primary_inspector123',
                'first_name': 'Primary',
                'last_name': 'Inspector',
                'is_staff': True,
                'profile': {
                    'user_functionality': 'admin',
                    'admin_role': 'primary_inspector',
                    'company_name': 'Multicam QC',
                    'technical_email': 'primary@test.com',
                }
            },
            {
                'username': 'final_inspector',
                'email': 'final@test.com',
                'password': 'final_inspector123',
                'first_name': 'Final',
                'last_name': 'Inspector',
                'is_staff': True,
                'profile': {
                    'user_functionality': 'admin',
                    'admin_role': 'final_inspector',
                    'company_name': 'Multicam QC',
                    'technical_email': 'final@test.com',
                }
            },
            {
                'username': 'staff',
                'email': 'staff@test.com',
                'password': 'staff123',
                'first_name': 'Executive',
                'last_name': 'Staff',
                'is_staff': True,
                'profile': {
                    'user_functionality': 'admin',
                    'admin_role': 'staff_executive',
                    'company_name': 'Multicam Executive',
                    'technical_email': 'staff@test.com',
                }
            },
        ]
        
        for user_data in test_users:
            profile_data = user_data.pop('profile')
            password = user_data.pop('password')
            
            # Create or get user
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults=user_data
            )
            
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Created user: {user.username}'))
            else:
                self.stdout.write(self.style.WARNING(f'User already exists: {user.username}'))
            
            # Update profile
            profile = user.profile
            for key, value in profile_data.items():
                setattr(profile, key, value)
            profile.save()
            self.stdout.write(f'  → Profile: {profile.get_user_functionality_display()}, {profile.get_admin_role_display() or "N/A"}')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Test Users Created:'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        self.stdout.write('| Username          | Password              | Role                | Company     |')
        self.stdout.write('|-------------------|----------------------|---------------------|-------------|')
        self.stdout.write('| partner1a         | partner1a123         | Partner             | ACME        |')
        self.stdout.write('| partner1b         | partner1b123         | Partner             | ACME        |')
        self.stdout.write('| partner2a         | partner2a123         | Partner             | GLOBEX      |')
        self.stdout.write('| partner2b         | partner2b123         | Partner             | GLOBEX      |')
        self.stdout.write('| primary_inspector | primary_inspector123 | Primary Inspector   | -           |')
        self.stdout.write('| final_inspector   | final_inspector123   | Final Inspector     | -           |')
        self.stdout.write('| staff             | staff123             | Staff (Executive)   | -           |')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Partner Companies:'))
        self.stdout.write(f'  1. {company1.name} (Code: {company1.code})')
        self.stdout.write('     → partner1a and partner1b both belong to this company')
        self.stdout.write('     → FAs/Lots submitted by either are visible to both')
        self.stdout.write('')
        self.stdout.write(f'  2. {company2.name} (Code: {company2.code})')
        self.stdout.write('     → partner2a and partner2b both belong to this company')
        self.stdout.write('     → FAs/Lots submitted by either are visible to both')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Dashboard URLs:'))
        self.stdout.write('  Partner:   http://localhost:8000/portal/dashboard/partner/')
        self.stdout.write('  Inspector: http://localhost:8000/portal/admin/dashboard/')
        self.stdout.write('  Staff:     http://localhost:8000/portal/admin/staff/')

