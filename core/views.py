from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone
from .models import RawMaterialArticle, TechnicalDataSheet, CamouflageType, MarketingOrder
from .file_validation import validate_upload, FileValidationError
from accounts.models import UserProfile
from accounts.decorators import admin_required
from inspections.models import FirstArticleInspection


def home(request):
    """Public marketing homepage"""
    return render(request, 'core/home.html')


def patterns(request):
    """Patterns page"""
    return render(request, 'core/patterns.html')


def gallery(request):
    """Gallery page"""
    return render(request, 'core/gallery.html')


def faq(request):
    """FAQ page"""
    return render(request, 'core/faq.html')


def suppliers(request):
    """MultiCam Suppliers page"""
    return render(request, 'core/suppliers.html')


def about(request):
    """About page"""
    return render(request, 'core/about.html')


def contact(request):
    """Contact page"""
    return render(request, 'core/contact.html')


# RM Supplier Views

@login_required
def rm_new_article(request):
    """Register a new raw material article"""
    profile = request.profile
    
    # Check permission
    if not (profile.can_register_articles or profile.user_functionality in ['rm_supplier', 'admin']):
        messages.error(request, 'You do not have permission to register articles.')
        return redirect('dashboard:dashboard_router')
    
    if request.method == 'POST':
        # Get form data
        product_name = request.POST.get('product_name')
        product_code = request.POST.get('product_code', '')
        composition = request.POST.get('composition')
        construction = request.POST.get('construction')
        weight_group = request.POST.get('weight_group')
        weight_value = request.POST.get('weight_value') or None
        width = request.POST.get('width') or None
        finish = request.POST.get('finish', '')
        color = request.POST.get('color', 'Greige')
        description = request.POST.get('description', '')
        
        # Validate required fields
        if not all([product_name, composition, construction, weight_group]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'core/rm_new_article.html', {
                'camouflages': CamouflageType.objects.filter(status='active'),
            })
        
        # Create article
        article = RawMaterialArticle.objects.create(
            supplier=profile,
            product_name=product_name,
            product_code=product_code,
            composition=composition,
            construction=construction,
            weight_group=weight_group,
            weight_value=weight_value,
            width=width,
            finish=finish,
            color=color,
            description=description,
        )
        
        # Add approved camouflages
        camouflage_ids = request.POST.getlist('approved_camouflages')
        if camouflage_ids:
            article.approved_camouflages.set(camouflage_ids)
        
        # Handle TDS upload if provided (with server-side validation)
        tds_file = request.FILES.get('tds_file')
        if tds_file:
            try:
                validate_upload(tds_file)
            except FileValidationError as e:
                messages.error(request, f'File upload error: {e.message}')
                return render(request, 'core/rm_new_article.html', {
                    'camouflages': CamouflageType.objects.filter(status='active'),
                })
            
            TechnicalDataSheet.objects.create(
                article=article,
                file=tds_file,
                file_name=tds_file.name,
                version='1.0',
                uploaded_by=request.user,
                description='Initial TDS upload',
            )
        
        messages.success(request, f'Article "{product_name}" registered successfully!')
        return redirect('core:rm_article_list')
    
    context = {
        'camouflages': CamouflageType.objects.filter(status='active'),
    }
    return render(request, 'core/rm_new_article.html', context)


@login_required
def rm_article_list(request):
    """List RM supplier's articles"""
    profile = request.profile
    
    # Staff/admin see all, RM suppliers see their own
    if request.user.is_staff or profile.user_functionality == 'admin':
        articles = RawMaterialArticle.objects.all()
    else:
        articles = RawMaterialArticle.objects.filter(supplier=profile)
    
    return render(request, 'core/rm_article_list.html', {'articles': articles})


@login_required
def rm_upload_tds(request):
    """Upload TDS for an article"""
    profile = request.profile
    
    # Check permission
    if not (profile.can_upload_tds or profile.user_functionality in ['rm_supplier', 'admin']):
        messages.error(request, 'You do not have permission to upload TDS.')
        return redirect('dashboard:dashboard_router')
    
    # Get articles for dropdown
    if request.user.is_staff or profile.user_functionality == 'admin':
        articles = RawMaterialArticle.objects.all()
    else:
        articles = RawMaterialArticle.objects.filter(supplier=profile)
    
    if request.method == 'POST':
        article_id = request.POST.get('article')
        tds_file = request.FILES.get('tds_file')
        version = request.POST.get('version', '')
        description = request.POST.get('description', '')
        
        if not article_id or not tds_file:
            messages.error(request, 'Please select an article and upload a file.')
            return render(request, 'core/rm_upload_tds.html', {'articles': articles})
        
        article = get_object_or_404(RawMaterialArticle, pk=article_id)
        
        # Check ownership
        if profile.user_functionality not in ['admin'] and not request.user.is_staff:
            if article.supplier != profile:
                messages.error(request, 'You can only upload TDS for your own articles.')
                return redirect('core:rm_upload_tds')
        
        # Validate file before saving
        try:
            validate_upload(tds_file)
        except FileValidationError as e:
            messages.error(request, f'File upload error: {e.message}')
            return render(request, 'core/rm_upload_tds.html', {'articles': articles})
        
        TechnicalDataSheet.objects.create(
            article=article,
            file=tds_file,
            file_name=tds_file.name,
            version=version,
            uploaded_by=request.user,
            description=description,
        )
        
        messages.success(request, f'TDS uploaded successfully for {article.product_name}!')
        return redirect('core:rm_article_list')
    
    return render(request, 'core/rm_upload_tds.html', {'articles': articles})


@login_required
def rm_printer_list(request):
    """View list of MC printers"""
    profile = request.profile
    
    # Check permission
    if not (profile.can_view_printer_list or profile.user_functionality in ['rm_supplier', 'fp_supplier', 'government', 'admin']):
        messages.error(request, 'You do not have permission to view the printer list.')
        return redirect('dashboard:dashboard_router')
    
    # Get active printers
    printers = UserProfile.objects.filter(
        user_functionality='printer',
        status='active'
    ).select_related('mpp_level').annotate(
        approved_fa_count=Count('fa_submissions', filter=models.Q(fa_submissions__status='approved'))
    ).order_by('company_name')
    
    return render(request, 'core/rm_printer_list.html', {'printers': printers})


@login_required
def rm_finished_products(request):
    """View finished products that passed FAI"""
    profile = request.profile
    
    # Get approved FAs
    # For RM suppliers, show FAs that used their materials (once we have that link)
    # For now, show all approved FAs
    if request.user.is_staff or profile.user_functionality == 'admin':
        approved_fas = FirstArticleInspection.objects.filter(status='approved').order_by('-review_date')
    else:
        # TODO: Filter by RM supplier's materials once we have that relationship
        approved_fas = FirstArticleInspection.objects.filter(status='approved').order_by('-review_date')
    
    return render(request, 'core/rm_finished_products.html', {'approved_fas': approved_fas})


# FP Supplier Views

@login_required
def fp_rm_library(request):
    """Browse raw materials library"""
    profile = request.profile
    
    # Check permission
    if not (profile.can_browse_rm_library or profile.user_functionality in ['fp_supplier', 'government', 'admin']):
        messages.error(request, 'You do not have permission to browse the RM library.')
        return redirect('dashboard:dashboard_router')
    
    # Get filter parameters
    construction = request.GET.get('construction', '')
    weight_group = request.GET.get('weight_group', '')
    supplier_id = request.GET.get('supplier', '')
    
    # Base queryset
    articles = RawMaterialArticle.objects.filter(status='active').select_related('supplier')
    
    # Apply filters
    if construction:
        articles = articles.filter(construction=construction)
    if weight_group:
        articles = articles.filter(weight_group=weight_group)
    if supplier_id:
        articles = articles.filter(supplier_id=supplier_id)
    
    # Get filter options
    suppliers = UserProfile.objects.filter(
        user_functionality='rm_supplier',
        status='active'
    ).order_by('company_name')
    
    context = {
        'articles': articles,
        'suppliers': suppliers,
        'construction': construction,
        'weight_group': weight_group,
        'supplier_id': supplier_id,
    }
    return render(request, 'core/fp_rm_library.html', context)


@login_required
def fp_rm_suppliers_list(request):
    """View RM suppliers list"""
    profile = request.profile
    
    # Check permission
    if not (profile.can_browse_rm_library or profile.user_functionality in ['fp_supplier', 'government', 'admin']):
        messages.error(request, 'You do not have permission to view RM suppliers.')
        return redirect('dashboard:dashboard_router')
    
    # Get RM suppliers with their article counts
    suppliers = UserProfile.objects.filter(
        user_functionality='rm_supplier',
        status='active'
    ).annotate(
        article_count=Count('raw_material_articles')
    ).order_by('company_name')
    
    return render(request, 'core/fp_rm_suppliers_list.html', {'suppliers': suppliers})


@login_required
def fp_rm_supplier_detail(request, supplier_id):
    """View RM supplier details and products"""
    profile = request.profile
    
    supplier = get_object_or_404(UserProfile, pk=supplier_id, user_functionality='rm_supplier')
    articles = RawMaterialArticle.objects.filter(supplier=supplier, status='active')
    
    return render(request, 'core/fp_rm_supplier_detail.html', {
        'supplier': supplier,
        'articles': articles,
    })


# Marketing Order Views

@login_required
def fp_marketing_order(request):
    """Create marketing package order"""
    profile = request.profile
    
    # Check permission
    if not (profile.can_order_marketing or profile.user_functionality in ['fp_supplier', 'admin']):
        messages.error(request, 'You do not have permission to order marketing materials.')
        return redirect('dashboard:dashboard_router')
    
    if request.method == 'POST':
        # Get form data
        rm_supplier_id = request.POST.get('rm_supplier')
        rm_supplier_name = request.POST.get('rm_supplier_name', '')
        fabric_type = request.POST.get('fabric_type')
        camouflage_type_id = request.POST.get('camouflage_type')
        number_of_pieces = request.POST.get('number_of_pieces')
        yardage = request.POST.get('yardage_to_be_used') or None
        
        # Shipping info
        shipping_name = request.POST.get('shipping_name')
        shipping_street = request.POST.get('shipping_street')
        shipping_city = request.POST.get('shipping_city')
        shipping_state = request.POST.get('shipping_state', '')
        shipping_country = request.POST.get('shipping_country')
        shipping_postal_code = request.POST.get('shipping_postal_code')
        
        # Validate required fields
        if not all([fabric_type, camouflage_type_id, number_of_pieces, 
                    shipping_name, shipping_street, shipping_city, shipping_country, shipping_postal_code]):
            messages.error(request, 'Please fill in all required fields.')
        else:
            # Create order
            camouflage_type = get_object_or_404(CamouflageType, pk=camouflage_type_id)
            rm_supplier = None
            if rm_supplier_id:
                rm_supplier = UserProfile.objects.filter(pk=rm_supplier_id).first()
            
            order = MarketingOrder.objects.create(
                fp_supplier=profile,
                rm_supplier=rm_supplier,
                rm_supplier_name=rm_supplier_name if not rm_supplier else '',
                fabric_type=fabric_type,
                camouflage_type=camouflage_type,
                number_of_pieces=int(number_of_pieces),
                yardage_to_be_used=yardage,
                shipping_name=shipping_name,
                shipping_street=shipping_street,
                shipping_city=shipping_city,
                shipping_state=shipping_state,
                shipping_country=shipping_country,
                shipping_postal_code=shipping_postal_code,
            )
            
            messages.success(request, f'Marketing order #{order.order_id} submitted successfully!')
            return redirect('core:fp_marketing_orders_list')
    
    # Get dropdown options
    rm_suppliers = UserProfile.objects.filter(user_functionality='rm_supplier', status='active').order_by('company_name')
    camouflages = CamouflageType.objects.filter(status='active')
    
    context = {
        'rm_suppliers': rm_suppliers,
        'camouflages': camouflages,
        'profile': profile,
    }
    return render(request, 'core/fp_marketing_order.html', context)


@login_required
def fp_marketing_orders_list(request):
    """List FP supplier's marketing orders"""
    profile = request.profile
    
    # Staff see all orders, FP suppliers see their own
    if request.user.is_staff or profile.user_functionality == 'admin':
        orders = MarketingOrder.objects.all()
    else:
        orders = MarketingOrder.objects.filter(fp_supplier=profile)
    
    return render(request, 'core/fp_marketing_orders_list.html', {'orders': orders})


@login_required
def fp_marketing_order_detail(request, order_id):
    """Marketing order detail view"""
    profile = request.profile
    
    # Staff can see any order, FP suppliers only their own
    if request.user.is_staff or profile.user_functionality == 'admin':
        order = get_object_or_404(MarketingOrder, order_id=order_id)
    else:
        order = get_object_or_404(MarketingOrder, order_id=order_id, fp_supplier=profile)
    
    return render(request, 'core/fp_marketing_order_detail.html', {'order': order})


# Admin Marketing Order Management

@login_required
@admin_required
def admin_marketing_queue(request):
    """Admin queue for marketing orders"""
    
    # Filter by status
    status_filter = request.GET.get('status', 'pending')
    if status_filter == 'all':
        orders = MarketingOrder.objects.all()
    else:
        orders = MarketingOrder.objects.filter(status=status_filter)
    
    # Stats
    stats = {
        'pending': MarketingOrder.objects.filter(status='pending').count(),
        'approved': MarketingOrder.objects.filter(status='approved').count(),
        'processing': MarketingOrder.objects.filter(status='processing').count(),
        'shipped': MarketingOrder.objects.filter(status='shipped').count(),
    }
    
    return render(request, 'core/admin_marketing_queue.html', {
        'orders': orders,
        'stats': stats,
        'status_filter': status_filter,
    })


@login_required
@admin_required
def admin_marketing_process(request, order_id):
    """Admin process marketing order"""
    
    order = get_object_or_404(MarketingOrder, order_id=order_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            order.status = 'approved'
            order.processed_by = request.user
            messages.success(request, f'Order #{order.order_id} approved.')
        elif action == 'process':
            order.status = 'processing'
            messages.success(request, f'Order #{order.order_id} marked as processing.')
        elif action == 'ship':
            tracking = request.POST.get('tracking_number', '')
            order.status = 'shipped'
            order.tracking_number = tracking
            order.shipped_date = timezone.now().date()
            messages.success(request, f'Order #{order.order_id} marked as shipped.')
        elif action == 'deliver':
            order.status = 'delivered'
            order.delivered_date = timezone.now().date()
            messages.success(request, f'Order #{order.order_id} marked as delivered.')
        elif action == 'cancel':
            order.status = 'cancelled'
            messages.warning(request, f'Order #{order.order_id} cancelled.')
        
        order.admin_notes = request.POST.get('admin_notes', order.admin_notes)
        order.save()
        return redirect('core:admin_marketing_queue')
    
    return render(request, 'core/admin_marketing_process.html', {'order': order})
