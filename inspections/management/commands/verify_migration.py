"""
Management command to verify data migration completeness
"""
from django.core.management.base import BaseCommand
from accounts.models import UserProfile
from inspections.models import FirstArticleInspection, LotAcceptance


class Command(BaseCommand):
    help = 'Verify data migration completeness'

    def handle(self, *args, **options):
        self.stdout.write('='*80)
        self.stdout.write('MIGRATION VERIFICATION REPORT')
        self.stdout.write('='*80 + '\n')

        # Check printers
        printer_count = UserProfile.objects.filter(user_functionality='printer').count()
        self.stdout.write(f'Printers imported: {printer_count}')
        self.stdout.write(f'Expected: 38\n')

        # Check FAs
        fa_count = FirstArticleInspection.objects.count()
        fa_pending = FirstArticleInspection.objects.filter(status='pending').count()
        fa_approved = FirstArticleInspection.objects.filter(status='approved').count()
        fa_rejected = FirstArticleInspection.objects.filter(status='rejected').count()
        
        self.stdout.write(f'Total FAs: {fa_count}')
        self.stdout.write(f'  Pending: {fa_pending}')
        self.stdout.write(f'  Approved: {fa_approved}')
        self.stdout.write(f'  Rejected: {fa_rejected}\n')

        # Check Lots
        lot_count = LotAcceptance.objects.count()
        lot_pending = LotAcceptance.objects.filter(status='pending').count()
        lot_approved = LotAcceptance.objects.filter(status='approved').count()
        lot_rejected = LotAcceptance.objects.filter(status='rejected').count()
        
        self.stdout.write(f'Total Lots: {lot_count}')
        self.stdout.write(f'  Pending: {lot_pending}')
        self.stdout.write(f'  Approved: {lot_approved}')
        self.stdout.write(f'  Rejected: {lot_rejected}\n')

        # Check lot-FA relationships
        lots_without_fa = LotAcceptance.objects.filter(original_fa__isnull=True).count()
        if lots_without_fa > 0:
            self.stdout.write(
                self.style.WARNING(f'⚠ Warning: {lots_without_fa} lots without linked FA')
            )
        else:
            self.stdout.write(self.style.SUCCESS('✓ All lots linked to FAs'))

        # Check for orphaned records
        orphaned_lots = 0
        for lot in LotAcceptance.objects.all():
            if not lot.original_fa:
                orphaned_lots += 1
        
        if orphaned_lots == 0:
            self.stdout.write(self.style.SUCCESS('✓ No orphaned lots found\n'))
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠ Warning: {orphaned_lots} orphaned lots found\n')
            )

        self.stdout.write('='*80)

