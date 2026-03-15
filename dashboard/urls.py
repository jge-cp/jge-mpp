from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard router - redirects based on user type
    path('dashboard/', views.dashboard_router, name='dashboard_router'),
    
    # Partner dashboard (replaces printer dashboard)
    path('dashboard/partner/', views.partner_dashboard, name='partner_dashboard'),
    
    # Backwards compatibility - redirect to partner dashboard
    path('dashboard/printer/', views.printer_dashboard, name='printer_dashboard'),
    
    # Admin/Inspector dashboard
    path('admin/dashboard/', views.inspector_dashboard, name='inspector_dashboard'),
    
    # Staff dashboard (executives, finance, operations)
    path('admin/staff/', views.staff_dashboard, name='staff_dashboard'),
    
    # Partner file repository
    path('files/', views.partner_files, name='partner_files'),
    path('files/<int:file_id>/view/', views.partner_file_view, name='partner_file_view'),
    
    # Legacy dashboards - redirect to appropriate new dashboards
    path('dashboard/rm-supplier/', views.rm_supplier_dashboard, name='rm_supplier_dashboard'),
    path('dashboard/fp-supplier/', views.fp_supplier_dashboard, name='fp_supplier_dashboard'),
    path('dashboard/government/', views.government_dashboard, name='government_dashboard'),
]
