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
        """Create test FAs, Lots, and Evaluations"""
        self.stdout.write('Creating test data...\n')
        
        # Get or create test users
        partner = self.get_or_create_user('partner', 'partner')
        primary_inspector = self.get_or_create_user('primary_inspector', 'primary_inspector')
        final_inspector = self.get_or_create_user('final_inspector', 'final_inspector')
        
        # Get camouflage types
        camos = list(CamouflageType.objects.all()[:3])
        if len(camos) < 3:
            self.stdout.write(self.style.ERROR('Not enough camouflage types! Run: python manage.py load_initial_data'))
            return
        
        # =====================================================
        # FA 1: FULLY APPROVED (passed primary + final)
        # =====================================================
        fa1 = FirstArticleInspection.objects.create(
            vendor=partner,
            fabric_style='Nylon 500D Cordura',
            multicam_variant=camos[0],
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number='LOT-2024-001',
            date_of_printing=date.today() - timedelta(days=10),
            submitter_first_name='John',
            submitter_last_name='Smith',
            status='approved',
            primary_inspector=primary_inspector.user,
            primary_review_date=timezone.now() - timedelta(days=5),
            final_inspector=final_inspector.user,
            final_review_date=timezone.now() - timedelta(days=2),
        )
        
        # Create primary evaluation for FA1
        eval1_primary = FAEvaluation.objects.create(
            fa=fa1,
            stage='primary',
            attempt_number=1,
            inspector=primary_inspector.user,
            pattern_execution='pass',
            scale='pass',
            spectral_reflectance='pass',
            comments='All criteria met. Good quality.',
            is_submitted=True,
            submitted_at=timezone.now() - timedelta(days=5),
        )
        self.create_color_evaluations(eval1_primary, camos[0], passing=True)
        
        # Create final evaluation for FA1
        eval1_final = FAEvaluation.objects.create(
            fa=fa1,
            stage='final',
            attempt_number=1,
            inspector=final_inspector.user,
            pattern_execution='pass',
            scale='pass',
            spectral_reflectance='pass',
            comments='Confirmed. Approved for production.',
            is_submitted=True,
            submitted_at=timezone.now() - timedelta(days=2),
        )
        self.create_color_evaluations(eval1_final, camos[0], passing=True)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ FA1: {fa1.fai_id} - APPROVED (passed primary + final)'))
        
        # =====================================================
        # FA 2: PENDING FINAL (passed primary, awaiting final)
        # =====================================================
        fa2 = FirstArticleInspection.objects.create(
            vendor=partner,
            fabric_style='Polyester Ripstop',
            multicam_variant=camos[1],
            shade_standard='bravo',
            spectral_reflectance_requirement='bravo',
            fa_lot_number='LOT-2024-002',
            date_of_printing=date.today() - timedelta(days=7),
            submitter_first_name='Jane',
            submitter_last_name='Doe',
            status='pending_final',
            primary_inspector=primary_inspector.user,
            primary_review_date=timezone.now() - timedelta(days=3),
        )
        
        # Create primary evaluation for FA2
        eval2_primary = FAEvaluation.objects.create(
            fa=fa2,
            stage='primary',
            attempt_number=1,
            inspector=primary_inspector.user,
            pattern_execution='pass',
            scale='pass',
            spectral_reflectance='pass',
            comments='Primary review passed. Ready for final.',
            is_submitted=True,
            submitted_at=timezone.now() - timedelta(days=3),
        )
        self.create_color_evaluations(eval2_primary, camos[1], passing=True)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ FA2: {fa2.fai_id} - PENDING FINAL (passed primary, awaiting final)'))
        
        # =====================================================
        # FA 3: PENDING PRIMARY (awaiting first review)
        # =====================================================
        fa3 = FirstArticleInspection.objects.create(
            vendor=partner,
            fabric_style='Cotton Twill',
            multicam_variant=camos[2],
            shade_standard='alpha',
            spectral_reflectance_requirement='charlie',
            fa_lot_number='LOT-2024-003',
            date_of_printing=date.today() - timedelta(days=2),
            submitter_first_name='Bob',
            submitter_last_name='Johnson',
            status='pending',
        )
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ FA3: {fa3.fai_id} - PENDING (awaiting primary review)'))
        
        # =====================================================
        # LOT 1: APPROVED (linked to FA1)
        # =====================================================
        lot1 = LotAcceptance.objects.create(
            vendor=partner,
            original_fa=fa1,
            fabric_style=fa1.fabric_style,
            shade_standard=fa1.shade_standard,
            shade_standard_number=fa1.shade_standard_number or '',
            spectral_reflectance_requirement=fa1.spectral_reflectance_requirement,
            original_fa_lot_number=fa1.fa_lot_number,
            lot_lot_number='LOT-PROD-001',
            number_of_yards_printed=5000,
            number_of_samples=3,
            individual_sample_numbers='LOT-PROD-001-1, LOT-PROD-001-2, LOT-PROD-001-3',
            date_of_printing=date.today() - timedelta(days=5),
            date_shipped=date.today() - timedelta(days=4),
            submitter_first_name='John',
            submitter_last_name='Smith',
            submitted=True,
            status='approved',
            inspector=primary_inspector.user,
            review_date=date.today() - timedelta(days=1),
            inspector_comments='Lot approved. Quality consistent with FA.',
        )
        
        # Create lot evaluation
        lot_eval = LotEvaluation.objects.create(
            lot=lot1,
            inspector=primary_inspector.user,
            comments='All samples passed inspection.',
            is_submitted=True,
            submitted_at=timezone.now() - timedelta(days=1),
        )
        
        # Create sample evaluations
        for i in range(1, 4):
            sample_eval = LotSampleEvaluation.objects.create(
                lot_evaluation=lot_eval,
                sample_number=i,
                sample_id=f'LOT-PROD-001-{i}',
                pattern_execution='pass',
                scale='pass',
                spectral_reflectance='pass',
            )
            # Create color evaluations for each sample
            for color in camos[0].colors.all():
                LotSampleColorEvaluation.objects.create(
                    sample_evaluation=sample_eval,
                    color=color,
                    rating='4',  # Slight difference - passing
                )
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ LOT1: {lot1.lot_id} - APPROVED (linked to FA1)'))
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('TEST DATA CREATED SUCCESSFULLY'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(f'''
Summary:
  FAs:  {FirstArticleInspection.objects.count()} total
    - {fa1.fai_id}: APPROVED (both reviews passed)
    - {fa2.fai_id}: PENDING_FINAL (awaiting final review)
    - {fa3.fai_id}: PENDING (awaiting primary review)
  
  Lots: {LotAcceptance.objects.count()} total
    - {lot1.lot_id}: APPROVED

Test Users:
  - partner / partner123
  - primary_inspector / primary_inspector123
  - final_inspector / final_inspector123
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

    def create_color_evaluations(self, evaluation, camo_type, passing=True):
        """Create color evaluations for all colors in the variant"""
        for color in camo_type.colors.all():
            FAColorEvaluation.objects.create(
                evaluation=evaluation,
                color=color,
                rating='4' if passing else '2',  # 4=Slight (pass), 2=Considerable (fail)
                comment='',
            )

