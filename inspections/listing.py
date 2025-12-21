from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.db.models import Q, QuerySet
from django.utils.dateparse import parse_date

from accounts.models import PartnerCompany, UserProfile
from inspections.models import FirstArticleInspection, LotAcceptance


@dataclass(frozen=True)
class ListFilters:
    q: str = ""
    status: str = ""
    submitted_by: str = ""  # user id as string
    company: str = ""       # company id as string
    date_from: str = ""     # YYYY-MM-DD
    date_to: str = ""       # YYYY-MM-DD


FA_STATUS_OPTIONS = [
    ("pending", "Awaiting Primary"),
    ("pending_final", "Awaiting Final"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
]

LOT_STATUS_OPTIONS = [
    ("pending", "Awaiting Review"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
]


def parse_list_filters(get_params) -> ListFilters:
    return ListFilters(
        q=(get_params.get("q") or "").strip(),
        status=(get_params.get("status") or "").strip(),
        submitted_by=(get_params.get("submitted_by") or "").strip(),
        company=(get_params.get("company") or "").strip(),
        date_from=(get_params.get("date_from") or "").strip(),
        date_to=(get_params.get("date_to") or "").strip(),
    )


def _apply_date_range(qs: QuerySet, field: str, date_from: str, date_to: str) -> QuerySet:
    d_from = parse_date(date_from) if date_from else None
    d_to = parse_date(date_to) if date_to else None

    if d_from:
        qs = qs.filter(**{f"{field}__date__gte": d_from})
    if d_to:
        qs = qs.filter(**{f"{field}__date__lte": d_to})
    return qs


def _apply_submitted_by(qs: QuerySet, submitted_by: str) -> QuerySet:
    if submitted_by and submitted_by.isdigit():
        return qs.filter(submitter_user_id=int(submitted_by))
    return qs


def _apply_company(qs: QuerySet, company: str) -> QuerySet:
    if company and company.isdigit():
        return qs.filter(company_id=int(company))
    return qs


def build_fa_queryset(profile: UserProfile, filters: ListFilters, *, base_qs: QuerySet | None = None) -> QuerySet:
    qs = base_qs or FirstArticleInspection.objects.all()

    # Scope
    if profile.is_partner():
        if profile.company:
            qs = qs.filter(company=profile.company)
        else:
            qs = qs.filter(vendor=profile)

    qs = qs.select_related("vendor", "vendor__user", "company", "multicam_variant").order_by("-submission_date")

    # Filters
    if filters.status:
        qs = qs.filter(status=filters.status)

    qs = _apply_submitted_by(qs, filters.submitted_by)

    # Company filter only meaningful for non-partners
    if not profile.is_partner():
        qs = _apply_company(qs, filters.company)

    qs = _apply_date_range(qs, "submission_date", filters.date_from, filters.date_to)

    # Search
    if filters.q:
        q = filters.q
        search_q = (
            Q(fabric_style__icontains=q)
            | Q(fa_lot_number__icontains=q)
            | Q(fai_id__icontains=q)
            | Q(multicam_variant__camouflage_name__icontains=q)
            | Q(submitter_email__icontains=q)
            | Q(submitter_first_name__icontains=q)
            | Q(submitter_last_name__icontains=q)
        )
        if not profile.is_partner():
            search_q |= Q(company__name__icontains=q) | Q(company__code__icontains=q) | Q(vendor__company_name__icontains=q)
        qs = qs.filter(search_q)

    return qs


def build_lot_queryset(profile: UserProfile, filters: ListFilters, *, base_qs: QuerySet | None = None) -> QuerySet:
    qs = base_qs or LotAcceptance.objects.all()

    if profile.is_partner():
        if profile.company:
            qs = qs.filter(company=profile.company)
        else:
            qs = qs.filter(vendor=profile)

    qs = qs.select_related(
        "vendor", "vendor__user", "company",
        "original_fa", "original_fa__multicam_variant"
    ).order_by("-submission_date")

    if filters.status:
        qs = qs.filter(status=filters.status)

    qs = _apply_submitted_by(qs, filters.submitted_by)

    if not profile.is_partner():
        qs = _apply_company(qs, filters.company)

    qs = _apply_date_range(qs, "submission_date", filters.date_from, filters.date_to)

    if filters.q:
        q = filters.q
        search_q = (
            Q(fabric_style__icontains=q)
            | Q(lot_lot_number__icontains=q)
            | Q(lot_id__icontains=q)
            | Q(original_fa__fa_lot_number__icontains=q)
            | Q(original_fa__multicam_variant__camouflage_name__icontains=q)
            | Q(submitter_email__icontains=q)
            | Q(submitter_first_name__icontains=q)
            | Q(submitter_last_name__icontains=q)
        )
        if not profile.is_partner():
            search_q |= Q(company__name__icontains=q) | Q(company__code__icontains=q) | Q(vendor__company_name__icontains=q)
        qs = qs.filter(search_q)

    return qs


def submitted_by_options_for_partner(profile: UserProfile) -> list[tuple[int, str]]:
    if profile.company:
        qs = UserProfile.objects.filter(user_functionality="partner", company=profile.company).select_related("user").order_by("user__last_name", "user__first_name", "user__username")
    else:
        qs = UserProfile.objects.filter(pk=profile.pk).select_related("user")

    return [(p.user_id, f"{p.user.get_full_name() or p.user.username}") for p in qs]


def submitted_by_options_for_inspector() -> list[tuple[int, str]]:
    qs = UserProfile.objects.filter(user_functionality="partner").select_related("user", "company").order_by("company__code", "user__last_name", "user__first_name", "user__username")
    options: list[tuple[int, str]] = []
    for p in qs:
        company = p.company.code if p.company else (p.company_name or "")
        label = p.user.get_full_name() or p.user.username
        if company:
            label = f"{label} — {company}"
        options.append((p.user_id, label))
    return options


def company_options_for_inspector() -> list[tuple[int, str]]:
    qs = PartnerCompany.objects.all().order_by("code", "name")
    return [(c.id, f"{c.name} ({c.code})") for c in qs]


