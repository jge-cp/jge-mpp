from django.db import models
from django.contrib.auth.models import User
from django.core.validators import EmailValidator


class UserProfile(models.Model):
    """Extended user profile for all user types (DB1)"""
    
    # MVP: Only partner and admin types
    # Future: May split partner into fabric_printer, webbing_printer, rm_supplier, fp_supplier
    USER_FUNCTIONALITY_CHOICES = [
        ('partner', 'Partner'),  # Generic term for all submitters (printers, suppliers, etc.)
        ('admin', 'Internal Staff'),
    ]
    
    # Admin roles for internal staff
    ADMIN_ROLE_CHOICES = [
        ('', 'N/A'),
        ('primary_inspector', 'Primary Inspector (FA First Review + Lots)'),
        ('final_inspector', 'Final Inspector (FA Final Review Only)'),
        ('staff_executive', 'Staff - Executive'),
        ('staff_finance', 'Staff - Finance'),
        ('staff_operations', 'Staff - Operations'),
        ('full_admin', 'Full Admin'),
    ]
    
    # Partner type - for future categorization
    PARTNER_TYPE_CHOICES = [
        ('standard', 'Standard'),
        ('narrow_goods', 'Narrow Goods Specialist'),
        ('alternate', 'Alternate Account'),
        ('special', 'Special Account'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('test', 'Test Account'),
    ]
    
    # One-to-one relationship with Django User
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Track original values to detect changes
    __original_user_functionality = None
    __original_admin_role = None
    
    # Company information
    company_name = models.CharField(max_length=255)
    technical_email = models.EmailField(unique=True, validators=[EmailValidator()])
    technical_contact = models.CharField(max_length=255, blank=True)
    commercial_email = models.EmailField(blank=True)
    commercial_contact = models.CharField(max_length=255, blank=True)
    
    # Address fields
    street = models.CharField(max_length=255, blank=True)
    number = models.CharField(max_length=50, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    telephone = models.CharField(max_length=50, blank=True)
    
    # User type and functionality
    user_functionality = models.CharField(
        max_length=20,
        choices=USER_FUNCTIONALITY_CHOICES,
        default='partner'
    )
    
    # Admin role (only applicable when user_functionality='admin')
    admin_role = models.CharField(
        max_length=20,
        choices=ADMIN_ROLE_CHOICES,
        blank=True,
        default='',
        help_text='Only applicable for admin users'
    )
    
    # Feature flags for granular permission control
    can_submit_fa = models.BooleanField(default=False, help_text='Can submit First Articles')
    can_submit_lots = models.BooleanField(default=False, help_text='Can submit Lots')
    can_submit_reports = models.BooleanField(default=False, help_text='Can submit monthly reports')
    can_review_fa = models.BooleanField(default=False, help_text='Can review/approve FA submissions')
    can_review_lots = models.BooleanField(default=False, help_text='Can review/approve Lot submissions')
    can_register_articles = models.BooleanField(default=False, help_text='Can register new RM articles')
    can_upload_tds = models.BooleanField(default=False, help_text='Can upload Technical Data Sheets')
    can_view_printer_list = models.BooleanField(default=False, help_text='Can view printer list')
    can_browse_rm_library = models.BooleanField(default=False, help_text='Can browse RM library')
    can_order_marketing = models.BooleanField(default=False, help_text='Can order marketing materials')
    can_manage_users = models.BooleanField(default=False, help_text='Can manage user accounts')
    
    # Partner-specific fields
    partner_type = models.CharField(
        max_length=20,
        choices=PARTNER_TYPE_CHOICES,
        blank=True
    )
    
    # License information
    license_agreement_date = models.DateField(null=True, blank=True)
    license_expiry_date = models.DateField(null=True, blank=True)
    license_agreement_docs = models.FileField(
        upload_to='licenses/%Y/%m/',
        blank=True,
        null=True
    )
    
    # Legacy Google Sheets IDs (for migration)
    google_sheet_fa_id = models.CharField(max_length=255, blank=True)
    google_sheet_lot_id = models.CharField(max_length=255, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    
    # Additional fields
    mpp_level = models.ForeignKey(
        'core.PrinterLevel',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        indexes = [
            models.Index(fields=['user_functionality']),
            models.Index(fields=['technical_email']),
            models.Index(fields=['company_name']),
            models.Index(fields=['status']),
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store original values to detect changes on save
        # Use __dict__.get to avoid triggering deferred field loading
        self.__original_user_functionality = self.__dict__.get('user_functionality', 'partner')
        self.__original_admin_role = self.__dict__.get('admin_role', '')
    
    def __str__(self):
        return f"{self.company_name} ({self.get_user_functionality_display()})"
    
    def save(self, *args, **kwargs):
        # Check if this is a new instance or if user_functionality/admin_role changed
        is_new = self.pk is None
        functionality_changed = self.__original_user_functionality != self.user_functionality
        admin_role_changed = self.__original_admin_role != self.admin_role
        
        # Prevent removing the last admin (safety check)
        if not is_new and functionality_changed:
            if self.__original_user_functionality == 'admin' and self.user_functionality != 'admin':
                # Check if this would leave no admins
                admin_count = UserProfile.objects.filter(user_functionality='admin').exclude(pk=self.pk).count()
                if admin_count == 0:
                    from django.core.exceptions import ValidationError
                    raise ValidationError(
                        "Cannot change the last admin user to a non-admin type. "
                        "Create another admin user first, or use Django's superuser to recover."
                    )
        
        # Auto-update permissions if user type or admin role changed
        if is_new or functionality_changed or (self.user_functionality == 'admin' and admin_role_changed):
            self.set_default_permissions()
        
        super().save(*args, **kwargs)
        
        # Update tracked values after save
        self.__original_user_functionality = self.user_functionality
        self.__original_admin_role = self.admin_role
    
    def get_full_address(self):
        """Return formatted full address"""
        parts = []
        if self.street:
            parts.append(self.street)
        if self.number:
            parts.append(self.number)
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.country:
            parts.append(self.country)
        return ', '.join(parts) if parts else ''
    
    def set_default_permissions(self):
        """Set default permissions based on user_functionality type and admin_role"""
        # Reset all permissions first
        self.can_submit_fa = False
        self.can_submit_lots = False
        self.can_submit_reports = False
        self.can_review_fa = False
        self.can_review_lots = False
        self.can_register_articles = False
        self.can_upload_tds = False
        self.can_view_printer_list = False
        self.can_browse_rm_library = False
        self.can_order_marketing = False
        self.can_manage_users = False
        
        if self.user_functionality == 'partner':
            # Partners can submit FAs, lots, and reports
            self.can_submit_fa = True
            self.can_submit_lots = True
            self.can_submit_reports = True
        
        elif self.user_functionality == 'admin':
            # Base admin permissions - viewing
            self.can_view_printer_list = True
            self.can_browse_rm_library = True
            
            # Role-specific permissions
            if self.admin_role == 'primary_inspector':
                # Primary Inspector: FA first review + all Lot reviews
                self.can_review_fa = True
                self.can_review_lots = True
            
            elif self.admin_role == 'final_inspector':
                # Final Inspector: FA final review only (no lots)
                self.can_review_fa = True
            
            elif self.admin_role in ['staff_executive', 'staff_finance', 'staff_operations']:
                # Staff roles: read-only dashboard access (no special permissions needed)
                pass
            
            elif self.admin_role == 'full_admin':
                # Full admin gets all permissions
                self.can_submit_fa = True
                self.can_submit_lots = True
                self.can_submit_reports = True
                self.can_review_fa = True
                self.can_review_lots = True
                self.can_register_articles = True
                self.can_upload_tds = True
                self.can_order_marketing = True
                self.can_manage_users = True
    
    def is_partner(self):
        """Check if user is a Partner (submits FAs/Lots)"""
        return self.user_functionality == 'partner'
    
    # Backwards compatibility alias
    def is_printer(self):
        """Alias for is_partner() - for backwards compatibility"""
        return self.is_partner()
    
    def is_admin(self):
        """Check if user is Internal Staff"""
        return self.user_functionality == 'admin'
    
    def is_primary_inspector(self):
        """Check if user is a Primary Inspector (FA first review + all Lot reviews)"""
        return self.user_functionality == 'admin' and self.admin_role in ['primary_inspector', 'full_admin']
    
    def is_final_inspector(self):
        """Check if user is a Final Inspector (FA final review only)"""
        return self.user_functionality == 'admin' and self.admin_role in ['final_inspector', 'full_admin']
    
    def is_any_inspector(self):
        """Check if user is any type of inspector"""
        return self.is_primary_inspector() or self.is_final_inspector()
    
    def is_staff(self):
        """Check if user is staff (executive, finance, operations)"""
        return self.user_functionality == 'admin' and self.admin_role in [
            'staff_executive', 'staff_finance', 'staff_operations', 'full_admin'
        ]
    
    def is_staff_executive(self):
        """Check if user is executive staff"""
        return self.user_functionality == 'admin' and self.admin_role in ['staff_executive', 'full_admin']
    
    def is_staff_finance(self):
        """Check if user is finance staff"""
        return self.user_functionality == 'admin' and self.admin_role in ['staff_finance', 'full_admin']
    
    # Backwards compatibility alias
    def is_inspector(self):
        """Alias for is_any_inspector() - for backwards compatibility"""
        return self.is_any_inspector()
    
    def get_dashboard_url(self):
        """Return the appropriate dashboard URL based on user type and role"""
        if self.user_functionality == 'partner':
            return 'dashboard:partner_dashboard'
        elif self.user_functionality == 'admin':
            # Route admin users based on their role
            if self.admin_role in ['primary_inspector', 'final_inspector']:
                return 'dashboard:inspector_dashboard'
            elif self.admin_role in ['staff_executive', 'staff_finance', 'staff_operations']:
                return 'dashboard:staff_dashboard'
            elif self.admin_role == 'full_admin':
                return 'dashboard:inspector_dashboard'
            else:
                return 'dashboard:staff_dashboard'
        return 'dashboard:partner_dashboard'  # Default fallback
    
    def get_partner_level_display(self):
        """Return the partner level name or 'Standard' if not set"""
        if self.mpp_level:
            return self.mpp_level.level_name
        return 'Standard'
