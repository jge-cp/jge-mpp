from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q, Sum
from datetime import timedelta
from inspections.models import FirstArticleInspection, LotAcceptance, MonthlyReport
from accounts.models import UserProfile
from inspections.listing import parse_list_filters, build_fa_queryset, build_lot_queryset, submitted_by_options_for_inspector, company_options_for_inspector


def get_or_create_profile(user):
    """Helper to get or create user profile"""
    profile = getattr(user, 'profile', None)
    if not profile:
        profile = UserProfile.objects.create(
            user=user,
            company_name=user.email.split('@')[0] if '@' in user.email else user.username,
            technical_email=user.email or f"{user.username}@example.com",
            user_functionality='admin' if user.is_staff else 'partner',
        )
        profile.set_default_permissions()
        profile.save()
    return profile


@login_required
def dashboard_router(request):
    """Route to appropriate dashboard based on user type"""
    profile = get_or_create_profile(request.user)
    
    # Get dashboard URL from profile
    dashboard_url = profile.get_dashboard_url()
    return redirect(dashboard_url)


@login_required
def partner_dashboard(request):
    """Partner dashboard - for all partners who submit FAs and Lots"""
    profile = get_or_create_profile(request.user)
    
    # Redirect to appropriate dashboard if not a partner
    if profile.user_functionality != 'partner':
        return redirect(profile.get_dashboard_url())
    
    # Get stats - include pending_final in the "in review" count
    fa_stats = {
        'pending': FirstArticleInspection.objects.filter(
            vendor=profile, 
            status__in=['pending', 'pending_final']
        ).count(),
        'approved': FirstArticleInspection.objects.filter(vendor=profile, status='approved').count(),
        'rejected': FirstArticleInspection.objects.filter(vendor=profile, status='rejected').count(),
    }
    
    lot_stats = {
        'pending': LotAcceptance.objects.filter(vendor=profile, status='pending').count(),
        'approved': LotAcceptance.objects.filter(vendor=profile, status='approved').count(),
        'rejected': LotAcceptance.objects.filter(vendor=profile, status='rejected').count(),
    }
    
    # Recent activity
    recent_fas = FirstArticleInspection.objects.filter(vendor=profile).order_by('-submission_date')[:5]
    recent_lots = LotAcceptance.objects.filter(vendor=profile).order_by('-submission_date')[:5]
    
    context = {
        'profile': profile,
        'fa_stats': fa_stats,
        'lot_stats': lot_stats,
        'recent_fas': recent_fas,
        'recent_lots': recent_lots,
    }
    
    if getattr(request, "htmx", False):
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
    profile = get_or_create_profile(request.user)
    
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
    
    # Base querysets depending on inspector type
    if is_primary:
        # Primary Inspector sees pending FAs and all pending lots
        fa_base = FirstArticleInspection.objects.filter(status='pending').select_related('vendor', 'company', 'multicam_variant')
        lot_base = LotAcceptance.objects.filter(status='pending').select_related('vendor', 'company', 'original_fa__multicam_variant')
        fa_pending = FirstArticleInspection.objects.filter(status='pending').count()
        fa_pending_final = FirstArticleInspection.objects.filter(status='pending_final').count()
        lot_pending = LotAcceptance.objects.filter(status='pending').count()
    else:
        # Final Inspector sees pending_final FAs only
        fa_base = FirstArticleInspection.objects.filter(status='pending_final').select_related('vendor', 'company', 'multicam_variant')
        lot_base = LotAcceptance.objects.none()
        fa_pending = 0
        fa_pending_final = FirstArticleInspection.objects.filter(status='pending_final').count()
        lot_pending = 0
    
    # Apply filters
    fas = build_fa_queryset(profile, fa_filters, base_qs=fa_base)
    lots = build_lot_queryset(profile, lot_filters, base_qs=lot_base)
    
    # Filter options for dropdowns
    fa_status_options = [
        ('pending', 'Awaiting Primary'),
        ('pending_final', 'Awaiting Final'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    lot_status_options = [
        ('pending', 'Awaiting Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    fa_submitted_by_options = submitted_by_options_for_inspector()
    fa_company_options = company_options_for_inspector()
    lot_submitted_by_options = submitted_by_options_for_inspector()
    lot_company_options = company_options_for_inspector()
    
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
    
    # === FA Statistics ===
    fa_stats = {
        'total': FirstArticleInspection.objects.count(),
        'approved': FirstArticleInspection.objects.filter(status='approved').count(),
        'rejected': FirstArticleInspection.objects.filter(status='rejected').count(),
        'pending': FirstArticleInspection.objects.filter(status='pending').count(),
        'pending_final': FirstArticleInspection.objects.filter(status='pending_final').count(),
        'this_month': FirstArticleInspection.objects.filter(submission_date__gte=thirty_days_ago).count(),
    }
    
    # === Lot Statistics ===
    lot_stats = {
        'total': LotAcceptance.objects.count(),
        'approved': LotAcceptance.objects.filter(status='approved').count(),
        'rejected': LotAcceptance.objects.filter(status='rejected').count(),
        'pending': LotAcceptance.objects.filter(status='pending').count(),
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
        'fa_status_options': fa_status_options,
        'fa_submitted_by_options': fa_submitted_by_options,
        'fa_company_options': fa_company_options,
        'fa_clear_url': fa_clear_url,
        # Filter context for Lot
        'lot_filters': lot_filters,
        'lot_status_options': lot_status_options,
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
                'is_inspector': True,
                'show_company_column': True,
                'empty_text': 'No First Articles in queue',
            })
        elif htmx_target == 'lot-queue-results':
            return render(request, 'partials/submissions/_results.html', {
                'items': lots,
                'kind': 'lot',
                'mode': 'queue',
                'row_url': 'inspections:lot_review',
                'is_inspector': True,
                'show_company_column': True,
                'empty_text': 'No Lots in queue',
            })
        else:
            # Default: return full dashboard fragment
            return render(request, 'dashboard/_inspector_dashboard_live.html', context)
    return render(request, 'dashboard/inspector_dashboard.html', context)


@login_required
def staff_dashboard(request):
    """Staff dashboard - for executives, finance, operations with high-level stats and drill-down"""
    profile = get_or_create_profile(request.user)
    
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
    
    # === FA Statistics ===
    fa_stats = {
        'total': FirstArticleInspection.objects.count(),
        'approved': FirstArticleInspection.objects.filter(status='approved').count(),
        'rejected': FirstArticleInspection.objects.filter(status='rejected').count(),
        'pending': FirstArticleInspection.objects.filter(status='pending').count(),
        'pending_final': FirstArticleInspection.objects.filter(status='pending_final').count(),
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
    
    # === Lot Statistics ===
    lot_stats = {
        'total': LotAcceptance.objects.count(),
        'approved': LotAcceptance.objects.filter(status='approved').count(),
        'rejected': LotAcceptance.objects.filter(status='rejected').count(),
        'pending': LotAcceptance.objects.filter(status='pending').count(),
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
