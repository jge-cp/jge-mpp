"""
Management command to load variant colors for shade matching evaluation.

Each MultiCam variant has specific colors that inspectors evaluate during
FA and Lot reviews. This command loads the official color specifications.
"""
from django.core.management.base import BaseCommand
from core.models import CamouflageType, VariantColor


# Official color specifications per variant
VARIANT_COLORS = {
    'Multicam': [
        (1, 'Cream 524'),
        (2, 'Tan 525'),
        (3, 'Pale Green 526'),
        (4, 'Olive 527'),
        (5, 'Dark Green 528'),
        (6, 'Brown 529'),
        (7, 'Dark Brown 530'),
    ],
    'Multicam Alpine': [
        (1, 'White 124'),
        (2, 'Light Gray 125'),
        (3, 'Medium Gray 126'),
    ],
    'Multicam Tropic': [
        (1, 'Olive 251'),
        (2, 'Bright Green 252'),
        (3, 'Green 253'),
        (4, 'Dark Green 254'),
        (5, 'Dark Brown 255'),
    ],
    'Multicam Black': [
        (1, 'Olive 205'),
        (2, 'Gray 206'),
        (3, 'Black 207'),
    ],
    'Multicam Arid': [
        (1, 'Light Tan 170'),
        (2, 'Urban Tan 171'),
        (3, 'Olive 172'),
        (4, 'Light Coyote 173'),
        (5, 'Highland 174'),
    ],
}


class Command(BaseCommand):
    help = 'Load variant colors for shade matching evaluation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing colors before loading',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Loading Variant Colors'))
        self.stdout.write('=' * 50)
        
        if options['clear']:
            deleted_count = VariantColor.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING(f'Cleared {deleted_count} existing colors'))
        
        total_created = 0
        total_updated = 0
        
        for variant_name, colors in VARIANT_COLORS.items():
            # Find the camouflage type
            try:
                camo_type = CamouflageType.objects.get(camouflage_name=variant_name)
            except CamouflageType.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f'✗ Camouflage type "{variant_name}" not found. '
                    f'Run "python manage.py load_initial_data" first.'
                ))
                continue
            
            self.stdout.write(f'\n{variant_name}:')
            
            for position, color_name in colors:
                color, created = VariantColor.objects.update_or_create(
                    camouflage_type=camo_type,
                    position=position,
                    defaults={'color_name': color_name}
                )
                
                if created:
                    total_created += 1
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {position}. {color_name}'))
                else:
                    total_updated += 1
                    self.stdout.write(f'  ↻ Updated: {position}. {color_name}')
        
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS(
            f'Summary: Created {total_created}, Updated {total_updated}'
        ))
        
        # Show color counts
        self.stdout.write('\nColors per variant:')
        for camo in CamouflageType.objects.filter(status='active'):
            count = camo.colors.count()
            if count > 0:
                self.stdout.write(f'  {camo.camouflage_name}: {count} colors')

