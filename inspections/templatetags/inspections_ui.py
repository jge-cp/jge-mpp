from __future__ import annotations

from django import template
from django.utils import timezone
from django.utils.timesince import timesince

register = template.Library()


def _timesince_or_blank(dt) -> str:
    if not dt:
        return ""
    return timesince(dt, timezone.now())


def _subtext_class_for_badge(badge_variant: str) -> str:
    # keep consistent with existing dashboard styling - all use muted text
    return {
        "badge-approved": "text-gray-500",
        "badge-rejected": "text-gray-500",
        "badge-pending-final": "text-gray-500",
        "badge-pending": "text-gray-500",
    }.get(badge_variant, "text-muted")


@register.simple_tag
def fa_status_meta(fa, mode: str = "list") -> dict:
    """
    Returns a dict of display metadata for a FirstArticleInspection's status.

    mode:
      - list: partner/staff list displays (Awaiting Primary/Final/etc.)
      - dashboard: compact labels for dashboard cards
      - queue: inspector queue labels (Ready for Primary/Final Review)
    """
    status = getattr(fa, "status", "") or ""

    # Defaults
    badge_variant = "badge-pending"
    label = "Awaiting Primary"
    subtext = ""

    if status == "approved":
        badge_variant = "badge-approved"
        label = "✓ Approved" if mode in {"dashboard", "list"} else "Approved"
        subtext = "Passed Both Reviews"
    elif status == "rejected":
        badge_variant = "badge-rejected"
        label = "✗ Rejected"
        # try to explain stage
        if getattr(fa, "final_inspector", None):
            subtext = "Failed Final"
        elif getattr(fa, "primary_inspector", None):
            subtext = "Failed Primary"
        else:
            subtext = "Rejected"
    elif status == "pending_final":
        badge_variant = "badge-pending-final"
        if mode == "queue":
            label = "Ready for Final Review"
            subtext = "✓ Passed Primary Review"
        else:
            label = "Awaiting Final"
            subtext = "✓ Passed Primary"
    else:
        badge_variant = "badge-pending"
        if mode == "queue":
            label = "Ready for Primary Review"
            subtext = f"Waiting {_timesince_or_blank(getattr(fa, 'submission_date', None))}"
        else:
            label = "Awaiting Primary"
            subtext = f"{_timesince_or_blank(getattr(fa, 'submission_date', None))} ago"

    return {
        "badge_variant": badge_variant,
        "badge_label": label,
        "subtext": subtext,
        "subtext_class": _subtext_class_for_badge(badge_variant),
    }


@register.simple_tag
def lot_status_meta(lot, mode: str = "list") -> dict:
    """
    Returns a dict of display metadata for a LotAcceptance's status.

    mode:
      - list/dashboard: user-facing labels
      - queue: inspector queue labels (Ready for Review)
    """
    status = getattr(lot, "status", "") or ""

    badge_variant = "badge-pending"
    label = "Awaiting Review"
    subtext = ""

    if status == "approved":
        badge_variant = "badge-approved"
        label = "✓ Approved"
        subtext = "Ready for Production"
    elif status == "rejected":
        badge_variant = "badge-rejected"
        label = "✗ Rejected"
        subtext = "See Review Comments"
    else:
        badge_variant = "badge-pending"
        if mode == "queue":
            label = "Ready for Review"
            subtext = f"Waiting {_timesince_or_blank(getattr(lot, 'submission_date', None))}"
        else:
            label = "Awaiting Review"
            subtext = f"{_timesince_or_blank(getattr(lot, 'submission_date', None))} ago"

    return {
        "badge_variant": badge_variant,
        "badge_label": label,
        "subtext": subtext,
        "subtext_class": _subtext_class_for_badge(badge_variant),
    }


