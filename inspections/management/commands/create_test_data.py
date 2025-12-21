"""
Management command to create test FA and Lot data for development/testing.

Usage:
    python manage.py create_test_data           # Add test data (keeps existing)
    python manage.py create_test_data --clear   # Clear existing data first
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from inspections.models import (
    FirstArticleInspection, LotAcceptance, 
    FAEvaluation, FAColorEvaluation,
    LotEvaluation, LotSampleEvaluation, LotSampleColorEvaluation
)
from notifications.models import Notification
from accounts.models import UserProfile
from core.models import CamouflageType, VariantColor
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create test FA and Lot data with various statuses'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing FA, Lot, and Evaluation data before creating test data',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.clear_data()
        
        self.create_test_data()

    def clear_data(self):
        """Clear all inspection-related data"""
        self.stdout.write('Clearing existing data...')
        
        # Delete in order to respect foreign keys
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
        
        LotAcceptance.objects.all().delete()
        self.stdout.write('  ✓ LotAcceptance cleared')
        
        FirstArticleInspection.objects.all().delete()
        self.stdout.write('  ✓ FirstArticleInspection cleared')
        
        Notification.objects.all().delete()
        self.stdout.write('  ✓ Notifications cleared')
        
        self.stdout.write(self.style.SUCCESS('All test data cleared!\n'))

    def create_test_data(self):
        """Create test FAs, Lots, and Evaluations for all 4 partner users"""
        self.stdout.write('Creating test data...\n')
        
        # Get or create test users
        partner1a = self.get_or_create_user('partner1a', 'partner')
        partner1b = self.get_or_create_user('partner1b', 'partner')
        partner2a = self.get_or_create_user('partner2a', 'partner')
        partner2b = self.get_or_create_user('partner2b', 'partner')
        primary_inspector = self.get_or_create_user('primary_inspector', 'primary_inspector')
        final_inspector = self.get_or_create_user('final_inspector', 'final_inspector')
        
        # Get camouflage types
        camos = list(CamouflageType.objects.all()[:4])
        if len(camos) < 4:
            self.stdout.write(self.style.ERROR('Not enough camouflage types! Run: python manage.py load_initial_data'))
            return
        
        fa_list = []
        lot_list = []
        
        # =====================================================
        # COMPANY 1 (ACME) - FAs
        # =====================================================
        
        # FA 1A: APPROVED (partner1a) - for creating lots
        fa1a = FirstArticleInspection.objects.create(
            vendor=partner1a,
            fabric_style='Nylon 500D Cordura',
            multicam_variant=camos[0],
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number='LOT-2024-001',
            date_of_printing=date.today() - timedelta(days=10),
            submitter_first_name='Alice',
            submitter_last_name='Anderson',
            status='approved',
            primary_inspector=primary_inspector.user,
            primary_review_date=timezone.now() - timedelta(days=5),
            final_inspector=final_inspector.user,
            final_review_date=timezone.now() - timedelta(days=2),
        )
        
        # Create primary and final evaluations for FA1A
        eval1a_primary = self.create_evaluation(fa1a, 'primary', primary_inspector.user, camos[0], passing=True, days_ago=5)
        eval1a_final = self.create_evaluation(fa1a, 'final', final_inspector.user, camos[0], passing=True, days_ago=2)
        fa_list.append(fa1a)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {fa1a.fai_id}: APPROVED (partner1a from ACME)'))
        
        # FA 1B: PENDING FINAL (partner1b) - Company 1
        fa1b = FirstArticleInspection.objects.create(
            vendor=partner1b,
            fabric_style='Polyester Ripstop',
            multicam_variant=camos[1],
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number='LOT-2024-002',
            date_of_printing=date.today() - timedelta(days=7),
            submitter_first_name='Bob',
            submitter_last_name='Baker',
            status='pending_final',
            primary_inspector=primary_inspector.user,
            primary_review_date=timezone.now() - timedelta(days=3),
        )
        eval1b_primary = self.create_evaluation(fa1b, 'primary', primary_inspector.user, camos[1], passing=True, days_ago=3)
        fa_list.append(fa1b)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {fa1b.fai_id}: PENDING FINAL (partner1b from ACME)'))
        
        # =====================================================
        # COMPANY 2 (GLOBEX) - FAs
        # =====================================================
        
        # FA 2A: APPROVED (partner2a) - for creating lots
        fa2a = FirstArticleInspection.objects.create(
            vendor=partner2a,
            fabric_style='Cotton Canvas',
            multicam_variant=camos[2],
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number='LOT-2024-003',
            date_of_printing=date.today() - timedelta(days=12),
            submitter_first_name='Charlie',
            submitter_last_name='Chen',
            status='approved',
            primary_inspector=primary_inspector.user,
            primary_review_date=timezone.now() - timedelta(days=7),
            final_inspector=final_inspector.user,
            final_review_date=timezone.now() - timedelta(days=4),
        )
        eval2a_primary = self.create_evaluation(fa2a, 'primary', primary_inspector.user, camos[2], passing=True, days_ago=7)
        eval2a_final = self.create_evaluation(fa2a, 'final', final_inspector.user, camos[2], passing=True, days_ago=4)
        fa_list.append(fa2a)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {fa2a.fai_id}: APPROVED (partner2a from GLOBEX)'))
        
        # FA 2B: PENDING FINAL (partner2b) - Company 2
        fa2b = FirstArticleInspection.objects.create(
            vendor=partner2b,
            fabric_style='Nylon Taffeta',
            multicam_variant=camos[3],
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number='LOT-2024-004',
            date_of_printing=date.today() - timedelta(days=6),
            submitter_first_name='Diana',
            submitter_last_name='Davis',
            status='pending_final',
            primary_inspector=primary_inspector.user,
            primary_review_date=timezone.now() - timedelta(days=2),
        )
        eval2b_primary = self.create_evaluation(fa2b, 'primary', primary_inspector.user, camos[3], passing=True, days_ago=2)
        fa_list.append(fa2b)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {fa2b.fai_id}: PENDING FINAL (partner2b from GLOBEX)'))
        
        # =====================================================
        # COMPANY 1 (ACME) - LOTS (2 pending)
        # =====================================================
        
        # LOT 1A: PENDING (partner1a, linked to FA1A)
        lot1a = LotAcceptance.objects.create(
            vendor=partner1a,
            original_fa=fa1a,
            fabric_style=fa1a.fabric_style,
            shade_standard=fa1a.shade_standard,
            shade_standard_number=fa1a.shade_standard_number or '',
            spectral_reflectance_requirement=fa1a.spectral_reflectance_requirement,
            original_fa_lot_number=fa1a.fa_lot_number,
            lot_lot_number='LOT-PROD-001',
            number_of_yards_printed=3000,
            number_of_samples=2,
            individual_sample_numbers='LOT-PROD-001-1, LOT-PROD-001-2',
            date_of_printing=date.today() - timedelta(days=3),
            date_shipped=date.today() - timedelta(days=2),
            submitter_first_name='Alice',
            submitter_last_name='Anderson',
            submitted=True,
            status='pending',
        )
        lot_list.append(lot1a)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {lot1a.lot_id}: PENDING (partner1a from ACME)'))
        
        # LOT 1B: PENDING (partner1b, linked to FA1A)
        lot1b = LotAcceptance.objects.create(
            vendor=partner1b,
            original_fa=fa1a,
            fabric_style=fa1a.fabric_style,
            shade_standard=fa1a.shade_standard,
            shade_standard_number=fa1a.shade_standard_number or '',
            spectral_reflectance_requirement=fa1a.spectral_reflectance_requirement,
            original_fa_lot_number=fa1a.fa_lot_number,
            lot_lot_number='LOT-PROD-002',
            number_of_yards_printed=2500,
            number_of_samples=2,
            individual_sample_numbers='LOT-PROD-002-1, LOT-PROD-002-2',
            date_of_printing=date.today() - timedelta(days=2),
            date_shipped=date.today() - timedelta(days=1),
            submitter_first_name='Bob',
            submitter_last_name='Baker',
            submitted=True,
            status='pending',
        )
        lot_list.append(lot1b)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {lot1b.lot_id}: PENDING (partner1b from ACME)'))
        
        # =====================================================
        # COMPANY 2 (GLOBEX) - LOTS (2 pending)
        # =====================================================
        
        # LOT 2A: PENDING (partner2a, linked to FA2A)
        lot2a = LotAcceptance.objects.create(
            vendor=partner2a,
            original_fa=fa2a,
            fabric_style=fa2a.fabric_style,
            shade_standard=fa2a.shade_standard,
            shade_standard_number=fa2a.shade_standard_number or '',
            spectral_reflectance_requirement=fa2a.spectral_reflectance_requirement,
            original_fa_lot_number=fa2a.fa_lot_number,
            lot_lot_number='LOT-PROD-003',
            number_of_yards_printed=4000,
            number_of_samples=3,
            individual_sample_numbers='LOT-PROD-003-1, LOT-PROD-003-2, LOT-PROD-003-3',
            date_of_printing=date.today() - timedelta(days=4),
            date_shipped=date.today() - timedelta(days=3),
            submitter_first_name='Charlie',
            submitter_last_name='Chen',
            submitted=True,
            status='pending',
        )
        lot_list.append(lot2a)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {lot2a.lot_id}: PENDING (partner2a from GLOBEX)'))
        
        # LOT 2B: PENDING (partner2b, linked to FA2A)
        lot2b = LotAcceptance.objects.create(
            vendor=partner2b,
            original_fa=fa2a,
            fabric_style=fa2a.fabric_style,
            shade_standard=fa2a.shade_standard,
            shade_standard_number=fa2a.shade_standard_number or '',
            spectral_reflectance_requirement=fa2a.spectral_reflectance_requirement,
            original_fa_lot_number=fa2a.fa_lot_number,
            lot_lot_number='LOT-PROD-004',
            number_of_yards_printed=3500,
            number_of_samples=2,
            individual_sample_numbers='LOT-PROD-004-1, LOT-PROD-004-2',
            date_of_printing=date.today() - timedelta(days=3),
            date_shipped=date.today() - timedelta(days=2),
            submitter_first_name='Diana',
            submitter_last_name='Davis',
            submitted=True,
            status='pending',
        )
        lot_list.append(lot2b)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {lot2b.lot_id}: PENDING (partner2b from GLOBEX)'))
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('TEST DATA CREATED SUCCESSFULLY'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'''
Summary:
  FAs:  {FirstArticleInspection.objects.count()} total
    COMPANY 1 (ACME):
      - {fa1a.fai_id}: APPROVED (partner1a)
      - {fa1b.fai_id}: PENDING_FINAL (partner1b)
    COMPANY 2 (GLOBEX):
      - {fa2a.fai_id}: APPROVED (partner2a)
      - {fa2b.fai_id}: PENDING_FINAL (partner2b)
  
  Lots: {LotAcceptance.objects.count()} total
    COMPANY 1 (ACME):
      - {lot1a.lot_id}: PENDING (partner1a)
      - {lot1b.lot_id}: PENDING (partner1b)
    COMPANY 2 (GLOBEX):
      - {lot2a.lot_id}: PENDING (partner2a)
      - {lot2b.lot_id}: PENDING (partner2b)

Test Users:
  Company 1: partner1a / partner1a123,  partner1b / partner1b123
  Company 2: partner2a / partner2a123,  partner2b / partner2b123
  Inspectors: primary_inspector / primary_inspector123
             final_inspector / final_inspector123
''')

    def get_or_create_user(self, username, role):
        """Get or create a test user with the appropriate role"""
        try:
            profile = UserProfile.objects.get(user__username=username)
            return profile
        except UserProfile.DoesNotExist:
            # Run setup_test_users command
            from django.core.management import call_command
            call_command('setup_test_users')
            return UserProfile.objects.get(user__username=username)

    def create_evaluation(self, fa, stage, inspector, camo_type, passing=True, days_ago=1):
        """Create an FA evaluation with color evaluations"""
        eval = FAEvaluation.objects.create(
            fa=fa,
            stage=stage,
            attempt_number=1,
            inspector=inspector,
            pattern_execution='pass' if passing else 'fail',
            scale='pass' if passing else 'fail',
            spectral_reflectance='pass' if passing else 'fail',
            comments=f'{"Passed" if passing else "Failed"} {stage} review.',
            is_submitted=True,
            submitted_at=timezone.now() - timedelta(days=days_ago),
        )
        self.create_color_evaluations(eval, camo_type, passing)
        return eval

    def create_color_evaluations(self, evaluation, camo_type, passing=True):
        """Create color evaluations for all colors in the variant"""
        for color in camo_type.colors.all():
            FAColorEvaluation.objects.create(
                evaluation=evaluation,
                color=color,
                rating='4' if passing else '2',  # 4=Slight (pass), 2=Considerable (fail)
                comment='',
            )

