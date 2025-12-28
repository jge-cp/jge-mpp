"""
Management command to load initial reference data:
- Camouflage types
- Variant colors (for shade matching evaluation)
- Printer levels (optional)
"""
from django.core.management.base import BaseCommand
from core.models import CamouflageType, VariantColor, PrinterLevel


# Official color specifications per variant
# Variants without defined colors get TEST COLOR
VARIANT_COLORS = {
    'Multicam': [
        'Cream 524', 'Tan 525', 'Pale Green 526', 'Olive 527',
        'Dark Green 528', 'Brown 529', 'Dark Brown 530'
    ],
    'Multicam Alpine': ['White 124', 'Light Gray 125', 'Medium Gray 126'],
    'Multicam Tropic': [
        'Olive 251', 'Bright Green 252', 'Green 253',
        'Dark Green 254', 'Dark Brown 255'
    ],
    'Multicam Black': ['Olive 205', 'Gray 206', 'Black 207'],
    'Multicam Arid': [
        'Light Tan 170', 'Urban Tan 171', 'Olive 172',
        'Light Coyote 173', 'Highland 174'
    ],
    'IMTP': ['TEST COLOR'],
    'MTP (UK)': ['TEST COLOR'],
    'MC Denmark': ['TEST COLOR'],
}


class Command(BaseCommand):
    help = 'Load initial reference data (camouflage types, variant colors)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Loading Reference Data'))
        self.stdout.write('=' * 60)
        
        # Step 1: Create camouflage types
        self.stdout.write('\n[1] Camouflage Types:')
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
        
        camo_created = 0
        camo_updated = 0
        
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
                camo_created += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {ct.camouflage_name}'))
            else:
                camo_updated += 1
                self.stdout.write(f'  ↻ Updated: {ct.camouflage_name}')
        
        self.stdout.write(f'  Summary: {camo_created} created, {camo_updated} updated')
        
        # Step 2: Create variant colors
        self.stdout.write('\n[2] Variant Colors:')
        color_created = 0
        color_updated = 0
        
        for variant_name, colors in VARIANT_COLORS.items():
            try:
                camo_type = CamouflageType.objects.get(camouflage_name=variant_name)
            except CamouflageType.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'  ✗ Variant "{variant_name}" not found'))
                continue
            
            for position, color_name in enumerate(colors, start=1):
                color, created = VariantColor.objects.update_or_create(
                    camouflage_type=camo_type,
                    position=position,
                    defaults={'color_name': color_name}
                )
                if created:
                    color_created += 1
                else:
                    color_updated += 1
            
            self.stdout.write(self.style.SUCCESS(f'  ✓ {variant_name}: {len(colors)} colors'))
        
        self.stdout.write(f'  Summary: {color_created} created, {color_updated} updated')
        
        # Final summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Reference data loaded successfully!'))
        self.stdout.write(f'  Camouflage types: {CamouflageType.objects.count()}')
        self.stdout.write(f'  Variant colors: {VariantColor.objects.count()}')
