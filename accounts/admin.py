import logging

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordResetForm
from django.conf import settings
from unfold.admin import ModelAdmin, TabularInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from .models import UserProfile, PartnerCompany

logger = logging.getLogger(__name__)


class UserProfileInline(TabularInline):
    """Inline to show UserProfile on User admin page"""
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    fields = ['user_functionality', 'admin_role', 'company', 'company_name', 'status']
    readonly_fields = ['company_name']
    autocomplete_fields = ['company']


# Unregister the default User admin
admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    """Custom User admin with UserProfile inline"""
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    inlines = [UserProfileInline]
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'get_user_type']
    actions = ['send_password_reset_email']

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'usable_password', 'password1', 'password2'),
        }),
    )
    
    def get_user_type(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.get_user_functionality_display()
        return '-'
    get_user_type.short_description = 'User Type'

    def response_add(self, request, obj, post_url_continue=None):
        """Remind admin to assign company/role after creating a user."""
        self.message_user(
            request,
            'Now assign a company and role below. A welcome email will be sent automatically when you save.',
            messages.INFO,
        )
        return super().response_add(request, obj, post_url_continue)

    def save_related(self, request, form, formsets, change):
        """After inlines are saved, send welcome email if company was just assigned to a new user."""
        super().save_related(request, form, formsets, change)
        user = form.instance
        if not user.email or user.last_login is not None:
            return
        profile = getattr(user, 'profile', None)
        if not profile or not profile.company:
            return
        try:
            reset_form = PasswordResetForm({'email': user.email})
            if reset_form.is_valid():
                reset_form.save(
                    request=request,
                    use_https=request.is_secure(),
                    email_template_name='registration/welcome_email.html',
                    subject_template_name='registration/welcome_subject.txt',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                )
                self.message_user(request, f'Welcome email sent to {user.email}.', messages.SUCCESS)
        except Exception as e:
            logger.error(f'Failed to send welcome email to {user.email}: {e}')
            self.message_user(request, f'Welcome email failed: {e}', messages.WARNING)
    
    @admin.action(description='Send password reset email to selected users')
    def send_password_reset_email(self, request, queryset):
        """Send password reset email to selected users"""
        sent_count = 0
        skipped_count = 0
        
        for user in queryset:
            if not user.email:
                skipped_count += 1
                continue
            
            form = PasswordResetForm({'email': user.email})
            if form.is_valid():
                form.save(
                    request=request,
                    use_https=request.is_secure(),
                    email_template_name='registration/password_reset_email.html',
                    subject_template_name='registration/password_reset_subject.txt',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                )
                sent_count += 1
        
        if sent_count:
            self.message_user(request, f'Password reset email sent to {sent_count} user(s).')
        if skipped_count:
            self.message_user(request, f'Skipped {skipped_count} user(s) without email addresses.', level='warning')


@admin.register(PartnerCompany)
class PartnerCompanyAdmin(ModelAdmin):
    """Admin for Partner Companies"""
    list_display = ['name', 'code', 'status', 'is_standard', 'is_narrow', 'contact_name', 'contact_email', 'created_at']
    list_filter = ['status', 'is_standard', 'is_narrow']
    search_fields = ['name', 'code', 'contact_name', 'contact_email']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']
    
    fieldsets = (
        ('Company Identity', {
            'fields': ('code', 'name', 'status'),
            'description': 'The code is used for FA/Lot ID prefixes (e.g., ACME-FA-0001). Set it once and do not change after FAs exist.'
        }),
        ('Partner Categories', {
            'fields': ('is_standard', 'is_narrow'),
            'description': 'Determines which files and resources are visible to this company\'s users. A company can be both Standard and Narrow.',
        }),
        ('Primary Contact', {
            'fields': ('contact_name', 'contact_email', 'contact_phone'),
        }),
        ('Address', {
            'fields': ('street', 'city', 'state', 'country', 'postal_code'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    def has_module_permission(self, request):
        """Hide from admin sidebar — profiles are managed via User inline."""
        return False

    list_display = ['company_name', 'user', 'company', 'user_functionality', 'admin_role', 'status', 'technical_email']
    list_filter = ['user_functionality', 'admin_role', 'status', 'partner_type', 'company']
    search_fields = ['company_name', 'technical_email', 'commercial_email', 'company__name', 'company__code']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['company']
    actions = ['reset_to_default_permissions']
    
    @admin.action(description='Reset selected profiles to default permissions')
    def reset_to_default_permissions(self, request, queryset):
        """Reset permissions to defaults based on user_functionality"""
        for profile in queryset:
            profile.set_default_permissions()
            profile.save(update_fields=[
                'can_submit_fa', 'can_submit_lots', 'can_submit_reports',
                'can_review_fa', 'can_review_lots',
                'can_register_articles', 'can_upload_tds',
                'can_view_printer_list', 'can_browse_rm_library',
                'can_order_marketing', 'can_manage_users',
            ])
        self.message_user(request, f'Reset permissions for {queryset.count()} profile(s).')
    
    fieldsets = (
        ('User Account', {
            'fields': ('user', 'user_functionality', 'admin_role', 'status')
        }),
        ('Partner Company', {
            'fields': ('company',),
            'description': 'Link this user to a Partner Company. All users in a company can see the company\'s FAs and Lots.',
        }),
        ('Portal Permissions', {
            'fields': (
                'can_submit_fa', 'can_submit_lots', 'can_submit_reports',
                'can_review_fa', 'can_review_lots',
                'can_register_articles', 'can_upload_tds',
                'can_view_printer_list', 'can_browse_rm_library',
                'can_order_marketing', 'can_manage_users',
            ),
            'description': 'These are the actual portal permissions. They are set automatically based on User Type but can be customized.',
        }),
        ('Legacy Company Information', {
            'fields': ('company_name', 'technical_email', 'technical_contact', 
                      'commercial_email', 'commercial_contact'),
            'description': 'Legacy fields - use Partner Company above for new users.',
            'classes': ('collapse',)
        }),
        ('Address', {
            'fields': ('street', 'number', 'city', 'state', 'country', 'telephone'),
            'classes': ('collapse',)
        }),
        ('Partner Information', {
            'fields': ('partner_type', 'mpp_level', 'license_agreement_date', 
                      'license_expiry_date', 'license_agreement_docs'),
            'classes': ('collapse',)
        }),
        ('Legacy Data', {
            'fields': ('google_sheet_fa_id', 'google_sheet_lot_id'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
