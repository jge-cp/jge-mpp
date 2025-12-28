"""
Management command to create test FA and Lot data for development/testing.

Creates comprehensive test data covering all statuses:
- FAs: pending, pending_final, approved, rejected
- Lots: pending, approved, rejected

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
        """Create test FAs, Lots, and Evaluations covering all statuses"""
        self.stdout.write('Creating test data...\n')
        
        # Get or create test users
        partner1a = self.get_or_create_user('partner1a', 'partner')
        partner1b = self.get_or_create_user('partner1b', 'partner')
        partner2a = self.get_or_create_user('partner2a', 'partner')
        partner2b = self.get_or_create_user('partner2b', 'partner')
        primary_inspector = self.get_or_create_user('primary_inspector', 'primary_inspector')
        final_inspector = self.get_or_create_user('final_inspector', 'final_inspector')
        
        # Get camouflage types (need at least 5 for variety)
        camos = list(CamouflageType.objects.all()[:5])
        if len(camos) < 5:
            self.stdout.write(self.style.ERROR('Not enough camouflage types! Run: python manage.py load_initial_data'))
            return
        
        # =====================================================
        # FIRST ARTICLES - All Statuses
        # =====================================================
        self.stdout.write(self.style.HTTP_INFO('\n[First Articles]'))
        
        # FA 1: PENDING PRIMARY (partner1a, ACME) - newly submitted, no review yet
        fa_pending = FirstArticleInspection.objects.create(
            vendor=partner1a,
            fabric_style='Nylon 500D Cordura',
            multicam_variant=camos[0],  # Multicam
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number='LOT-2024-001',
            date_of_printing=date.today() - timedelta(days=2),
            submitter_first_name='Alice',
            submitter_last_name='Anderson',
            status='pending',
        )
        self.stdout.write(self.style.SUCCESS(f'  ✓ {fa_pending.fai_id}: PENDING PRIMARY (partner1a, ACME)'))
        
        # FA 2: PENDING FINAL (partner1b, ACME) - passed primary, awaiting final
        fa_pending_final_1 = FirstArticleInspection.objects.create(
            vendor=partner1b,
            fabric_style='Polyester Ripstop',
            multicam_variant=camos[1],  # Multicam Tropic
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
        self.create_fa_evaluation(fa_pending_final_1, 'primary', primary_inspector.user, passing=True, days_ago=3)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {fa_pending_final_1.fai_id}: PENDING FINAL (partner1b, ACME)'))
        
        # FA 3: PENDING FINAL (partner2b, GLOBEX) - passed primary, awaiting final
        fa_pending_final_2 = FirstArticleInspection.objects.create(
            vendor=partner2b,
            fabric_style='Nylon Taffeta',
            multicam_variant=camos[2],  # Multicam Arid
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number='LOT-2024-003',
            date_of_printing=date.today() - timedelta(days=6),
            submitter_first_name='Diana',
            submitter_last_name='Davis',
            status='pending_final',
            primary_inspector=primary_inspector.user,
            primary_review_date=timezone.now() - timedelta(days=2),
        )
        self.create_fa_evaluation(fa_pending_final_2, 'primary', primary_inspector.user, passing=True, days_ago=2)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {fa_pending_final_2.fai_id}: PENDING FINAL (partner2b, GLOBEX)'))
        
        # FA 4: APPROVED (partner1a, ACME) - fully approved, can create lots
        fa_approved_1 = FirstArticleInspection.objects.create(
            vendor=partner1a,
            fabric_style='Cotton Canvas',
            multicam_variant=camos[3],  # Multicam Black
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number='LOT-2024-004',
            date_of_printing=date.today() - timedelta(days=14),
            submitter_first_name='Alice',
            submitter_last_name='Anderson',
            status='approved',
            primary_inspector=primary_inspector.user,
            primary_review_date=timezone.now() - timedelta(days=10),
            final_inspector=final_inspector.user,
            final_review_date=timezone.now() - timedelta(days=7),
        )
        self.create_fa_evaluation(fa_approved_1, 'primary', primary_inspector.user, passing=True, days_ago=10)
        self.create_fa_evaluation(fa_approved_1, 'final', final_inspector.user, passing=True, days_ago=7)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {fa_approved_1.fai_id}: APPROVED (partner1a, ACME)'))
        
        # FA 5: APPROVED (partner2a, GLOBEX) - fully approved, can create lots
        fa_approved_2 = FirstArticleInspection.objects.create(
            vendor=partner2a,
            fabric_style='Nylon Oxford',
            multicam_variant=camos[4],  # Multicam Alpine
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number='LOT-2024-005',
            date_of_printing=date.today() - timedelta(days=20),
            submitter_first_name='Charlie',
            submitter_last_name='Chen',
            status='approved',
            primary_inspector=primary_inspector.user,
            primary_review_date=timezone.now() - timedelta(days=15),
            final_inspector=final_inspector.user,
            final_review_date=timezone.now() - timedelta(days=12),
        )
        self.create_fa_evaluation(fa_approved_2, 'primary', primary_inspector.user, passing=True, days_ago=15)
        self.create_fa_evaluation(fa_approved_2, 'final', final_inspector.user, passing=True, days_ago=12)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {fa_approved_2.fai_id}: APPROVED (partner2a, GLOBEX)'))
        
        # FA 6: REJECTED (partner2a, GLOBEX) - rejected at primary stage
        fa_rejected = FirstArticleInspection.objects.create(
            vendor=partner2a,
            fabric_style='Polyester Blend',
            multicam_variant=camos[0],  # Multicam
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number='LOT-2024-006',
            date_of_printing=date.today() - timedelta(days=8),
            submitter_first_name='Charlie',
            submitter_last_name='Chen',
            status='rejected',
            primary_inspector=primary_inspector.user,
            primary_review_date=timezone.now() - timedelta(days=5),
        )
        self.create_fa_evaluation(fa_rejected, 'primary', primary_inspector.user, passing=False, days_ago=5)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {fa_rejected.fai_id}: REJECTED (partner2a, GLOBEX)'))
        
        # =====================================================
        # LOT ACCEPTANCES - All Statuses
        # =====================================================
        self.stdout.write(self.style.HTTP_INFO('\n[Lot Acceptances]'))
        
        # LOT 1: PENDING (partner1a, ACME) - linked to approved FA
        lot_pending_1 = LotAcceptance.objects.create(
            vendor=partner1a,
            original_fa=fa_approved_1,
            fabric_style=fa_approved_1.fabric_style,
            shade_standard=fa_approved_1.shade_standard,
            shade_standard_number=fa_approved_1.shade_standard_number or '',
            spectral_reflectance_requirement=fa_approved_1.spectral_reflectance_requirement,
            original_fa_lot_number=fa_approved_1.fa_lot_number,
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
        self.stdout.write(self.style.SUCCESS(f'  ✓ {lot_pending_1.lot_id}: PENDING (partner1a, ACME)'))
        
        # LOT 2: PENDING (partner1b, ACME) - linked to approved FA
        lot_pending_2 = LotAcceptance.objects.create(
            vendor=partner1b,
            original_fa=fa_approved_1,
            fabric_style=fa_approved_1.fabric_style,
            shade_standard=fa_approved_1.shade_standard,
            shade_standard_number=fa_approved_1.shade_standard_number or '',
            spectral_reflectance_requirement=fa_approved_1.spectral_reflectance_requirement,
            original_fa_lot_number=fa_approved_1.fa_lot_number,
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
        self.stdout.write(self.style.SUCCESS(f'  ✓ {lot_pending_2.lot_id}: PENDING (partner1b, ACME)'))
        
        # LOT 3: PENDING (partner2a, GLOBEX) - linked to approved FA
        lot_pending_3 = LotAcceptance.objects.create(
            vendor=partner2a,
            original_fa=fa_approved_2,
            fabric_style=fa_approved_2.fabric_style,
            shade_standard=fa_approved_2.shade_standard,
            shade_standard_number=fa_approved_2.shade_standard_number or '',
            spectral_reflectance_requirement=fa_approved_2.spectral_reflectance_requirement,
            original_fa_lot_number=fa_approved_2.fa_lot_number,
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
        self.stdout.write(self.style.SUCCESS(f'  ✓ {lot_pending_3.lot_id}: PENDING (partner2a, GLOBEX)'))
        
        # LOT 4: PENDING (partner2b, GLOBEX) - linked to approved FA
        lot_pending_4 = LotAcceptance.objects.create(
            vendor=partner2b,
            original_fa=fa_approved_2,
            fabric_style=fa_approved_2.fabric_style,
            shade_standard=fa_approved_2.shade_standard,
            shade_standard_number=fa_approved_2.shade_standard_number or '',
            spectral_reflectance_requirement=fa_approved_2.spectral_reflectance_requirement,
            original_fa_lot_number=fa_approved_2.fa_lot_number,
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
        self.stdout.write(self.style.SUCCESS(f'  ✓ {lot_pending_4.lot_id}: PENDING (partner2b, GLOBEX)'))
        
        # LOT 5: APPROVED (partner2a, GLOBEX) - reviewed and passed
        lot_approved = LotAcceptance.objects.create(
            vendor=partner2a,
            original_fa=fa_approved_2,
            fabric_style=fa_approved_2.fabric_style,
            shade_standard=fa_approved_2.shade_standard,
            shade_standard_number=fa_approved_2.shade_standard_number or '',
            spectral_reflectance_requirement=fa_approved_2.spectral_reflectance_requirement,
            original_fa_lot_number=fa_approved_2.fa_lot_number,
            lot_lot_number='LOT-PROD-005',
            number_of_yards_printed=5000,
            number_of_samples=2,
            individual_sample_numbers='LOT-PROD-005-1, LOT-PROD-005-2',
            date_of_printing=date.today() - timedelta(days=10),
            date_shipped=date.today() - timedelta(days=9),
            submitter_first_name='Charlie',
            submitter_last_name='Chen',
            submitted=True,
            status='approved',
            inspector=primary_inspector.user,
            review_date=timezone.now() - timedelta(days=7),
        )
        self.create_lot_evaluation(lot_approved, primary_inspector.user, passing=True, days_ago=7)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {lot_approved.lot_id}: APPROVED (partner2a, GLOBEX)'))
        
        # LOT 6: REJECTED (partner2b, GLOBEX) - reviewed and failed
        lot_rejected = LotAcceptance.objects.create(
            vendor=partner2b,
            original_fa=fa_approved_2,
            fabric_style=fa_approved_2.fabric_style,
            shade_standard=fa_approved_2.shade_standard,
            shade_standard_number=fa_approved_2.shade_standard_number or '',
            spectral_reflectance_requirement=fa_approved_2.spectral_reflectance_requirement,
            original_fa_lot_number=fa_approved_2.fa_lot_number,
            lot_lot_number='LOT-PROD-006',
            number_of_yards_printed=2000,
            number_of_samples=2,
            individual_sample_numbers='LOT-PROD-006-1, LOT-PROD-006-2',
            date_of_printing=date.today() - timedelta(days=8),
            date_shipped=date.today() - timedelta(days=7),
            submitter_first_name='Diana',
            submitter_last_name='Davis',
            submitted=True,
            status='rejected',
            inspector=primary_inspector.user,
            review_date=timezone.now() - timedelta(days=5),
        )
        self.create_lot_evaluation(lot_rejected, primary_inspector.user, passing=False, days_ago=5)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {lot_rejected.lot_id}: REJECTED (partner2b, GLOBEX)'))
        
        # Summary
        self.print_summary()

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

    def create_fa_evaluation(self, fa, stage, inspector, passing=True, days_ago=1):
        """Create an FA evaluation with color evaluations for all variant colors"""
        evaluation = FAEvaluation.objects.create(
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
        
        # Create color evaluations for all colors in the variant
        colors = fa.multicam_variant.colors.all()
        for color in colors:
            FAColorEvaluation.objects.create(
                evaluation=evaluation,
                color=color,
                rating='4' if passing else '2',  # 4=Slight (pass), 2=Considerable (fail)
                comment='Within tolerance' if passing else 'Color mismatch detected',
            )
        
        return evaluation

    def create_lot_evaluation(self, lot, inspector, passing=True, days_ago=1):
        """Create a Lot evaluation with sample and color evaluations"""
        evaluation = LotEvaluation.objects.create(
            lot=lot,
            inspector=inspector,
            comments=f'{"Passed" if passing else "Failed"} lot review.',
            is_submitted=True,
            submitted_at=timezone.now() - timedelta(days=days_ago),
        )
        
        # Create sample evaluations (based on number_of_samples)
        sample_ids = lot.individual_sample_numbers.split(', ') if lot.individual_sample_numbers else []
        for i in range(lot.number_of_samples):
            sample_id = sample_ids[i] if i < len(sample_ids) else f'Sample-{i+1}'
            sample_eval = LotSampleEvaluation.objects.create(
                lot_evaluation=evaluation,
                sample_number=i + 1,
                sample_id=sample_id,
                pattern_execution='pass' if passing else 'fail',
                scale='pass' if passing else 'fail',
                spectral_reflectance='pass' if passing else 'fail',
                comments='Within tolerance' if passing else 'Failed inspection',
            )
            
            # Create color evaluations for each sample
            if lot.original_fa and lot.original_fa.multicam_variant:
                colors = lot.original_fa.multicam_variant.colors.all()
                for color in colors:
                    LotSampleColorEvaluation.objects.create(
                        sample_evaluation=sample_eval,
                        color=color,
                        rating='4' if passing else '2',
                        comment='',
                    )
        
        return evaluation

    def print_summary(self):
        """Print summary of created test data"""
        fa_counts = {
            'pending': FirstArticleInspection.objects.filter(status='pending').count(),
            'pending_final': FirstArticleInspection.objects.filter(status='pending_final').count(),
            'approved': FirstArticleInspection.objects.filter(status='approved').count(),
            'rejected': FirstArticleInspection.objects.filter(status='rejected').count(),
        }
        
        lot_counts = {
            'pending': LotAcceptance.objects.filter(status='pending').count(),
            'approved': LotAcceptance.objects.filter(status='approved').count(),
            'rejected': LotAcceptance.objects.filter(status='rejected').count(),
        }
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('TEST DATA CREATED SUCCESSFULLY'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'''
First Articles ({sum(fa_counts.values())} total):
  - Pending Primary: {fa_counts['pending']}
  - Pending Final:   {fa_counts['pending_final']}
  - Approved:        {fa_counts['approved']}
  - Rejected:        {fa_counts['rejected']}

Lot Acceptances ({sum(lot_counts.values())} total):
  - Pending:   {lot_counts['pending']}
  - Approved:  {lot_counts['approved']}
  - Rejected:  {lot_counts['rejected']}

Test Users:
  ACME Corp:         partner1a / partner1a123
                     partner1b / partner1b123
  Globex Industries: partner2a / partner2a123
                     partner2b / partner2b123
  Inspectors:        primary_inspector / primary_inspector123
                     final_inspector / final_inspector123
''')
