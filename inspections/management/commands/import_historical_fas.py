"""
Management command to import historical FA data from CSV exports
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from accounts.models import UserProfile
from inspections.models import FirstArticleInspection
from core.models import CamouflageType
import csv
from datetime import datetime


class Command(BaseCommand):
    help = 'Import historical FA data from CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to CSV file with historical FA data'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        created_count = 0
        error_count = 0

        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        with transaction.atomic():
                            # Find printer by company name or email
                            company_name = row.get('company_name', '').strip()
                            printer_email = row.get('printer_email', '').strip()
                            
                            if printer_email:
                                try:
                                    profile = UserProfile.objects.get(technical_email=printer_email)
                                except UserProfile.DoesNotExist:
                                    self.stdout.write(
                                        self.style.WARNING(
                                            f"Row {row_num}: Printer not found for {printer_email}"
                                        )
                                    )
                                    error_count += 1
                                    continue
                            elif company_name:
                                try:
                                    profile = UserProfile.objects.get(company_name=company_name)
                                except UserProfile.DoesNotExist:
                                    self.stdout.write(
                                        self.style.WARNING(
                                            f"Row {row_num}: Printer not found for {company_name}"
                                        )
                                    )
                                    error_count += 1
                                    continue
                            else:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"Row {row_num}: No company name or email provided"
                                    )
                                )
                                error_count += 1
                                continue

                            # Get or create camouflage type
                            variant_name = row.get('variant', 'Multicam').strip()
                            try:
                                variant = CamouflageType.objects.get(camouflage_name=variant_name)
                            except CamouflageType.DoesNotExist:
                                variant = CamouflageType.objects.create(
                                    camouflage_name=variant_name,
                                    status='active'
                                )

                            # Parse dates
                            date_of_printing = None
                            if row.get('date_of_printing'):
                                try:
                                    date_of_printing = datetime.strptime(row['date_of_printing'], '%Y-%m-%d').date()
                                except ValueError:
                                    try:
                                        date_of_printing = datetime.strptime(row['date_of_printing'], '%m/%d/%Y').date()
                                    except ValueError:
                                        pass

                            submission_date = None
                            if row.get('submission_date'):
                                try:
                                    submission_date = datetime.strptime(row['submission_date'], '%Y-%m-%d %H:%M:%S')
                                except ValueError:
                                    try:
                                        submission_date = datetime.strptime(row['submission_date'], '%Y-%m-%d')
                                    except ValueError:
                                        pass

                            if not dry_run:
                                # Create FA record
                                fa = FirstArticleInspection.objects.create(
                                    fai_id=row.get('fai_id', '').strip() or None,  # Will be auto-generated if empty
                                    vendor=profile,
                                    fabric_style=row.get('fabric_style', '').strip(),
                                    multicam_variant=variant,
                                    shade_standard=row.get('shade_standard', 'alpha').strip(),
                                    shade_standard_number=row.get('shade_standard_number', '').strip(),
                                    spectral_reflectance_requirement=row.get('spectral_reflectance_requirement', 'alpha').strip(),
                                    fa_lot_number=row.get('fa_lot_number', '').strip(),
                                    date_of_printing=date_of_printing or datetime.now().date(),
                                    status=row.get('status', 'approved').strip(),
                                    submitted=True,
                                )
                                
                                if submission_date:
                                    fa.submission_date = submission_date
                                    fa.save(update_fields=['submission_date'])

                                created_count += 1
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f"✓ Row {row_num}: Created FA {fa.fai_id}"
                                    )
                                )
                            else:
                                self.stdout.write(
                                    f"[CREATE] Row {row_num}: FA for {profile.company_name}"
                                )
                                created_count += 1

                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f"✗ Row {row_num}: Error - {str(e)}"
                            )
                        )

        except FileNotFoundError:
            raise CommandError(f'CSV file not found: {csv_file}')
        except Exception as e:
            raise CommandError(f'Error reading CSV file: {str(e)}')

        # Summary
        self.stdout.write('\n' + '='*80)
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN SUMMARY (no changes made):'))
        else:
            self.stdout.write(self.style.SUCCESS('IMPORT SUMMARY:'))
        
        self.stdout.write(f'  Created: {created_count}')
        self.stdout.write(f'  Errors:  {error_count}')
        self.stdout.write('='*80 + '\n')

