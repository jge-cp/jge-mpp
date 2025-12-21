"""
Backfill missing VariantColor rows.

Some camouflage variants may exist without any colors configured. Since FA/Lot
evaluation relies on variant colors, this command ensures every CamouflageType
has at least one color by inserting a single placeholder color.

Usage:
  python manage.py backfill_variant_temp_colors
  python manage.py backfill_variant_temp_colors --dry-run
  python manage.py backfill_variant_temp_colors --include-inactive
"""

# pyright: reportAttributeAccessIssue=false

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from core.models import CamouflageType, VariantColor


class Command(BaseCommand):
    help = "Ensure every CamouflageType has at least one VariantColor by adding a TEMP COLOR when missing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would change, but do not write to the database.",
        )
        parser.add_argument(
            "--include-inactive",
            action="store_true",
            help="Also backfill inactive/development variants (default: active only).",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        include_inactive: bool = options["include_inactive"]

        qs = CamouflageType.objects.all()  # pyright: ignore[reportAttributeAccessIssue]
        if not include_inactive:
            qs = qs.filter(status="active")

        missing = (
            qs.annotate(color_count=Count("colors"))
            .filter(color_count=0)
            .order_by("camouflage_name")
        )

        if not missing.exists():
            self.stdout.write(self.style.SUCCESS("All variants already have at least one color."))
            return

        # Style helpers are not typed in pyright stubs; treat as dynamic.
        self.stdout.write(self.style.MIGRATE_HEADING("Backfilling TEMP COLOR for variants with zero colors"))  # pyright: ignore[reportAttributeAccessIssue]
        self.stdout.write(f"Found {missing.count()} variant(s) missing colors.")

        created = 0
        with transaction.atomic():  # pyright: ignore[reportGeneralTypeIssues]
            for camo in missing:
                msg = f'- {camo.camouflage_name} ({camo.status})'
                if dry_run:
                    self.stdout.write(f"{msg}: would create VariantColor(position=1, color_name='TEMP COLOR')")
                    continue

                VariantColor.objects.create(  # pyright: ignore[reportAttributeAccessIssue]
                    camouflage_type=camo,
                    position=1,
                    color_name="TEMP COLOR",
                )
                created += 1
                self.stdout.write(self.style.SUCCESS(f"{msg}: created TEMP COLOR"))  # pyright: ignore[reportAttributeAccessIssue]

            if dry_run:
                # Ensure no accidental writes even if logic changes later.
                transaction.set_rollback(True)

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run complete (no changes written)."))  # pyright: ignore[reportAttributeAccessIssue]
        else:
            self.stdout.write(self.style.SUCCESS(f"Done. Created {created} TEMP COLOR row(s)."))  # pyright: ignore[reportAttributeAccessIssue]

