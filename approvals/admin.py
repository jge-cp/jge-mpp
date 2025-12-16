from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import CamouflageApproval


@admin.register(CamouflageApproval)
class CamouflageApprovalAdmin(ModelAdmin):
    list_display = ['printer', 'camouflage_type', 'approval_date', 'status', 'expiry_date']
    list_filter = ['status', 'approval_date', 'camouflage_type']
    search_fields = ['printer__company_name', 'camouflage_type__camouflage_name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'approval_date'
