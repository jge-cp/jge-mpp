"""
Management command to load initial reference data:
- Camouflage types
- Printer levels (optional)
"""
from django.core.management.base import BaseCommand
from core.models import CamouflageType, PrinterLevel


class Command(BaseCommand):
    help = 'Load initial reference data (camouflage types, printer levels)'

    def handle(self, *args, **options):
        # Create camouflage types
        camouflage_types = [
            {'name': 'Multicam', 'description': 'Original MC pattern', 'environment': 'Multi-environment', 'sort_order': 1},
            {'name': 'Multicam Tropic', 'description': 'Tropical/jungle variant', 'environment': 'Dense vegetation, wet', 'sort_order': 2},
            {'name': 'Multicam Arid', 'description': 'Desert variant', 'environment': 'Desert, dry environments', 'sort_order': 3},
            {'name': 'Multicam Black', 'description': 'Law enforcement variant', 'environment': 'Urban, tactical', 'sort_order': 4},
            {'name': 'Multicam Alpine', 'description': 'Snow/winter variant', 'environment': 'Snow, winter conditions', 'sort_order': 5},
            {'name': 'IMTP', 'description': 'International Multi-Terrain Pattern', 'environment': 'Multi-environment', 'sort_order': 6},
            {'name': 'MTP (UK)', 'description': 'British Multi-Terrain Pattern', 'environment': 'Multi-environment', 'sort_order': 7},
            {'name': 'MC Denmark', 'description': 'Denmark military variant', 'environment': 'Multi-environment', 'sort_order': 8},
        ]
        
        created_count = 0
        updated_count = 0
        
        for ct_data in camouflage_types:
            ct, created = CamouflageType.objects.update_or_create(
                camouflage_name=ct_data['name'],
                defaults={
                    'description': ct_data['description'],
                    'environment': ct_data['environment'],
                    'sort_order': ct_data['sort_order'],
                    'status': 'active',
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Created: {ct.camouflage_name}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f'↻ Updated: {ct.camouflage_name}'))
        
        self.stdout.write(self.style.SUCCESS(f'\nSummary: Created {created_count}, Updated {updated_count}'))

