"""
Tests for inspections/managers.py

Tests the custom model managers and querysets for FA and Lot models.
"""
from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model

from accounts.models import UserProfile, PartnerCompany
from inspections.models import FirstArticleInspection, LotAcceptance
from core.models import CamouflageType

User = get_user_model()


class FAManagerTestCase(TestCase):
    """Base test case with common FA test data."""
    
    def setUp(self):
        # Create companies
        self.company_a = PartnerCompany.objects.create(name='Company A', code='CA')
        self.company_b = PartnerCompany.objects.create(name='Company B', code='CB')
        
        # Create users
        self.partner_a = User.objects.create_user('partnerA', 'a@test.com', 'pass')
        self.partner_a.profile.user_functionality = 'partner'
        self.partner_a.profile.company = self.company_a
        self.partner_a.profile.save()
        
        self.partner_b = User.objects.create_user('partnerB', 'b@test.com', 'pass')
        self.partner_b.profile.user_functionality = 'partner'
        self.partner_b.profile.company = self.company_b
        self.partner_b.profile.save()
        
        self.inspector = User.objects.create_user('inspector', 'i@test.com', 'pass')
        self.inspector.profile.user_functionality = 'admin'
        self.inspector.profile.admin_role = 'primary_inspector'
        self.inspector.profile.save()
        
        # Create camouflage type
        self.camo = CamouflageType.objects.create(camouflage_name='Multicam')
        
        # Create FAs for different statuses and companies
        self.fa_a_pending = self._create_fa(self.partner_a.profile, self.company_a, 'FA-A1', 'pending')
        self.fa_a_pending_final = self._create_fa(self.partner_a.profile, self.company_a, 'FA-A2', 'pending_final')
        self.fa_a_approved = self._create_fa(self.partner_a.profile, self.company_a, 'FA-A3', 'approved')
        self.fa_a_rejected = self._create_fa(self.partner_a.profile, self.company_a, 'FA-A4', 'rejected')
        
        self.fa_b_pending = self._create_fa(self.partner_b.profile, self.company_b, 'FA-B1', 'pending')
        self.fa_b_approved = self._create_fa(self.partner_b.profile, self.company_b, 'FA-B2', 'approved')
    
    def _create_fa(self, vendor, company, lot_number, status):
        return FirstArticleInspection.objects.create(
            vendor=vendor,
            company=company,
            fabric_style='Test Fabric',
            multicam_variant=self.camo,
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number=lot_number,
            date_of_printing=date.today(),
            submitter_first_name='Test',
            submitter_last_name='User',
            status=status,
        )


class FAManagerForUserTests(FAManagerTestCase):
    """Tests for FAManager.for_user() method."""
    
    def test_partner_sees_own_company_fas_only(self):
        """Partner should only see FAs from their company."""
        fas = FirstArticleInspection.objects.for_user(self.partner_a.profile)
        
        self.assertEqual(fas.count(), 4)  # All company A FAs
        for fa in fas:
            self.assertEqual(fa.company, self.company_a)
    
    def test_partner_does_not_see_other_company(self):
        """Partner should not see other company's FAs."""
        fas = FirstArticleInspection.objects.for_user(self.partner_a.profile)
        
        self.assertNotIn(self.fa_b_pending, fas)
        self.assertNotIn(self.fa_b_approved, fas)
    
    def test_inspector_sees_all_fas(self):
        """Inspector should see all FAs."""
        fas = FirstArticleInspection.objects.for_user(self.inspector.profile)
        
        self.assertEqual(fas.count(), 6)  # All FAs


class FAManagerStatusFiltersTests(FAManagerTestCase):
    """Tests for FAManager status filter methods."""
    
    def test_pending_filter(self):
        """pending() should return only pending status FAs."""
        fas = FirstArticleInspection.objects.pending()
        
        self.assertEqual(fas.count(), 2)  # FA-A1, FA-B1
        for fa in fas:
            self.assertEqual(fa.status, 'pending')
    
    def test_pending_final_filter(self):
        """pending_final() should return only pending_final status FAs."""
        fas = FirstArticleInspection.objects.pending_final()
        
        self.assertEqual(fas.count(), 1)  # FA-A2
        self.assertEqual(fas.first().status, 'pending_final')
    
    def test_pending_any_filter(self):
        """pending_any() should return pending and pending_final FAs."""
        fas = FirstArticleInspection.objects.pending_any()
        
        self.assertEqual(fas.count(), 3)  # FA-A1, FA-A2, FA-B1
        for fa in fas:
            self.assertIn(fa.status, ['pending', 'pending_final'])
    
    def test_approved_filter(self):
        """approved() should return only approved FAs."""
        fas = FirstArticleInspection.objects.approved()
        
        self.assertEqual(fas.count(), 2)  # FA-A3, FA-B2
        for fa in fas:
            self.assertEqual(fa.status, 'approved')
    
    def test_rejected_filter(self):
        """rejected() should return only rejected FAs."""
        fas = FirstArticleInspection.objects.rejected()
        
        self.assertEqual(fas.count(), 1)  # FA-A4
        self.assertEqual(fas.first().status, 'rejected')


class FAManagerChainedFiltersTests(FAManagerTestCase):
    """Tests for chaining FAManager methods."""
    
    def test_for_user_then_pending(self):
        """Should be able to chain for_user().pending()."""
        fas = FirstArticleInspection.objects.for_user(self.partner_a.profile).pending()
        
        self.assertEqual(fas.count(), 1)  # FA-A1
        self.assertEqual(fas.first(), self.fa_a_pending)
    
    def test_pending_then_for_user(self):
        """Should be able to chain pending().for_user()."""
        fas = FirstArticleInspection.objects.pending().for_user(self.partner_a.profile)
        
        self.assertEqual(fas.count(), 1)  # FA-A1
        self.assertEqual(fas.first(), self.fa_a_pending)
    
    def test_for_user_pending_any(self):
        """Partner should see their pending and pending_final FAs."""
        fas = FirstArticleInspection.objects.for_user(self.partner_a.profile).pending_any()
        
        self.assertEqual(fas.count(), 2)  # FA-A1, FA-A2


class LotManagerTestCase(TestCase):
    """Base test case with common Lot test data."""
    
    def setUp(self):
        # Create companies
        self.company_a = PartnerCompany.objects.create(name='Company A', code='CA')
        self.company_b = PartnerCompany.objects.create(name='Company B', code='CB')
        
        # Create users
        self.partner_a = User.objects.create_user('partnerA', 'a@test.com', 'pass')
        self.partner_a.profile.user_functionality = 'partner'
        self.partner_a.profile.company = self.company_a
        self.partner_a.profile.save()
        
        self.partner_b = User.objects.create_user('partnerB', 'b@test.com', 'pass')
        self.partner_b.profile.user_functionality = 'partner'
        self.partner_b.profile.company = self.company_b
        self.partner_b.profile.save()
        
        self.inspector = User.objects.create_user('inspector', 'i@test.com', 'pass')
        self.inspector.profile.user_functionality = 'admin'
        self.inspector.profile.admin_role = 'primary_inspector'
        self.inspector.profile.save()
        
        # Create camouflage type
        self.camo = CamouflageType.objects.create(camouflage_name='Multicam')
        
        # Create approved FAs (required for Lots)
        self.fa_a = self._create_fa(self.partner_a.profile, self.company_a, 'FA-A1')
        self.fa_b = self._create_fa(self.partner_b.profile, self.company_b, 'FA-B1')
        
        # Create Lots
        self.lot_a_pending = self._create_lot(self.partner_a.profile, self.company_a, self.fa_a, 'LOT-A1', 'pending')
        self.lot_a_approved = self._create_lot(self.partner_a.profile, self.company_a, self.fa_a, 'LOT-A2', 'approved')
        self.lot_a_rejected = self._create_lot(self.partner_a.profile, self.company_a, self.fa_a, 'LOT-A3', 'rejected')
        
        self.lot_b_pending = self._create_lot(self.partner_b.profile, self.company_b, self.fa_b, 'LOT-B1', 'pending')
    
    def _create_fa(self, vendor, company, lot_number):
        return FirstArticleInspection.objects.create(
            vendor=vendor,
            company=company,
            fabric_style='Test Fabric',
            multicam_variant=self.camo,
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number=lot_number,
            date_of_printing=date.today(),
            submitter_first_name='Test',
            submitter_last_name='User',
            status='approved',
        )
    
    def _create_lot(self, vendor, company, fa, lot_number, status):
        return LotAcceptance.objects.create(
            vendor=vendor,
            company=company,
            original_fa=fa,
            fabric_style=fa.fabric_style,
            shade_standard=fa.shade_standard,
            spectral_reflectance_requirement=fa.spectral_reflectance_requirement,
            original_fa_lot_number=fa.fa_lot_number,
            lot_lot_number=lot_number,
            number_of_yards_printed=1000,
            number_of_samples=3,
            individual_sample_numbers='S1,S2,S3',
            date_of_printing=date.today(),
            submitter_first_name='Test',
            submitter_last_name='User',
            status=status,
        )


class LotManagerForUserTests(LotManagerTestCase):
    """Tests for LotManager.for_user() method."""
    
    def test_partner_sees_own_company_lots_only(self):
        """Partner should only see Lots from their company."""
        lots = LotAcceptance.objects.for_user(self.partner_a.profile)
        
        self.assertEqual(lots.count(), 3)  # All company A Lots
        for lot in lots:
            self.assertEqual(lot.company, self.company_a)
    
    def test_partner_does_not_see_other_company(self):
        """Partner should not see other company's Lots."""
        lots = LotAcceptance.objects.for_user(self.partner_a.profile)
        
        self.assertNotIn(self.lot_b_pending, lots)
    
    def test_inspector_sees_all_lots(self):
        """Inspector should see all Lots."""
        lots = LotAcceptance.objects.for_user(self.inspector.profile)
        
        self.assertEqual(lots.count(), 4)  # All Lots


class LotManagerStatusFiltersTests(LotManagerTestCase):
    """Tests for LotManager status filter methods."""
    
    def test_pending_filter(self):
        """pending() should return only pending status Lots."""
        lots = LotAcceptance.objects.pending()
        
        self.assertEqual(lots.count(), 2)  # LOT-A1, LOT-B1
        for lot in lots:
            self.assertEqual(lot.status, 'pending')
    
    def test_approved_filter(self):
        """approved() should return only approved Lots."""
        lots = LotAcceptance.objects.approved()
        
        self.assertEqual(lots.count(), 1)  # LOT-A2
        self.assertEqual(lots.first().status, 'approved')
    
    def test_rejected_filter(self):
        """rejected() should return only rejected Lots."""
        lots = LotAcceptance.objects.rejected()
        
        self.assertEqual(lots.count(), 1)  # LOT-A3
        self.assertEqual(lots.first().status, 'rejected')


class LotManagerChainedFiltersTests(LotManagerTestCase):
    """Tests for chaining LotManager methods."""
    
    def test_for_user_then_pending(self):
        """Should be able to chain for_user().pending()."""
        lots = LotAcceptance.objects.for_user(self.partner_a.profile).pending()
        
        self.assertEqual(lots.count(), 1)  # LOT-A1
        self.assertEqual(lots.first(), self.lot_a_pending)
    
    def test_inspector_pending(self):
        """Inspector should see all pending Lots."""
        lots = LotAcceptance.objects.for_user(self.inspector.profile).pending()
        
        self.assertEqual(lots.count(), 2)  # LOT-A1, LOT-B1

