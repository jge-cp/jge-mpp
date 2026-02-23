from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404
from django.utils import timezone
from django.db.models import Count, Q, Sum
from datetime import timedelta
from inspections.models import FirstArticleInspection, LotAcceptance, MonthlyReport
from accounts.models import UserProfile
from core.models import PartnerFile
from inspections.listing import (
    parse_list_filters, build_fa_queryset, build_lot_queryset,
    submitted_by_options_for_inspector, submitted_by_options_for_partner,
    company_options_for_inspector, variant_options,
    FA_STATUS_OPTIONS, LOT_STATUS_OPTIONS,
    FA_SORT_FIELDS, LOT_SORT_FIELDS, _apply_sort, _apply_date_range,
    _apply_variant_fa, _apply_variant_lot, _apply_company,
)


@login_required
def dashboard_router(request):
    """Route to appropriate dashboard based on user type"""
    profile = request.profile
    
    # Get dashboard URL from profile
    dashboard_url = profile.get_dashboard_url()
    return redirect(dashboard_url)


@login_required
def partner_dashboard(request):
    """Partner dashboard - for all partners who submit FAs and Lots"""
    profile = request.profile
    
    # Redirect to appropriate dashboard if not a partner
    if profile.user_functionality != 'partner':
        return redirect(profile.get_dashboard_url())
    
    # Get stats using model managers (access control built-in)
    fa_base = FirstArticleInspection.objects.for_user(profile)
    lot_base = LotAcceptance.objects.for_user(profile)
    
    fa_stats = {
        'pending': fa_base.pending_any().count(),
        'approved': fa_base.approved().count(),
        'rejected': fa_base.rejected().count(),
    }
    
    lot_stats = {
        'pending': lot_base.pending().count(),
        'approved': lot_base.approved().count(),
        'rejected': lot_base.rejected().count(),
    }
    
    # Get filter values from request
    fa_filters = {
        'q': request.GET.get('fa_q', ''),
        'status': request.GET.get('fa_status', ''),
        'variant': request.GET.get('fa_variant', ''),
        'company': request.GET.get('fa_company', ''),
        'submitted_by': request.GET.get('fa_submitted_by', ''),
        'date_from': request.GET.get('fa_date_from', ''),
        'date_to': request.GET.get('fa_date_to', ''),
        'sort': request.GET.get('fa_sort', ''),
        'sort_dir': request.GET.get('fa_sort_dir', ''),
    }
    lot_filters = {
        'q': request.GET.get('lot_q', ''),
        'status': request.GET.get('lot_status', ''),
        'variant': request.GET.get('lot_variant', ''),
        'company': request.GET.get('lot_company', ''),
        'submitted_by': request.GET.get('lot_submitted_by', ''),
        'date_from': request.GET.get('lot_date_from', ''),
        'date_to': request.GET.get('lot_date_to', ''),
        'sort': request.GET.get('lot_sort', ''),
        'sort_dir': request.GET.get('lot_sort_dir', ''),
    }
    
    # Build FA queryset with filters using model manager (access control built-in)
    fa_qs = FirstArticleInspection.objects.for_user(profile).with_related()
    if fa_filters['q']:
        fa_qs = fa_qs.filter(
            Q(fabric_style__icontains=fa_filters['q']) |
            Q(fa_lot_number__icontains=fa_filters['q']) |
            Q(multicam_variant__camouflage_name__icontains=fa_filters['q']) |
            Q(company__name__icontains=fa_filters['q'])
        )
    if fa_filters['status']:
        fa_qs = fa_qs.filter(status=fa_filters['status'])
    fa_qs = _apply_variant_fa(fa_qs, fa_filters['variant'])
    fa_qs = _apply_company(fa_qs, fa_filters['company'])
    fa_qs = _apply_date_range(fa_qs, 'submission_date', fa_filters['date_from'], fa_filters['date_to'])
    fa_qs = _apply_sort(fa_qs, fa_filters['sort'], fa_filters['sort_dir'], FA_SORT_FIELDS)
    recent_fas = fa_qs[:10]
    
    # Build Lot queryset with filters using model manager (access control built-in)
    lot_qs = LotAcceptance.objects.for_user(profile).with_related()
    if lot_filters['q']:
        lot_qs = lot_qs.filter(
            Q(fabric_style__icontains=lot_filters['q']) |
            Q(lot_lot_number__icontains=lot_filters['q']) |
            Q(original_fa__multicam_variant__camouflage_name__icontains=lot_filters['q']) |
            Q(company__name__icontains=lot_filters['q'])
        )
    if lot_filters['status']:
        lot_qs = lot_qs.filter(status=lot_filters['status'])
    lot_qs = _apply_variant_lot(lot_qs, lot_filters['variant'])
    lot_qs = _apply_company(lot_qs, lot_filters['company'])
    lot_qs = _apply_date_range(lot_qs, 'submission_date', lot_filters['date_from'], lot_filters['date_to'])
    lot_qs = _apply_sort(lot_qs, lot_filters['sort'], lot_filters['sort_dir'], LOT_SORT_FIELDS)
    recent_lots = lot_qs[:10]
    
    # Get filter options - same for all users
    fa_submitted_by_options = submitted_by_options_for_partner(profile)
    lot_submitted_by_options = submitted_by_options_for_partner(profile)
    
    context = {
        'profile': profile,
        'fa_stats': fa_stats,
        'lot_stats': lot_stats,
        'recent_fas': recent_fas,
        'recent_lots': recent_lots,
        'fa_status_options': FA_STATUS_OPTIONS,
        'lot_status_options': LOT_STATUS_OPTIONS,
        'fa_variant_options': variant_options(),
        'lot_variant_options': variant_options(),
        'fa_company_options': company_options_for_inspector(),
        'lot_company_options': company_options_for_inspector(),
        'fa_submitted_by_options': fa_submitted_by_options,
        'lot_submitted_by_options': lot_submitted_by_options,
        'fa_filters': fa_filters,
        'lot_filters': lot_filters,
    }
    
    if getattr(request, "htmx", False):
        htmx_target = getattr(request.htmx, 'target', None)
        
        # Return only the specific partial based on HTMX target
        if htmx_target == 'fa-queue-results':
            return render(request, 'partials/submissions/_results.html', {
                'items': recent_fas,
                'kind': 'fa',
                'mode': 'list',
                'row_url': 'inspections:fa_detail',
                'empty_text': 'No First Articles yet. Submit your first one above!',
                'filters': fa_filters,
                'form_id': 'fa-filters-form',
                'target_id': 'fa-queue-results',
                'sort_prefix': 'fa_',
            })
        elif htmx_target == 'lot-queue-results':
            return render(request, 'partials/submissions/_results.html', {
                'items': recent_lots,
                'kind': 'lot',
                'mode': 'list',
                'row_url': 'inspections:lot_detail',
                'empty_text': 'No Lots yet. You can submit lots after an FA is approved.',
                'filters': lot_filters,
                'form_id': 'lot-filters-form',
                'target_id': 'lot-queue-results',
                'sort_prefix': 'lot_',
            })
        else:
            # Default: return full dashboard fragment
            return render(request, 'dashboard/_partner_dashboard_live.html', context)
    return render(request, 'dashboard/partner_dashboard.html', context)


# Backwards compatibility alias
@login_required
def printer_dashboard(request):
    """Alias for partner_dashboard - backwards compatibility"""
    return partner_dashboard(request)


@login_required
def inspector_dashboard(request):
    """Inspector dashboard - for Primary and Final Inspectors"""
    profile = request.profile
    
    # Redirect if not admin/staff
    if profile.user_functionality != 'admin' and not request.user.is_staff:
        return redirect(profile.get_dashboard_url())
    
    # Redirect staff to staff dashboard
    if profile.is_staff() and not profile.is_any_inspector():
        return redirect('dashboard:staff_dashboard')
    
    # Time ranges
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)
    
    # Determine inspector type for showing relevant queues
    is_primary = profile.is_primary_inspector()
    is_final = profile.is_final_inspector()
    
    # === Parse filters and build querysets ===
    # Use separate parameter namespaces for FA and Lot filters
    fa_params = {k.replace('fa_', ''): v for k, v in request.GET.items() if k.startswith('fa_')}
    lot_params = {k.replace('lot_', ''): v for k, v in request.GET.items() if k.startswith('lot_')}
    
    fa_filters = parse_list_filters(fa_params)
    lot_filters = parse_list_filters(lot_params)
    
    # Base querysets depending on inspector type (using model managers)
    if is_primary:
        # Primary Inspector sees pending FAs and all pending lots
        fa_base = FirstArticleInspection.objects.pending().with_related()
        lot_base = LotAcceptance.objects.pending().with_related()
        fa_pending = FirstArticleInspection.objects.pending().count()
        fa_pending_final = FirstArticleInspection.objects.pending_final().count()
        lot_pending = LotAcceptance.objects.pending().count()
    else:
        # Final Inspector sees pending_final FAs only
        fa_base = FirstArticleInspection.objects.pending_final().with_related()
        lot_base = LotAcceptance.objects.none()
        fa_pending = 0
        fa_pending_final = FirstArticleInspection.objects.pending_final().count()
        lot_pending = 0
    
    # Apply filters
    fas = build_fa_queryset(profile, fa_filters, base_qs=fa_base)
    lots = build_lot_queryset(profile, lot_filters, base_qs=lot_base)
    
    # Filter options for dropdowns
    fa_submitted_by_options = submitted_by_options_for_inspector()
    fa_company_options = company_options_for_inspector()
    fa_variant_options = variant_options()
    lot_submitted_by_options = submitted_by_options_for_inspector()
    lot_company_options = company_options_for_inspector()
    lot_variant_options = variant_options()
    
    # Clear URLs - preserve the other section's filters when clearing one section
    fa_clear_url = request.path + '?' + '&'.join(f"{k}={v}" for k, v in request.GET.items() if k.startswith('lot_'))
    lot_clear_url = request.path + '?' + '&'.join(f"{k}={v}" for k, v in request.GET.items() if k.startswith('fa_'))
    
    # Remove trailing ? if no params
    if fa_clear_url.endswith('?'):
        fa_clear_url = request.path
    if lot_clear_url.endswith('?'):
        lot_clear_url = request.path
    
    # === Overall Stats ===
    total_partners = UserProfile.objects.filter(user_functionality='partner').count()
    active_partners = UserProfile.objects.filter(user_functionality='partner', status='active').count()
    
    # === FA Statistics (using model managers) ===
    fa_stats = {
        'total': FirstArticleInspection.objects.count(),
        'approved': FirstArticleInspection.objects.approved().count(),
        'rejected': FirstArticleInspection.objects.rejected().count(),
        'pending': FirstArticleInspection.objects.pending().count(),
        'pending_final': FirstArticleInspection.objects.pending_final().count(),
        'this_month': FirstArticleInspection.objects.filter(submission_date__gte=thirty_days_ago).count(),
    }
    
    # === Lot Statistics (using model managers) ===
    lot_stats = {
        'total': LotAcceptance.objects.count(),
        'approved': LotAcceptance.objects.approved().count(),
        'rejected': LotAcceptance.objects.rejected().count(),
        'pending': LotAcceptance.objects.pending().count(),
        'this_month': LotAcceptance.objects.filter(submission_date__gte=thirty_days_ago).count(),
    }
    
    # === Recent Activity (last 7 days) ===
    recent_fa_submissions = FirstArticleInspection.objects.filter(
        submission_date__gte=seven_days_ago
    ).select_related('vendor').order_by('-submission_date')[:5]
    
    recent_lot_submissions = LotAcceptance.objects.filter(
        submission_date__gte=seven_days_ago
    ).select_related('vendor').order_by('-submission_date')[:5]
    
    # === Top Partners (by submission volume) ===
    top_partners = UserProfile.objects.filter(
        user_functionality='partner'
    ).annotate(
        fa_count=Count('fa_submissions'),
        lot_count=Count('lot_submissions')
    ).order_by('-fa_count')[:5]
    
    # === Alerts (items needing attention) ===
    alerts = []
    
    # FAs pending > 7 days (for primary inspector)
    if is_primary:
        old_fas = FirstArticleInspection.objects.filter(
            status='pending',
            submission_date__lt=seven_days_ago
        ).count()
        if old_fas > 0:
            alerts.append({
                'type': 'warning',
                'message': f'{old_fas} FA(s) pending primary review for more than 7 days',
                'link': '/portal/admin/fa/queue/primary/',
            })
        
        # Lots pending > 7 days
        old_lots = LotAcceptance.objects.filter(
            status='pending',
            submission_date__lt=seven_days_ago
        ).count()
        if old_lots > 0:
            alerts.append({
                'type': 'warning',
                'message': f'{old_lots} Lot(s) pending for more than 7 days',
                'link': '/portal/admin/lot/queue/',
            })
    
    # FAs pending final review > 7 days (for final inspector)
    if is_final:
        old_final_fas = FirstArticleInspection.objects.filter(
            status='pending_final',
            updated_at__lt=seven_days_ago
        ).count()
        if old_final_fas > 0:
            alerts.append({
                'type': 'warning',
                'message': f'{old_final_fas} FA(s) pending final review for more than 7 days',
                'link': '/portal/admin/fa/queue/final/',
            })
    
    context = {
        'profile': profile,
        'is_primary': is_primary,
        'is_final': is_final,
        # Queue stats
        'fa_pending': fa_pending,
        'fa_pending_final': fa_pending_final,
        'lot_pending': lot_pending,
        # Filtered querysets
        'fas': fas,
        'lots': lots,
        # Filter context for FA
        'fa_filters': fa_filters,
        'fa_status_options': FA_STATUS_OPTIONS,
        'fa_variant_options': fa_variant_options,
        'fa_submitted_by_options': fa_submitted_by_options,
        'fa_company_options': fa_company_options,
        'fa_clear_url': fa_clear_url,
        # Filter context for Lot
        'lot_filters': lot_filters,
        'lot_status_options': LOT_STATUS_OPTIONS,
        'lot_variant_options': lot_variant_options,
        'lot_submitted_by_options': lot_submitted_by_options,
        'lot_company_options': lot_company_options,
        'lot_clear_url': lot_clear_url,
        # User stats
        'total_partners': total_partners,
        'active_partners': active_partners,
        # FA/Lot stats
        'fa_stats': fa_stats,
        'lot_stats': lot_stats,
        # Recent activity
        'recent_fa_submissions': recent_fa_submissions,
        'recent_lot_submissions': recent_lot_submissions,
        # Top partners
        'top_partners': top_partners,
        # Alerts
        'alerts': alerts,
    }
    
    if getattr(request, "htmx", False):
        htmx_target = getattr(request.htmx, 'target', None)
        
        # Return only the specific partial based on HTMX target
        if htmx_target == 'fa-queue-results':
            return render(request, 'partials/submissions/_results.html', {
                'items': fas,
                'kind': 'fa',
                'mode': 'queue',
                'row_url': 'inspections:fa_review',
                'empty_text': 'No First Articles in queue',
                'filters': fa_filters,
                'form_id': 'fa-filters-form',
                'target_id': 'fa-queue-results',
                'sort_prefix': 'fa_',
            })
        elif htmx_target == 'lot-queue-results':
            return render(request, 'partials/submissions/_results.html', {
                'items': lots,
                'kind': 'lot',
                'mode': 'queue',
                'row_url': 'inspections:lot_review',
                'empty_text': 'No Lots in queue',
                'filters': lot_filters,
                'form_id': 'lot-filters-form',
                'target_id': 'lot-queue-results',
                'sort_prefix': 'lot_',
            })
        else:
            # Default: return full dashboard fragment
            return render(request, 'dashboard/_inspector_dashboard_live.html', context)
    return render(request, 'dashboard/inspector_dashboard.html', context)


@login_required
def staff_dashboard(request):
    """Staff dashboard - for executives, finance, operations with high-level stats and drill-down"""
    profile = request.profile
    
    # Redirect if not admin
    if profile.user_functionality != 'admin':
        return redirect(profile.get_dashboard_url())
    
    # Time ranges
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    ninety_days_ago = now - timedelta(days=90)
    one_year_ago = now - timedelta(days=365)
    
    # === High-Level Summary Stats ===
    summary = {
        'total_partners': UserProfile.objects.filter(user_functionality='partner').count(),
        'active_partners': UserProfile.objects.filter(user_functionality='partner', status='active').count(),
        'total_fas': FirstArticleInspection.objects.count(),
        'total_lots': LotAcceptance.objects.count(),
        'total_reports': MonthlyReport.objects.count(),
    }
    
    # === FA Statistics (using model managers) ===
    fa_stats = {
        'total': FirstArticleInspection.objects.count(),
        'approved': FirstArticleInspection.objects.approved().count(),
        'rejected': FirstArticleInspection.objects.rejected().count(),
        'pending': FirstArticleInspection.objects.pending().count(),
        'pending_final': FirstArticleInspection.objects.pending_final().count(),
        'this_month': FirstArticleInspection.objects.filter(submission_date__gte=thirty_days_ago).count(),
        'this_quarter': FirstArticleInspection.objects.filter(submission_date__gte=ninety_days_ago).count(),
        'this_year': FirstArticleInspection.objects.filter(submission_date__gte=one_year_ago).count(),
    }
    
    # Calculate approval rate
    if fa_stats['approved'] + fa_stats['rejected'] > 0:
        fa_stats['approval_rate'] = round(
            fa_stats['approved'] / (fa_stats['approved'] + fa_stats['rejected']) * 100, 1
        )
    else:
        fa_stats['approval_rate'] = 0
    
    # === Lot Statistics (using model managers) ===
    lot_stats = {
        'total': LotAcceptance.objects.count(),
        'approved': LotAcceptance.objects.approved().count(),
        'rejected': LotAcceptance.objects.rejected().count(),
        'pending': LotAcceptance.objects.pending().count(),
        'this_month': LotAcceptance.objects.filter(submission_date__gte=thirty_days_ago).count(),
        'this_quarter': LotAcceptance.objects.filter(submission_date__gte=ninety_days_ago).count(),
        'this_year': LotAcceptance.objects.filter(submission_date__gte=one_year_ago).count(),
    }
    
    # Calculate approval rate
    if lot_stats['approved'] + lot_stats['rejected'] > 0:
        lot_stats['approval_rate'] = round(
            lot_stats['approved'] / (lot_stats['approved'] + lot_stats['rejected']) * 100, 1
        )
    else:
        lot_stats['approval_rate'] = 0
    
    # === Total Yardage (from approved lots) ===
    total_yardage = LotAcceptance.objects.filter(
        status='approved'
    ).aggregate(Sum('number_of_yards_printed'))['number_of_yards_printed__sum'] or 0
    
    yardage_this_month = LotAcceptance.objects.filter(
        status='approved',
        submission_date__gte=thirty_days_ago
    ).aggregate(Sum('number_of_yards_printed'))['number_of_yards_printed__sum'] or 0
    
    yardage_this_year = LotAcceptance.objects.filter(
        status='approved',
        submission_date__gte=one_year_ago
    ).aggregate(Sum('number_of_yards_printed'))['number_of_yards_printed__sum'] or 0
    
    # === Monthly Report Stats ===
    report_stats = {
        'total': MonthlyReport.objects.count(),
        'submitted': MonthlyReport.objects.filter(status='submitted').count(),
        'reviewed': MonthlyReport.objects.filter(status='reviewed').count(),
        'invoiced': MonthlyReport.objects.filter(status='invoiced').count(),
        'total_yardage_reported': MonthlyReport.objects.aggregate(
            Sum('yardage_produced')
        )['yardage_produced__sum'] or 0,
    }
    
    # === Top Partners by Volume ===
    top_partners = UserProfile.objects.filter(
        user_functionality='partner',
        status='active'
    ).annotate(
        fa_count=Count('fa_submissions'),
        lot_count=Count('lot_submissions'),
        approved_fas=Count('fa_submissions', filter=Q(fa_submissions__status='approved')),
        approved_lots=Count('lot_submissions', filter=Q(lot_submissions__status='approved')),
    ).order_by('-lot_count')[:10]
    
    # === Monthly Trends (last 6 months) for charts ===
    monthly_trends = []
    for i in range(6):
        month_start = now - timedelta(days=30 * (i + 1))
        month_end = now - timedelta(days=30 * i)
        monthly_trends.append({
            'month': month_end.strftime('%b %Y'),
            'fa_submitted': FirstArticleInspection.objects.filter(
                submission_date__gte=month_start,
                submission_date__lt=month_end
            ).count(),
            'lots_submitted': LotAcceptance.objects.filter(
                submission_date__gte=month_start,
                submission_date__lt=month_end
            ).count(),
            'fa_approved': FirstArticleInspection.objects.filter(
                status='approved',
                final_review_date__gte=month_start,
                final_review_date__lt=month_end
            ).count(),
            'lot_approved': LotAcceptance.objects.filter(
                status='approved',
                review_date__gte=month_start,
                review_date__lt=month_end
            ).count(),
        })
    monthly_trends.reverse()  # Oldest first
    
    # === Recent Activity ===
    recent_fas = FirstArticleInspection.objects.select_related('vendor').order_by('-submission_date')[:10]
    recent_lots = LotAcceptance.objects.select_related('vendor').order_by('-submission_date')[:10]
    
    # === All Partners for drill-down ===
    all_partners = UserProfile.objects.filter(
        user_functionality='partner'
    ).annotate(
        fa_count=Count('fa_submissions'),
        lot_count=Count('lot_submissions')
    ).order_by('company_name')
    
    context = {
        'profile': profile,
        'summary': summary,
        'fa_stats': fa_stats,
        'lot_stats': lot_stats,
        'total_yardage': total_yardage,
        'yardage_this_month': yardage_this_month,
        'yardage_this_year': yardage_this_year,
        'report_stats': report_stats,
        'top_partners': top_partners,
        'monthly_trends': monthly_trends,
        'recent_fas': recent_fas,
        'recent_lots': recent_lots,
        'all_partners': all_partners,
    }
    
    if getattr(request, "htmx", False):
        return render(request, 'dashboard/_staff_dashboard_live.html', context)
    return render(request, 'dashboard/staff_dashboard.html', context)


# Legacy dashboard functions - redirect to appropriate dashboards
@login_required
def rm_supplier_dashboard(request):
    """Deprecated - redirects to partner dashboard"""
    messages.info(request, 'RM Supplier dashboard has been merged into Partner dashboard.')
    return redirect('dashboard:partner_dashboard')


@login_required
def fp_supplier_dashboard(request):
    """Deprecated - redirects to partner dashboard"""
    messages.info(request, 'FP Supplier dashboard has been merged into Partner dashboard.')
    return redirect('dashboard:partner_dashboard')


@login_required
def government_dashboard(request):
    """Deprecated - redirects to staff dashboard"""
    messages.info(request, 'Government dashboard has been merged into Staff dashboard.')
    return redirect('dashboard:staff_dashboard')


@login_required
def partner_files(request):
    """File repository for partners, filtered by their company's categories."""
    profile = request.profile
    
    if not profile.is_partner():
        messages.warning(request, 'File repository is only available for partners.')
        return redirect(profile.get_dashboard_url())
    
    company = profile.company
    if not company:
        files = PartnerFile.objects.none()
    else:
        categories = []
        if company.is_standard:
            categories.append('standard')
        if company.is_narrow:
            categories.append('narrow')
        categories.append('both')
        files = PartnerFile.objects.filter(is_active=True, category__in=categories)
    
    category_filter = request.GET.get('category', '')
    if category_filter:
        files = files.filter(category=category_filter)
    
    context = {
        'files': files,
        'company': company,
        'category_filter': category_filter,
    }
    return render(request, 'dashboard/partner_files.html', context)


@login_required
def partner_file_download(request, file_id):
    """Serve a partner file download after checking access."""
    profile = request.profile
    
    if not profile.is_partner():
        raise Http404
    
    company = profile.company
    if not company:
        raise Http404
    
    pf = PartnerFile.objects.filter(pk=file_id, is_active=True).first()
    if not pf:
        raise Http404
    
    # Verify the partner's company has access to this file's category
    if pf.category == 'standard' and not company.is_standard:
        raise Http404
    if pf.category == 'narrow' and not company.is_narrow:
        raise Http404
    
    try:
        return FileResponse(pf.file.open('rb'), as_attachment=True, filename=pf.file.name.split('/')[-1])
    except FileNotFoundError:
        raise Http404
