"""
Management command to import historical Lot data from CSV exports
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from accounts.models import UserProfile
from inspections.models import LotAcceptance, FirstArticleInspection
import csv
from datetime import datetime


class Command(BaseCommand):
    help = 'Import historical Lot data from CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to CSV file with historical Lot data'
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
                            # Find printer
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
                                error_count += 1
                                continue

                            # Find original FA
                            original_fa_id = row.get('original_fa_id', '').strip()
                            if not original_fa_id:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"Row {row_num}: No original FA ID provided"
                                    )
                                )
                                error_count += 1
                                continue

                            try:
                                original_fa = FirstArticleInspection.objects.get(fai_id=original_fa_id)
                            except FirstArticleInspection.DoesNotExist:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"Row {row_num}: Original FA {original_fa_id} not found"
                                    )
                                )
                                error_count += 1
                                continue

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

                            if not dry_run:
                                # Create Lot record
                                lot = LotAcceptance.objects.create(
                                    lot_id=row.get('lot_id', '').strip() or None,  # Will be auto-generated if empty
                                    vendor=profile,
                                    original_fa=original_fa,
                                    fabric_style=row.get('fabric_style', original_fa.fabric_style).strip(),
                                    shade_standard=row.get('shade_standard', original_fa.shade_standard).strip(),
                                    shade_standard_number=row.get('shade_standard_number', original_fa.shade_standard_number).strip(),
                                    spectral_reflectance_requirement=row.get('spectral_reflectance_requirement', original_fa.spectral_reflectance_requirement).strip(),
                                    original_fa_lot_number=row.get('original_fa_lot_id', original_fa.fa_lot_number).strip(),
                                    lot_lot_number=row.get('lot_lot_number', '').strip(),
                                    number_of_yards_printed=int(row.get('number_of_yards_printed', 0)) or 1,
                                    number_of_samples=int(row.get('number_of_samples', 3)) or 3,
                                    individual_sample_numbers=row.get('individual_sample_numbers', '').strip(),
                                    date_of_printing=date_of_printing or datetime.now().date(),
                                    status=row.get('status', 'approved').strip(),
                                    submitted=True,
                                )

                                created_count += 1
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f"✓ Row {row_num}: Created Lot {lot.lot_id}"
                                    )
                                )
                            else:
                                self.stdout.write(
                                    f"[CREATE] Row {row_num}: Lot for {profile.company_name}"
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

