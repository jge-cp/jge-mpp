from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from .models import (
    FirstArticleInspection, LotAcceptance, 
    FAEvaluation, FAColorEvaluation, is_passing_rating,
    LotEvaluation, LotSampleEvaluation, LotSampleColorEvaluation
)
from .forms import (
    FirstArticleInspectionForm, LotAcceptanceForm, FAReviewForm,
    FAEvaluationForm, FAColorEvaluationForm, create_color_evaluation_formset,
    LotEvaluationForm, LotSampleEvaluationForm, LotSampleColorEvaluationForm
)


@login_required
def fa_submit(request):
    """FA submission form"""
    profile = getattr(request.user, 'profile', None)
    if not profile:
        from accounts.models import UserProfile
        profile = UserProfile.objects.create(
            user=request.user,
            company_name=request.user.email.split('@')[0] if '@' in request.user.email else request.user.username,
            technical_email=request.user.email,
        )
    
    if request.method == 'POST':
        form = FirstArticleInspectionForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            fa = form.save(commit=False)
            fa.vendor = profile
            fa.submitted = True
            fa.save()
            
            # Handle file uploads if any
            if 'submission_documents' in request.FILES:
                from core.models import FileUpload
                for file in request.FILES.getlist('submission_documents'):
                    file_upload = FileUpload.objects.create(
                        uploaded_by=request.user,
                        file=file,
                        file_name=file.name,
                        file_type=file.name.split('.')[-1],
                        file_size=file.size,
                        related_to_model='FirstArticleInspection',
                        related_to_id=fa.pk,
                    )
                    fa.submission_documents.add(file_upload)
            
            # Send email notification to inspector
            from .emails import send_fa_submitted_email
            send_fa_submitted_email(fa)
            
            messages.success(request, f'FA submitted successfully! FA ID: {fa.fai_id}')
            return redirect('inspections:fa_detail', fai_id=fa.fai_id)
    else:
        form = FirstArticleInspectionForm(user=request.user)
    
    return render(request, 'inspections/fa_submit.html', {'form': form})


@login_required
def fa_list(request):
    """FA list/history view - Partners see their own, inspectors/staff see all"""
    profile = getattr(request.user, 'profile', None)
    if not profile:
        from accounts.models import UserProfile
        profile = UserProfile.objects.create(
            user=request.user,
            company_name=request.user.email.split('@')[0] if '@' in request.user.email else request.user.username,
            technical_email=request.user.email,
        )
    
    # Partners see only their FAs, inspectors/staff see all
    if profile.is_partner():
        fas = FirstArticleInspection.objects.filter(vendor=profile).order_by('-submission_date')
    else:
        fas = FirstArticleInspection.objects.select_related('vendor').order_by('-submission_date')
    
    return render(request, 'inspections/fa_list.html', {'fas': fas, 'profile': profile})


@login_required
def fa_detail(request, fai_id):
    """FA detail view - accessible by vendor or any inspector/staff"""
    profile = getattr(request.user, 'profile', None)
    if not profile:
        from accounts.models import UserProfile
        profile = UserProfile.objects.create(
            user=request.user,
            company_name=request.user.email.split('@')[0] if '@' in request.user.email else request.user.username,
            technical_email=request.user.email,
        )
    
    # Partners can only see their own FAs, inspectors/staff can see all
    if profile.is_partner():
        fa = get_object_or_404(FirstArticleInspection, fai_id=fai_id, vendor=profile)
    else:
        fa = get_object_or_404(FirstArticleInspection, fai_id=fai_id)
    
    # Get evaluation history
    evaluation_history = fa.get_evaluation_history()
    
    context = {
        'fa': fa,
        'evaluation_history': evaluation_history,
        'can_resubmit': fa.can_resubmit() and profile.is_partner() and fa.vendor == profile,
    }
    return render(request, 'inspections/fa_detail.html', context)


@login_required
def fa_resubmit(request, fai_id):
    """Handle FA resubmission after rejection"""
    profile = getattr(request.user, 'profile', None)
    if not profile or not profile.is_partner():
        messages.error(request, 'Only partners can resubmit First Articles.')
        return redirect('dashboard:partner_dashboard')
    
    fa = get_object_or_404(FirstArticleInspection, fai_id=fai_id, vendor=profile)
    
    if not fa.can_resubmit():
        messages.error(request, 'This First Article cannot be resubmitted. Only rejected FAs can be resubmitted.')
        return redirect('inspections:fa_detail', fai_id=fai_id)
    
    if request.method == 'POST':
        # Resubmit the FA
        new_attempt = fa.resubmit()
        
        # Send notification email to Primary Inspector
        from .emails import send_fa_submitted_email
        send_fa_submitted_email(fa)
        
        messages.success(request, f'First Article {fa.display_name} has been resubmitted for review (Attempt #{new_attempt}).')
        return redirect('inspections:fa_detail', fai_id=fai_id)
    
    # GET request - show confirmation page
    return render(request, 'inspections/fa_resubmit_confirm.html', {'fa': fa})


@login_required
def fa_evaluation_history(request, fai_id):
    """View full evaluation history for an FA"""
    profile = getattr(request.user, 'profile', None)
    if not profile:
        messages.error(request, 'User profile not found.')
        return redirect('dashboard:partner_dashboard')
    
    # Partners can only see their own FAs, inspectors/staff can see all
    if profile.is_partner():
        fa = get_object_or_404(FirstArticleInspection, fai_id=fai_id, vendor=profile)
    else:
        fa = get_object_or_404(FirstArticleInspection, fai_id=fai_id)
    
    # Get all evaluations with related data
    evaluations = fa.evaluations.select_related('inspector').prefetch_related(
        'color_evaluations__color'
    ).order_by('-attempt_number', 'stage')
    
    # Group by attempt number for easier template rendering
    evaluation_history = fa.get_evaluation_history()
    
    # Get variant colors for display
    variant_colors = fa.multicam_variant.colors.all().order_by('position')
    
    context = {
        'fa': fa,
        'evaluations': evaluations,
        'evaluation_history': evaluation_history,
        'variant_colors': variant_colors,
    }
    return render(request, 'inspections/fa_evaluation_history.html', context)


@login_required
def lot_submit(request):
    """Lot submission form"""
    profile = getattr(request.user, 'profile', None)
    if not profile:
        from accounts.models import UserProfile
        profile = UserProfile.objects.create(
            user=request.user,
            company_name=request.user.email.split('@')[0] if '@' in request.user.email else request.user.username,
            technical_email=request.user.email,
        )
    
    if request.method == 'POST':
        form = LotAcceptanceForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            lot = form.save(commit=False)
            lot.vendor = profile
            
            # Auto-populate fields from original FA
            original_fa = form.cleaned_data['original_fa']
            lot.fabric_style = original_fa.fabric_style
            lot.shade_standard = original_fa.shade_standard
            lot.shade_standard_number = original_fa.shade_standard_number
            lot.spectral_reflectance_requirement = original_fa.spectral_reflectance_requirement
            lot.original_fa_lot_number = original_fa.fa_lot_number
            
            lot.submitted = True
            lot.save()
            
            # Handle file uploads if any
            if 'submission_documents' in request.FILES:
                from core.models import FileUpload
                for file in request.FILES.getlist('submission_documents'):
                    file_upload = FileUpload.objects.create(
                        uploaded_by=request.user,
                        file=file,
                        file_name=file.name,
                        file_type=file.name.split('.')[-1],
                        file_size=file.size,
                        related_to_model='LotAcceptance',
                        related_to_id=lot.pk,
                    )
                    lot.submission_documents.add(file_upload)
            
            # Send email notification to inspector
            from .emails import send_lot_submitted_email
            send_lot_submitted_email(lot)
            
            messages.success(request, f'Lot submitted successfully! Lot ID: {lot.lot_id}')
            return redirect('inspections:lot_detail', lot_id=lot.lot_id)
    else:
        form = LotAcceptanceForm(user=request.user)
        
        # Check if user has any approved FAs
        if profile:
            approved_fas_count = FirstArticleInspection.objects.filter(
                vendor=profile,
                status='approved'
            ).count()
            if approved_fas_count == 0:
                messages.warning(
                    request,
                    'You need at least one approved First Article before submitting a lot. '
                    'Please submit an FA first and wait for approval.'
                )
    
    return render(request, 'inspections/lot_submit.html', {'form': form})


@login_required
def get_fa_details(request, fai_id):
    """HTMX endpoint to get FA details for lot submission preview"""
    try:
        fa = FirstArticleInspection.objects.get(fai_id=fai_id)
        # Verify user has access to this FA
        profile = getattr(request.user, 'profile', None)
        if profile and fa.vendor == profile and fa.status == 'approved':
            return render(request, 'inspections/partials/fa_details_preview.html', {'fa': fa})
    except FirstArticleInspection.DoesNotExist:
        pass
    
    return render(request, 'inspections/partials/fa_details_preview.html', {'fa': None})


@login_required
def lot_list(request):
    """Lot list/history view - Partners see their own, inspectors/staff see all"""
    profile = getattr(request.user, 'profile', None)
    if not profile:
        from accounts.models import UserProfile
        profile = UserProfile.objects.create(
            user=request.user,
            company_name=request.user.email.split('@')[0] if '@' in request.user.email else request.user.username,
            technical_email=request.user.email,
        )
    
    # Partners see only their Lots, inspectors/staff see all
    if profile.is_partner():
        lots = LotAcceptance.objects.filter(vendor=profile).order_by('-submission_date')
    else:
        lots = LotAcceptance.objects.select_related('vendor').order_by('-submission_date')
    
    return render(request, 'inspections/lot_list.html', {'lots': lots, 'profile': profile})


@login_required
def lot_detail(request, lot_id):
    """Lot detail view"""
    profile = getattr(request.user, 'profile', None)
    if not profile:
        from accounts.models import UserProfile
        profile = UserProfile.objects.create(
            user=request.user,
            company_name=request.user.email.split('@')[0] if '@' in request.user.email else request.user.username,
            technical_email=request.user.email,
        )
    lot = get_object_or_404(LotAcceptance, lot_id=lot_id, vendor=profile)
    return render(request, 'inspections/lot_detail.html', {'lot': lot})


@login_required
def fa_review_queue(request):
    """Legacy FA review queue - redirects to appropriate queue based on role"""
    profile = getattr(request.user, 'profile', None)
    if not profile or not profile.is_any_inspector():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard:partner_dashboard')
    
    # Redirect based on inspector type
    if profile.is_primary_inspector():
        return redirect('inspections:fa_review_queue_primary')
    elif profile.is_final_inspector():
        return redirect('inspections:fa_review_queue_final')
    else:
        # Full admin - show primary queue by default
        return redirect('inspections:fa_review_queue_primary')


@login_required
def fa_review_queue_primary(request):
    """Primary Inspector FA review queue - shows pending FAs"""
    profile = getattr(request.user, 'profile', None)
    if not profile or not (profile.is_primary_inspector() or profile.admin_role == 'full_admin'):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard:partner_dashboard')
    
    pending_fas = FirstArticleInspection.objects.filter(status='pending').order_by('submission_date')
    context = {
        'pending_fas': pending_fas,
        'queue_type': 'primary',
        'queue_title': 'Primary Review Queue',
    }
    return render(request, 'inspections/fa_review_queue.html', context)


@login_required
def fa_review_queue_final(request):
    """Final Inspector FA review queue - shows pending_final FAs"""
    profile = getattr(request.user, 'profile', None)
    if not profile or not (profile.is_final_inspector() or profile.admin_role == 'full_admin'):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard:partner_dashboard')
    
    pending_fas = FirstArticleInspection.objects.filter(status='pending_final').order_by('submission_date')
    # Also show rejected FAs for visibility (read-only)
    rejected_fas = FirstArticleInspection.objects.filter(status='rejected').order_by('-updated_at')[:10]
    
    context = {
        'pending_fas': pending_fas,
        'rejected_fas': rejected_fas,
        'queue_type': 'final',
        'queue_title': 'Final Review Queue',
    }
    return render(request, 'inspections/fa_review_queue.html', context)


@login_required
def fa_review(request, fai_id):
    """
    FA Evaluation interface using the new shade rating system.
    
    Shows:
    - All variant colors with rating dropdowns (0-5 scale)
    - Pattern Execution, Scale, Spectral Reflectance (Pass/Fail)
    - Visual red/green pass/fail indicators
    - Auto-calculated overall result
    
    For Final Inspector: Pre-loads Primary Inspector's ratings.
    """
    profile = getattr(request.user, 'profile', None)
    if not profile or not profile.is_any_inspector():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard:partner_dashboard')
    
    fa = get_object_or_404(FirstArticleInspection, fai_id=fai_id)
    
    # Determine which review stage we're in
    is_primary_review = fa.status == 'pending'
    is_final_review = fa.status == 'pending_final'
    is_completed = fa.status in ['approved', 'rejected']
    
    # Check if primary inspector is viewing their own evaluation during final review
    is_primary_viewing_pending_final = (
        is_final_review and 
        profile.is_primary_inspector() and 
        not profile.is_final_inspector()
    )
    
    # Determine read-only status
    # - Completed FAs are always read-only
    # - Primary viewing pending_final: read-only if final has started, editable if not
    is_read_only = is_completed
    final_has_started = False
    
    if is_primary_viewing_pending_final:
        # Check if final inspector has started their review
        final_eval = fa.get_latest_evaluation('final')
        final_has_started = final_eval is not None
        is_read_only = final_has_started  # Read-only if final has started
    
    # Determine stage based on FA status and user role
    if is_completed or is_primary_viewing_pending_final:
        # For completed FAs or primary viewing pending_final, show their own stage
        if profile.is_primary_inspector():
            stage = 'primary'
        elif profile.is_final_inspector():
            stage = 'final'
        else:
            latest_eval = fa.get_latest_evaluation('final') or fa.get_latest_evaluation('primary')
            stage = latest_eval.stage if latest_eval else 'primary'
    else:
        # Active review - check permissions
        if is_primary_review and not (profile.is_primary_inspector() or profile.admin_role == 'full_admin'):
            messages.error(request, 'Only Primary Inspectors can review FAs at this stage.')
            return redirect('inspections:fa_review_queue_final')
        
        if is_final_review and not (profile.is_final_inspector() or profile.admin_role == 'full_admin'):
            messages.error(request, 'Only Final Inspectors can review FAs at this stage.')
            return redirect('inspections:fa_review_queue_primary')
        
        # Determine stage for evaluation
        stage = 'primary' if is_primary_review else 'final'
    
    # Get current attempt number (for resubmissions)
    current_attempt = fa.get_current_attempt_number()
    
    # For completed FAs OR primary viewing pending_final, show existing evaluations
    if is_completed or is_primary_viewing_pending_final:
        # Get the latest submitted evaluation for the requested stage
        evaluation = fa.get_latest_evaluation(stage)
        if not evaluation:
            # Fall back to showing whatever evaluation exists
            evaluation = fa.get_latest_evaluation('final') or fa.get_latest_evaluation('primary')
        created = False
        
        # Update current_attempt to match the evaluation we're viewing
        if evaluation:
            current_attempt = evaluation.attempt_number
    # Get or create evaluation for this stage (for pending FAs)
    elif stage == 'primary':
        # Check if we need a NEW attempt (after resubmission)
        # A new attempt is needed if:
        # 1. There's an existing submitted primary for the current attempt, OR
        # 2. The FA was rejected (meaning both primary and final from last attempt are done)
        last_primary = fa.get_latest_evaluation('primary')
        last_final = fa.get_latest_evaluation('final')
        
        need_new_attempt = False
        if last_primary and last_primary.is_submitted:
            # If final also exists and submitted (whether pass or fail), need new attempt
            if last_final and last_final.is_submitted:
                need_new_attempt = True
            # If primary failed, also need new attempt
            elif not last_primary.all_pass:
                need_new_attempt = True
        
        if need_new_attempt:
            current_attempt = fa.get_next_attempt_number()
        
        # Check if there's an existing evaluation for this attempt
        try:
            evaluation = FAEvaluation.objects.get(
                fa=fa, stage=stage, attempt_number=current_attempt
            )
            created = False
        except FAEvaluation.DoesNotExist:
            evaluation = FAEvaluation.objects.create(
                fa=fa, stage=stage, attempt_number=current_attempt, inspector=request.user
            )
            created = True
    else:
        # Final review - use the attempt number from the LATEST SUBMITTED PRIMARY
        latest_submitted_primary = fa.evaluations.filter(
            stage='primary', is_submitted=True
        ).order_by('-attempt_number').first()
        
        if latest_submitted_primary:
            current_attempt = latest_submitted_primary.attempt_number
        
        evaluation, created = FAEvaluation.objects.get_or_create(
                fa=fa,
                stage=stage,
                attempt_number=current_attempt,
                defaults={'inspector': request.user}
            )
    
    # Get primary evaluation for reference - use the one from the SAME attempt as current evaluation
    if evaluation:
        primary_evaluation = fa.evaluations.filter(
            stage='primary', 
            attempt_number=evaluation.attempt_number,
            is_submitted=True
        ).first()
    else:
        primary_evaluation = fa.get_latest_evaluation('primary')
        if primary_evaluation and not primary_evaluation.is_submitted:
            primary_evaluation = None
    
    # For final review, pre-load primary inspector's ratings if evaluation is new
    if is_final_review and created and primary_evaluation:
        # Copy overall criteria from primary
        evaluation.pattern_execution = primary_evaluation.pattern_execution
        evaluation.scale = primary_evaluation.scale
        evaluation.spectral_reflectance = primary_evaluation.spectral_reflectance
        evaluation.save()
    
    # Get variant colors for this FA
    variant_colors = fa.multicam_variant.colors.all().order_by('position')
    
    if request.method == 'POST' and not is_read_only:
        # Process the evaluation form (only for pending FAs)
        eval_form = FAEvaluationForm(request.POST, instance=evaluation, fa=fa)
        
        if eval_form.is_valid():
            evaluation = eval_form.save(commit=False)
            evaluation.inspector = request.user
            evaluation.save()
            
            # Process color evaluations
            all_colors_valid = True
            for color in variant_colors:
                prefix = f'color_{color.id}'
                rating = request.POST.get(f'{prefix}-rating', '')
                comment = request.POST.get(f'{prefix}-comment', '')
                
                if rating:
                    color_eval, _ = FAColorEvaluation.objects.update_or_create(
                        evaluation=evaluation,
                        color=color,
                        defaults={'rating': rating, 'comment': comment}
                    )
                else:
                    all_colors_valid = False
            
            # Check if this is a submission
            if 'submit_evaluation' in request.POST:
                if not all_colors_valid:
                    messages.error(request, 'Please rate all colors before submitting.')
                elif not evaluation.pattern_execution or not evaluation.scale:
                    messages.error(request, 'Please evaluate Pattern Execution and Scale.')
                else:
                    # Submit the evaluation
                    evaluation.submit()
                    
                    # Send appropriate emails
                    if evaluation.all_pass:
                        if stage == 'primary':
                            from .emails import send_fa_pending_final_email
                            send_fa_pending_final_email(fa)
                            messages.success(request, f'FA {fa.display_name} passed primary review and sent to final inspector.')
                        else:
                            from .emails import send_fa_approved_email
                            send_fa_approved_email(fa)
                            messages.success(request, f'FA {fa.display_name} fully approved! Partner can now submit lots.')
                    else:
                        from .emails import send_fa_rejected_email
                        send_fa_rejected_email(fa, evaluation=evaluation)
                        messages.warning(request, f'FA {fa.display_name} rejected due to failing criteria.')
                    
                    # Redirect to appropriate queue
                    if stage == 'primary':
                        return redirect('inspections:fa_review_queue_primary')
                    else:
                        return redirect('inspections:fa_review_queue_final')
            else:
                messages.info(request, 'Evaluation saved (not submitted).')
    else:
        eval_form = FAEvaluationForm(instance=evaluation, fa=fa)
    
    # Build color forms with existing data
    color_forms = []
    for color in variant_colors:
        try:
            color_eval = evaluation.color_evaluations.get(color=color)
        except FAColorEvaluation.DoesNotExist:
            color_eval = None
        
        # For final review, pre-load from primary if no existing evaluation
        # Also save them to DB so they persist
        if is_final_review and created and not color_eval and primary_evaluation:
            try:
                primary_color_eval = primary_evaluation.color_evaluations.get(color=color)
                # Create the color evaluation with pre-loaded values
                color_eval = FAColorEvaluation.objects.create(
                    evaluation=evaluation,
                    color=color,
                    rating=primary_color_eval.rating,
                    comment=primary_color_eval.comment
                )
            except FAColorEvaluation.DoesNotExist:
                pass
        
        form = FAColorEvaluationForm(
            prefix=f'color_{color.id}',
            instance=color_eval
        )
        color_forms.append((color, form, color_eval))
    
    # Handle inspection document uploads
    if request.method == 'POST' and 'inspection_documents' in request.FILES:
        from core.models import FileUpload
        for file in request.FILES.getlist('inspection_documents'):
            file_upload = FileUpload.objects.create(
                uploaded_by=request.user,
                file=file,
                file_name=file.name,
                file_type=file.name.split('.')[-1],
                file_size=file.size,
                related_to_model='FirstArticleInspection',
                related_to_id=fa.pk,
            )
            fa.inspection_documents.add(file_upload)
    
    # Get evaluation history for this FA
    evaluation_history = fa.get_evaluation_history()
    
    # Get both evaluations for display (so we can show both primary and final)
    primary_eval_for_display = fa.get_latest_evaluation('primary')
    final_eval_for_display = fa.get_latest_evaluation('final')
    
    context = {
        'fa': fa,
        'evaluation': evaluation,
        'eval_form': eval_form,
        'color_forms': color_forms,
        'is_primary_review': is_primary_review,
        'is_final_review': is_final_review,
        'is_completed': is_completed,
        'is_read_only': is_read_only,
        'is_primary_viewing_pending_final': is_primary_viewing_pending_final,
        'final_has_started': final_has_started,
        'review_stage': stage,
        'primary_evaluation': primary_evaluation,
        'primary_eval_for_display': primary_eval_for_display,
        'final_eval_for_display': final_eval_for_display,
        'evaluation_history': evaluation_history,
        'current_attempt': evaluation.attempt_number if evaluation else 1,
    }
    return render(request, 'inspections/fa_review.html', context)


@login_required
def lot_review_queue(request):
    """Lot review queue - Primary Inspector only"""
    profile = getattr(request.user, 'profile', None)
    if not profile or not profile.is_primary_inspector():
        messages.error(request, 'Only Primary Inspectors can review lots.')
        return redirect('dashboard:partner_dashboard')
    
    pending_lots = LotAcceptance.objects.filter(status='pending').order_by('submission_date')
    return render(request, 'inspections/lot_review_queue.html', {'pending_lots': pending_lots})


@login_required
def lot_review(request, lot_id):
    """
    Lot Evaluation interface using the new multi-sample rating system.
    Primary Inspector only (unlike FA which has two stages).
    
    Each sample gets its own evaluation section with:
    - Color ratings (0-5 scale)
    - Pattern Execution, Scale, Spectral Reflectance (Pass/Fail)
    - Visual red/green indicators
    """
    profile = getattr(request.user, 'profile', None)
    if not profile or not (profile.is_primary_inspector() or profile.admin_role == 'full_admin'):
        messages.error(request, 'Only Primary Inspectors can review lots.')
        return redirect('dashboard:partner_dashboard')
    
    lot = get_object_or_404(LotAcceptance, lot_id=lot_id)
    
    if lot.status != 'pending':
        messages.warning(request, f'Lot {lot.display_name} has already been reviewed.')
        return redirect('inspections:lot_detail', lot_id=lot_id)
    
    # Get or create evaluation
    evaluation, created = LotEvaluation.objects.get_or_create(
        lot=lot,
        defaults={'inspector': request.user}
    )
    
    # Get variant colors for this lot's FA
    variant = lot.original_fa.multicam_variant
    variant_colors = variant.colors.all().order_by('position')
    
    # Parse sample IDs from the lot
    sample_ids = [s.strip() for s in lot.individual_sample_numbers.split(',')]
    num_samples = len(sample_ids)
    
    # Ensure sample evaluations exist for each sample
    sample_evaluations = []
    for i, sample_id in enumerate(sample_ids, start=1):
        sample_eval, _ = LotSampleEvaluation.objects.get_or_create(
            lot_evaluation=evaluation,
            sample_number=i,
            defaults={'sample_id': sample_id}
        )
        if not sample_eval.sample_id:
            sample_eval.sample_id = sample_id
            sample_eval.save()
        sample_evaluations.append(sample_eval)
    
    if request.method == 'POST':
        eval_form = LotEvaluationForm(request.POST, instance=evaluation)
        
        if eval_form.is_valid():
            evaluation = eval_form.save(commit=False)
            evaluation.inspector = request.user
            evaluation.save()
            
            all_samples_complete = True
            
            # Process each sample evaluation
            for sample_eval in sample_evaluations:
                sample_prefix = f'sample_{sample_eval.sample_number}'
                
                # Update overall criteria
                sample_eval.pattern_execution = request.POST.get(f'{sample_prefix}_pattern', '')
                sample_eval.scale = request.POST.get(f'{sample_prefix}_scale', '')
                sample_eval.spectral_reflectance = request.POST.get(f'{sample_prefix}_spectral', '')
                sample_eval.comments = request.POST.get(f'{sample_prefix}_comments', '')
                sample_eval.save()
                
                # Process color evaluations
                for color in variant_colors:
                    color_prefix = f'{sample_prefix}_color_{color.id}'
                    rating = request.POST.get(f'{color_prefix}-rating', '')
                    comment = request.POST.get(f'{color_prefix}-comment', '')
                    
                    if rating:
                        LotSampleColorEvaluation.objects.update_or_create(
                            sample_evaluation=sample_eval,
                            color=color,
                            defaults={'rating': rating, 'comment': comment}
                        )
                    else:
                        all_samples_complete = False
                
                # Check if sample has required fields
                if not sample_eval.pattern_execution or not sample_eval.scale:
                    all_samples_complete = False
            
            # Check if this is a submission
            if 'submit_evaluation' in request.POST:
                if not all_samples_complete:
                    messages.error(request, 'Please complete all sample evaluations before submitting.')
                else:
                    # Submit the evaluation
                    evaluation.submit()
                    
                    # Send appropriate emails
                    if evaluation.all_pass:
                        from .emails import send_lot_approved_email
                        send_lot_approved_email(lot)
                        messages.success(request, f'Lot {lot.display_name} approved!')
                    else:
                        from .emails import send_lot_rejected_email
                        send_lot_rejected_email(lot)
                        messages.warning(request, f'Lot {lot.display_name} rejected due to failing criteria.')
                    
                    return redirect('inspections:lot_review_queue')
            else:
                messages.info(request, 'Evaluation saved (not submitted).')
    else:
        eval_form = LotEvaluationForm(instance=evaluation)
    
    # Build sample forms with color data
    samples_data = []
    for sample_eval in sample_evaluations:
        # Get existing color evaluations for this sample
        color_forms = []
        for color in variant_colors:
            try:
                color_eval = sample_eval.color_evaluations.get(color=color)
            except LotSampleColorEvaluation.DoesNotExist:
                color_eval = None
            color_forms.append((color, color_eval))
        
        samples_data.append({
            'sample_eval': sample_eval,
            'sample_number': sample_eval.sample_number,
            'sample_id': sample_eval.sample_id,
            'color_forms': color_forms,
        })
    
    context = {
        'lot': lot,
        'evaluation': evaluation,
        'eval_form': eval_form,
        'samples_data': samples_data,
        'variant_colors': variant_colors,
        'num_samples': num_samples,
    }
    return render(request, 'inspections/lot_review.html', context)


# Monthly Reporting Views

@login_required
def report_submit(request):
    """Monthly report submission form"""
    from .forms import MonthlyReportForm
    from .models import MonthlyReport
    
    profile = getattr(request.user, 'profile', None)
    if not profile:
        messages.error(request, 'User profile not found.')
        return redirect('dashboard:partner_dashboard')
    
    # Check if user has permission to submit reports
    if not profile.can_submit_reports and profile.user_functionality != 'partner':
        messages.error(request, 'You do not have permission to submit monthly reports.')
        return redirect('dashboard:partner_dashboard')
    
    if request.method == 'POST':
        form = MonthlyReportForm(request.POST, user=request.user)
        if form.is_valid():
            report = form.save(commit=False)
            report.partner = profile
            report.report_date = timezone.now().date()
            report.save()
            
            # Send email notification to accounting
            from .emails import send_report_submitted_email
            send_report_submitted_email(report)
            
            messages.success(request, f'Monthly report submitted successfully!')
            return redirect('inspections:report_list')
    else:
        form = MonthlyReportForm(user=request.user)
    
    return render(request, 'inspections/report_submit.html', {'form': form})


@login_required
def report_list(request):
    """List partner's monthly reports"""
    from .models import MonthlyReport
    
    profile = getattr(request.user, 'profile', None)
    if not profile:
        messages.error(request, 'User profile not found.')
        return redirect('dashboard:partner_dashboard')
    
    # Staff can see all reports, partners see their own
    if request.user.is_staff or profile.user_functionality == 'admin':
        reports = MonthlyReport.objects.all().order_by('-report_date')
    else:
        reports = MonthlyReport.objects.filter(partner=profile).order_by('-report_date')
    
    return render(request, 'inspections/report_list.html', {'reports': reports})


@login_required
def report_detail(request, report_id):
    """Monthly report detail view"""
    from .models import MonthlyReport
    
    profile = getattr(request.user, 'profile', None)
    if not profile:
        messages.error(request, 'User profile not found.')
        return redirect('dashboard:partner_dashboard')
    
    # Staff can see any report, partners only their own
    if request.user.is_staff or profile.user_functionality == 'admin':
        report = get_object_or_404(MonthlyReport, report_id=report_id)
    else:
        report = get_object_or_404(MonthlyReport, report_id=report_id, partner=profile)
    
    return render(request, 'inspections/report_detail.html', {'report': report})


# Accounting Views

@login_required
def accounting_reports_queue(request):
    """Accounting queue of submitted reports"""
    from .models import MonthlyReport
    
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard:partner_dashboard')
    
    # Filter by status
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'submitted':
        reports = MonthlyReport.objects.filter(status='submitted').order_by('-report_date')
    elif status_filter == 'reviewed':
        reports = MonthlyReport.objects.filter(status='reviewed').order_by('-report_date')
    elif status_filter == 'invoiced':
        reports = MonthlyReport.objects.filter(status='invoiced').order_by('-report_date')
    else:
        reports = MonthlyReport.objects.all().order_by('-report_date')
    
    # Calculate totals
    from django.db.models import Sum
    totals = {
        'total_yardage': reports.aggregate(Sum('yardage_produced'))['yardage_produced__sum'] or 0,
        'submitted_count': MonthlyReport.objects.filter(status='submitted').count(),
        'reviewed_count': MonthlyReport.objects.filter(status='reviewed').count(),
        'invoiced_count': MonthlyReport.objects.filter(status='invoiced').count(),
    }
    
    context = {
        'reports': reports,
        'totals': totals,
        'status_filter': status_filter,
    }
    return render(request, 'inspections/accounting_reports_queue.html', context)


@login_required
def accounting_review(request, report_id):
    """Accounting review interface for a report"""
    from .models import MonthlyReport
    from .forms import AccountingReviewForm
    
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard:partner_dashboard')
    
    report = get_object_or_404(MonthlyReport, report_id=report_id)
    
    if request.method == 'POST':
        form = AccountingReviewForm(request.POST, instance=report)
        action = request.POST.get('action')
        
        if form.is_valid():
            report = form.save(commit=False)
            report.reviewed_by = request.user
            report.reviewed_date = timezone.now()
            
            if action == 'review':
                report.status = 'reviewed'
                messages.success(request, f'Report #{report.report_id} marked as reviewed.')
            elif action == 'invoice':
                if not report.invoice_reference:
                    messages.error(request, 'Please enter an invoice reference.')
                    return render(request, 'inspections/accounting_review.html', {'report': report, 'form': form})
                report.status = 'invoiced'
                messages.success(request, f'Report #{report.report_id} marked as invoiced.')
            
            report.save()
            return redirect('inspections:accounting_reports_queue')
    else:
        form = AccountingReviewForm(instance=report)
    
    return render(request, 'inspections/accounting_review.html', {'report': report, 'form': form})
