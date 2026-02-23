from django.db import models
from django.contrib.auth.models import User


class PrinterLevel(models.Model):
    """Printer levels/tiers (DB6)"""
    
    level_name = models.CharField(max_length=50, unique=True)
    level_description = models.TextField(blank=True)
    permissions = models.JSONField(default=dict, blank=True)
    requirements = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['sort_order', 'level_name']
        verbose_name = 'Printer Level'
        verbose_name_plural = 'Printer Levels'
    
    def __str__(self):
        return self.level_name


class CamouflageType(models.Model):
    """Camouflage patterns and variants (DB2)"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('development', 'In Development'),
    ]
    
    camouflage_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    environment = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    sort_order = models.IntegerField(default=0)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sort_order', 'camouflage_name']
        verbose_name = 'Camouflage Type'
        verbose_name_plural = 'Camouflage Types'
    
    def __str__(self):
        return self.camouflage_name


class VariantColor(models.Model):
    """Shade matching colors for each camouflage variant.
    
    Each MultiCam variant has specific colors that must be evaluated
    during FA and Lot inspections. The number of colors varies by variant:
    - MultiCam®: 7 colors
    - MultiCam® Alpine: 3 colors
    - MultiCam® Tropic: 5 colors
    - MultiCam® Black: 3 colors
    - MultiCam® Arid: 5 colors
    """
    
    camouflage_type = models.ForeignKey(
        CamouflageType,
        on_delete=models.CASCADE,
        related_name='colors'
    )
    position = models.IntegerField(
        help_text='Color position (1-7). Determines display order.'
    )
    color_name = models.CharField(
        max_length=50,
        help_text='Color name with code (e.g., "Cream 524")'
    )
    
    class Meta:
        unique_together = ['camouflage_type', 'position']
        ordering = ['camouflage_type', 'position']
        verbose_name = 'Variant Color'
        verbose_name_plural = 'Variant Colors'
    
    def __str__(self):
        return f"{self.camouflage_type.camouflage_name} - {self.color_name}"


class CamouflageFile(models.Model):
    """Files associated with camouflage types"""
    
    FILE_TYPE_CHOICES = [
        ('pdf_word', 'PDF/Word Document'),
        ('ai', 'AI/Vector File'),
        ('image', 'Image File'),
    ]
    
    camouflage = models.ForeignKey(
        CamouflageType,
        on_delete=models.CASCADE,
        related_name='files'
    )
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    file = models.FileField(upload_to='camouflage/%Y/%m/')
    version = models.CharField(max_length=50, blank=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_camouflage_files'
    )
    is_latest = models.BooleanField(default=True)
    description = models.CharField(max_length=255, blank=True)
    
    class Meta:
        ordering = ['-upload_date']
        verbose_name = 'Camouflage File'
        verbose_name_plural = 'Camouflage Files'
    
    def __str__(self):
        return f"{self.camouflage.camouflage_name} - {self.get_file_type_display()}"


class FileUpload(models.Model):
    """General file upload tracking"""
    
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_files'
    )
    file = models.FileField(upload_to='uploads/%Y/%m/')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)  # pdf, doc, jpg, etc.
    file_size = models.IntegerField()  # bytes
    upload_date = models.DateTimeField(auto_now_add=True)
    content_type = models.CharField(max_length=100, blank=True)
    related_to_model = models.CharField(max_length=50, blank=True)  # Which model
    related_to_id = models.CharField(max_length=50, null=True, blank=True)  # Which record (can be string for fai_id/lot_id)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-upload_date']
        verbose_name = 'File Upload'
        verbose_name_plural = 'File Uploads'
    
    def __str__(self):
        return f"{self.file_name} ({self.file_type})"


class PartnerFile(models.Model):
    """
    Files uploaded by admins for partners to download.
    Visibility is controlled by category: standard partners, narrow partners, or both.
    """
    
    CATEGORY_CHOICES = [
        ('standard', 'Standard Only'),
        ('narrow', 'Narrow Only'),
        ('both', 'Both (Standard & Narrow)'),
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='partner_files/%Y/%m/')
    category = models.CharField(
        max_length=10,
        choices=CATEGORY_CHOICES,
        default='both',
        help_text='Which partner types can see this file'
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_partner_files'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Partner File'
        verbose_name_plural = 'Partner Files'
    
    def __str__(self):
        return f"{self.title} ({self.get_category_display()})"
    
    @property
    def file_extension(self):
        if self.file and self.file.name:
            return self.file.name.rsplit('.', 1)[-1].upper() if '.' in self.file.name else ''
        return ''
    
    @property
    def file_size_display(self):
        """Human-readable file size"""
        try:
            size = self.file.size
        except (FileNotFoundError, ValueError):
            return ''
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"


class RawMaterialArticle(models.Model):
    """Raw Material Article registered by RM Suppliers (DB6)"""
    
    CONSTRUCTION_CHOICES = [
        ('woven', 'Woven'),
        ('knit', 'Knit'),
        ('nonwoven', 'Non-Woven'),
    ]
    
    WEIGHT_GROUP_CHOICES = [
        ('light', 'Light (<4 oz/yd²)'),
        ('medium', 'Medium (4-8 oz/yd²)'),
        ('heavy', 'Heavy (>8 oz/yd²)'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('pending', 'Pending Approval'),
    ]
    
    # Auto-generated ID
    article_id = models.AutoField(primary_key=True)
    
    # RM Supplier who registered this
    supplier = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.CASCADE,
        related_name='raw_material_articles',
        limit_choices_to={'user_functionality': 'rm_supplier'}
    )
    
    # Product details
    product_name = models.CharField(max_length=255, help_text='Fabric/material name')
    product_code = models.CharField(max_length=100, blank=True, help_text='Supplier product code')
    
    # Composition/content
    composition = models.CharField(max_length=255, help_text='Fiber content (e.g., 50% Nylon, 50% Cotton)')
    construction = models.CharField(max_length=20, choices=CONSTRUCTION_CHOICES)
    weight_group = models.CharField(max_length=20, choices=WEIGHT_GROUP_CHOICES)
    weight_value = models.DecimalField(
        max_digits=6, decimal_places=2,
        null=True, blank=True,
        help_text='Weight in oz/yd²'
    )
    
    # Approved camouflage types
    approved_camouflages = models.ManyToManyField(
        CamouflageType,
        related_name='approved_articles',
        blank=True,
        help_text='Camouflage types this material is approved for'
    )
    
    # Additional specs
    width = models.DecimalField(
        max_digits=6, decimal_places=2,
        null=True, blank=True,
        help_text='Width in inches'
    )
    finish = models.CharField(max_length=255, blank=True, help_text='Finish type')
    color = models.CharField(max_length=100, blank=True, default='Greige')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Notes
    description = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['supplier', 'product_name']
        verbose_name = 'Raw Material Article'
        verbose_name_plural = 'Raw Material Articles'
        indexes = [
            models.Index(fields=['supplier']),
            models.Index(fields=['construction', 'weight_group']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.product_name} ({self.supplier.company_name})"


class TechnicalDataSheet(models.Model):
    """Technical Data Sheet for raw materials"""
    
    # Link to article
    article = models.ForeignKey(
        RawMaterialArticle,
        on_delete=models.CASCADE,
        related_name='tds_documents'
    )
    
    # File info
    file = models.FileField(upload_to='tds/%Y/%m/')
    file_name = models.CharField(max_length=255)
    version = models.CharField(max_length=50, blank=True)
    
    # Uploaded by
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_tds'
    )
    
    # Is this the current/latest version?
    is_current = models.BooleanField(default=True)
    
    # Description
    description = models.TextField(blank=True)
    
    # Timestamps
    upload_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-upload_date']
        verbose_name = 'Technical Data Sheet'
        verbose_name_plural = 'Technical Data Sheets'
    
    def __str__(self):
        return f"TDS: {self.article.product_name} v{self.version}"
    
    def save(self, *args, **kwargs):
        # Mark other TDS for this article as not current
        if self.is_current:
            TechnicalDataSheet.objects.filter(
                article=self.article,
                is_current=True
            ).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class MarketingOrder(models.Model):
    """Marketing package orders from FP Suppliers"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Auto-generated ID
    order_id = models.AutoField(primary_key=True)
    
    # FP Supplier who ordered
    fp_supplier = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.CASCADE,
        related_name='marketing_orders',
        limit_choices_to={'user_functionality': 'fp_supplier'}
    )
    
    # RM Supplier used
    rm_supplier = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marketing_orders_for',
        limit_choices_to={'user_functionality': 'rm_supplier'}
    )
    rm_supplier_name = models.CharField(max_length=255, blank=True, help_text='If RM supplier not in system')
    
    # Product info
    fabric_type = models.CharField(max_length=255)
    camouflage_type = models.ForeignKey(
        CamouflageType,
        on_delete=models.PROTECT,
        related_name='marketing_orders'
    )
    
    # Quantity
    number_of_pieces = models.IntegerField(help_text='Number of marketing pieces needed')
    yardage_to_be_used = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text='Expected yardage to be used (optional)'
    )
    
    # Shipping address
    shipping_name = models.CharField(max_length=255)
    shipping_street = models.CharField(max_length=255)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100, blank=True)
    shipping_country = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Tracking
    tracking_number = models.CharField(max_length=100, blank=True)
    shipped_date = models.DateField(null=True, blank=True)
    delivered_date = models.DateField(null=True, blank=True)
    
    # Admin notes
    admin_notes = models.TextField(blank=True)
    
    # Processed by
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_marketing_orders'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Marketing Order'
        verbose_name_plural = 'Marketing Orders'
        indexes = [
            models.Index(fields=['fp_supplier']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Order #{self.order_id} - {self.fp_supplier.company_name}"
    
    def get_full_shipping_address(self):
        """Return formatted shipping address"""
        parts = [self.shipping_street]
        city_state = self.shipping_city
        if self.shipping_state:
            city_state += f", {self.shipping_state}"
        parts.append(city_state)
        parts.append(self.shipping_postal_code)
        parts.append(self.shipping_country)
        return '\n'.join(parts)
