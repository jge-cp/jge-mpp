from django.urls import path
from . import views

app_name = 'inspections'

urlpatterns = [
    # FA URLs - Partner facing
    path('fa/submit/', views.fa_submit, name='fa_submit'),
    path('fa/list/', views.fa_list, name='fa_list'),
    path('fa/<str:fai_id>/', views.fa_detail, name='fa_detail'),
    path('fa/<str:fai_id>/resubmit/', views.fa_resubmit, name='fa_resubmit'),
    
    # Lot URLs - Partner facing
    path('lot/submit/', views.lot_submit, name='lot_submit'),
    path('lot/fa-details/<str:fai_id>/', views.get_fa_details, name='get_fa_details'),
    path('lot/fa-details-json/<str:fai_id>/', views.get_fa_details_json, name='get_fa_details_json'),
    path('lot/list/', views.lot_list, name='lot_list'),
    path('lot/<str:lot_id>/', views.lot_detail, name='lot_detail'),
    
    # Monthly Reporting URLs - Partner facing
    path('report/submit/', views.report_submit, name='report_submit'),
    path('report/list/', views.report_list, name='report_list'),
    path('report/<int:report_id>/', views.report_detail, name='report_detail'),
    
    # FA Review URLs - Inspector facing
    # Legacy route - redirects based on inspector type
    path('admin/fa/queue/', views.fa_review_queue, name='fa_review_queue'),
    # Primary Inspector queue - pending FAs
    path('admin/fa/queue/primary/', views.fa_review_queue_primary, name='fa_review_queue_primary'),
    # Final Inspector queue - pending_final FAs
    path('admin/fa/queue/final/', views.fa_review_queue_final, name='fa_review_queue_final'),
    # FA Review - handles both primary and final review
    path('admin/fa/review/<str:fai_id>/', views.fa_review, name='fa_review'),
    
    # Lot Review URLs - Primary Inspector only
    path('admin/lot/queue/', views.lot_review_queue, name='lot_review_queue'),
    path('admin/lot/review/<str:lot_id>/', views.lot_review, name='lot_review'),
    
    # HTMX Badge Endpoints - for sidebar queue counts
    path('badge/fa-primary/', views.fa_primary_queue_badge, name='fa_primary_queue_badge'),
    path('badge/fa-final/', views.fa_final_queue_badge, name='fa_final_queue_badge'),
    path('badge/lot/', views.lot_queue_badge, name='lot_queue_badge'),
    
    # Global search
    path('search/', views.global_search, name='global_search'),
    
    # Accounting URLs - Staff facing
    path('admin/reports/', views.accounting_reports_queue, name='accounting_reports_queue'),
    path('admin/reports/review/<int:report_id>/', views.accounting_review, name='accounting_review'),
]
