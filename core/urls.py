from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Public marketing pages
    path('', views.home, name='home'),
    path('patterns/', views.patterns, name='patterns'),
    path('gallery/', views.gallery, name='gallery'),
    path('faq/', views.faq, name='faq'),
    path('suppliers/', views.suppliers, name='suppliers'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    
    # RM Supplier URLs
    path('portal/rm/article/new/', views.rm_new_article, name='rm_new_article'),
    path('portal/rm/articles/', views.rm_article_list, name='rm_article_list'),
    path('portal/rm/tds/upload/', views.rm_upload_tds, name='rm_upload_tds'),
    path('portal/rm/printers/', views.rm_printer_list, name='rm_printer_list'),
    path('portal/rm/finished-products/', views.rm_finished_products, name='rm_finished_products'),
    
    # FP Supplier URLs
    path('portal/fp/rm-library/', views.fp_rm_library, name='fp_rm_library'),
    path('portal/fp/rm-suppliers/', views.fp_rm_suppliers_list, name='fp_rm_suppliers_list'),
    path('portal/fp/rm-suppliers/<int:supplier_id>/', views.fp_rm_supplier_detail, name='fp_rm_supplier_detail'),
    
    # Marketing Order URLs
    path('portal/fp/marketing/order/', views.fp_marketing_order, name='fp_marketing_order'),
    path('portal/fp/marketing/orders/', views.fp_marketing_orders_list, name='fp_marketing_orders_list'),
    path('portal/fp/marketing/orders/<int:order_id>/', views.fp_marketing_order_detail, name='fp_marketing_order_detail'),
    
    # Admin Marketing URLs
    path('portal/admin/marketing/', views.admin_marketing_queue, name='admin_marketing_queue'),
    path('portal/admin/marketing/<int:order_id>/', views.admin_marketing_process, name='admin_marketing_process'),
]
