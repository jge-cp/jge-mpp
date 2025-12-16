"""
Tests for the inspections app.
Tests FA submission, two-stage FA review, Lot workflows, and evaluation system.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import date
from accounts.models import UserProfile
from core.models import CamouflageType, VariantColor
from .models import (
    FirstArticleInspection, LotAcceptance,
    FAEvaluation, FAColorEvaluation,
    LotEvaluation, LotSampleEvaluation, LotSampleColorEvaluation,
    SHADE_RATING_CHOICES, PASSING_RATINGS, FAILING_RATINGS, is_passing_rating
)


class FirstArticleModelTests(TestCase):
    """Test FirstArticleInspection model behavior"""
    
    def setUp(self):
        # Create partner user
        self.user = User.objects.create_user(
            username='partner', email='partner@test.com', password='testpass123'
        )
        self.user.profile.user_functionality = 'partner'
        self.user.profile.company_name = 'TestPartner'
        self.user.profile.save()
        
        # Create camouflage type
        self.camo = CamouflageType.objects.create(
            camouflage_name='MultiCam Original',
            status='active'
        )
    
    def test_fai_id_auto_generated(self):
        """FA ID should be auto-generated with company prefix and FA pattern"""
        fa = FirstArticleInspection.objects.create(
            vendor=self.user.profile,
            fabric_style='Test Fabric 90200',
            multicam_variant=self.camo,
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number='LOT-001',
            date_of_printing=date.today(),
            name_of_printer_representative='John Doe'
        )
        self.assertIn('-FA-', fa.fai_id)
        self.assertRegex(fa.fai_id, r'-FA-\d{4}$')
    
    def test_default_status_is_pending(self):
        """New FA should have pending status"""
        fa = FirstArticleInspection.objects.create(
            vendor=self.user.profile,
            fabric_style='Test Fabric',
            multicam_variant=self.camo,
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number='LOT-001',
            date_of_printing=date.today(),
            name_of_printer_representative='John Doe'
        )
        self.assertEqual(fa.status, 'pending')
    
    def test_fa_status_choices(self):
        """FA should support all MVP status choices"""
        fa = FirstArticleInspection.objects.create(
            vendor=self.user.profile,
            fabric_style='Test Fabric',
            multicam_variant=self.camo,
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number='LOT-001',
            date_of_printing=date.today(),
            name_of_printer_representative='John Doe'
        )
        
        # Test all status transitions
        for status in ['pending', 'pending_final', 'approved', 'rejected']:
            fa.status = status
            fa.save()
            fa.refresh_from_db()
            self.assertEqual(fa.status, status)


class TwoStageReviewWorkflowTests(TestCase):
    """Test the two-stage FA review workflow with new evaluation system"""
    
    def setUp(self):
        self.client = Client()
        
        # Create partner
        self.partner = User.objects.create_user(
            username='partner', email='partner@test.com', password='testpass123'
        )
        self.partner.profile.user_functionality = 'partner'
        self.partner.profile.company_name = 'TestPartner'
        self.partner.profile.save()
        
        # Create Primary Inspector
        self.primary_inspector = User.objects.create_user(
            username='primary', email='primary@test.com', password='testpass123',
            is_staff=True
        )
        self.primary_inspector.profile.user_functionality = 'admin'
        self.primary_inspector.profile.admin_role = 'primary_inspector'
        self.primary_inspector.profile.save()
        
        # Create Final Inspector
        self.final_inspector = User.objects.create_user(
            username='final', email='final@test.com', password='testpass123',
            is_staff=True
        )
        self.final_inspector.profile.user_functionality = 'admin'
        self.final_inspector.profile.admin_role = 'final_inspector'
        self.final_inspector.profile.save()
        
        self.camo = CamouflageType.objects.create(
            camouflage_name='MultiCam Original',
            status='active'
        )
        
        # Create variant colors (required for new evaluation system)
        self.colors = []
        for i, color_name in enumerate(['Color 1', 'Color 2', 'Color 3'], 1):
            color = VariantColor.objects.create(
                camouflage_type=self.camo,
                position=i,
                color_name=color_name
            )
            self.colors.append(color)
        
        # Create pending FA
        self.fa = FirstArticleInspection.objects.create(
            vendor=self.partner.profile,
            fabric_style='Test Fabric',
            multicam_variant=self.camo,
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number='LOT-001',
            date_of_printing=date.today(),
            name_of_printer_representative='John Doe'
        )
    
    def _get_passing_eval_data(self):
        """Helper to build POST data for a passing evaluation"""
        data = {
            'pattern_execution': 'pass',
            'scale': 'pass',
            'spectral_reflectance': 'pass',
            'comments': 'All criteria pass',
            'submit_evaluation': 'Submit Evaluation',
        }
        # Add passing ratings for all colors
        for color in self.colors:
            data[f'color_{color.id}-rating'] = '4'  # Passing rating
            data[f'color_{color.id}-comment'] = ''
        return data
    
    def _get_failing_eval_data(self, fail_pattern=True):
        """Helper to build POST data for a failing evaluation"""
        data = {
            'pattern_execution': 'fail' if fail_pattern else 'pass',
            'scale': 'pass',
            'spectral_reflectance': 'pass',
            'comments': 'Pattern failed' if fail_pattern else 'Color failed',
            'submit_evaluation': 'Submit Evaluation',
        }
        # Add color ratings (first one failing if not fail_pattern)
        for i, color in enumerate(self.colors):
            if i == 0 and not fail_pattern:
                data[f'color_{color.id}-rating'] = '2'  # Failing rating
            else:
                data[f'color_{color.id}-rating'] = '4'  # Passing rating
            data[f'color_{color.id}-comment'] = ''
        return data
    
    def test_primary_queue_shows_pending_fas(self):
        """Primary queue should show only 'pending' FAs"""
        self.client.login(username='primary', password='testpass123')
        response = self.client.get(reverse('inspections:fa_review_queue_primary'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.fa.fai_id)
    
    def test_final_queue_shows_pending_final_fas(self):
        """Final queue should show only 'pending_final' FAs"""
        # Move FA to pending_final
        self.fa.status = 'pending_final'
        self.fa.save()
        
        self.client.login(username='final', password='testpass123')
        response = self.client.get(reverse('inspections:fa_review_queue_final'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.fa.fai_id)
    
    def test_final_inspector_cannot_access_primary_queue(self):
        """Final Inspector should not have access to primary queue"""
        self.client.login(username='final', password='testpass123')
        response = self.client.get(reverse('inspections:fa_review_queue_primary'))
        # Should redirect
        self.assertEqual(response.status_code, 302)
    
    def test_primary_inspector_cannot_review_pending_final(self):
        """Primary Inspector cannot review FA in pending_final status"""
        self.fa.status = 'pending_final'
        self.fa.save()
        
        self.client.login(username='primary', password='testpass123')
        response = self.client.get(reverse('inspections:fa_review', args=[self.fa.fai_id]))
        # Should redirect with error
        self.assertEqual(response.status_code, 302)
    
    def test_final_inspector_cannot_review_pending(self):
        """Final Inspector cannot review FA in pending status"""
        self.client.login(username='final', password='testpass123')
        response = self.client.get(reverse('inspections:fa_review', args=[self.fa.fai_id]))
        # Should redirect with error
        self.assertEqual(response.status_code, 302)
    
    def test_primary_approval_moves_to_pending_final(self):
        """Primary approval should move FA to pending_final status"""
        self.client.login(username='primary', password='testpass123')
        
        response = self.client.post(
            reverse('inspections:fa_review', args=[self.fa.fai_id]),
            self._get_passing_eval_data()
        )
        
        self.fa.refresh_from_db()
        self.assertEqual(self.fa.status, 'pending_final')
        
        # Check evaluation was created
        evaluation = FAEvaluation.objects.get(fa=self.fa, stage='primary')
        self.assertTrue(evaluation.is_submitted)
        self.assertEqual(evaluation.inspector, self.primary_inspector)
    
    def test_primary_rejection_sets_rejected(self):
        """Primary rejection (failing criteria) should set FA to rejected"""
        self.client.login(username='primary', password='testpass123')
        
        response = self.client.post(
            reverse('inspections:fa_review', args=[self.fa.fai_id]),
            self._get_failing_eval_data(fail_pattern=True)
        )
        
        self.fa.refresh_from_db()
        self.assertEqual(self.fa.status, 'rejected')
        
        # Check evaluation was created
        evaluation = FAEvaluation.objects.get(fa=self.fa, stage='primary')
        self.assertTrue(evaluation.is_submitted)
        self.assertFalse(evaluation.all_pass)
    
    def test_final_approval_completes_workflow(self):
        """Final approval should complete workflow with approved status"""
        # First create primary evaluation
        self.fa.status = 'pending_final'
        self.fa.save()
        
        primary_eval = FAEvaluation.objects.create(
            fa=self.fa,
            stage='primary',
            inspector=self.primary_inspector,
            pattern_execution='pass',
            scale='pass',
            spectral_reflectance='pass',
            is_submitted=True
        )
        for color in self.colors:
            FAColorEvaluation.objects.create(
                evaluation=primary_eval,
                color=color,
                rating='4'
            )
        
        self.client.login(username='final', password='testpass123')
        
        response = self.client.post(
            reverse('inspections:fa_review', args=[self.fa.fai_id]),
            self._get_passing_eval_data()
        )
        
        self.fa.refresh_from_db()
        self.assertEqual(self.fa.status, 'approved')
        
        # Check final evaluation was created
        evaluation = FAEvaluation.objects.get(fa=self.fa, stage='final')
        self.assertTrue(evaluation.is_submitted)
        self.assertEqual(evaluation.inspector, self.final_inspector)
    
    def test_final_rejection_sets_rejected(self):
        """Final rejection (failing criteria) should set FA to rejected"""
        # First create primary evaluation
        self.fa.status = 'pending_final'
        self.fa.save()
        
        primary_eval = FAEvaluation.objects.create(
            fa=self.fa,
            stage='primary',
            inspector=self.primary_inspector,
            pattern_execution='pass',
            scale='pass',
            spectral_reflectance='pass',
            is_submitted=True
        )
        for color in self.colors:
            FAColorEvaluation.objects.create(
                evaluation=primary_eval,
                color=color,
                rating='4'
            )
        
        self.client.login(username='final', password='testpass123')
        
        response = self.client.post(
            reverse('inspections:fa_review', args=[self.fa.fai_id]),
            self._get_failing_eval_data(fail_pattern=True)
        )
        
        self.fa.refresh_from_db()
        self.assertEqual(self.fa.status, 'rejected')
        
        # Check final evaluation was created
        evaluation = FAEvaluation.objects.get(fa=self.fa, stage='final')
        self.assertTrue(evaluation.is_submitted)
        self.assertFalse(evaluation.all_pass)


class LotAcceptanceTests(TestCase):
    """Test Lot submission and review (single-stage, Primary Inspector only)"""
    
    def setUp(self):
        self.client = Client()
        
        # Create partner
        self.partner = User.objects.create_user(
            username='partner', email='partner@test.com', password='testpass123'
        )
        self.partner.profile.user_functionality = 'partner'
        self.partner.profile.company_name = 'TestPartner'
        self.partner.profile.save()
        
        # Create Primary Inspector
        self.primary_inspector = User.objects.create_user(
            username='primary', email='primary@test.com', password='testpass123',
            is_staff=True
        )
        self.primary_inspector.profile.user_functionality = 'admin'
        self.primary_inspector.profile.admin_role = 'primary_inspector'
        self.primary_inspector.profile.save()
        
        # Create Final Inspector
        self.final_inspector = User.objects.create_user(
            username='final', email='final@test.com', password='testpass123',
            is_staff=True
        )
        self.final_inspector.profile.user_functionality = 'admin'
        self.final_inspector.profile.admin_role = 'final_inspector'
        self.final_inspector.profile.save()
        
        self.camo = CamouflageType.objects.create(
            camouflage_name='MultiCam Original',
            status='active'
        )
        
        # Create approved FA (required for Lot)
        self.fa = FirstArticleInspection.objects.create(
            vendor=self.partner.profile,
            fabric_style='Test Fabric',
            multicam_variant=self.camo,
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number='FA-LOT-001',
            date_of_printing=date.today(),
            name_of_printer_representative='John Doe',
            status='approved'
        )
    
    def test_lot_requires_approved_fa(self):
        """Lot should reference an approved FA"""
        lot = LotAcceptance.objects.create(
            vendor=self.partner.profile,
            fabric_style='Test Fabric',
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            original_fa_lot_number='FA-LOT-001',
            lot_lot_number='PROD-LOT-001',
            number_of_yards_printed=1000,
            number_of_samples=3,
            individual_sample_numbers='S1, S2, S3',
            date_of_printing=date.today(),
            name_of_submitter='John Doe',
            original_fa=self.fa
        )
        self.assertEqual(lot.original_fa, self.fa)
    
    def test_primary_inspector_can_review_lots(self):
        """Primary Inspector should be able to access lot review queue"""
        self.client.login(username='primary', password='testpass123')
        response = self.client.get(reverse('inspections:lot_review_queue'))
        self.assertEqual(response.status_code, 200)
    
    def test_final_inspector_cannot_review_lots(self):
        """Final Inspector should NOT be able to access lot review queue"""
        self.client.login(username='final', password='testpass123')
        response = self.client.get(reverse('inspections:lot_review_queue'))
        # Should redirect with error
        self.assertEqual(response.status_code, 302)
    
    def test_partner_cannot_review_lots(self):
        """Partners should NOT be able to access lot review queue"""
        self.client.login(username='partner', password='testpass123')
        response = self.client.get(reverse('inspections:lot_review_queue'))
        # Should redirect with error
        self.assertEqual(response.status_code, 302)


class FASubmissionViewTests(TestCase):
    """Test FA submission form and view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='partner', email='partner@test.com', password='testpass123'
        )
        self.user.profile.user_functionality = 'partner'
        self.user.profile.company_name = 'TestPartner'
        self.user.profile.save()
        
        self.camo = CamouflageType.objects.create(
            camouflage_name='MultiCam Original',
            status='active'
        )
        
        self.client.login(username='partner', password='testpass123')
    
    def test_fa_submit_page_loads(self):
        """FA submission page should be accessible to partners"""
        response = self.client.get(reverse('inspections:fa_submit'))
        self.assertEqual(response.status_code, 200)
    
    def test_fa_submit_requires_login(self):
        """FA submission should require authentication"""
        self.client.logout()
        response = self.client.get(reverse('inspections:fa_submit'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_successful_fa_submission(self):
        """Valid FA submission should create record"""
        initial_count = FirstArticleInspection.objects.count()
        
        response = self.client.post(reverse('inspections:fa_submit'), {
            'fabric_style': 'Test Fabric 90200',
            'multicam_variant': self.camo.pk,
            'shade_standard': 'alpha',
            'spectral_reflectance_requirement': 'alpha',
            'fa_lot_number': 'LOT-TEST-001',
            'date_of_printing': date.today().isoformat(),
            'name_of_printer_representative': 'John Doe',
        })
        
        self.assertEqual(FirstArticleInspection.objects.count(), initial_count + 1)
    
    def test_fa_list_shows_user_fas(self):
        """FA list should show only the logged-in user's FAs"""
        fa = FirstArticleInspection.objects.create(
            vendor=self.user.profile,
            fabric_style='My Fabric',
            multicam_variant=self.camo,
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number='LOT-001',
            date_of_printing=date.today(),
            name_of_printer_representative='John Doe'
        )
        
        response = self.client.get(reverse('inspections:fa_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Fabric')


class DashboardAccessTests(TestCase):
    """Test dashboard access based on user roles"""
    
    def setUp(self):
        self.client = Client()
        
        # Create users for each role
        self.partner = User.objects.create_user(
            username='partner', email='partner@test.com', password='testpass123'
        )
        self.partner.profile.user_functionality = 'partner'
        self.partner.profile.save()
        
        self.primary = User.objects.create_user(
            username='primary', email='primary@test.com', password='testpass123'
        )
        self.primary.profile.user_functionality = 'admin'
        self.primary.profile.admin_role = 'primary_inspector'
        self.primary.profile.save()
        
        self.final = User.objects.create_user(
            username='final', email='final@test.com', password='testpass123'
        )
        self.final.profile.user_functionality = 'admin'
        self.final.profile.admin_role = 'final_inspector'
        self.final.profile.save()
        
        self.staff = User.objects.create_user(
            username='staff', email='staff@test.com', password='testpass123'
        )
        self.staff.profile.user_functionality = 'admin'
        self.staff.profile.admin_role = 'staff_executive'
        self.staff.profile.save()
    
    def test_partner_dashboard_access(self):
        """Partner should access partner dashboard"""
        self.client.login(username='partner', password='testpass123')
        response = self.client.get(reverse('dashboard:partner_dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_inspector_dashboard_access(self):
        """Inspectors should access inspector dashboard"""
        self.client.login(username='primary', password='testpass123')
        response = self.client.get(reverse('dashboard:inspector_dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_staff_dashboard_access(self):
        """Staff should access staff dashboard"""
        self.client.login(username='staff', password='testpass123')
        response = self.client.get(reverse('dashboard:staff_dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_partner_redirected_from_inspector_dashboard(self):
        """Partner should be redirected from inspector dashboard"""
        self.client.login(username='partner', password='testpass123')
        response = self.client.get(reverse('dashboard:inspector_dashboard'))
        self.assertEqual(response.status_code, 302)


# =============================================================================
# SHADE RATING SYSTEM TESTS
# =============================================================================

class ShadeRatingTests(TestCase):
    """Test shade rating constants and helper functions"""
    
    def test_passing_ratings_are_3_and_above(self):
        """Ratings 3 and above should be in PASSING_RATINGS"""
        expected_passing = ['3', '3-4', '4', '4-5', '5']
        self.assertEqual(PASSING_RATINGS, expected_passing)
    
    def test_failing_ratings_are_below_3(self):
        """Ratings below 3 should be in FAILING_RATINGS"""
        expected_failing = ['0', '0-1', '1', '1-2', '2', '2-3']
        self.assertEqual(FAILING_RATINGS, expected_failing)
    
    def test_is_passing_rating_for_pass_values(self):
        """is_passing_rating should return True for passing ratings"""
        for rating in PASSING_RATINGS:
            self.assertTrue(is_passing_rating(rating), f"{rating} should pass")
    
    def test_is_passing_rating_for_fail_values(self):
        """is_passing_rating should return False for failing ratings"""
        for rating in FAILING_RATINGS:
            self.assertFalse(is_passing_rating(rating), f"{rating} should fail")
    
    def test_all_ratings_covered(self):
        """All rating choices should be either passing or failing"""
        all_ratings = [choice[0] for choice in SHADE_RATING_CHOICES]
        covered = set(PASSING_RATINGS + FAILING_RATINGS)
        self.assertEqual(set(all_ratings), covered)


class FAEvaluationModelTests(TestCase):
    """Test FAEvaluation model behavior"""
    
    @classmethod
    def setUpTestData(cls):
        # Create partner user
        cls.partner_user = User.objects.create_user(
            username='evalpartner', email='evalpartner@test.com', password='testpass123'
        )
        cls.partner_user.profile.user_functionality = 'partner'
        cls.partner_user.profile.company_name = 'EvalTestPartner'
        cls.partner_user.profile.save()
        
        # Create inspector user
        cls.inspector_user = User.objects.create_user(
            username='evalinspector', email='evalinspector@test.com', password='testpass123'
        )
        cls.inspector_user.profile.user_functionality = 'admin'
        cls.inspector_user.profile.admin_role = 'primary_inspector'
        cls.inspector_user.profile.save()
        
        # Create camouflage type with colors
        cls.multicam = CamouflageType.objects.create(
            camouflage_name='Multicam Eval Test',
            status='active'
        )
        
        # Create variant colors (3 colors for simpler testing)
        cls.color1 = VariantColor.objects.create(
            camouflage_type=cls.multicam,
            position=1,
            color_name='Test Color 1'
        )
        cls.color2 = VariantColor.objects.create(
            camouflage_type=cls.multicam,
            position=2,
            color_name='Test Color 2'
        )
        cls.color3 = VariantColor.objects.create(
            camouflage_type=cls.multicam,
            position=3,
            color_name='Test Color 3'
        )
    
    def _create_fa(self):
        """Helper to create a test FA"""
        return FirstArticleInspection.objects.create(
            vendor=self.partner_user.profile,
            fabric_style='Eval Test Fabric',
            multicam_variant=self.multicam,
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number='EVAL-LOT-001',
            date_of_printing=date.today(),
            name_of_printer_representative='Eval Tester'
        )
    
    def test_create_evaluation(self):
        """Should be able to create an FA evaluation"""
        fa = self._create_fa()
        eval = FAEvaluation.objects.create(
            fa=fa,
            stage='primary',
            inspector=self.inspector_user
        )
        self.assertEqual(eval.stage, 'primary')
        self.assertFalse(eval.is_submitted)
    
    def test_unique_together_constraint(self):
        """Only one evaluation per FA per stage"""
        fa = self._create_fa()
        FAEvaluation.objects.create(fa=fa, stage='primary', inspector=self.inspector_user)
        
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            FAEvaluation.objects.create(fa=fa, stage='primary', inspector=self.inspector_user)
    
    def test_all_colors_pass_with_passing_ratings(self):
        """all_colors_pass should be True when all colors have passing ratings"""
        fa = self._create_fa()
        eval = FAEvaluation.objects.create(
            fa=fa,
            stage='primary',
            inspector=self.inspector_user
        )
        
        # Add passing ratings for all colors
        FAColorEvaluation.objects.create(evaluation=eval, color=self.color1, rating='4')
        FAColorEvaluation.objects.create(evaluation=eval, color=self.color2, rating='3')
        FAColorEvaluation.objects.create(evaluation=eval, color=self.color3, rating='5')
        
        self.assertTrue(eval.all_colors_pass)
    
    def test_all_colors_pass_fails_with_one_failing_rating(self):
        """all_colors_pass should be False if any color fails"""
        fa = self._create_fa()
        eval = FAEvaluation.objects.create(
            fa=fa,
            stage='primary',
            inspector=self.inspector_user
        )
        
        # Two passing, one failing
        FAColorEvaluation.objects.create(evaluation=eval, color=self.color1, rating='4')
        FAColorEvaluation.objects.create(evaluation=eval, color=self.color2, rating='2')  # FAIL
        FAColorEvaluation.objects.create(evaluation=eval, color=self.color3, rating='5')
        
        self.assertFalse(eval.all_colors_pass)
    
    def test_overall_criteria_pass_all_pass(self):
        """overall_criteria_pass when pattern, scale, spectral all pass"""
        fa = self._create_fa()
        eval = FAEvaluation.objects.create(
            fa=fa,
            stage='primary',
            inspector=self.inspector_user,
            pattern_execution='pass',
            scale='pass',
            spectral_reflectance='pass'
        )
        self.assertTrue(eval.overall_criteria_pass)
    
    def test_overall_criteria_pass_fails_if_pattern_fails(self):
        """overall_criteria_pass False if pattern fails"""
        fa = self._create_fa()
        eval = FAEvaluation.objects.create(
            fa=fa,
            stage='primary',
            inspector=self.inspector_user,
            pattern_execution='fail',
            scale='pass',
            spectral_reflectance='pass'
        )
        self.assertFalse(eval.overall_criteria_pass)
    
    def test_overall_criteria_pass_spectral_blank_ok(self):
        """Spectral can be blank (Visible Spectrum Only)"""
        fa = self._create_fa()
        eval = FAEvaluation.objects.create(
            fa=fa,
            stage='primary',
            inspector=self.inspector_user,
            pattern_execution='pass',
            scale='pass',
            spectral_reflectance=''  # Visible Spectrum Only
        )
        self.assertTrue(eval.overall_criteria_pass)
    
    def test_all_pass_requires_colors_and_criteria(self):
        """all_pass requires both colors and criteria to pass"""
        fa = self._create_fa()
        eval = FAEvaluation.objects.create(
            fa=fa,
            stage='primary',
            inspector=self.inspector_user,
            pattern_execution='pass',
            scale='pass',
            spectral_reflectance='pass'
        )
        
        # Add passing colors
        FAColorEvaluation.objects.create(evaluation=eval, color=self.color1, rating='4')
        FAColorEvaluation.objects.create(evaluation=eval, color=self.color2, rating='3')
        FAColorEvaluation.objects.create(evaluation=eval, color=self.color3, rating='5')
        
        self.assertTrue(eval.all_pass)
        self.assertEqual(eval.result, 'pass')
    
    def test_submit_passes_updates_fa_to_pending_final(self):
        """Submitting passing primary eval moves FA to pending_final"""
        fa = self._create_fa()
        self.assertEqual(fa.status, 'pending')
        
        eval = FAEvaluation.objects.create(
            fa=fa,
            stage='primary',
            inspector=self.inspector_user,
            pattern_execution='pass',
            scale='pass',
            spectral_reflectance='pass'
        )
        
        # Add passing colors
        FAColorEvaluation.objects.create(evaluation=eval, color=self.color1, rating='4')
        FAColorEvaluation.objects.create(evaluation=eval, color=self.color2, rating='3')
        FAColorEvaluation.objects.create(evaluation=eval, color=self.color3, rating='5')
        
        eval.submit()
        
        fa.refresh_from_db()
        self.assertEqual(fa.status, 'pending_final')
        self.assertTrue(eval.is_submitted)
        self.assertIsNotNone(eval.submitted_at)
    
    def test_submit_fails_updates_fa_to_rejected(self):
        """Submitting failing eval moves FA to rejected"""
        fa = self._create_fa()
        
        eval = FAEvaluation.objects.create(
            fa=fa,
            stage='primary',
            inspector=self.inspector_user,
            pattern_execution='fail',  # FAIL
            scale='pass',
            spectral_reflectance='pass'
        )
        
        # Add passing colors (but pattern fails)
        FAColorEvaluation.objects.create(evaluation=eval, color=self.color1, rating='4')
        FAColorEvaluation.objects.create(evaluation=eval, color=self.color2, rating='3')
        FAColorEvaluation.objects.create(evaluation=eval, color=self.color3, rating='5')
        
        eval.submit()
        
        fa.refresh_from_db()
        self.assertEqual(fa.status, 'rejected')
    
    def test_submit_final_pass_updates_fa_to_approved(self):
        """Submitting passing final eval moves FA to approved"""
        fa = self._create_fa()
        fa.status = 'pending_final'
        fa.save()
        
        eval = FAEvaluation.objects.create(
            fa=fa,
            stage='final',
            inspector=self.inspector_user,
            pattern_execution='pass',
            scale='pass',
            spectral_reflectance='pass'
        )
        
        # Add passing colors
        FAColorEvaluation.objects.create(evaluation=eval, color=self.color1, rating='4')
        FAColorEvaluation.objects.create(evaluation=eval, color=self.color2, rating='3')
        FAColorEvaluation.objects.create(evaluation=eval, color=self.color3, rating='5')
        
        eval.submit()
        
        fa.refresh_from_db()
        self.assertEqual(fa.status, 'approved')


class FAColorEvaluationModelTests(TestCase):
    """Test FAColorEvaluation model behavior"""
    
    @classmethod
    def setUpTestData(cls):
        # Create partner user
        cls.partner_user = User.objects.create_user(
            username='colorpartner', email='colorpartner@test.com', password='testpass123'
        )
        cls.partner_user.profile.user_functionality = 'partner'
        cls.partner_user.profile.company_name = 'ColorTestPartner'
        cls.partner_user.profile.save()
        
        # Create inspector user
        cls.inspector_user = User.objects.create_user(
            username='colorinspector', email='colorinspector@test.com', password='testpass123'
        )
        
        # Create camouflage type with colors
        cls.multicam = CamouflageType.objects.create(
            camouflage_name='Multicam Color Test',
            status='active'
        )
        
        cls.color = VariantColor.objects.create(
            camouflage_type=cls.multicam,
            position=1,
            color_name='Test Color'
        )
    
    def _create_fa_and_eval(self):
        """Helper to create FA and evaluation"""
        fa = FirstArticleInspection.objects.create(
            vendor=self.partner_user.profile,
            fabric_style='Color Test Fabric',
            multicam_variant=self.multicam,
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number='COLOR-LOT-001',
            date_of_printing=date.today(),
            name_of_printer_representative='Color Tester'
        )
        eval = FAEvaluation.objects.create(
            fa=fa,
            stage='primary',
            inspector=self.inspector_user
        )
        return fa, eval
    
    def test_create_color_evaluation(self):
        """Should be able to create a color evaluation"""
        fa, eval = self._create_fa_and_eval()
        color_eval = FAColorEvaluation.objects.create(
            evaluation=eval,
            color=self.color,
            rating='4',
            comment='Looks good'
        )
        self.assertEqual(color_eval.rating, '4')
        self.assertTrue(color_eval.is_passing)
        self.assertEqual(color_eval.result, 'pass')
    
    def test_is_passing_for_each_rating(self):
        """Test is_passing for all possible ratings"""
        fa, eval = self._create_fa_and_eval()
        
        for rating_code, rating_label in SHADE_RATING_CHOICES:
            # Clean up previous
            FAColorEvaluation.objects.filter(evaluation=eval).delete()
            
            color_eval = FAColorEvaluation.objects.create(
                evaluation=eval,
                color=self.color,
                rating=rating_code
            )
            
            expected_pass = rating_code in PASSING_RATINGS
            self.assertEqual(
                color_eval.is_passing, 
                expected_pass,
                f"Rating {rating_code} should {'pass' if expected_pass else 'fail'}"
            )
    
    def test_blank_rating_is_failing(self):
        """Blank rating should be failing"""
        fa, eval = self._create_fa_and_eval()
        color_eval = FAColorEvaluation.objects.create(
            evaluation=eval,
            color=self.color,
            rating=''
        )
        self.assertFalse(color_eval.is_passing)
        self.assertEqual(color_eval.result, 'fail')
    
    def test_unique_together_constraint(self):
        """Only one evaluation per color per evaluation"""
        fa, eval = self._create_fa_and_eval()
        FAColorEvaluation.objects.create(evaluation=eval, color=self.color, rating='4')
        
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            FAColorEvaluation.objects.create(evaluation=eval, color=self.color, rating='5')


# =============================================================================
# LOT EVALUATION TESTS
# =============================================================================

class LotEvaluationModelTests(TestCase):
    """Test the new LotEvaluation model and related models"""
    
    def setUp(self):
        self.partner = User.objects.create_user(
            username='partner', email='partner@test.com', password='testpass123'
        )
        self.partner.profile.user_functionality = 'partner'
        self.partner.profile.company_name = 'TestPartner'
        self.partner.profile.save()
        
        self.inspector = User.objects.create_user(
            username='inspector', email='inspector@test.com', password='testpass123'
        )
        
        self.camo = CamouflageType.objects.create(
            camouflage_name='MultiCam Original',
            status='active'
        )
        
        # Create colors
        self.colors = []
        for i, name in enumerate(['Color 1', 'Color 2', 'Color 3'], 1):
            color = VariantColor.objects.create(
                camouflage_type=self.camo,
                position=i,
                color_name=name
            )
            self.colors.append(color)
        
        self.fa = FirstArticleInspection.objects.create(
            vendor=self.partner.profile,
            fabric_style='Test Fabric',
            multicam_variant=self.camo,
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number='FA-LOT-001',
            date_of_printing=date.today(),
            name_of_printer_representative='John Doe',
            status='approved'
        )
        
        self.lot = LotAcceptance.objects.create(
            vendor=self.partner.profile,
            fabric_style='Test Fabric',
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            original_fa_lot_number='FA-LOT-001',
            lot_lot_number='PROD-LOT-001',
            number_of_yards_printed=1000,
            number_of_samples=3,
            individual_sample_numbers='PROD-LOT-001-1, PROD-LOT-001-2, PROD-LOT-001-3',
            date_of_printing=date.today(),
            name_of_submitter='John Doe',
            original_fa=self.fa
        )
    
    def test_sample_count_auto_calculation(self):
        """Sample count should be auto-calculated from yards printed"""
        from .models import calculate_sample_count
        
        self.assertEqual(calculate_sample_count(500), 2)
        self.assertEqual(calculate_sample_count(800), 2)
        self.assertEqual(calculate_sample_count(801), 3)
        self.assertEqual(calculate_sample_count(10000), 3)
        self.assertEqual(calculate_sample_count(22000), 3)
        self.assertEqual(calculate_sample_count(22001), 5)
        self.assertEqual(calculate_sample_count(50000), 5)
    
    def test_lot_auto_generates_sample_ids(self):
        """Lot should auto-generate sample IDs on save"""
        lot = LotAcceptance.objects.create(
            vendor=self.partner.profile,
            fabric_style='Test Fabric',
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            original_fa_lot_number='FA-LOT-001',
            lot_lot_number='AUTO-LOT-001',
            number_of_yards_printed=500,  # Should give 2 samples
            number_of_samples=2,
            individual_sample_numbers='',  # Empty, should auto-generate
            date_of_printing=date.today(),
            name_of_submitter='John Doe',
            original_fa=self.fa
        )
        self.assertIn('AUTO-LOT-001-1', lot.individual_sample_numbers)
        self.assertIn('AUTO-LOT-001-2', lot.individual_sample_numbers)
    
    def test_lot_evaluation_creation(self):
        """LotEvaluation should be creatable and link to Lot"""
        evaluation = LotEvaluation.objects.create(
            lot=self.lot,
            inspector=self.inspector
        )
        self.assertEqual(evaluation.lot, self.lot)
        self.assertFalse(evaluation.is_submitted)
    
    def test_lot_sample_evaluation_creation(self):
        """LotSampleEvaluation should be creatable within LotEvaluation"""
        evaluation = LotEvaluation.objects.create(
            lot=self.lot,
            inspector=self.inspector
        )
        sample = LotSampleEvaluation.objects.create(
            lot_evaluation=evaluation,
            sample_number=1,
            sample_id='PROD-LOT-001-1',
            pattern_execution='pass',
            scale='pass',
            spectral_reflectance='pass'
        )
        self.assertEqual(sample.lot_evaluation, evaluation)
        self.assertEqual(sample.sample_number, 1)
    
    def test_lot_sample_color_evaluation(self):
        """LotSampleColorEvaluation should track color ratings per sample"""
        evaluation = LotEvaluation.objects.create(
            lot=self.lot,
            inspector=self.inspector
        )
        sample = LotSampleEvaluation.objects.create(
            lot_evaluation=evaluation,
            sample_number=1,
            sample_id='PROD-LOT-001-1',
            pattern_execution='pass',
            scale='pass'
        )
        color_eval = LotSampleColorEvaluation.objects.create(
            sample_evaluation=sample,
            color=self.colors[0],
            rating='4'
        )
        self.assertTrue(color_eval.is_passing)
        self.assertEqual(color_eval.result, 'pass')
    
    def test_lot_sample_all_pass(self):
        """Sample should pass only if all colors and criteria pass"""
        evaluation = LotEvaluation.objects.create(
            lot=self.lot,
            inspector=self.inspector
        )
        sample = LotSampleEvaluation.objects.create(
            lot_evaluation=evaluation,
            sample_number=1,
            sample_id='PROD-LOT-001-1',
            pattern_execution='pass',
            scale='pass'
        )
        
        # Add all passing color evaluations
        for color in self.colors:
            LotSampleColorEvaluation.objects.create(
                sample_evaluation=sample,
                color=color,
                rating='4'
            )
        
        self.assertTrue(sample.all_colors_pass)
        self.assertTrue(sample.overall_criteria_pass)
        self.assertTrue(sample.all_pass)
    
    def test_lot_sample_fails_with_failing_color(self):
        """Sample should fail if any color fails"""
        evaluation = LotEvaluation.objects.create(
            lot=self.lot,
            inspector=self.inspector
        )
        sample = LotSampleEvaluation.objects.create(
            lot_evaluation=evaluation,
            sample_number=1,
            sample_id='PROD-LOT-001-1',
            pattern_execution='pass',
            scale='pass'
        )
        
        # Add one failing color
        LotSampleColorEvaluation.objects.create(
            sample_evaluation=sample,
            color=self.colors[0],
            rating='2'  # Failing rating
        )
        for color in self.colors[1:]:
            LotSampleColorEvaluation.objects.create(
                sample_evaluation=sample,
                color=color,
                rating='4'
            )
        
        self.assertFalse(sample.all_colors_pass)
        self.assertFalse(sample.all_pass)
    
    def test_lot_evaluation_submit_approval(self):
        """Submitting passing evaluation should approve lot"""
        evaluation = LotEvaluation.objects.create(
            lot=self.lot,
            inspector=self.inspector
        )
        
        # Create a passing sample
        sample = LotSampleEvaluation.objects.create(
            lot_evaluation=evaluation,
            sample_number=1,
            sample_id='PROD-LOT-001-1',
            pattern_execution='pass',
            scale='pass'
        )
        for color in self.colors:
            LotSampleColorEvaluation.objects.create(
                sample_evaluation=sample,
                color=color,
                rating='4'
            )
        
        evaluation.submit()
        
        self.lot.refresh_from_db()
        self.assertTrue(evaluation.is_submitted)
        self.assertEqual(self.lot.status, 'approved')
    
    def test_lot_evaluation_submit_rejection(self):
        """Submitting failing evaluation should reject lot"""
        evaluation = LotEvaluation.objects.create(
            lot=self.lot,
            inspector=self.inspector
        )
        
        # Create a failing sample
        sample = LotSampleEvaluation.objects.create(
            lot_evaluation=evaluation,
            sample_number=1,
            sample_id='PROD-LOT-001-1',
            pattern_execution='fail',  # Failing
            scale='pass'
        )
        for color in self.colors:
            LotSampleColorEvaluation.objects.create(
                sample_evaluation=sample,
                color=color,
                rating='4'
            )
        
        evaluation.submit()
        
        self.lot.refresh_from_db()
        self.assertTrue(evaluation.is_submitted)
        self.assertEqual(self.lot.status, 'rejected')


class FAEvaluationPersistenceTests(TestCase):
    """Test that FA evaluation data persists correctly"""
    
    def setUp(self):
        self.client = Client()
        
        # Create inspector
        self.inspector = User.objects.create_user(
            username='inspector', email='inspector@test.com', password='testpass123'
        )
        self.inspector.profile.user_functionality = 'admin'
        self.inspector.profile.admin_role = 'primary_inspector'
        self.inspector.profile.save()
        
        # Create partner
        self.partner = User.objects.create_user(
            username='partner', email='partner@test.com', password='testpass123'
        )
        self.partner.profile.user_functionality = 'partner'
        self.partner.profile.company_name = 'TestPartner'
        self.partner.profile.save()
        
        # Create camo with colors
        self.camo = CamouflageType.objects.create(
            camouflage_name='MultiCam Test',
            status='active'
        )
        self.colors = []
        for i, name in enumerate(['Color 1', 'Color 2', 'Color 3'], 1):
            color = VariantColor.objects.create(
                camouflage_type=self.camo,
                position=i,
                color_name=name
            )
            self.colors.append(color)
        
        # Create pending FA
        self.fa = FirstArticleInspection.objects.create(
            vendor=self.partner.profile,
            fabric_style='Test Fabric',
            multicam_variant=self.camo,
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number='LOT-001',
            date_of_printing=date.today(),
            name_of_printer_representative='John Doe',
            status='pending'
        )
    
    def test_color_ratings_persist_after_save_draft(self):
        """Color ratings should persist after clicking Save Draft"""
        self.client.login(username='inspector', password='testpass123')
        
        # Submit evaluation with Save Draft
        post_data = {
            'pattern_execution': 'pass',
            'scale': 'pass',
            'spectral_reflectance': 'pass',
            'comments': 'Test comment',
            'save_draft': 'Save Draft',
        }
        # Add color ratings
        for color in self.colors:
            post_data[f'color_{color.id}-rating'] = '4'
            post_data[f'color_{color.id}-comment'] = f'Comment for {color.color_name}'
        
        response = self.client.post(
            reverse('inspections:fa_review', args=[self.fa.fai_id]),
            post_data
        )
        
        # Verify evaluations were saved
        self.fa.refresh_from_db()
        self.assertEqual(self.fa.status, 'pending')  # Still pending (not submitted)
        
        evaluation = FAEvaluation.objects.get(fa=self.fa, stage='primary')
        self.assertEqual(evaluation.pattern_execution, 'pass')
        
        # Verify color evaluations
        color_evals = evaluation.color_evaluations.all()
        self.assertEqual(color_evals.count(), 3)
        
        for color_eval in color_evals:
            self.assertEqual(color_eval.rating, '4')
            self.assertTrue(color_eval.is_passing)
    
    def test_color_ratings_visible_after_page_reload(self):
        """Color ratings should be visible when returning to the page"""
        self.client.login(username='inspector', password='testpass123')
        
        # Create evaluation with color ratings directly
        evaluation = FAEvaluation.objects.create(
            fa=self.fa,
            stage='primary',
            attempt_number=1,
            inspector=self.inspector,
            pattern_execution='pass',
            scale='pass'
        )
        for color in self.colors:
            FAColorEvaluation.objects.create(
                evaluation=evaluation,
                color=color,
                rating='3',
                comment='Test'
            )
        
        # Load the review page
        response = self.client.get(
            reverse('inspections:fa_review', args=[self.fa.fai_id])
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check that color_forms in context has the saved data
        color_forms = response.context['color_forms']
        self.assertEqual(len(color_forms), 3)
        
        for color, form, color_eval in color_forms:
            self.assertIsNotNone(color_eval)
            self.assertEqual(color_eval.rating, '3')
            self.assertTrue(color_eval.is_passing)
    
    def test_evaluation_visible_after_rejection(self):
        """Evaluation should be visible and editable after FA is rejected"""
        # Create a submitted (failed) evaluation
        evaluation = FAEvaluation.objects.create(
            fa=self.fa,
            stage='primary',
            attempt_number=1,
            inspector=self.inspector,
            pattern_execution='fail',  # This will cause rejection
            scale='pass',
            is_submitted=True
        )
        for color in self.colors:
            FAColorEvaluation.objects.create(
                evaluation=evaluation,
                color=color,
                rating='2',  # Failing rating
                comment='Failed'
            )
        
        # Set FA to rejected
        self.fa.status = 'rejected'
        self.fa.save()
        
        # Login as inspector and view
        self.client.login(username='inspector', password='testpass123')
        response = self.client.get(
            reverse('inspections:fa_review', args=[self.fa.fai_id])
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Inspectors can always edit - not read-only
        self.assertFalse(response.context['is_read_only'])
        self.assertTrue(response.context['is_completed'])
        
        # Should have the evaluation data
        context_eval = response.context['evaluation']
        self.assertEqual(context_eval.pattern_execution, 'fail')
        
        # Color forms should have the saved data
        for color, form, color_eval in response.context['color_forms']:
            self.assertIsNotNone(color_eval)
            self.assertEqual(color_eval.rating, '2')
