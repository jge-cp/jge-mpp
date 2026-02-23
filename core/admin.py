from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import PrinterLevel, CamouflageType, CamouflageFile, FileUpload, VariantColor, PartnerFile


@admin.register(PrinterLevel)
class PrinterLevelAdmin(ModelAdmin):
    list_display = ['level_name', 'sort_order']
    list_editable = ['sort_order']
    ordering = ['sort_order']


class VariantColorInline(TabularInline):
    """Inline admin for editing colors directly on CamouflageType page"""
    model = VariantColor
    extra = 1
    ordering = ['position']


@admin.register(CamouflageType)
class CamouflageTypeAdmin(ModelAdmin):
    list_display = ['camouflage_name', 'status', 'color_count', 'sort_order', 'created_date']
    list_filter = ['status']
    list_editable = ['sort_order']
    search_fields = ['camouflage_name', 'description']
    ordering = ['sort_order']
    inlines = [VariantColorInline]
    
    def color_count(self, obj):
        return obj.colors.count()
    color_count.short_description = 'Colors'


@admin.register(VariantColor)
class VariantColorAdmin(ModelAdmin):
    list_display = ['camouflage_type', 'position', 'color_name']
    list_filter = ['camouflage_type']
    list_editable = ['position', 'color_name']
    ordering = ['camouflage_type', 'position']
    search_fields = ['color_name', 'camouflage_type__camouflage_name']


@admin.register(CamouflageFile)
class CamouflageFileAdmin(ModelAdmin):
    list_display = ['camouflage', 'file_type', 'version', 'is_latest', 'upload_date']
    list_filter = ['file_type', 'is_latest', 'upload_date']
    search_fields = ['camouflage__camouflage_name', 'description']
    readonly_fields = ['upload_date']


@admin.register(FileUpload)
class FileUploadAdmin(ModelAdmin):
    list_display = ['file_name', 'file_type', 'uploaded_by', 'upload_date', 'is_active']
    list_filter = ['file_type', 'is_active', 'upload_date']
    search_fields = ['file_name', 'description']
    readonly_fields = ['upload_date', 'file_size']


@admin.register(PartnerFile)
class PartnerFileAdmin(ModelAdmin):
    list_display = ['title', 'category', 'file_extension', 'is_active', 'uploaded_by', 'created_at']
    list_filter = ['category', 'is_active']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'file', 'category', 'is_active'),
        }),
        ('Metadata', {
            'fields': ('uploaded_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
