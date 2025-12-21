"""
End-to-end workflow tests for the MVP.
Tests all major actions: FA submission, FA reviews, Lot submission, Lot review.
Verifies both email and in-app notifications are created correctly.

Email Backend Behavior:
- If EMAIL_HOST_PASSWORD is set in .env, tests will use Resend (real emails sent via SMTP)
- Otherwise, uses locmem backend (emails captured in mail.outbox for content assertions)

When Resend is configured:
- Emails are actually sent to recipients
- Test assertions verify notifications were created (not email content)
- This allows testing actual email delivery in development

When locmem is used:
- Emails are captured in mail.outbox
- Test assertions verify email content (recipients, subject, body)
- No actual emails are sent
"""
import os
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.core import mail
from datetime import date
from accounts.models import UserProfile
from core.models import CamouflageType, VariantColor
from inspections.models import (
    FirstArticleInspection, LotAcceptance,
    FAEvaluation, FAColorEvaluation,
    LotEvaluation, LotSampleEvaluation, LotSampleColorEvaluation
)
from notifications.models import Notification

# Use Resend if configured in .env, otherwise use locmem for test assertions
# Check if EMAIL_HOST_PASSWORD is set (indicates Resend is configured)
_use_real_email = bool(os.getenv('EMAIL_HOST_PASSWORD'))
_email_backend = (
    os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
    if _use_real_email
    else 'django.core.mail.backends.locmem.EmailBackend'
)

# Use Resend test addresses when sending real emails to avoid domain reputation issues
# See: https://resend.com/docs/dashboard/emails/send-test-emails
if _use_real_email:
    TEST_EMAIL_PARTNER = 'delivered+partner@resend.dev'
    TEST_EMAIL_PRIMARY = 'delivered+primary_inspector@resend.dev'
    TEST_EMAIL_FINAL = 'delivered+final_inspector@resend.dev'
    TEST_EMAIL_STAFF = 'delivered+staff@resend.dev'
else:
    TEST_EMAIL_PARTNER = 'partner@test.com'
    TEST_EMAIL_PRIMARY = 'primary@test.com'
    TEST_EMAIL_FINAL = 'final@test.com'
    TEST_EMAIL_STAFF = 'staff@test.com'


@override_settings(EMAIL_BACKEND=_email_backend)
class FullWorkflowWithNotificationsTest(TestCase):
    """
    End-to-end test of the complete MVP workflow:
    1. Partner submits First Article -> email to Primary Inspector
    2. Primary Inspector reviews and approves -> email to Final Inspector  
    3. Final Inspector reviews and approves -> email to Partner
    4. Partner submits Lot -> email to Primary Inspector
    5. Primary Inspector reviews and approves Lot -> email to Partner
    
    Email assertions:
    - If Resend is configured (EMAIL_HOST_PASSWORD set), emails are actually sent
    - Otherwise, emails are captured in mail.outbox for content assertions
    """
    
    def assert_email_sent(self, expected_count=1, recipient_email=None, subject_contains=None, notification_type=None, recipient_user=None):
        """
        Conditionally assert email was sent.
        If using Resend (real emails), verify notification was created.
        If using locmem, verify email content in mail.outbox.
        """
        if _use_real_email:
            # When using Resend, verify notification was created (email was actually sent)
            if notification_type and recipient_user:
                notification = Notification.objects.filter(
                    recipient=recipient_user,
                    notification_type=notification_type
                ).first()
                self.assertIsNotNone(notification, f"Email notification of type {notification_type} should be created")
        else:
            # When using locmem, verify email content
            self.assertEqual(len(mail.outbox), expected_count)
            if recipient_email:
                self.assertIn(recipient_email, mail.outbox[0].to)
            if subject_contains:
                self.assertIn(subject_contains, mail.outbox[0].subject)
    
    def setUp(self):
        self.client = Client()
        
        # Create partner user (uses Resend test address when configured)
        self.partner = User.objects.create_user(
            username='partner', 
            email=TEST_EMAIL_PARTNER, 
            password='partner123'
        )
        self.partner.profile.user_functionality = 'partner'
        self.partner.profile.company_name = 'Test Partner Company'
        self.partner.profile.technical_email = TEST_EMAIL_PARTNER
        self.partner.profile.status = 'active'
        self.partner.profile.save()
        
        # Create primary inspector (uses Resend test address when configured)
        self.primary_inspector = User.objects.create_user(
            username='primary_inspector',
            email=TEST_EMAIL_PRIMARY,
            password='primary123'
        )
        self.primary_inspector.profile.user_functionality = 'admin'
        self.primary_inspector.profile.admin_role = 'primary_inspector'
        self.primary_inspector.profile.technical_email = TEST_EMAIL_PRIMARY
        self.primary_inspector.profile.status = 'active'
        self.primary_inspector.profile.save()
        
        # Create final inspector (uses Resend test address when configured)
        self.final_inspector = User.objects.create_user(
            username='final_inspector',
            email=TEST_EMAIL_FINAL,
            password='final123'
        )
        self.final_inspector.profile.user_functionality = 'admin'
        self.final_inspector.profile.admin_role = 'final_inspector'
        self.final_inspector.profile.technical_email = TEST_EMAIL_FINAL
        self.final_inspector.profile.status = 'active'
        self.final_inspector.profile.save()
        
        # Create staff user (uses Resend test address when configured)
        self.staff = User.objects.create_user(
            username='staff',
            email=TEST_EMAIL_STAFF,
            password='staff123'
        )
        self.staff.profile.user_functionality = 'admin'
        self.staff.profile.admin_role = 'staff_executive'
        self.staff.profile.technical_email = TEST_EMAIL_STAFF
        self.staff.profile.status = 'active'
        self.staff.profile.save()
        
        # Create camouflage type with colors
        self.camo = CamouflageType.objects.create(
            camouflage_name='MultiCam Original',
            status='active'
        )
        self.colors = []
        for i, name in enumerate(['Tan 525', 'Olive 527', 'Brown 529'], 1):
            color = VariantColor.objects.create(
                camouflage_type=self.camo,
                position=i,
                color_name=name
            )
            self.colors.append(color)
    
    def _get_passing_eval_data(self):
        """Build POST data for a passing evaluation"""
        data = {
            'pattern_execution': 'pass',
            'scale': 'pass',
            'spectral_reflectance': 'pass',
            'comments': 'All criteria passed',
            'submit_evaluation': 'Submit Evaluation',
        }
        for color in self.colors:
            data[f'color_{color.id}-rating'] = '4'
            data[f'color_{color.id}-comment'] = ''
        return data
    
    def _get_failing_eval_data(self):
        """Build POST data for a failing evaluation"""
        data = {
            'pattern_execution': 'fail',
            'scale': 'pass',
            'spectral_reflectance': 'pass',
            'comments': 'Pattern execution failed',
            'submit_evaluation': 'Submit Evaluation',
        }
        for color in self.colors:
            data[f'color_{color.id}-rating'] = '4'
            data[f'color_{color.id}-comment'] = ''
        return data
    
    def test_step1_partner_submits_fa(self):
        """Step 1: Partner submits First Article - triggers email to Primary Inspector"""
        if not _use_real_email:
            mail.outbox.clear()
        Notification.objects.all().delete()
        
        # Directly create FA and call notification function to test notification system
        # (Form submission via POST is covered by other tests)
        fa = FirstArticleInspection.objects.create(
            vendor=self.partner.profile,
            fabric_style='Nylon/Cotton 90210',
            multicam_variant=self.camo,
            shade_standard='alpha',
            spectral_reflectance_requirement='full',
            fa_lot_number='LOT-2024-001',
            date_of_printing=date.today(),
            submitter_first_name='John',
            submitter_last_name='Doe',
            status='pending'
        )
        
        # Trigger the notification
        from inspections.emails import send_fa_submitted_notification
        send_fa_submitted_notification(fa)
        
        # Check FA was created correctly
        self.assertEqual(fa.status, 'pending')
        self.assertEqual(fa.vendor, self.partner.profile)
        
        # Check email was sent to Primary Inspector
        # When using Resend: email is actually sent (verify notification created)
        # When using locmem: verify email content in mail.outbox
        if _use_real_email:
            notification = Notification.objects.filter(
                recipient=self.primary_inspector,
                notification_type='fa_submitted'
            ).first()
            self.assertIsNotNone(notification, "Email notification should be created when FA is submitted")
        else:
            self.assertEqual(len(mail.outbox), 1)
            self.assertIn(TEST_EMAIL_PRIMARY, mail.outbox[0].to)
            self.assertIn('PRIMARY INSPECTOR', mail.outbox[0].subject)
            self.assertIn('First Article', mail.outbox[0].subject)
        
        # Check in-app notification was created
        notifications = Notification.objects.filter(
            recipient=self.primary_inspector,
            notification_type='fa_submitted',
            channel='in_app'
        )
        self.assertEqual(notifications.count(), 1)
        self.assertIn('New First Article', notifications.first().title)

    def test_partner_can_submit_fa_via_view_and_status_stays_pending(self):
        """
        Regression: cover actual POST submit path (not just model create).
        Ensures FA lands in pending and does not incorrectly show as failed.
        """
        self.client.login(username='partner', password='partner123')

        payload = {
            'fabric_style': 'Submit View Fabric',
            'multicam_variant': self.camo.id,
            'shade_standard': 'alpha',
            'shade_standard_number': '',
            'spectral_reflectance_requirement': 'alpha',
            'fa_lot_number': 'LOT-SUBMIT-001',
            'date_of_printing': date.today().isoformat(),
            'first_article_ship_date': '',
            'tracking_number': '',
            'submitter_first_name': 'Pat',
            'submitter_last_name': 'Ner',
        }

        response = self.client.post(reverse('inspections:fa_submit'), payload, follow=True)
        self.assertEqual(response.status_code, 200)

        fa = FirstArticleInspection.objects.get(
            vendor=self.partner.profile,
            fa_lot_number='LOT-SUBMIT-001',
        )
        self.assertEqual(fa.status, 'pending')
        self.assertTrue(fa.submitted)
    
    def test_step2_primary_inspector_approves_fa(self):
        """Step 2: Primary Inspector approves FA - triggers email to Final Inspector"""
        # Create a pending FA
        fa = FirstArticleInspection.objects.create(
            vendor=self.partner.profile,
            fabric_style='Test Fabric',
            multicam_variant=self.camo,
            shade_standard='alpha',
            spectral_reflectance_requirement='full',
            fa_lot_number='LOT-STEP2-001',
            date_of_printing=date.today(),
            submitter_first_name='John',
            submitter_last_name='Doe',
            status='pending'
        )
        
        if not _use_real_email:
            mail.outbox.clear()
        Notification.objects.all().delete()
        
        self.client.login(username='primary_inspector', password='primary123')
        
        response = self.client.post(
            reverse('inspections:fa_review', args=[fa.fai_id]),
            self._get_passing_eval_data()
        )
        
        # Check FA moved to pending_final
        fa.refresh_from_db()
        self.assertEqual(fa.status, 'pending_final')
        
        # Check email was sent to Final Inspector
        self.assert_email_sent(
            expected_count=1,
            recipient_email=TEST_EMAIL_FINAL,
            subject_contains='FINAL INSPECTOR',
            notification_type='fa_pending_final',
            recipient_user=self.final_inspector
        )
        
        # Check in-app notification for Final Inspector
        notifications = Notification.objects.filter(
            recipient=self.final_inspector,
            notification_type='fa_pending_final',
            channel='in_app'
        )
        self.assertEqual(notifications.count(), 1)
    
    def test_step3_primary_inspector_rejects_fa(self):
        """Step 2 (alt): Primary Inspector rejects FA - triggers email to Partner"""
        # Create a pending FA
        fa = FirstArticleInspection.objects.create(
            vendor=self.partner.profile,
            fabric_style='Test Fabric Reject',
            multicam_variant=self.camo,
            shade_standard='alpha',
            spectral_reflectance_requirement='full',
            fa_lot_number='LOT-REJECT-001',
            date_of_printing=date.today(),
            submitter_first_name='John',
            submitter_last_name='Doe',
            status='pending'
        )
        
        if not _use_real_email:
            mail.outbox.clear()
        Notification.objects.all().delete()
        
        self.client.login(username='primary_inspector', password='primary123')
        
        response = self.client.post(
            reverse('inspections:fa_review', args=[fa.fai_id]),
            self._get_failing_eval_data()
        )
        
        # Check FA was rejected
        fa.refresh_from_db()
        self.assertEqual(fa.status, 'rejected')
        
        # Check email was sent to Partner
        self.assert_email_sent(
            expected_count=1,
            recipient_email=TEST_EMAIL_PARTNER,
            subject_contains='PARTNER',
            notification_type='fa_rejected',
            recipient_user=self.partner
        )
        
        # Check in-app notification for Partner
        notifications = Notification.objects.filter(
            recipient=self.partner,
            notification_type='fa_rejected',
            channel='in_app'
        )
        self.assertEqual(notifications.count(), 1)
    
    def test_step4_final_inspector_approves_fa(self):
        """Step 3: Final Inspector approves FA - triggers email to Partner"""
        # Create FA at pending_final status
        fa = FirstArticleInspection.objects.create(
            vendor=self.partner.profile,
            fabric_style='Test Fabric Final',
            multicam_variant=self.camo,
            shade_standard='alpha',
            spectral_reflectance_requirement='full',
            fa_lot_number='LOT-FINAL-001',
            date_of_printing=date.today(),
            submitter_first_name='John',
            submitter_last_name='Doe',
            status='pending_final',
            primary_inspector=self.primary_inspector
        )
        
        # Create primary evaluation
        primary_eval = FAEvaluation.objects.create(
            fa=fa,
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
        
        if not _use_real_email:
            mail.outbox.clear()
        Notification.objects.all().delete()
        
        self.client.login(username='final_inspector', password='final123')
        
        response = self.client.post(
            reverse('inspections:fa_review', args=[fa.fai_id]),
            self._get_passing_eval_data()
        )
        
        # Check FA was approved
        fa.refresh_from_db()
        self.assertEqual(fa.status, 'approved')
        
        # Check email was sent to Partner
        self.assert_email_sent(
            expected_count=1,
            recipient_email=TEST_EMAIL_PARTNER,
            subject_contains='PARTNER',
            notification_type='fa_approved',
            recipient_user=self.partner
        )
        
        # Check in-app notification for Partner
        notifications = Notification.objects.filter(
            recipient=self.partner,
            notification_type='fa_approved',
            channel='in_app'
        )
        self.assertEqual(notifications.count(), 1)
    
    def test_step5_final_inspector_rejects_fa(self):
        """Step 3 (alt): Final Inspector rejects FA - emails to Partner AND Primary Inspector"""
        # Create FA at pending_final status
        fa = FirstArticleInspection.objects.create(
            vendor=self.partner.profile,
            fabric_style='Test Fabric Final Reject',
            multicam_variant=self.camo,
            shade_standard='alpha',
            spectral_reflectance_requirement='full',
            fa_lot_number='LOT-FINAL-REJ-001',
            date_of_printing=date.today(),
            submitter_first_name='John',
            submitter_last_name='Doe',
            status='pending_final',
            primary_inspector=self.primary_inspector
        )
        
        # Create primary evaluation
        primary_eval = FAEvaluation.objects.create(
            fa=fa,
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
        
        if not _use_real_email:
            mail.outbox.clear()
        Notification.objects.all().delete()
        
        self.client.login(username='final_inspector', password='final123')
        
        response = self.client.post(
            reverse('inspections:fa_review', args=[fa.fai_id]),
            self._get_failing_eval_data()
        )
        
        # Check FA was rejected
        fa.refresh_from_db()
        self.assertEqual(fa.status, 'rejected')
        
        # Check emails were sent to both Partner AND Primary Inspector
        if _use_real_email:
            # Verify notifications were created for both recipients
            partner_notif = Notification.objects.filter(
                recipient=self.partner,
                notification_type='fa_rejected'
            ).first()
            primary_notif = Notification.objects.filter(
                recipient=self.primary_inspector,
                notification_type='fa_rejected'
            ).first()
            self.assertIsNotNone(partner_notif, "Partner should receive rejection notification")
            self.assertIsNotNone(primary_notif, "Primary Inspector should receive final rejection notification")
        else:
            self.assertEqual(len(mail.outbox), 2)
            recipients = [msg.to[0] for msg in mail.outbox]
            self.assertIn(TEST_EMAIL_PARTNER, recipients)
            self.assertIn(TEST_EMAIL_PRIMARY, recipients)
        
        # Check in-app notifications
        partner_notifs = Notification.objects.filter(
            recipient=self.partner,
            notification_type='fa_rejected',
            channel='in_app'
        )
        self.assertEqual(partner_notifs.count(), 1)
        
        primary_notifs = Notification.objects.filter(
            recipient=self.primary_inspector,
            notification_type='fa_rejected',
            channel='in_app'
        )
        self.assertEqual(primary_notifs.count(), 1)
    
    def test_step6_partner_submits_lot(self):
        """Step 4: Partner submits Lot against approved FA - email to Primary Inspector"""
        # Create approved FA
        fa = FirstArticleInspection.objects.create(
            vendor=self.partner.profile,
            fabric_style='Approved Fabric',
            multicam_variant=self.camo,
            shade_standard='alpha',
            spectral_reflectance_requirement='full',
            fa_lot_number='FA-APPROVED-001',
            date_of_printing=date.today(),
            submitter_first_name='John',
            submitter_last_name='Doe',
            status='approved'
        )
        
        if not _use_real_email:
            mail.outbox.clear()
        Notification.objects.all().delete()
        
        # Directly create Lot and call notification function to test notification system
        lot = LotAcceptance.objects.create(
            vendor=self.partner.profile,
            fabric_style=fa.fabric_style,
            shade_standard=fa.shade_standard,
            spectral_reflectance_requirement=fa.spectral_reflectance_requirement,
            original_fa_lot_number=fa.fa_lot_number,
            lot_lot_number='LOT-PROD-001',
            number_of_yards_printed=1000,
            number_of_samples=3,
            individual_sample_numbers='LOT-PROD-001-1, LOT-PROD-001-2, LOT-PROD-001-3',
            date_of_printing=date.today(),
            submitter_first_name='John',
            submitter_last_name='Doe',
            original_fa=fa,
            status='pending'
        )
        
        # Trigger the notification
        from inspections.emails import send_lot_submitted_notification
        send_lot_submitted_notification(lot)
        
        # Check Lot was created correctly
        self.assertEqual(lot.status, 'pending')
        self.assertEqual(lot.original_fa, fa)
        
        # Check email was sent to Primary Inspector
        self.assert_email_sent(
            expected_count=1,
            recipient_email=TEST_EMAIL_PRIMARY,
            subject_contains='PRIMARY INSPECTOR',
            notification_type='lot_submitted',
            recipient_user=self.primary_inspector
        )
        
        # Check in-app notification for Primary Inspector
        notifications = Notification.objects.filter(
            recipient=self.primary_inspector,
            notification_type='lot_submitted',
            channel='in_app'
        )
        self.assertEqual(notifications.count(), 1)

    def test_partner_can_submit_lot_via_view_requires_approved_fa(self):
        """
        Covers actual POST submit path for lots.
        """
        # Approved FA owned by partner
        fa = FirstArticleInspection.objects.create(
            vendor=self.partner.profile,
            fabric_style='Approved Fabric For Lot Submit',
            multicam_variant=self.camo,
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number='FA-FOR-LOT-SUBMIT',
            date_of_printing=date.today(),
            status='approved',
        )

        self.client.login(username='partner', password='partner123')

        payload = {
            'original_fa': fa.fai_id,  # ModelForm Select uses PK; here PK is fai_id
            'lot_lot_number': 'LOT-SUBMIT-001',
            'number_of_yards_printed': '1000',
            'date_of_printing': date.today().isoformat(),
            'date_shipped': '',
            'tracking_number': '',
            'submitter_first_name': 'Pat',
            'submitter_last_name': 'Ner',
            # Hidden fields expected by view:
            'individual_sample_numbers': 'LOT-SUBMIT-001-1, LOT-SUBMIT-001-2, LOT-SUBMIT-001-3',
            'number_of_samples': '3',
        }

        response = self.client.post(reverse('inspections:lot_submit'), payload, follow=True)
        self.assertEqual(response.status_code, 200)

        lot = LotAcceptance.objects.get(
            vendor=self.partner.profile,
            lot_lot_number='LOT-SUBMIT-001',
        )
        self.assertEqual(lot.status, 'pending')
        self.assertTrue(lot.submitted)

    def test_fa_evaluation_submit_blocked_when_variant_has_no_colors(self):
        """
        Regression for the reported issue: without VariantColor rows, an intended PASS
        could be computed as FAIL and flip the FA to rejected. We block submission instead.
        """
        # Create a camo variant with no colors
        camo_no_colors = CamouflageType.objects.create(
            camouflage_name='No Colors Variant',
            status='active',
        )

        fa = FirstArticleInspection.objects.create(
            vendor=self.partner.profile,
            fabric_style='No Colors Fabric',
            multicam_variant=camo_no_colors,
            shade_standard='alpha',
            spectral_reflectance_requirement='alpha',
            fa_lot_number='LOT-NOCOLORS-FA',
            date_of_printing=date.today(),
            status='pending',
        )

        self.client.login(username='primary_inspector', password='primary123')
        response = self.client.post(
            reverse('inspections:fa_review', args=[fa.fai_id]),
            {
                'pattern_execution': 'pass',
                'scale': 'pass',
                'spectral_reflectance': 'pass',
                'comments': 'Should not be allowed without colors',
                'submit_evaluation': 'Submit Evaluation',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        fa.refresh_from_db()
        self.assertEqual(fa.status, 'pending')
    
    def test_step7_primary_inspector_approves_lot(self):
        """Step 5: Primary Inspector approves Lot - email to Partner"""
        # Create approved FA and Lot
        fa = FirstArticleInspection.objects.create(
            vendor=self.partner.profile,
            fabric_style='FA For Lot',
            multicam_variant=self.camo,
            shade_standard='alpha',
            spectral_reflectance_requirement='full',
            fa_lot_number='FA-LOT-001',
            date_of_printing=date.today(),
            submitter_first_name='John',
            submitter_last_name='Doe',
            status='approved'
        )
        
        lot = LotAcceptance.objects.create(
            vendor=self.partner.profile,
            fabric_style='FA For Lot',
            shade_standard='alpha',
            spectral_reflectance_requirement='full',
            original_fa_lot_number='FA-LOT-001',
            lot_lot_number='LOT-APPROVE-001',
            number_of_yards_printed=1000,
            number_of_samples=3,
            individual_sample_numbers='LOT-APPROVE-001-1, LOT-APPROVE-001-2, LOT-APPROVE-001-3',
            date_of_printing=date.today(),
            submitter_first_name='John',
            submitter_last_name='Doe',
            original_fa=fa,
            status='pending'
        )
        
        if not _use_real_email:
            mail.outbox.clear()
        Notification.objects.all().delete()
        
        # Create and submit a passing evaluation
        lot_eval = LotEvaluation.objects.create(
            lot=lot,
            inspector=self.primary_inspector
        )
        
        # Create passing sample evaluation
        sample = LotSampleEvaluation.objects.create(
            lot_evaluation=lot_eval,
            sample_number=1,
            sample_id='LOT-APPROVE-001-1',
            pattern_execution='pass',
            scale='pass',
            spectral_reflectance='pass'
        )
        for color in self.colors:
            LotSampleColorEvaluation.objects.create(
                sample_evaluation=sample,
                color=color,
                rating='4'
            )
        
        # Submit evaluation
        lot_eval.submit()
        
        # Trigger the notification (as the view does after submit)
        from inspections.emails import send_lot_approved_notification
        send_lot_approved_notification(lot)
        
        # Check Lot was approved
        lot.refresh_from_db()
        self.assertEqual(lot.status, 'approved')
        
        # Check email was sent to Partner
        self.assert_email_sent(
            expected_count=1,
            recipient_email=TEST_EMAIL_PARTNER,
            subject_contains='PARTNER',
            notification_type='lot_approved',
            recipient_user=self.partner
        )
        
        # Check in-app notification for Partner
        notifications = Notification.objects.filter(
            recipient=self.partner,
            notification_type='lot_approved',
            channel='in_app'
        )
        self.assertEqual(notifications.count(), 1)
    
    def test_step8_primary_inspector_rejects_lot(self):
        """Step 5 (alt): Primary Inspector rejects Lot - email to Partner"""
        # Create approved FA and Lot
        fa = FirstArticleInspection.objects.create(
            vendor=self.partner.profile,
            fabric_style='FA For Lot Reject',
            multicam_variant=self.camo,
            shade_standard='alpha',
            spectral_reflectance_requirement='full',
            fa_lot_number='FA-LOT-REJ-001',
            date_of_printing=date.today(),
            submitter_first_name='John',
            submitter_last_name='Doe',
            status='approved'
        )
        
        lot = LotAcceptance.objects.create(
            vendor=self.partner.profile,
            fabric_style='FA For Lot Reject',
            shade_standard='alpha',
            spectral_reflectance_requirement='full',
            original_fa_lot_number='FA-LOT-REJ-001',
            lot_lot_number='LOT-REJECT-001',
            number_of_yards_printed=1000,
            number_of_samples=3,
            individual_sample_numbers='LOT-REJECT-001-1, LOT-REJECT-001-2, LOT-REJECT-001-3',
            date_of_printing=date.today(),
            submitter_first_name='John',
            submitter_last_name='Doe',
            original_fa=fa,
            status='pending'
        )
        
        if not _use_real_email:
            mail.outbox.clear()
        Notification.objects.all().delete()
        
        # Create and submit a failing evaluation
        lot_eval = LotEvaluation.objects.create(
            lot=lot,
            inspector=self.primary_inspector
        )
        
        # Create failing sample evaluation (pattern fails)
        sample = LotSampleEvaluation.objects.create(
            lot_evaluation=lot_eval,
            sample_number=1,
            sample_id='LOT-REJECT-001-1',
            pattern_execution='fail',  # FAIL
            scale='pass',
            spectral_reflectance='pass'
        )
        for color in self.colors:
            LotSampleColorEvaluation.objects.create(
                sample_evaluation=sample,
                color=color,
                rating='4'
            )
        
        # Submit evaluation
        lot_eval.submit()
        
        # Trigger the notification (as the view does after submit)
        from inspections.emails import send_lot_rejected_notification
        send_lot_rejected_notification(lot)
        
        # Check Lot was rejected
        lot.refresh_from_db()
        self.assertEqual(lot.status, 'rejected')
        
        # Check email was sent to Partner
        self.assert_email_sent(
            expected_count=1,
            recipient_email=TEST_EMAIL_PARTNER,
            subject_contains='PARTNER',
            notification_type='lot_rejected',
            recipient_user=self.partner
        )
        
        # Check in-app notification for Partner
        notifications = Notification.objects.filter(
            recipient=self.partner,
            notification_type='lot_rejected',
            channel='in_app'
        )
        self.assertEqual(notifications.count(), 1)
    
    def test_staff_dashboard_access(self):
        """Step 6: Staff can view dashboard with all stats"""
        # Create some data for the staff to see
        fa = FirstArticleInspection.objects.create(
            vendor=self.partner.profile,
            fabric_style='Staff View FA',
            multicam_variant=self.camo,
            shade_standard='alpha',
            spectral_reflectance_requirement='full',
            fa_lot_number='STAFF-FA-001',
            date_of_printing=date.today(),
            submitter_first_name='John',
            submitter_last_name='Doe',
            status='approved'
        )
        
        self.client.login(username='staff', password='staff123')
        
        response = self.client.get(reverse('dashboard:staff_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Staff should see statistics
        self.assertIn('fa_stats', response.context)
        self.assertIn('lot_stats', response.context)


@override_settings(EMAIL_BACKEND=_email_backend)
class NotificationContentTest(TestCase):
    """Test that notification content is correct and informative."""
    
    def setUp(self):
        # Create users (uses Resend test addresses when configured)
        self.partner = User.objects.create_user(
            username='partner', email=TEST_EMAIL_PARTNER, password='partner123'
        )
        self.partner.profile.user_functionality = 'partner'
        self.partner.profile.company_name = 'Acme Fabrics Inc.'
        self.partner.profile.technical_email = TEST_EMAIL_PARTNER
        self.partner.profile.status = 'active'
        self.partner.profile.save()
        
        self.primary = User.objects.create_user(
            username='primary', email=TEST_EMAIL_PRIMARY, password='primary123'
        )
        self.primary.profile.user_functionality = 'admin'
        self.primary.profile.admin_role = 'primary_inspector'
        self.primary.profile.technical_email = TEST_EMAIL_PRIMARY
        self.primary.profile.status = 'active'
        self.primary.profile.save()
        
        self.camo = CamouflageType.objects.create(
            camouflage_name='MultiCam Tropic',
            status='active'
        )
    
    def test_fa_submitted_notification_contains_key_info(self):
        """FA submitted notification should contain all key information."""
        if not _use_real_email:
            mail.outbox.clear()
        
        fa = FirstArticleInspection.objects.create(
            vendor=self.partner.profile,
            fabric_style='Premium Nylon 500D',
            multicam_variant=self.camo,
            shade_standard='alpha',
            spectral_reflectance_requirement='full',
            fa_lot_number='2024-BATCH-42',
            date_of_printing=date.today(),
            submitter_first_name='Jane',
            submitter_last_name='Smith',
            status='pending'
        )
        
        from inspections.emails import send_fa_submitted_notification
        send_fa_submitted_notification(fa)
        
        # Check email content (only when using locmem)
        if _use_real_email:
            # When using Resend, verify notification was created
            notification = Notification.objects.filter(
                recipient=self.primary,
                notification_type='fa_submitted'
            ).first()
            self.assertIsNotNone(notification, "Email notification should be created")
            # Verify notification contains key info
            self.assertIn('Acme Fabrics', notification.message)
            self.assertIn('Premium Nylon 500D', notification.message)
            self.assertIn('MultiCam Tropic', notification.message)
            self.assertIn('2024-BATCH-42', notification.message)
        else:
            email = mail.outbox[0]
            self.assertIn('Acme Fabrics', email.body)  # Company name
            self.assertIn('Premium Nylon 500D', email.body)  # Fabric style
            self.assertIn('MultiCam Tropic', email.body)  # Variant
            self.assertIn('2024-BATCH-42', email.body)  # Lot number
            self.assertIn(fa.fai_id, email.body)  # FA ID
        
        # Check in-app notification
        notification = Notification.objects.filter(
            notification_type='fa_submitted',
            channel='in_app'
        ).first()
        
        self.assertIn('Acme Fabrics', notification.title)
        self.assertIn(fa.fai_id, notification.action_url)
    
    def test_notification_action_urls_are_correct(self):
        """Notification action URLs should point to correct pages."""
        fa = FirstArticleInspection.objects.create(
            vendor=self.partner.profile,
            fabric_style='Test Fabric',
            multicam_variant=self.camo,
            shade_standard='alpha',
            spectral_reflectance_requirement='full',
            fa_lot_number='URL-TEST-001',
            date_of_printing=date.today(),
            submitter_first_name='Test',
            submitter_last_name='User',
            status='pending'
        )
        
        from inspections.emails import send_fa_submitted_notification
        send_fa_submitted_notification(fa)
        
        # For Primary Inspector, action URL should be review page
        notification = Notification.objects.filter(
            recipient=self.primary,
            notification_type='fa_submitted',
            channel='in_app'
        ).first()
        
        self.assertIn('/portal/admin/fa/review/', notification.action_url)
        self.assertIn(fa.fai_id, notification.action_url)


@override_settings(EMAIL_BACKEND=_email_backend)  
class InAppNotificationTest(TestCase):
    """Test in-app notification functionality."""
    
    def setUp(self):
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='testuser', email='test@test.com', password='test123'
        )
        self.user.profile.user_functionality = 'admin'
        self.user.profile.admin_role = 'primary_inspector'
        self.user.profile.status = 'active'
        self.user.profile.save()
    
    def test_notification_dropdown_shows_unread_count(self):
        """Notification dropdown should show correct unread count."""
        # Create some notifications
        for i in range(3):
            Notification.objects.create(
                recipient=self.user,
                channel='in_app',
                notification_type='fa_submitted',
                title=f'Test {i}',
                message='Test message',
                status='sent'
            )
        
        self.client.login(username='testuser', password='test123')
        
        response = self.client.get(reverse('notifications:dropdown'))
        self.assertEqual(response.status_code, 200)
        
        # Should show 3 unread notifications
        self.assertContains(response, 'Test 0')
        self.assertContains(response, 'Test 1')
        self.assertContains(response, 'Test 2')
    
    def test_mark_notification_as_read(self):
        """Marking a notification as read should update its status."""
        notification = Notification.objects.create(
            recipient=self.user,
            channel='in_app',
            notification_type='fa_submitted',
            title='Test',
            message='Test message',
            status='sent'
        )
        
        self.client.login(username='testuser', password='test123')
        
        response = self.client.post(
            reverse('notifications:mark_read', args=[notification.id])
        )
        
        notification.refresh_from_db()
        self.assertEqual(notification.status, 'read')
        self.assertIsNotNone(notification.read_at)
    
    def test_mark_all_as_read(self):
        """Marking all as read should update all notifications."""
        for i in range(5):
            Notification.objects.create(
                recipient=self.user,
                channel='in_app',
                notification_type='fa_submitted',
                title=f'Test {i}',
                message='Test message',
                status='sent'
            )
        
        self.client.login(username='testuser', password='test123')
        
        response = self.client.post(reverse('notifications:mark_all_read'))
        
        unread = Notification.objects.filter(
            recipient=self.user,
            status='sent'
        ).count()
        
        self.assertEqual(unread, 0)
    
    def test_notification_list_view(self):
        """Notification list view should show all notifications."""
        for i in range(10):
            Notification.objects.create(
                recipient=self.user,
                channel='in_app',
                notification_type='fa_submitted',
                title=f'Notification {i}',
                message=f'Message {i}',
                status='sent'
            )
        
        self.client.login(username='testuser', password='test123')
        
        response = self.client.get(reverse('notifications:list'))
        self.assertEqual(response.status_code, 200)
        
        # Should show all notifications
        for i in range(10):
            self.assertContains(response, f'Notification {i}')
