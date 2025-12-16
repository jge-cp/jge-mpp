"""
Django Management Command: Import Printers from CSV

Usage:
    python manage.py import_printers path/to/printers_import.csv

This command imports printer data from the Excel/CSV export into the Django database.
It handles:
- Creating new printer accounts
- Updating existing accounts
- Generating temporary passwords
- Sending welcome emails (optional)
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from accounts.models import UserProfile
import csv
import secrets
import string

User = get_user_model()


class Command(BaseCommand):
    help = 'Import printers from CSV file generated from Master List Excel'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to CSV file with printer data'
        )
        parser.add_argument(
            '--send-emails',
            action='store_true',
            help='Send welcome emails with temporary passwords to all printers'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip printers that already exist (default is to update them)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing'
        )

    def generate_temp_password(self, length=12):
        """Generate a secure temporary password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        return password

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        send_emails = options['send_emails']
        skip_existing = options['skip_existing']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        passwords = {}  # Store temp passwords for output

        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                    try:
                        with transaction.atomic():
                            company_name = row['company_name'].strip()
                            email = row['technical_email'].strip()
                            
                            if not email:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"Row {row_num}: Skipping {company_name} - no email"
                                    )
                                )
                                skipped_count += 1
                                continue

                            # Check if user exists
                            try:
                                user = User.objects.get(email=email)
                                user_exists = True
                            except User.DoesNotExist:
                                user_exists = False

                            if user_exists and skip_existing:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"Row {row_num}: Skipping {company_name} - already exists"
                                    )
                                )
                                skipped_count += 1
                                continue

                            if not dry_run:
                                # Create or update User
                                if not user_exists:
                                    temp_password = self.generate_temp_password()
                                    user = User.objects.create_user(
                                        username=email,
                                        email=email,
                                        password=temp_password
                                    )
                                    passwords[email] = temp_password
                                    user_created = True
                                else:
                                    user_created = False

                                # Create or update UserProfile
                                profile, profile_created = UserProfile.objects.update_or_create(
                                    user=user,
                                    defaults={
                                        'company_name': company_name,
                                        'technical_email': email,
                                        'technical_contact': row.get('technical_contact', '').strip() or f"{company_name} QA Team",
                                        'commercial_email': row.get('commercial_email', '').strip(),
                                        'user_functionality': row.get('user_functionality', 'printer').strip(),
                                        'printer_type': row.get('printer_type', 'standard').strip() or None,
                                        'status': row.get('status', 'active').strip(),
                                        'notes': row.get('notes', '').strip(),
                                        'google_sheet_fa_id': row.get('google_sheet_fa_id', '').strip(),
                                        'google_sheet_lot_id': row.get('google_sheet_lot_id', '').strip(),
                                    }
                                )

                                if user_created:
                                    created_count += 1
                                    self.stdout.write(
                                        self.style.SUCCESS(
                                            f"✓ Row {row_num}: Created {company_name} ({email})"
                                        )
                                    )
                                else:
                                    updated_count += 1
                                    self.stdout.write(
                                        self.style.SUCCESS(
                                            f"↻ Row {row_num}: Updated {company_name} ({email})"
                                        )
                                    )
                            else:
                                # Dry run
                                action = "CREATE" if not user_exists else "UPDATE"
                                self.stdout.write(
                                    f"[{action}] Row {row_num}: {company_name} ({email})"
                                )
                                if not user_exists:
                                    created_count += 1
                                else:
                                    updated_count += 1

                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f"✗ Row {row_num}: Error processing {row.get('company_name', 'Unknown')} - {str(e)}"
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
        self.stdout.write(f'  Updated: {updated_count}')
        self.stdout.write(f'  Skipped: {skipped_count}')
        self.stdout.write(f'  Errors:  {error_count}')
        self.stdout.write('='*80 + '\n')

        # Output temporary passwords if any were generated
        if passwords and not dry_run:
            self.stdout.write(self.style.WARNING('\nTEMPORARY PASSWORDS (save these securely!):'))
            self.stdout.write('-'*80)
            for email, password in passwords.items():
                self.stdout.write(f'{email}: {password}')
            self.stdout.write('-'*80)
            self.stdout.write(
                self.style.WARNING(
                    '\n⚠ IMPORTANT: Save these passwords! Users must change them on first login.'
                )
            )

        # Email sending
        if send_emails and passwords and not dry_run:
            self.stdout.write('\n' + self.style.WARNING('Sending welcome emails...'))
            sent_count = 0
            failed_count = 0
            
            from django.core.mail import send_mail
            from django.conf import settings
            
            site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
            
            for email, password in passwords.items():
                try:
                    send_mail(
                        subject='Welcome to MC Partner Program Portal',
                        message=f"""
Welcome to the MC Partner Program Portal!

Your account has been created. Please use the following credentials to log in:

Email: {email}
Temporary Password: {password}

Login URL: {site_url}/login/

IMPORTANT: You must change your password upon first login.

If you have any questions, please contact support.

Best regards,
MC Partner Program Team
                        """,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False,
                    )
                    sent_count += 1
                    self.stdout.write(f'  ✓ Sent to {email}')
                except Exception as e:
                    failed_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Failed to send to {email}: {str(e)}')
                    )
            
            self.stdout.write(f'\nEmails sent: {sent_count}, Failed: {failed_count}')

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    '\nDry run complete. Run without --dry-run to import for real.'
                )
            )

