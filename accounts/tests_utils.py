"""
Tests for accounts/utils.py

Tests the centralized profile management and access control utility functions.

Note: UserProfile is auto-created by a signal when User is created (see accounts/signals.py).
Tests must account for this behavior.
"""
from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.http import Http404
from accounts.models import UserProfile, PartnerCompany
from accounts.utils import (
    get_or_create_profile,
    get_fa_for_user,
    get_lot_for_user,
    get_fa_stats,
    get_lot_stats,
)
from inspections.models import FirstArticleInspection, LotAcceptance
from core.models import CamouflageType

User = get_user_model()


def create_fa(vendor, company, camo, fabric_style, fa_lot_number, status='pending'):
    """Helper to create FA with all required fields."""
    return FirstArticleInspection.objects.create(
        vendor=vendor,
        company=company,
        multicam_variant=camo,
        fabric_style=fabric_style,
        fa_lot_number=fa_lot_number,
        status=status,
        shade_standard='alpha',
        spectral_reflectance_requirement='alpha',
        date_of_printing=date.today(),
        submitter_first_name='Test',
        submitter_last_name='User',
    )


def create_lot(vendor, company, original_fa, lot_lot_number, status='pending'):
    """Helper to create Lot with all required fields.
    
    Note: multicam_variant is a property derived from original_fa, not a field.
    """
    return LotAcceptance.objects.create(
        vendor=vendor,
        company=company,
        original_fa=original_fa,
        fabric_style=original_fa.fabric_style,
        shade_standard=original_fa.shade_standard,
        spectral_reflectance_requirement=original_fa.spectral_reflectance_requirement,
        original_fa_lot_number=original_fa.fa_lot_number,
        lot_lot_number=lot_lot_number,
        number_of_yards_printed=1000,
        number_of_samples=3,
        individual_sample_numbers=f'{lot_lot_number}-1, {lot_lot_number}-2, {lot_lot_number}-3',
        status=status,
        date_of_printing=date.today(),
        submitter_first_name='Test',
        submitter_last_name='User',
    )


class GetOrCreateProfileTests(TestCase):
    """Tests for get_or_create_profile helper function."""
    
    def test_returns_existing_profile(self):
        """Should return existing profile created by signal."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # Signal auto-creates profile - verify it exists
        self.assertTrue(hasattr(user, 'profile'))
        original_profile = user.profile
        
        result = get_or_create_profile(user)
        
        self.assertEqual(result.pk, original_profile.pk)
        self.assertEqual(UserProfile.objects.filter(user=user).count(), 1)
    
    def test_returns_same_profile_on_multiple_calls(self):
        """Multiple calls should return same profile without creating duplicates."""
        user = User.objects.create_user(
            username='multiuser',
            email='multi@example.com',
            password='testpass123'
        )
        
        result1 = get_or_create_profile(user)
        result2 = get_or_create_profile(user)
        result3 = get_or_create_profile(user)
        
        self.assertEqual(result1.pk, result2.pk)
        self.assertEqual(result2.pk, result3.pk)
        self.assertEqual(UserProfile.objects.filter(user=user).count(), 1)
    
    def test_signal_creates_profile_with_email_derived_company_name(self):
        """Company name should default to email prefix (via signal)."""
        user = User.objects.create_user(
            username='emailuser',
            email='mycompany@example.com',
            password='testpass123'
        )
        
        result = get_or_create_profile(user)
        
        self.assertEqual(result.company_name, 'mycompany')
    
    def test_signal_creates_profile_with_username_when_no_email(self):
        """Company name should default to username if no email (via signal)."""
        user = User.objects.create_user(
            username='noemailuser',
            email='',
            password='testpass123'
        )
        
        result = get_or_create_profile(user)
        
        self.assertEqual(result.company_name, 'noemailuser')
    
    def test_staff_user_gets_admin_functionality(self):
        """Staff users should get admin user_functionality (via signal)."""
        user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )
        
        result = get_or_create_profile(user)
        
        self.assertEqual(result.user_functionality, 'admin')
    
    def test_regular_user_gets_partner_functionality(self):
        """Regular users should get partner user_functionality (via signal)."""
        user = User.objects.create_user(
            username='partneruser',
            email='partner@example.com',
            password='testpass123',
            is_staff=False
        )
        
        result = get_or_create_profile(user)
        
        self.assertEqual(result.user_functionality, 'partner')
    
    def test_creates_profile_if_deleted(self):
        """Should create profile if somehow deleted after user creation."""
        user = User.objects.create_user(
            username='deletedprofile',
            email='deleted@example.com',
            password='testpass123'
        )
        # Delete the auto-created profile
        UserProfile.objects.filter(user=user).delete()
        # Refresh user from db to clear cached profile relation
        user.refresh_from_db()
        
        # Now get_or_create_profile should create a new one
        result = get_or_create_profile(user)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.user, user)
        self.assertEqual(UserProfile.objects.filter(user=user).count(), 1)
    
    def test_default_permissions_set_for_partner(self):
        """Partner users should have submit permissions set by default."""
        user = User.objects.create_user(
            username='permuser',
            email='perm@example.com',
            password='testpass123',
            is_staff=False
        )
        
        result = get_or_create_profile(user)
        
        # Partner users should have submit permissions set by default
        self.assertTrue(result.can_submit_fa)
        self.assertTrue(result.can_submit_lots)


class GetFAForUserTests(TestCase):
    """Tests for get_fa_for_user access control helper."""
    
    def setUp(self):
        """Set up test data."""
        # Create camouflage type
        self.camo, _ = CamouflageType.objects.get_or_create(
            camouflage_name='Multicam'
        )
        
        # Create company A and partner
        self.company_a = PartnerCompany.objects.create(code='COMPA', name='Company A')
        self.partner_a = User.objects.create_user('partnera', 'a@a.com', 'pass')
        self.partner_a.profile.company = self.company_a
        self.partner_a.profile.user_functionality = 'partner'
        self.partner_a.profile.save()
        
        # Create company B and partner
        self.company_b = PartnerCompany.objects.create(code='COMPB', name='Company B')
        self.partner_b = User.objects.create_user('partnerb', 'b@b.com', 'pass')
        self.partner_b.profile.company = self.company_b
        self.partner_b.profile.user_functionality = 'partner'
        self.partner_b.profile.save()
        
        # Create inspector
        self.inspector = User.objects.create_user('inspector', 'i@i.com', 'pass')
        self.inspector.profile.user_functionality = 'admin'
        self.inspector.profile.admin_role = 'primary_inspector'
        self.inspector.profile.save()
        
        # Create FA for company A
        self.fa_a = create_fa(
            self.partner_a.profile, self.company_a, self.camo,
            'Fabric A', 'LOTA', 'pending'
        )
        
        # Create FA for company B
        self.fa_b = create_fa(
            self.partner_b.profile, self.company_b, self.camo,
            'Fabric B', 'LOTB', 'pending_final'
        )
    
    def test_partner_can_access_own_company_fa(self):
        """Partner should be able to access their company's FA."""
        result = get_fa_for_user(self.partner_a.profile, self.fa_a.fai_id)
        self.assertEqual(result.pk, self.fa_a.pk)
    
    def test_partner_cannot_access_other_company_fa(self):
        """Partner should not be able to access other company's FA."""
        with self.assertRaises(Http404):
            get_fa_for_user(self.partner_a.profile, self.fa_b.fai_id)
    
    def test_inspector_can_access_any_fa(self):
        """Inspector should be able to access any FA."""
        result_a = get_fa_for_user(self.inspector.profile, self.fa_a.fai_id)
        result_b = get_fa_for_user(self.inspector.profile, self.fa_b.fai_id)
        
        self.assertEqual(result_a.pk, self.fa_a.pk)
        self.assertEqual(result_b.pk, self.fa_b.pk)
    
    def test_nonexistent_fa_raises_404(self):
        """Accessing non-existent FA should raise 404."""
        with self.assertRaises(Http404):
            get_fa_for_user(self.inspector.profile, 'NONEXISTENT-ID')


class GetLotForUserTests(TestCase):
    """Tests for get_lot_for_user access control helper."""
    
    def setUp(self):
        """Set up test data."""
        self.camo, _ = CamouflageType.objects.get_or_create(
            camouflage_name='Multicam'
        )
        
        # Create company A and partner
        self.company_a = PartnerCompany.objects.create(code='COMPA', name='Company A')
        self.partner_a = User.objects.create_user('partnera', 'a@a.com', 'pass')
        self.partner_a.profile.company = self.company_a
        self.partner_a.profile.user_functionality = 'partner'
        self.partner_a.profile.save()
        
        # Create company B and partner
        self.company_b = PartnerCompany.objects.create(code='COMPB', name='Company B')
        self.partner_b = User.objects.create_user('partnerb', 'b@b.com', 'pass')
        self.partner_b.profile.company = self.company_b
        self.partner_b.profile.user_functionality = 'partner'
        self.partner_b.profile.save()
        
        # Create inspector
        self.inspector = User.objects.create_user('inspector', 'i@i.com', 'pass')
        self.inspector.profile.user_functionality = 'admin'
        self.inspector.profile.admin_role = 'primary_inspector'
        self.inspector.profile.save()
        
        # Create FA (required for lot)
        self.fa_a = create_fa(
            self.partner_a.profile, self.company_a, self.camo,
            'Fabric A', 'LOTA', 'approved'
        )
        self.fa_b = create_fa(
            self.partner_b.profile, self.company_b, self.camo,
            'Fabric B', 'LOTB', 'approved'
        )
        
        # Create Lot for company A
        self.lot_a = create_lot(
            self.partner_a.profile, self.company_a, self.fa_a,
            'LOT-A-001', 'pending'
        )
        
        # Create Lot for company B
        self.lot_b = create_lot(
            self.partner_b.profile, self.company_b, self.fa_b,
            'LOT-B-001', 'pending'
        )
    
    def test_partner_can_access_own_company_lot(self):
        """Partner should be able to access their company's Lot."""
        result = get_lot_for_user(self.partner_a.profile, self.lot_a.lot_id)
        self.assertEqual(result.pk, self.lot_a.pk)
    
    def test_partner_cannot_access_other_company_lot(self):
        """Partner should not be able to access other company's Lot."""
        with self.assertRaises(Http404):
            get_lot_for_user(self.partner_a.profile, self.lot_b.lot_id)
    
    def test_inspector_can_access_any_lot(self):
        """Inspector should be able to access any Lot."""
        result_a = get_lot_for_user(self.inspector.profile, self.lot_a.lot_id)
        result_b = get_lot_for_user(self.inspector.profile, self.lot_b.lot_id)
        
        self.assertEqual(result_a.pk, self.lot_a.pk)
        self.assertEqual(result_b.pk, self.lot_b.pk)
    
    def test_nonexistent_lot_raises_404(self):
        """Accessing non-existent Lot should raise 404."""
        with self.assertRaises(Http404):
            get_lot_for_user(self.inspector.profile, 'NONEXISTENT-ID')


class GetFAStatsTests(TestCase):
    """Tests for get_fa_stats helper."""
    
    def setUp(self):
        """Set up test data."""
        self.camo, _ = CamouflageType.objects.get_or_create(
            camouflage_name='Multicam'
        )
        self.company = PartnerCompany.objects.create(code='TEST', name='Test')
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass')
        self.user.profile.company = self.company
        self.user.profile.user_functionality = 'partner'
        self.user.profile.save()
        
        # Create FAs with different statuses
        statuses = ['pending', 'pending', 'pending_final', 'approved', 'approved', 'approved', 'rejected']
        for i, status in enumerate(statuses):
            create_fa(
                self.user.profile, self.company, self.camo,
                f'Fabric {i}', f'LOT-{i}', status
            )
    
    def test_counts_all_statuses_correctly(self):
        """Should correctly count pending, approved, rejected."""
        qs = FirstArticleInspection.objects.all()
        stats = get_fa_stats(qs)
        
        # 2 pending + 1 pending_final = 3 "pending"
        self.assertEqual(stats['pending'], 3)
        self.assertEqual(stats['approved'], 3)
        self.assertEqual(stats['rejected'], 1)
    
    def test_empty_queryset_returns_zeros(self):
        """Empty queryset should return zeros."""
        qs = FirstArticleInspection.objects.none()
        stats = get_fa_stats(qs)
        
        self.assertEqual(stats['pending'], 0)
        self.assertEqual(stats['approved'], 0)
        self.assertEqual(stats['rejected'], 0)


class GetLotStatsTests(TestCase):
    """Tests for get_lot_stats helper."""
    
    def setUp(self):
        """Set up test data."""
        self.camo, _ = CamouflageType.objects.get_or_create(
            camouflage_name='Multicam'
        )
        self.company = PartnerCompany.objects.create(code='TEST', name='Test')
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass')
        self.user.profile.company = self.company
        self.user.profile.user_functionality = 'partner'
        self.user.profile.save()
        
        # Create approved FA for lots
        self.fa = create_fa(
            self.user.profile, self.company, self.camo,
            'Fabric', 'FA-LOT', 'approved'
        )
        
        # Create Lots with different statuses
        statuses = ['pending', 'pending', 'approved', 'approved', 'approved', 'rejected']
        for i, status in enumerate(statuses):
            create_lot(
                self.user.profile, self.company, self.fa,
                f'LOT-{i}', status
            )
    
    def test_counts_all_statuses_correctly(self):
        """Should correctly count pending, approved, rejected."""
        qs = LotAcceptance.objects.all()
        stats = get_lot_stats(qs)
        
        self.assertEqual(stats['pending'], 2)
        self.assertEqual(stats['approved'], 3)
        self.assertEqual(stats['rejected'], 1)
    
    def test_empty_queryset_returns_zeros(self):
        """Empty queryset should return zeros."""
        qs = LotAcceptance.objects.none()
        stats = get_lot_stats(qs)
        
        self.assertEqual(stats['pending'], 0)
        self.assertEqual(stats['approved'], 0)
        self.assertEqual(stats['rejected'], 0)
