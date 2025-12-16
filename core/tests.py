"""
Tests for the core app.
Tests public pages, camouflage types, variant colors, and file uploads.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.db import IntegrityError
from django.core.management import call_command
from io import StringIO
from .models import CamouflageType, PrinterLevel, VariantColor


class PublicPageTests(TestCase):
    """Test public marketing pages are accessible"""
    
    def setUp(self):
        self.client = Client()
    
    def test_home_page_loads(self):
        """Home page should be accessible"""
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
    
    def test_about_page_loads(self):
        """About page should be accessible"""
        response = self.client.get(reverse('core:about'))
        self.assertEqual(response.status_code, 200)
    
    def test_contact_page_loads(self):
        """Contact page should be accessible"""
        response = self.client.get(reverse('core:contact'))
        self.assertEqual(response.status_code, 200)


class CamouflageTypeModelTests(TestCase):
    """Test CamouflageType model"""
    
    def test_create_camouflage_type(self):
        """Should be able to create camouflage type"""
        camo = CamouflageType.objects.create(
            camouflage_name='MultiCam Original',
            status='active'
        )
        self.assertEqual(str(camo), 'MultiCam Original')
    
    def test_camouflage_type_status_choices(self):
        """Camouflage type should have valid status choices"""
        camo = CamouflageType.objects.create(
            camouflage_name='Test Camo',
            status='active'
        )
        self.assertIn(camo.status, ['active', 'inactive', 'development'])


class PrinterLevelModelTests(TestCase):
    """Test PrinterLevel model"""
    
    def test_create_printer_level(self):
        """Should be able to create printer level"""
        level = PrinterLevel.objects.create(
            level_name='Silver',
            level_description='Silver tier partner'
        )
        self.assertEqual(str(level), 'Silver')
    
    def test_printer_level_ordering(self):
        """Printer levels should be ordered by sort_order"""
        gold = PrinterLevel.objects.create(
            level_name='Gold', sort_order=1
        )
        silver = PrinterLevel.objects.create(
            level_name='Silver', sort_order=2
        )
        
        levels = list(PrinterLevel.objects.all())
        self.assertEqual(levels[0], gold)
        self.assertEqual(levels[1], silver)


class VariantColorModelTests(TestCase):
    """Test VariantColor model for shade matching evaluation"""
    
    @classmethod
    def setUpTestData(cls):
        """Create test camouflage type"""
        cls.multicam = CamouflageType.objects.create(
            camouflage_name='Multicam',
            status='active'
        )
        cls.alpine = CamouflageType.objects.create(
            camouflage_name='Multicam Alpine',
            status='active'
        )
    
    def test_create_variant_color(self):
        """Should be able to create a variant color"""
        color = VariantColor.objects.create(
            camouflage_type=self.multicam,
            position=1,
            color_name='Cream 524'
        )
        self.assertEqual(str(color), 'Multicam - Cream 524')
        self.assertEqual(color.position, 1)
    
    def test_variant_color_unique_together(self):
        """Each position should be unique per camouflage type"""
        VariantColor.objects.create(
            camouflage_type=self.multicam,
            position=1,
            color_name='Cream 524'
        )
        
        # Creating another color at position 1 for same variant should fail
        with self.assertRaises(IntegrityError):
            VariantColor.objects.create(
                camouflage_type=self.multicam,
                position=1,
                color_name='Tan 525'
            )
    
    def test_same_position_different_variants(self):
        """Same position can exist for different variants"""
        VariantColor.objects.create(
            camouflage_type=self.multicam,
            position=1,
            color_name='Cream 524'
        )
        
        # Same position for different variant should work
        color = VariantColor.objects.create(
            camouflage_type=self.alpine,
            position=1,
            color_name='White 124'
        )
        self.assertEqual(color.color_name, 'White 124')
    
    def test_variant_color_ordering(self):
        """Colors should be ordered by camouflage type then position"""
        VariantColor.objects.create(
            camouflage_type=self.multicam,
            position=3,
            color_name='Pale Green 526'
        )
        VariantColor.objects.create(
            camouflage_type=self.multicam,
            position=1,
            color_name='Cream 524'
        )
        VariantColor.objects.create(
            camouflage_type=self.multicam,
            position=2,
            color_name='Tan 525'
        )
        
        colors = list(VariantColor.objects.filter(camouflage_type=self.multicam))
        self.assertEqual(colors[0].color_name, 'Cream 524')
        self.assertEqual(colors[1].color_name, 'Tan 525')
        self.assertEqual(colors[2].color_name, 'Pale Green 526')
    
    def test_camouflage_type_colors_relationship(self):
        """CamouflageType should have colors relationship"""
        VariantColor.objects.create(
            camouflage_type=self.multicam,
            position=1,
            color_name='Cream 524'
        )
        VariantColor.objects.create(
            camouflage_type=self.multicam,
            position=2,
            color_name='Tan 525'
        )
        
        self.assertEqual(self.multicam.colors.count(), 2)
    
    def test_cascade_delete(self):
        """Deleting camouflage type should delete its colors"""
        color = VariantColor.objects.create(
            camouflage_type=self.alpine,
            position=1,
            color_name='White 124'
        )
        color_id = color.id
        alpine_id = self.alpine.id
        
        self.assertEqual(VariantColor.objects.filter(camouflage_type_id=alpine_id).count(), 1)
        
        self.alpine.delete()
        
        # Color should be deleted (CASCADE)
        self.assertFalse(VariantColor.objects.filter(id=color_id).exists())


class LoadVariantColorsCommandTests(TestCase):
    """Test the load_variant_colors management command"""
    
    @classmethod
    def setUpTestData(cls):
        """Create required camouflage types"""
        CamouflageType.objects.create(camouflage_name='Multicam', status='active')
        CamouflageType.objects.create(camouflage_name='Multicam Alpine', status='active')
        CamouflageType.objects.create(camouflage_name='Multicam Tropic', status='active')
        CamouflageType.objects.create(camouflage_name='Multicam Black', status='active')
        CamouflageType.objects.create(camouflage_name='Multicam Arid', status='active')
    
    def test_load_variant_colors_creates_colors(self):
        """Command should create all variant colors"""
        out = StringIO()
        call_command('load_variant_colors', stdout=out)
        
        # Check expected color counts
        multicam = CamouflageType.objects.get(camouflage_name='Multicam')
        alpine = CamouflageType.objects.get(camouflage_name='Multicam Alpine')
        tropic = CamouflageType.objects.get(camouflage_name='Multicam Tropic')
        black = CamouflageType.objects.get(camouflage_name='Multicam Black')
        arid = CamouflageType.objects.get(camouflage_name='Multicam Arid')
        
        self.assertEqual(multicam.colors.count(), 7)
        self.assertEqual(alpine.colors.count(), 3)
        self.assertEqual(tropic.colors.count(), 5)
        self.assertEqual(black.colors.count(), 3)
        self.assertEqual(arid.colors.count(), 5)
    
    def test_load_variant_colors_correct_names(self):
        """Command should create colors with correct names"""
        call_command('load_variant_colors')
        
        multicam = CamouflageType.objects.get(camouflage_name='Multicam')
        colors = list(multicam.colors.order_by('position'))
        
        self.assertEqual(colors[0].color_name, 'Cream 524')
        self.assertEqual(colors[1].color_name, 'Tan 525')
        self.assertEqual(colors[6].color_name, 'Dark Brown 530')
    
    def test_load_variant_colors_idempotent(self):
        """Running command twice should not duplicate colors"""
        call_command('load_variant_colors')
        call_command('load_variant_colors')
        
        multicam = CamouflageType.objects.get(camouflage_name='Multicam')
        self.assertEqual(multicam.colors.count(), 7)
    
    def test_load_variant_colors_clear_option(self):
        """--clear option should remove existing colors first"""
        call_command('load_variant_colors')
        
        # Manually add an extra color
        multicam = CamouflageType.objects.get(camouflage_name='Multicam')
        VariantColor.objects.create(
            camouflage_type=multicam,
            position=8,
            color_name='Extra Color 999'
        )
        
        self.assertEqual(multicam.colors.count(), 8)
        
        # Run with --clear
        call_command('load_variant_colors', clear=True)
        
        # Should only have the standard 7 colors
        self.assertEqual(multicam.colors.count(), 7)
