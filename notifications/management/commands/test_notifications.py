"""
Management command to test all notification types.

Triggers each notification type using existing test data.
Test users should use Resend test emails (delivered+username@resend.dev)
which always show as "Delivered" in Resend dashboard.

Usage:
    python manage.py test_notifications           # Test all notifications
    python manage.py test_notifications --list    # List available notification types
    python manage.py test_notifications fa_submitted  # Test specific notification
    
For production:
    ./scripts/prod_run.sh test_notifications
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from inspections.models import FirstArticleInspection, LotAcceptance
from inspections.emails import (
    send_fa_submitted_notification,
    send_fa_pending_final_notification,
    send_fa_approved_notification,
    send_fa_rejected_notification,
    send_lot_submitted_notification,
    send_lot_approved_notification,
    send_lot_rejected_notification,
)


class Command(BaseCommand):
    help = 'Test all notification types using existing test data'

    NOTIFICATION_TYPES = {
        'fa_submitted': {
            'description': 'FA submitted → Primary Inspector',
            'function': send_fa_submitted_notification,
            'model': 'fa',
            'status': 'pending',
        },
        'fa_pending_final': {
            'description': 'FA passed primary → Final Inspector',
            'function': send_fa_pending_final_notification,
            'model': 'fa',
            'status': 'pending_final',
        },
        'fa_approved': {
            'description': 'FA fully approved → Partner',
            'function': send_fa_approved_notification,
            'model': 'fa',
            'status': 'approved',
        },
        'fa_rejected': {
            'description': 'FA rejected → Partner (+ Primary if final rejection)',
            'function': send_fa_rejected_notification,
            'model': 'fa',
            'status': 'rejected',
        },
        'lot_submitted': {
            'description': 'Lot submitted → Primary Inspector',
            'function': send_lot_submitted_notification,
            'model': 'lot',
            'status': 'pending',
        },
        'lot_approved': {
            'description': 'Lot approved → Partner',
            'function': send_lot_approved_notification,
            'model': 'lot',
            'status': 'approved',
        },
        'lot_rejected': {
            'description': 'Lot rejected → Partner',
            'function': send_lot_rejected_notification,
            'model': 'lot',
            'status': 'rejected',
        },
    }

    def add_arguments(self, parser):
        parser.add_argument(
            'notification_type',
            nargs='?',
            default='all',
            help='Notification type to test (or "all" for all types)',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all available notification types',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending',
        )

    def handle(self, *args, **options):
        if options['list']:
            self.list_notification_types()
            return

        notification_type = options['notification_type']
        dry_run = options['dry_run']

        if notification_type == 'all':
            self.test_all_notifications(dry_run)
        elif notification_type in self.NOTIFICATION_TYPES:
            self.test_notification(notification_type, dry_run)
        else:
            self.stdout.write(self.style.ERROR(f'Unknown notification type: {notification_type}'))
            self.stdout.write('Use --list to see available types')

    def list_notification_types(self):
        """List all available notification types"""
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Available Notification Types:'))
        self.stdout.write('-' * 60)
        for name, info in self.NOTIFICATION_TYPES.items():
            self.stdout.write(f'  {name:20} {info["description"]}')
        self.stdout.write('')
        self.stdout.write('Usage: python manage.py test_notifications <type>')
        self.stdout.write('       python manage.py test_notifications all')
        self.stdout.write('')

    def test_all_notifications(self, dry_run=False):
        """Test all notification types"""
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('TESTING ALL NOTIFICATIONS'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No emails will be sent'))
        
        self.stdout.write('')

        # Get test data
        fa_pending = FirstArticleInspection.objects.filter(status='pending').first()
        fa_pending_final = FirstArticleInspection.objects.filter(status='pending_final').first()
        fa_approved = FirstArticleInspection.objects.filter(status='approved').first()
        lot_pending = LotAcceptance.objects.filter(status='pending').first()

        results = []

        # FA Submitted
        if fa_pending:
            results.append(self._test('fa_submitted', fa_pending, dry_run))
        else:
            results.append(('fa_submitted', 'SKIPPED', 'No pending FA found'))

        # FA Pending Final
        if fa_pending_final:
            results.append(self._test('fa_pending_final', fa_pending_final, dry_run))
        else:
            results.append(('fa_pending_final', 'SKIPPED', 'No pending_final FA found'))

        # FA Approved
        if fa_approved:
            results.append(self._test('fa_approved', fa_approved, dry_run))
        else:
            results.append(('fa_approved', 'SKIPPED', 'No approved FA found'))

        # FA Rejected (use any FA)
        any_fa = fa_pending or fa_pending_final or fa_approved
        if any_fa:
            results.append(self._test('fa_rejected', any_fa, dry_run))
        else:
            results.append(('fa_rejected', 'SKIPPED', 'No FA found'))

        # Lot Submitted
        if lot_pending:
            results.append(self._test('lot_submitted', lot_pending, dry_run))
        else:
            results.append(('lot_submitted', 'SKIPPED', 'No pending Lot found'))

        # Lot Approved (use pending lot for test)
        if lot_pending:
            results.append(self._test('lot_approved', lot_pending, dry_run))
        else:
            results.append(('lot_approved', 'SKIPPED', 'No Lot found'))

        # Lot Rejected (use pending lot for test)
        if lot_pending:
            results.append(self._test('lot_rejected', lot_pending, dry_run))
        else:
            results.append(('lot_rejected', 'SKIPPED', 'No Lot found'))

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('RESULTS'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        sent = sum(1 for r in results if r[1] == 'SENT')
        skipped = sum(1 for r in results if r[1] == 'SKIPPED')
        failed = sum(1 for r in results if r[1] == 'FAILED')
        
        for name, status, detail in results:
            if status == 'SENT':
                self.stdout.write(f'  ✓ {name:20} {self.style.SUCCESS(status):15} {detail}')
            elif status == 'SKIPPED':
                self.stdout.write(f'  - {name:20} {self.style.WARNING(status):15} {detail}')
            else:
                self.stdout.write(f'  ✗ {name:20} {self.style.ERROR(status):15} {detail}')
        
        self.stdout.write('')
        self.stdout.write(f'Sent: {sent}, Skipped: {skipped}, Failed: {failed}')
        self.stdout.write('')
        self.stdout.write('Check Resend dashboard: https://resend.com/emails')
        self.stdout.write('')

    def _test(self, notification_type, obj, dry_run=False):
        """Test a single notification"""
        info = self.NOTIFICATION_TYPES[notification_type]
        
        try:
            if dry_run:
                if info['model'] == 'fa':
                    detail = f'{obj.fai_id} → {obj.vendor.user.email}'
                else:
                    detail = f'{obj.lot_id} → {obj.vendor.user.email}'
                return (notification_type, 'DRY_RUN', detail)
            
            # Actually send
            info['function'](obj)
            
            if info['model'] == 'fa':
                detail = f'{obj.fai_id}'
            else:
                detail = f'{obj.lot_id}'
            
            return (notification_type, 'SENT', detail)
            
        except Exception as e:
            return (notification_type, 'FAILED', str(e))

    def test_notification(self, notification_type, dry_run=False):
        """Test a specific notification type"""
        info = self.NOTIFICATION_TYPES[notification_type]
        
        self.stdout.write('')
        self.stdout.write(f'Testing: {notification_type}')
        self.stdout.write(f'Description: {info["description"]}')
        self.stdout.write('')
        
        # Find appropriate test object
        if info['model'] == 'fa':
            obj = FirstArticleInspection.objects.filter(status=info['status']).first()
            if not obj:
                obj = FirstArticleInspection.objects.first()
            if not obj:
                self.stdout.write(self.style.ERROR('No FA found to test with'))
                return
        else:
            obj = LotAcceptance.objects.filter(status=info['status']).first()
            if not obj:
                obj = LotAcceptance.objects.first()
            if not obj:
                self.stdout.write(self.style.ERROR('No Lot found to test with'))
                return
        
        name, status, detail = self._test(notification_type, obj, dry_run)
        
        if status == 'SENT':
            self.stdout.write(self.style.SUCCESS(f'✓ Notification sent: {detail}'))
        elif status == 'DRY_RUN':
            self.stdout.write(self.style.WARNING(f'Would send: {detail}'))
        else:
            self.stdout.write(self.style.ERROR(f'✗ Failed: {detail}'))
        
        self.stdout.write('')
        self.stdout.write('Check Resend dashboard: https://resend.com/emails')

