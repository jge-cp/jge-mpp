"""
Notification functions for FA and Lot workflows.

Uses the NotificationService to send both email and in-app notifications,
with logging of all notifications sent.

Two-stage FA review process:
1. Primary Inspector reviews -> send_fa_pending_final_notification (to Final Inspector)
2. Final Inspector reviews -> send_fa_approved_notification or send_fa_rejected_notification (to Partner)
"""
from django.conf import settings
from notifications.services import (
    NotificationService, 
    get_primary_inspectors, 
    get_final_inspectors
)


def _format_fa_evaluation_details(evaluation):
    """Format an FAEvaluation's full details as plain text for email."""
    lines = []
    
    lines.append('  Overall Criteria:')
    pe = evaluation.pattern_execution.upper() if evaluation.pattern_execution else '-'
    lines.append(f'    Pattern Execution: {pe}')
    if evaluation.pattern_execution_comment:
        lines.append(f'      Comment: {evaluation.pattern_execution_comment}')
    
    sc = evaluation.scale.upper() if evaluation.scale else '-'
    lines.append(f'    Scale: {sc}')
    if evaluation.scale_comment:
        lines.append(f'      Comment: {evaluation.scale_comment}')
    
    sr = evaluation.spectral_reflectance.upper() if evaluation.spectral_reflectance else 'N/A'
    lines.append(f'    Spectral Reflectance: {sr}')
    if evaluation.spectral_reflectance_comment:
        lines.append(f'      Comment: {evaluation.spectral_reflectance_comment}')
    
    color_evals = evaluation.color_evaluations.select_related('color').all()
    if color_evals:
        lines.append('')
        lines.append('  Shade Matching:')
        for ce in color_evals:
            rating_display = ce.get_rating_display() if ce.rating else '-'
            result = 'PASS' if ce.is_passing else 'FAIL'
            line = f'    {ce.color.color_name}: {rating_display} ({result})'
            if ce.comment:
                line += f' — {ce.comment}'
            lines.append(line)
    
    if evaluation.comments:
        lines.append('')
        lines.append(f'  Comments: {evaluation.comments}')
    
    return '\n'.join(lines)


def _format_lot_sample_details(sample_evaluations):
    """Format LotSampleEvaluation details as plain text for email."""
    lines = []
    for sample in sample_evaluations:
        result = 'PASS' if sample.all_pass else 'FAIL'
        lines.append(f'  Sample {sample.sample_number} ({sample.sample_id}): {result}')
        
        pe = sample.pattern_execution.upper() if sample.pattern_execution else '-'
        lines.append(f'    Pattern Execution: {pe}')
        if sample.pattern_execution_comment:
            lines.append(f'      Comment: {sample.pattern_execution_comment}')
        
        sc = sample.scale.upper() if sample.scale else '-'
        lines.append(f'    Scale: {sc}')
        if sample.scale_comment:
            lines.append(f'      Comment: {sample.scale_comment}')
        
        sr = sample.spectral_reflectance.upper() if sample.spectral_reflectance else 'N/A'
        lines.append(f'    Spectral Reflectance: {sr}')
        if sample.spectral_reflectance_comment:
            lines.append(f'      Comment: {sample.spectral_reflectance_comment}')
        
        color_evals = sample.color_evaluations.select_related('color').all()
        if color_evals:
            lines.append('    Shade Matching:')
            for ce in color_evals:
                rating_display = ce.get_rating_display() if ce.rating else '-'
                cr = 'PASS' if ce.is_passing else 'FAIL'
                line = f'      {ce.color.color_name}: {rating_display} ({cr})'
                if ce.comment:
                    line += f' — {ce.comment}'
                lines.append(line)
        
        if sample.comments:
            lines.append(f'    Comments: {sample.comments}')
        lines.append('')
    
    return '\n'.join(lines)


def _get_latest_fa_evaluation(fa, stage=None):
    """Get the latest submitted evaluation for an FA, optionally filtered by stage."""
    qs = fa.evaluations.filter(is_submitted=True)
    if stage:
        qs = qs.filter(stage=stage)
    return qs.order_by('-submitted_at').first()


def send_fa_submitted_notification(fa):
    """
    Send notification when FA is submitted.
    
    If FA requires final-only review (BDCS, SWIR, or IMTP):
        → Notify Final Inspectors only (skips Primary)
    Otherwise:
        → Notify Primary Inspectors
    
    Sends both email and in-app notifications.
    """
    if fa.skip_primary_review:
        _send_fa_submitted_to_final(fa)
    else:
        _send_fa_submitted_to_primary(fa)


def _send_fa_submitted_to_primary(fa):
    """Send FA submitted notification to Primary Inspectors (standard flow)."""
    title = f'New First Article - {fa.vendor.company_name}'
    
    message = f"""A new First Article has been submitted for primary review:

FA ID: {fa.fai_id}
Partner: {fa.vendor.company_name}
Fabric Style: {fa.fabric_style}
Variant: {fa.multicam_variant.camouflage_name}
Lot: {fa.fa_lot_number}
Submitted: {fa.submission_date.strftime('%B %d, %Y at %I:%M %p')}

Please review the submission at: {settings.SITE_URL}/portal/admin/fa/review/{fa.fai_id}/"""
    
    recipients = get_primary_inspectors()
    
    NotificationService.notify(
        recipients=recipients,
        notification_type='fa_submitted',
        title=title,
        message=message,
        related_object=fa,
        action_url=f'/portal/admin/fa/review/{fa.fai_id}/',
        channels=['email', 'in_app'],
        email_subject=f'[TO: PRIMARY INSPECTOR] New First Article Submitted - {fa.vendor.company_name}'
    )


def _send_fa_submitted_to_final(fa):
    """Send FA submitted notification directly to Final Inspectors (BDCS/SWIR/IMTP)."""
    skip_reasons = []
    if fa.is_bdcs:
        skip_reasons.append('BDCS')
    if fa.spectral_reflectance_requirement == 'swir':
        skip_reasons.append('SWIR')
    if fa.multicam_variant and fa.multicam_variant.camouflage_name == 'IMTP':
        skip_reasons.append('IMTP')
    skip_reason_str = ', '.join(skip_reasons)
    
    title = f'New First Article (Direct to Final) - {fa.vendor.company_name}'
    
    message = f"""A First Article has been submitted and has skipped the primary inspection due to {skip_reason_str}. It is awaiting final approval.

FA ID: {fa.fai_id}
Partner: {fa.vendor.company_name}
Fabric Style: {fa.fabric_style}
Variant: {fa.multicam_variant.camouflage_name}
Lot: {fa.fa_lot_number}
Submitted: {fa.submission_date.strftime('%B %d, %Y at %I:%M %p')}

Please review the submission at: {settings.SITE_URL}/portal/admin/fa/review/{fa.fai_id}/"""
    
    recipients = get_final_inspectors()
    
    NotificationService.notify(
        recipients=recipients,
        notification_type='fa_submitted',
        title=title,
        message=message,
        related_object=fa,
        action_url=f'/portal/admin/fa/review/{fa.fai_id}/',
        channels=['email', 'in_app'],
        email_subject=f'[TO: FINAL INSPECTOR] New First Article (Direct Review) - {fa.vendor.company_name}'
    )


def send_fa_pending_final_notification(fa):
    """
    Send notification to Final Inspectors when Primary Inspector approves FA.
    Includes full primary evaluation details.
    """
    evaluation = _get_latest_fa_evaluation(fa, stage='primary')
    
    eval_details = ''
    if evaluation:
        eval_details = f"""
Primary Evaluation Details:
{_format_fa_evaluation_details(evaluation)}
"""
    
    title = f'FA Ready for Final Review - {fa.display_name}'
    
    inspector_name = fa.primary_inspector.get_full_name() if fa.primary_inspector else 'Unknown'
    review_date = fa.primary_review_date.strftime('%B %d, %Y') if fa.primary_review_date else 'N/A'
    
    message = f"""A First Article has passed primary review and is ready for final approval:

FA ID: {fa.fai_id}
Partner: {fa.vendor.company_name}
Fabric Style: {fa.fabric_style}
Variant: {fa.multicam_variant.camouflage_name}
Lot: {fa.fa_lot_number}

Primary Review:
- Reviewed by: {inspector_name}
- Date: {review_date}
{eval_details}
Please complete the final review at: {settings.SITE_URL}/portal/admin/fa/review/{fa.fai_id}/"""
    
    recipients = get_final_inspectors()
    
    NotificationService.notify(
        recipients=recipients,
        notification_type='fa_pending_final',
        title=title,
        message=message,
        related_object=fa,
        action_url=f'/portal/admin/fa/review/{fa.fai_id}/',
        channels=['email', 'in_app'],
        email_subject=f'[TO: FINAL INSPECTOR] FA Ready for Final Review - {fa.fai_id}'
    )


def send_fa_approved_notification(fa):
    """
    Send notification to partner when FA is fully approved (after final review).
    Includes full final evaluation details.
    """
    evaluation = _get_latest_fa_evaluation(fa, stage='final')
    
    eval_details = ''
    if evaluation:
        inspector_name = evaluation.inspector.get_full_name() if evaluation.inspector else 'Inspector'
        eval_details = f"""
Evaluation Details (reviewed by {inspector_name}):
{_format_fa_evaluation_details(evaluation)}
"""
    
    title = f'First Article Approved - {fa.display_name}'
    
    message = f"""Great news! Your First Article has been fully approved.

FA ID: {fa.fai_id}
Fabric: {fa.fabric_style}
Variant: {fa.multicam_variant.camouflage_name}
Lot: {fa.fa_lot_number}
{eval_details}
You can now submit production lots using this approval.

View details: {settings.SITE_URL}/portal/fa/{fa.fai_id}/"""
    
    NotificationService.notify(
        recipients=[fa.vendor.user],
        notification_type='fa_approved',
        title=title,
        message=message,
        related_object=fa,
        action_url=f'/portal/fa/{fa.fai_id}/',
        channels=['email', 'in_app'],
        email_subject=f'[TO: PARTNER] First Article Approved - {fa.fai_id}'
    )


def send_fa_rejected_notification(fa, evaluation=None):
    """
    Send notification to partner when FA is rejected (at any stage).
    If rejected at final review, also notify Primary Inspector.
    Includes full evaluation details.
    """
    if evaluation:
        rejection_stage = 'final review' if evaluation.stage == 'final' else 'primary review'
    elif fa.final_inspector:
        rejection_stage = 'final review'
        evaluation = _get_latest_fa_evaluation(fa, stage='final')
    else:
        rejection_stage = 'primary review'
        evaluation = _get_latest_fa_evaluation(fa, stage='primary')
    
    eval_details = ''
    if evaluation:
        inspector_name = evaluation.inspector.get_full_name() if evaluation.inspector else 'Inspector'
        eval_details = f"""
Evaluation Details (reviewed by {inspector_name}):
{_format_fa_evaluation_details(evaluation)}
"""
    
    comments = evaluation.comments if evaluation else ''
    
    title = f'First Article Requires Revision - {fa.display_name}'
    
    message = f"""Your First Article submission requires revision:

FA ID: {fa.fai_id}
Fabric: {fa.fabric_style}
Variant: {fa.multicam_variant.camouflage_name}
Lot: {fa.fa_lot_number}
Rejected at: {rejection_stage.title()}
{eval_details}
Please address the issues and resubmit when ready.

View details and resubmit: {settings.SITE_URL}/portal/fa/{fa.fai_id}/"""
    
    NotificationService.notify(
        recipients=[fa.vendor.user],
        notification_type='fa_rejected',
        title=title,
        message=message,
        related_object=fa,
        action_url=f'/portal/fa/{fa.fai_id}/',
        channels=['email', 'in_app'],
        email_subject=f'[TO: PARTNER] First Article Requires Revision - {fa.fai_id}'
    )
    
    # If rejected at final review, notify Primary Inspector
    # BUT only if this FA went through primary review (not BDCS/SWIR/IMTP)
    if rejection_stage == 'final review' and not fa.skip_primary_review:
        _send_fa_final_rejection_to_primary(fa, evaluation)


def _send_fa_final_rejection_to_primary(fa, evaluation=None):
    """Send notification to Primary Inspector when Final Inspector rejects."""
    eval_details = ''
    if evaluation:
        eval_details = f"""
Final Review Details:
{_format_fa_evaluation_details(evaluation)}
"""
    
    comments = evaluation.comments if evaluation else ''
    
    title = f'FA Rejected at Final Review - {fa.display_name}'
    
    message = f"""A First Article you previously approved has been rejected at final review:

FA ID: {fa.fai_id}
Partner: {fa.vendor.company_name}
Fabric: {fa.fabric_style}
Variant: {fa.multicam_variant.camouflage_name}
Lot: {fa.fa_lot_number}

Final Review Comments: {comments or 'No comments provided.'}
{eval_details}
The partner has been notified and may resubmit. If resubmitted, you will be 
asked to review it again before it goes to final review.

View FA: {settings.SITE_URL}/portal/fa/{fa.fai_id}/"""
    
    recipients = get_primary_inspectors()
    
    NotificationService.notify(
        recipients=recipients,
        notification_type='fa_rejected',
        title=title,
        message=message,
        related_object=fa,
        action_url=f'/portal/fa/{fa.fai_id}/',
        channels=['email', 'in_app'],
        email_subject=f'[TO: PRIMARY INSPECTOR] FA Rejected at Final Review - {fa.fai_id}'
    )


def send_lot_submitted_notification(lot):
    """
    Send notification to Primary Inspector when lot is submitted.
    Sends both email and in-app notifications.
    """
    title = f'New Lot Submitted - {lot.vendor.company_name}'
    
    message = f"""A new lot has been submitted for acceptance:

Lot ID: {lot.lot_id}
Partner: {lot.vendor.company_name}
Fabric: {lot.fabric_style}
Variant: {lot.multicam_variant.camouflage_name if lot.multicam_variant else '-'}
Original FA: {lot.original_fa.fai_id}
Lot Number: {lot.lot_lot_number}
Yards: {lot.number_of_yards_printed}
Samples: {lot.number_of_samples}
Submitted: {lot.submission_date.strftime('%B %d, %Y at %I:%M %p')}

Please review the submission at: {settings.SITE_URL}/portal/admin/lot/review/{lot.lot_id}/"""
    
    recipients = get_primary_inspectors()
    
    NotificationService.notify(
        recipients=recipients,
        notification_type='lot_submitted',
        title=title,
        message=message,
        related_object=lot,
        action_url=f'/portal/admin/lot/review/{lot.lot_id}/',
        channels=['email', 'in_app'],
        email_subject=f'[TO: PRIMARY INSPECTOR] New Lot Submitted - {lot.vendor.company_name}'
    )


def send_lot_approved_notification(lot, evaluation=None):
    """
    Send notification to partner when lot is approved.
    Includes full evaluation details per sample.
    """
    if not evaluation:
        evaluation = lot.evaluations.filter(is_submitted=True).order_by('-submitted_at').first()
    
    eval_details = ''
    if evaluation:
        inspector_name = evaluation.inspector.get_full_name() if evaluation.inspector else 'Inspector'
        samples = evaluation.sample_evaluations.all().prefetch_related('color_evaluations__color')
        sample_text = _format_lot_sample_details(samples)
        overall_comment = f'\nOverall Comments: {evaluation.comments}\n' if evaluation.comments else ''
        eval_details = f"""
Evaluation Details (reviewed by {inspector_name}):
{sample_text}{overall_comment}"""
    
    title = f'Lot Approved - {lot.display_name}'
    
    message = f"""Your lot has been approved for production:

Lot ID: {lot.lot_id}
Lot Number: {lot.lot_lot_number}
Fabric: {lot.fabric_style}
Variant: {lot.multicam_variant.camouflage_name if lot.multicam_variant else '-'}
Yards: {lot.number_of_yards_printed}
{eval_details}
View details: {settings.SITE_URL}/portal/lot/{lot.lot_id}/"""
    
    NotificationService.notify(
        recipients=[lot.vendor.user],
        notification_type='lot_approved',
        title=title,
        message=message,
        related_object=lot,
        action_url=f'/portal/lot/{lot.lot_id}/',
        channels=['email', 'in_app'],
        email_subject=f'[TO: PARTNER] Lot Approved - {lot.lot_id}'
    )


def send_lot_rejected_notification(lot, evaluation=None):
    """
    Send notification to partner when lot is rejected.
    Includes full evaluation details per sample.
    """
    if not evaluation:
        evaluation = lot.evaluations.filter(is_submitted=True).order_by('-submitted_at').first()
    
    eval_details = ''
    if evaluation:
        inspector_name = evaluation.inspector.get_full_name() if evaluation.inspector else 'Inspector'
        samples = evaluation.sample_evaluations.all().prefetch_related('color_evaluations__color')
        sample_text = _format_lot_sample_details(samples)
        overall_comment = f'\nOverall Comments: {evaluation.comments}\n' if evaluation.comments else ''
        eval_details = f"""
Evaluation Details (reviewed by {inspector_name}):
{sample_text}{overall_comment}"""
    
    title = f'Lot Requires Attention - {lot.display_name}'
    
    message = f"""Your lot submission was rejected:

Lot ID: {lot.lot_id}
Lot Number: {lot.lot_lot_number}
Fabric: {lot.fabric_style}
Variant: {lot.multicam_variant.camouflage_name if lot.multicam_variant else '-'}
{eval_details}
Please review and take appropriate action.

View details: {settings.SITE_URL}/portal/lot/{lot.lot_id}/"""
    
    NotificationService.notify(
        recipients=[lot.vendor.user],
        notification_type='lot_rejected',
        title=title,
        message=message,
        related_object=lot,
        action_url=f'/portal/lot/{lot.lot_id}/',
        channels=['email', 'in_app'],
        email_subject=f'[TO: PARTNER] Lot Requires Attention - {lot.lot_id}'
    )


def send_report_submitted_notification(report):
    """
    Send notification to accounting when monthly report is submitted.
    Email only (no in-app notification for accounting).
    """
    title = f'Monthly Report Submitted - {report.partner.company_name}'
    
    message = f"""A new monthly report has been submitted:

Report ID: #{report.report_id}
Partner: {report.partner.company_name}
Period: {report.period_from.strftime('%B %d, %Y')} to {report.period_to.strftime('%B %d, %Y')}
Customer: {report.customer_name}
MC Variant: {report.mc_variant.camouflage_name}
Yardage: {report.yardage_produced}
Non-License Fee: {'Yes' if report.non_license_fee_printing else 'No'}
Submitted: {report.created_at.strftime('%B %d, %Y at %I:%M %p')}

Please review the report at: {settings.SITE_URL}/portal/admin/reports/review/{report.report_id}/"""
    
    accounting_email = settings.DEFAULT_FROM_EMAIL
    
    NotificationService.notify(
        recipients=[accounting_email],
        notification_type='report_submitted',
        title=title,
        message=message,
        related_object=report,
        action_url=f'/portal/admin/reports/review/{report.report_id}/',
        channels=['email'],
        email_subject=f'[TO: ACCOUNTING] Monthly Report Submitted - {report.partner.company_name}'
    )


# Backwards compatibility aliases
send_fa_submitted_email = send_fa_submitted_notification
send_fa_pending_final_email = send_fa_pending_final_notification
send_fa_approved_email = send_fa_approved_notification
send_fa_rejected_email = send_fa_rejected_notification
send_lot_submitted_email = send_lot_submitted_notification
send_lot_approved_email = send_lot_approved_notification
send_lot_rejected_email = send_lot_rejected_notification
send_report_submitted_email = send_report_submitted_notification
