from django.db import models, transaction, IntegrityError
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
import re

from .managers import FAManager, LotManager


# =============================================================================
# SHADE MATCHING RATING SYSTEM
# =============================================================================
# Rating scale for shade matching evaluation (0-5 with half-steps)
# Ratings 3 and above = PASS, below 3 = FAIL

SHADE_RATING_CHOICES = [
    ('0', '0 - Off-Shade'),
    ('0-1', '0-1 - Off-Shade/Much'),
    ('1', '1 - Much'),
    ('1-2', '1-2 - Much/Considerable'),
    ('2', '2 - Considerable'),
    ('2-3', '2-3 - Considerable/Noticeable'),
    ('3', '3 - Noticeable'),
    ('3-4', '3-4 - Noticeable/Slight'),
    ('4', '4 - Slight'),
    ('4-5', '4-5 - Slight/Equal'),
    ('5', '5 - Equal'),
]

# Ratings that result in PASS (>= 3)
PASSING_RATINGS = ['3', '3-4', '4', '4-5', '5']

# Ratings that result in FAIL (< 3)
FAILING_RATINGS = ['0', '0-1', '1', '1-2', '2', '2-3']


def is_passing_rating(rating):
    """Check if a shade rating is passing (>= 3)"""
    return rating in PASSING_RATINGS


# Simple Pass/Fail choices for Pattern Execution, Scale, Spectral Reflectance
PASS_FAIL_CHOICES = [
    ('pass', 'Pass'),
    ('fail', 'Fail'),
]

# Inspector stage choices
INSPECTOR_STAGE_CHOICES = [
    ('primary', 'Primary Inspector (1947)'),
    ('final', 'Final Inspector (Crye)'),
]


class FirstArticleInspection(models.Model):
    """First Article Inspection model (from FA Main schema)
    
    Two-stage review process:
    1. Primary Inspector reviews -> pending_final or rejected
    2. Final Inspector reviews -> approved or rejected
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending Primary Review'),
        ('pending_final', 'Pending Final Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    SHADE_STANDARD_CHOICES = [
        ('alpha', 'Alpha'),
        ('beta', 'Beta'),
    ]
    
    SPECTRAL_REFLECTANCE_CHOICES = [
        ('alpha', 'Alpha'),
        ('beta', 'Beta'),
        ('swir', 'SWIR'),  # Short-Wave Infrared - skips primary review
    ]
    
    EVALUATION_CHOICES = [
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ]
    
    # Auto-generated ID: {company_code}-FA-{sequence}
    fai_id = models.CharField(max_length=50, primary_key=True)
    
    # Company that owns this FA (scoped visibility for partners)
    company = models.ForeignKey(
        'accounts.PartnerCompany',
        on_delete=models.PROTECT,
        related_name='fa_submissions',
        null=True,  # Nullable for migration; new FAs should always have company
        blank=True,
        help_text='Partner company that owns this FA'
    )
    
    # Vendor (partner user who submitted) - legacy FK, kept for backwards compat
    # For new submissions, also populate submitter_* snapshot fields
    vendor = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,  # Changed from CASCADE: preserve FA even if user deleted
        null=True,
        blank=True,
        related_name='fa_submissions'
    )
    
    # Immutable submitter snapshot (audit trail - survives user deletion)
    submitter_user_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Original User ID at time of submission (immutable)'
    )
    submitter_email = models.EmailField(
        blank=True,
        default='',
        help_text='Submitter email at time of submission (immutable)'
    )
    
    # System generated unique ID
    fsid = models.CharField(max_length=50, unique=True, blank=True)
    
    # Status - system generated (two-stage review)
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Historic FA flag - for legacy data imports (admin-only)
    is_historic = models.BooleanField(
        default=False,
        help_text='Historic FAs are imported legacy data. Some fields may be N/A. Only admins can set this.'
    )
    
    # BDCS inspection flag - if checked, skips primary review
    is_bdcs = models.BooleanField(
        default=False,
        verbose_name='BDCS',
        help_text='Check if this is a BDCS inspection. BDCS submissions skip primary review.'
    )
    
    # FREE FORM fields (from FA Main)
    fabric_style = models.CharField(max_length=200)
    
    # DROPDOWN fields (from FA Main)
    multicam_variant = models.ForeignKey(
        'core.CamouflageType',
        on_delete=models.PROTECT,
        related_name='fa_submissions'
    )
    
    shade_standard = models.CharField(
        max_length=10,
        choices=SHADE_STANDARD_CHOICES
    )
    
    shade_standard_number = models.CharField(max_length=20, blank=True)
    
    spectral_reflectance_requirement = models.CharField(
        max_length=20,
        choices=SPECTRAL_REFLECTANCE_CHOICES
    )
    
    # FREEFORM (from FA Main) - The First Article's lot number
    fa_lot_number = models.CharField(max_length=50)
    
    # DATE fields (from FA Main)
    date_of_printing = models.DateField()
    first_article_ship_date = models.DateField(null=True, blank=True)
    
    # FREEFORM (from FA Main)
    tracking_number = models.CharField(max_length=50, blank=True)
    submitter_first_name = models.CharField(max_length=50, default='')
    submitter_last_name = models.CharField(max_length=50, default='')
    
    @property
    def submitter_full_name(self):
        """Return full name as 'Last, First' format"""
        return f"{self.submitter_last_name}, {self.submitter_first_name}".strip(', ')
    
    @property
    def skip_primary_review(self):
        """
        Returns True if this FA should skip primary inspector and go directly to final.
        
        Triggers:
        - IMTP selected as multicam variant
        - SWIR selected as spectral reflectance requirement
        - BDCS checkbox is checked
        """
        # Check IMTP variant
        is_imtp = self.multicam_variant and self.multicam_variant.camouflage_name == 'IMTP'
        # Check SWIR spectral requirement
        is_swir = self.spectral_reflectance_requirement == 'swir'
        # Check BDCS checkbox
        is_bdcs_checked = self.is_bdcs
        
        return is_imtp or is_swir or is_bdcs_checked
    
    # BOOLEAN (from FA Main)
    submitted = models.BooleanField(default=False)
    
    # DATE - SYSTEM GENERATED (from FA Main)
    submission_date = models.DateTimeField(auto_now_add=True)
    
    # SYSTEM GENERATED (from FA Main)
    sheet_name_generated = models.CharField(max_length=250, blank=True)
    
    # === TWO-STAGE REVIEW PROCESS ===
    
    # Primary Inspector (Stage 1: FA first review + all Lot reviews)
    primary_inspector = models.ForeignKey(
        User,
        related_name='primary_reviewed_fas',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    primary_review_date = models.DateField(null=True, blank=True)
    primary_comments = models.TextField(blank=True)
    
    # Primary evaluation criteria
    primary_pattern_execution = models.CharField(
        max_length=50,
        choices=EVALUATION_CHOICES,
        blank=True
    )
    primary_scale = models.CharField(
        max_length=50,
        choices=EVALUATION_CHOICES,
        blank=True
    )
    primary_spectral_reflectance = models.CharField(
        max_length=50,
        choices=EVALUATION_CHOICES,
        blank=True
    )
    
    # Final Inspector (Stage 2: FA final review only)
    final_inspector = models.ForeignKey(
        User,
        related_name='final_reviewed_fas',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    final_review_date = models.DateField(null=True, blank=True)
    final_comments = models.TextField(blank=True)
    
    # Final evaluation criteria
    final_pattern_execution = models.CharField(
        max_length=50,
        choices=EVALUATION_CHOICES,
        blank=True
    )
    final_scale = models.CharField(
        max_length=50,
        choices=EVALUATION_CHOICES,
        blank=True
    )
    final_spectral_reflectance = models.CharField(
        max_length=50,
        choices=EVALUATION_CHOICES,
        blank=True
    )
    
    # Legacy fields for backwards compatibility
    # (maps to primary_inspector data for existing code)
    @property
    def inspector(self):
        """Backwards compatibility: returns primary inspector"""
        return self.primary_inspector
    
    @property
    def review_date(self):
        """Backwards compatibility: returns primary review date"""
        return self.primary_review_date
    
    @property
    def inspector_comments(self):
        """Backwards compatibility: returns primary comments"""
        return self.primary_comments
    
    @property
    def pattern_execution(self):
        """Backwards compatibility: returns primary pattern execution"""
        return self.primary_pattern_execution
    
    @property
    def scale(self):
        """Backwards compatibility: returns primary scale"""
        return self.primary_scale
    
    @property
    def spectral_reflectance(self):
        """Backwards compatibility: returns primary spectral reflectance"""
        return self.primary_spectral_reflectance
    
    @property
    def display_name(self):
        """Returns formatted display name: {fabric_style} - {variant} - {fa_lot_number}"""
        variant_name = self.multicam_variant.camouflage_name if self.multicam_variant else 'Unknown'
        return f"{self.fabric_style} - {variant_name} - {self.fa_lot_number}"
    
    # Files
    submission_documents = models.ManyToManyField(
        'core.FileUpload',
        related_name='fa_submissions',
        blank=True
    )
    inspection_documents = models.ManyToManyField(
        'core.FileUpload',
        related_name='fa_inspections',
        blank=True
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Custom manager with access control and status filters
    objects = FAManager()
    
    class Meta:
        ordering = ['-submission_date']
        verbose_name = 'First Article Inspection'
        verbose_name_plural = 'First Article Inspections'
        indexes = [
            models.Index(fields=['status', 'submission_date']),
            models.Index(fields=['vendor', 'submission_date']),
            models.Index(fields=['multicam_variant']),
        ]
    
    def __str__(self):
        return self.display_name
    
    def get_current_attempt_number(self):
        """Get the current evaluation attempt number for this FA"""
        latest = self.evaluations.order_by('-attempt_number').first()
        return latest.attempt_number if latest else 1
    
    @property
    def current_attempt(self):
        """Property version for template access"""
        return self.get_current_attempt_number()
    
    def get_next_attempt_number(self):
        """Get the next attempt number for a new evaluation round"""
        return self.get_current_attempt_number() + 1
    
    def get_latest_evaluation(self, stage):
        """Get the most recent evaluation for a specific stage"""
        return self.evaluations.filter(stage=stage).order_by('-attempt_number').first()
    
    def get_evaluation_history(self):
        """Get all evaluations grouped by attempt number"""
        evaluations = self.evaluations.select_related('inspector').prefetch_related(
            'color_evaluations__color'
        ).order_by('-attempt_number', 'stage')
        
        # Group by attempt number
        history = {}
        for eval in evaluations:
            if eval.attempt_number not in history:
                history[eval.attempt_number] = {'primary': None, 'final': None}
            history[eval.attempt_number][eval.stage] = eval
        
        return history
    
    def can_resubmit(self):
        """Check if this FA can be resubmitted (only if rejected)"""
        return self.status == 'rejected'

    def _reset_review_fields_for_new_attempt(self):
        """
        Clear denormalized review fields so a new attempt doesn't carry stale inspector/comments/criteria.
        The attempt history remains in FAEvaluation/FAColorEvaluation.
        """
        self.primary_inspector = None
        self.primary_review_date = None
        self.primary_comments = ''
        self.primary_pattern_execution = ''
        self.primary_scale = ''
        self.primary_spectral_reflectance = ''

        self.final_inspector = None
        self.final_review_date = None
        self.final_comments = ''
        self.final_pattern_execution = ''
        self.final_scale = ''
        self.final_spectral_reflectance = ''
    
    def resubmit(self):
        """
        Handle FA resubmission after rejection.
        Changes status back to 'pending' for a new evaluation round.
        """
        if not self.pk:
            raise ValueError("Cannot resubmit an unsaved First Article.")

        with transaction.atomic():
            fa = FirstArticleInspection.objects.select_for_update().get(pk=self.pk)
            if fa.status != 'rejected':
                raise ValueError("Only rejected FAs can be resubmitted")

            fa.status = 'pending'
            fa._reset_review_fields_for_new_attempt()
            fa.save()

            # Next attempt number is derived from existing evaluation history.
            return fa.get_next_attempt_number()
    
    def save(self, *args, **kwargs):
        """Auto-generate fai_id and fsid if not set, populate company and submitter snapshot"""
        # Concurrency hardening:
        # This ID is derived from "last record + 1" which can race under concurrent creates.
        # We keep the same external format, but retry on integrity collisions.
        
        # Auto-populate company from vendor if not set (for new submissions)
        if not self.company_id and self.vendor:
            self.company = self.vendor.company
        
        # Populate immutable submitter snapshot on first save
        if self._state.adding and self.vendor:
            if not self.submitter_user_id:
                self.submitter_user_id = self.vendor.user_id
            if not self.submitter_email:
                self.submitter_email = self.vendor.user.email or ''
            if not self.submitter_first_name:
                self.submitter_first_name = self.vendor.user.first_name or ''
            if not self.submitter_last_name:
                self.submitter_last_name = self.vendor.user.last_name or ''
        
        max_attempts = 5
        for attempt in range(max_attempts):
            if not self.fai_id:
                # Generate fai_id: {company_code}-FA-{sequence}
                # Use company.code if available, else derive from vendor
                if self.company:
                    company_prefix = self.company.code
                elif self.vendor:
                    company_prefix = self.vendor.get_company_code()
                else:
                    company_prefix = 'UNKNOWN'
                
                # Sequence is per-company (not per-vendor)
                if self.company:
                    last_fa = FirstArticleInspection.objects.filter(
                        company=self.company
                    ).order_by('-fai_id').first()
                else:
                    # Fallback for legacy: per-vendor
                    last_fa = FirstArticleInspection.objects.filter(
                        vendor=self.vendor
                    ).order_by('-fai_id').first()
                
                if last_fa and last_fa.fai_id:
                    match = re.search(r'-FA-(\d+)', last_fa.fai_id)
                    sequence = int(match.group(1)) + 1 if match else 1
                else:
                    sequence = 1
                
                self.fai_id = f"{company_prefix}-FA-{sequence:04d}"
            
            if not self.fsid:
                # Generate unique fsid
                import uuid
                self.fsid = str(uuid.uuid4())[:8].upper()
            
            # Generate sheet name
            if not self.sheet_name_generated:
                self.sheet_name_generated = f"{self.fabric_style} - {self.multicam_variant.camouflage_name} - {self.fa_lot_number}"
            
            try:
                super().save(*args, **kwargs)
                break
            except IntegrityError:
                # Only retry on create; updates should not be regenerating primary keys.
                if not self._state.adding:
                    raise
                if attempt >= max_attempts - 1:
                    raise
                # Clear and retry with a new sequence.
                self.fai_id = ''
                continue


class LotAcceptance(models.Model):
    """Lot Acceptance model (from LA Main schema)"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    EVALUATION_TYPE_CHOICES = [
        ('simple', '27-row form (2 samples)'),
        ('standard', '37-row form (3 samples)'),
        ('complex', '57-row form (6+ samples)'),
    ]
    
    EVALUATION_CHOICES = [
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ]
    
    # Auto-generated ID: {company_code}-LOT-{sequence}
    lot_id = models.CharField(max_length=50, primary_key=True)
    
    # Company that owns this Lot (scoped visibility for partners)
    company = models.ForeignKey(
        'accounts.PartnerCompany',
        on_delete=models.PROTECT,
        related_name='lot_submissions',
        null=True,  # Nullable for migration; new Lots should always have company
        blank=True,
        help_text='Partner company that owns this Lot'
    )
    
    # Vendor (partner user who submitted) - legacy FK, kept for backwards compat
    vendor = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,  # Changed from CASCADE: preserve Lot even if user deleted
        null=True,
        blank=True,
        related_name='lot_submissions'
    )
    
    # Immutable submitter snapshot (audit trail - survives user deletion)
    submitter_user_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Original User ID at time of submission (immutable)'
    )
    submitter_email = models.EmailField(
        blank=True,
        default='',
        help_text='Submitter email at time of submission (immutable)'
    )
    
    # System generated unique ID
    fsid = models.CharField(max_length=50, unique=True, blank=True)
    
    # Status - system generated
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # DROPDOWN - Approved rows from FA workbook (from LA Main)
    fabric_style = models.CharField(max_length=200)  # From approved FA
    
    # SYSTEM GENERATED from FA Workbook (from LA Main)
    shade_standard = models.CharField(max_length=10)  # From FA
    shade_standard_number = models.CharField(max_length=20, blank=True)  # From FA
    spectral_reflectance_requirement = models.CharField(max_length=20)  # From FA
    original_fa_lot_number = models.CharField(max_length=50)  # Copied from FA's fa_lot_number
    
    # FREEFORM (from LA Main) - The Lot's own lot number
    lot_lot_number = models.CharField(max_length=50)  # Partner enters
    
    # FREEFORM INT (from LA Main)
    number_of_yards_printed = models.IntegerField(validators=[MinValueValidator(1)])
    
    # Additional fields from actual LA workbooks
    number_of_samples = models.IntegerField(validators=[MinValueValidator(1)])
    individual_sample_numbers = models.TextField()  # Comma-separated
    date_of_printing = models.DateField()
    date_shipped = models.DateField(null=True, blank=True)
    tracking_number = models.CharField(max_length=50, blank=True)
    submitter_first_name = models.CharField(max_length=50, default='')
    submitter_last_name = models.CharField(max_length=50, default='')
    
    @property
    def submitter_full_name(self):
        """Return full name as 'Last, First' format"""
        return f"{self.submitter_last_name}, {self.submitter_first_name}".strip(', ')
    
    # Link to original FA (CRITICAL!)
    original_fa = models.ForeignKey(
        FirstArticleInspection,
        on_delete=models.PROTECT,
        related_name='lots',
        help_text='Must reference approved FA'
    )
    
    @property
    def multicam_variant(self):
        """Returns the multicam variant from the original FA"""
        return self.original_fa.multicam_variant if self.original_fa else None
    
    @property
    def display_name(self):
        """Returns formatted display name: {fabric_style} - {variant} - {lot_lot_number}"""
        variant_name = self.multicam_variant.camouflage_name if self.multicam_variant else 'Unknown'
        return f"{self.fabric_style} - {variant_name} - {self.lot_lot_number}"
    
    # Submission tracking
    submitted = models.BooleanField(default=False)
    submission_date = models.DateTimeField(auto_now_add=True)
    sheet_name_generated = models.CharField(max_length=250, blank=True)
    
    # Inspector evaluation
    inspector = models.ForeignKey(
        User,
        related_name='inspected_lots',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    review_date = models.DateField(null=True, blank=True)
    
    # Evaluation type (determines form complexity)
    evaluation_type = models.CharField(
        max_length=20,
        choices=EVALUATION_TYPE_CHOICES,
        default='standard'
    )
    
    # Evaluation criteria (from LA Eval)
    pattern_execution = models.CharField(
        max_length=50,
        choices=EVALUATION_CHOICES,
        blank=True
    )
    scale = models.CharField(
        max_length=50,
        choices=EVALUATION_CHOICES,
        blank=True
    )
    spectral_reflectance = models.CharField(
        max_length=50,
        choices=EVALUATION_CHOICES,
        blank=True
    )
    evaluation_scores = models.JSONField(default=dict, blank=True)  # Flexible for different eval types
    inspector_comments = models.TextField(blank=True)
    
    # Files
    submission_documents = models.ManyToManyField(
        'core.FileUpload',
        related_name='lot_submissions',
        blank=True
    )
    inspection_documents = models.ManyToManyField(
        'core.FileUpload',
        related_name='lot_inspections',
        blank=True
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Custom manager with access control and status filters
    objects = LotManager()
    
    class Meta:
        ordering = ['-submission_date']
        verbose_name = 'Lot Acceptance'
        verbose_name_plural = 'Lot Acceptances'
        indexes = [
            models.Index(fields=['status', 'submission_date']),
            models.Index(fields=['vendor', 'submission_date']),
            models.Index(fields=['original_fa']),
        ]
    
    def __str__(self):
        return self.display_name
    
    def save(self, *args, **kwargs):
        """Auto-generate lot_id, fsid, sample count, sample IDs, populate company and submitter snapshot"""
        
        # Auto-populate company from vendor if not set (for new submissions)
        if not self.company_id and self.vendor:
            self.company = self.vendor.company
        
        # Populate immutable submitter snapshot on first save
        if self._state.adding and self.vendor:
            if not self.submitter_user_id:
                self.submitter_user_id = self.vendor.user_id
            if not self.submitter_email:
                self.submitter_email = self.vendor.user.email or ''
            if not self.submitter_first_name:
                self.submitter_first_name = self.vendor.user.first_name or ''
            if not self.submitter_last_name:
                self.submitter_last_name = self.vendor.user.last_name or ''
        
        max_attempts = 5
        for attempt in range(max_attempts):
            if not self.lot_id:
                # Generate lot_id: {company_code}-LOT-{sequence}
                # Use company.code if available, else derive from vendor
                if self.company:
                    company_prefix = self.company.code
                elif self.vendor:
                    company_prefix = self.vendor.get_company_code()
                else:
                    company_prefix = 'UNKNOWN'
                
                # Sequence is per-company (not per-vendor)
                if self.company:
                    last_lot = LotAcceptance.objects.filter(
                        company=self.company
                    ).order_by('-lot_id').first()
                else:
                    # Fallback for legacy: per-vendor
                    last_lot = LotAcceptance.objects.filter(
                        vendor=self.vendor
                    ).order_by('-lot_id').first()
                
                if last_lot and last_lot.lot_id:
                    match = re.search(r'-LOT-(\d+)', last_lot.lot_id)
                    sequence = int(match.group(1)) + 1 if match else 1
                else:
                    sequence = 1
                
                self.lot_id = f"{company_prefix}-LOT-{sequence:04d}"
            
            if not self.fsid:
                # Generate unique fsid
                import uuid
                self.fsid = str(uuid.uuid4())[:8].upper()
            
            # Auto-calculate sample count based on yards printed
            # Formula: 0-800 yards = 2, 801-22000 = 3, 22001+ = 5
            if self.number_of_yards_printed:
                if self.number_of_yards_printed <= 800:
                    self.number_of_samples = 2
                elif self.number_of_yards_printed <= 22000:
                    self.number_of_samples = 3
                else:
                    self.number_of_samples = 5
            
            # Auto-generate individual sample numbers if not set
            # Format: {lot_lot_number}-1, {lot_lot_number}-2, etc.
            if not self.individual_sample_numbers and self.lot_lot_number:
                sample_ids = [f"{self.lot_lot_number}-{i}" for i in range(1, self.number_of_samples + 1)]
                self.individual_sample_numbers = ', '.join(sample_ids)
            
            # Determine evaluation type based on sample count
            if self.number_of_samples <= 2:
                self.evaluation_type = 'simple'
            elif self.number_of_samples <= 3:
                self.evaluation_type = 'standard'
            else:
                self.evaluation_type = 'complex'
            
            # Generate sheet name: {fabric_style} - {variant} - {lot_lot_number}
            if not self.sheet_name_generated:
                variant_name = self.original_fa.multicam_variant.camouflage_name if self.original_fa and self.original_fa.multicam_variant else 'Unknown'
                self.sheet_name_generated = f"{self.fabric_style} - {variant_name} - {self.lot_lot_number}"
            
            try:
                super().save(*args, **kwargs)
                break
            except IntegrityError:
                if not self._state.adding:
                    raise
                if attempt >= max_attempts - 1:
                    raise
                self.lot_id = ''
                continue


class MonthlyReport(models.Model):
    """Monthly Report model (DB5) - For partners to report production for license fees"""
    
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('reviewed', 'Reviewed'),
        ('invoiced', 'Invoiced'),
    ]
    
    # Auto-generated ID
    report_id = models.AutoField(primary_key=True)
    
    # Partner who submitted (previously 'printer', made nullable for migration)
    partner = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.CASCADE,
        related_name='monthly_reports',
        null=True,
        blank=True
    )
    
    # Report period
    report_date = models.DateField(help_text='Date report was submitted')
    period_from = models.DateField(help_text='Reporting period start date')
    period_to = models.DateField(help_text='Reporting period end date')
    
    # Billing info
    billing_date = models.DateField()
    billing_document_reference = models.CharField(max_length=100, blank=True)
    
    # Customer info
    customer_name = models.CharField(max_length=255, help_text='Manufacturer/customer name')
    customer_po = models.CharField(max_length=100, blank=True, help_text='Customer PO number')
    
    # Production details
    lot_number = models.CharField(max_length=100, blank=True)
    material_number = models.CharField(max_length=100, blank=True)
    fabric_type = models.CharField(max_length=200, help_text='Fabric/substrate description')
    
    # MC Variant - links to approval
    mc_variant = models.ForeignKey(
        'core.CamouflageType',
        on_delete=models.PROTECT,
        related_name='monthly_reports'
    )
    
    # Production metrics
    yardage_produced = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text='Yardage produced'
    )
    cuttable_width = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Cuttable width in inches'
    )
    
    # Military/Government reference
    mpg_reference = models.CharField(max_length=100, blank=True, help_text='Military/Government reference')
    
    # Non-license fee printing flag
    non_license_fee_printing = models.BooleanField(
        default=False,
        help_text='Check if this is non-license fee printing'
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='submitted'
    )
    
    # Accounting fields (added by accounting staff)
    invoice_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text='Added by accounting after invoice generated'
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_reports'
    )
    reviewed_date = models.DateTimeField(null=True, blank=True)
    
    # Additional notes
    notes = models.TextField(blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-report_date', '-created_at']
        verbose_name = 'Monthly Report'
        verbose_name_plural = 'Monthly Reports'
        indexes = [
            models.Index(fields=['partner', 'report_date']),
            models.Index(fields=['status']),
            models.Index(fields=['period_from', 'period_to']),
        ]
    
    def __str__(self):
        return f"Report #{self.report_id} - {self.partner.company_name} - {self.period_from} to {self.period_to}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.period_to and self.period_from:
            if self.period_to < self.period_from:
                raise ValidationError('Period end date must be after start date')


# =============================================================================
# FA EVALUATION MODELS (New Shade Matching System)
# =============================================================================

class FAEvaluation(models.Model):
    """
    FA Evaluation record for a specific inspector stage and attempt.
    
    Each FA can have multiple evaluation attempts (after rejection + resubmission).
    Each attempt has two stages:
    1. Primary Inspector (1947) - first review
    2. Final Inspector (Crye) - final review (pre-loaded with primary's ratings)
    
    The evaluation includes:
    - Shade matching for all variant colors (3-7 depending on variant)
    - Pattern Execution (Pass/Fail)
    - Scale (Pass/Fail)
    - Spectral Reflectance (Pass/Fail, unless "Visible Spectrum Only")
    """
    
    fa = models.ForeignKey(
        FirstArticleInspection,
        on_delete=models.CASCADE,
        related_name='evaluations'
    )
    
    stage = models.CharField(
        max_length=10,
        choices=INSPECTOR_STAGE_CHOICES,
        help_text='Which inspection stage this evaluation is for'
    )
    
    # Track multiple evaluation attempts (for resubmissions after rejection)
    attempt_number = models.PositiveIntegerField(
        default=1,
        help_text='Evaluation attempt number (increments on resubmission)'
    )
    
    inspector = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='fa_evaluations'
    )
    
    evaluation_date = models.DateTimeField(auto_now_add=True)
    
    # Overall criteria (simple Pass/Fail per the original sheet)
    pattern_execution = models.CharField(
        max_length=10,
        choices=PASS_FAIL_CHOICES,
        blank=True,
        help_text='Pattern execution evaluation'
    )
    
    scale = models.CharField(
        max_length=10,
        choices=PASS_FAIL_CHOICES,
        blank=True,
        help_text='Scale evaluation'
    )
    
    spectral_reflectance = models.CharField(
        max_length=10,
        choices=PASS_FAIL_CHOICES,
        blank=True,
        help_text='Spectral reflectance evaluation (blank if Visible Spectrum Only)'
    )
    
    # Overall comments for this evaluation stage
    comments = models.TextField(
        blank=True,
        help_text='Overall comments for this evaluation'
    )
    
    # Is this evaluation complete/submitted?
    is_submitted = models.BooleanField(
        default=False,
        help_text='True when inspector has submitted this evaluation'
    )
    
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        # Allow multiple attempts per stage
        unique_together = ['fa', 'stage', 'attempt_number']
        ordering = ['fa', 'stage', '-attempt_number']
        verbose_name = 'FA Evaluation'
        verbose_name_plural = 'FA Evaluations'
    
    def __str__(self):
        return f"{self.fa.display_name} - {self.get_stage_display()}"
    
    @property
    def all_colors_pass(self):
        """Check if all color evaluations pass"""
        color_evals = self.color_evaluations.all()
        if not color_evals.exists():
            return False
        return all(eval.is_passing for eval in color_evals)
    
    @property
    def overall_criteria_pass(self):
        """Check if Pattern, Scale, Spectral all pass"""
        # Pattern and Scale must pass
        if self.pattern_execution != 'pass' or self.scale != 'pass':
            return False
        
        # Spectral must pass unless it's blank (Visible Spectrum Only)
        if self.spectral_reflectance and self.spectral_reflectance != 'pass':
            return False
        
        return True
    
    @property
    def all_pass(self):
        """Check if entire evaluation passes (all colors + all criteria)"""
        return self.all_colors_pass and self.overall_criteria_pass
    
    @property
    def result(self):
        """Returns 'pass' or 'fail' based on overall evaluation"""
        return 'pass' if self.all_pass else 'fail'
    
    def submit(self):
        """Mark evaluation as submitted and update FA status and inspector fields"""
        from django.utils import timezone

        if self.is_submitted:
            raise ValueError("This evaluation has already been submitted.")
        if not self.pk:
            raise ValueError("Cannot submit an unsaved evaluation.")
        if not self.inspector:
            raise ValueError("Cannot submit an evaluation without an inspector.")
        if not self.color_evaluations.exists():
            raise ValueError("Cannot submit an evaluation without color ratings.")

        # Atomic, state-checked transition. Prevents double-submit/back-button and tampering.
        with transaction.atomic():
            fa = FirstArticleInspection.objects.select_for_update().get(pk=self.fa.pk)

            if fa.status in ['approved', 'rejected']:
                raise ValueError("This First Article has already been completed and cannot be changed.")
            if self.stage == 'primary' and fa.status != 'pending':
                raise ValueError("Primary evaluation can only be submitted when FA is pending primary review.")
            if self.stage == 'final' and fa.status != 'pending_final':
                raise ValueError("Final evaluation can only be submitted when FA is pending final review.")

            # Mark evaluation submitted (audit)
            self.is_submitted = True
            self.submitted_at = timezone.now()
            self.save(update_fields=['is_submitted', 'submitted_at'])

            # Update FA inspector fields based on stage
            if self.stage == 'primary':
                fa.primary_inspector = self.inspector
                fa.primary_review_date = timezone.now().date()
                fa.primary_comments = self.comments
                fa.primary_pattern_execution = self.pattern_execution
                fa.primary_scale = self.scale
                fa.primary_spectral_reflectance = self.spectral_reflectance
            else:  # final stage
                fa.final_inspector = self.inspector
                fa.final_review_date = timezone.now().date()
                fa.final_comments = self.comments
                fa.final_pattern_execution = self.pattern_execution
                fa.final_scale = self.scale
                fa.final_spectral_reflectance = self.spectral_reflectance

            # Update FA status based on result
            if self.all_pass:
                fa.status = 'pending_final' if self.stage == 'primary' else 'approved'
            else:
                fa.status = 'rejected'

            fa.save()
            self.fa = fa


class FAColorEvaluation(models.Model):
    """
    Individual color evaluation within an FA evaluation.
    
    Each color gets:
    - A rating (0-5 scale with half-steps)
    - An optional comment
    - Auto-calculated result (Pass/Fail based on rating >= 3)
    """
    
    evaluation = models.ForeignKey(
        FAEvaluation,
        on_delete=models.CASCADE,
        related_name='color_evaluations'
    )
    
    color = models.ForeignKey(
        'core.VariantColor',
        on_delete=models.PROTECT,
        related_name='fa_evaluations'
    )
    
    rating = models.CharField(
        max_length=5,
        choices=SHADE_RATING_CHOICES,
        blank=True,
        help_text='Shade matching rating (>= 3 is Pass)'
    )
    
    comment = models.CharField(
        max_length=200,
        blank=True,
        help_text='Comment for this color evaluation'
    )
    
    class Meta:
        unique_together = ['evaluation', 'color']
        ordering = ['color__position']
        verbose_name = 'FA Color Evaluation'
        verbose_name_plural = 'FA Color Evaluations'
    
    def __str__(self):
        return f"{self.evaluation} - {self.color.color_name}: {self.rating}"
    
    @property
    def is_passing(self):
        """Check if this color evaluation passes (rating >= 3)"""
        if not self.rating:
            return False
        return is_passing_rating(self.rating)
    
    @property
    def result(self):
        """Returns 'pass' or 'fail' based on rating"""
        return 'pass' if self.is_passing else 'fail'


# =============================================================================
# LOT EVALUATION MODELS
# =============================================================================

def calculate_sample_count(yards_printed):
    """
    Calculate number of samples based on yards printed.
    
    From Google Sheets formula:
    - 0-800 yards: 2 samples
    - 801-22000 yards: 3 samples  
    - 22001+ yards: 5 samples
    """
    if yards_printed is None:
        return 2
    
    yards = int(yards_printed)
    if yards <= 800:
        return 2
    elif yards <= 22000:
        return 3
    else:
        return 5


class LotEvaluation(models.Model):
    """
    Overall evaluation for a Lot Acceptance submission.
    
    Unlike FA which has two stages (Primary -> Final), 
    Lots only have a single Primary Inspector review.
    """
    
    lot = models.ForeignKey(
        LotAcceptance,
        on_delete=models.CASCADE,
        related_name='evaluations'
    )
    
    inspector = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lot_evaluations'
    )
    
    evaluation_date = models.DateTimeField(auto_now_add=True)
    
    comments = models.TextField(
        blank=True,
        help_text='Overall evaluation comments'
    )
    
    is_submitted = models.BooleanField(
        default=False,
        help_text='Whether evaluation has been finalized'
    )
    
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['lot'], name='unique_lot_evaluation_per_lot'),
        ]
        ordering = ['-evaluation_date']
        verbose_name = 'Lot Evaluation'
        verbose_name_plural = 'Lot Evaluations'
    
    def __str__(self):
        return f"{self.lot.display_name} - Evaluation"
    
    @property
    def all_samples_pass(self):
        """Check if all sample evaluations pass"""
        sample_evals = self.sample_evaluations.all()
        if not sample_evals.exists():
            return False
        return all(sample.all_pass for sample in sample_evals)
    
    @property
    def all_pass(self):
        """Check if entire lot evaluation passes"""
        return self.all_samples_pass
    
    @property
    def result(self):
        """Returns 'pass' or 'fail' based on overall evaluation"""
        return 'pass' if self.all_pass else 'fail'
    
    def submit(self):
        """Mark evaluation as submitted and update Lot status"""
        from django.utils import timezone

        if self.is_submitted:
            raise ValueError("This lot evaluation has already been submitted.")
        if not self.pk:
            raise ValueError("Cannot submit an unsaved lot evaluation.")

        with transaction.atomic():
            lot = LotAcceptance.objects.select_for_update().get(pk=self.lot.pk)
            if lot.status in ['approved', 'rejected']:
                raise ValueError("This Lot has already been completed and cannot be changed.")
            if lot.status != 'pending':
                raise ValueError("Lot evaluation can only be submitted when Lot is pending review.")

            self.is_submitted = True
            self.submitted_at = timezone.now()
            self.save(update_fields=['is_submitted', 'submitted_at'])

            lot.status = 'approved' if self.all_pass else 'rejected'
            lot.inspector = self.inspector
            lot.review_date = timezone.now().date()
            lot.save()
            self.lot = lot


class LotSampleEvaluation(models.Model):
    """
    Evaluation for a single sample within a Lot.
    
    Each sample (e.g., "10010079014-1") has its own:
    - Color ratings (shade matching)
    - Pattern Execution (Pass/Fail)
    - Scale (Pass/Fail)
    - Spectral Reflectance (Pass/Fail)
    """
    
    lot_evaluation = models.ForeignKey(
        LotEvaluation,
        on_delete=models.CASCADE,
        related_name='sample_evaluations'
    )
    
    sample_number = models.PositiveIntegerField(
        help_text='Sample number (1, 2, 3, etc.)'
    )
    
    sample_id = models.CharField(
        max_length=100,
        help_text='Sample ID (e.g., "10010079014-1")'
    )
    
    pattern_execution = models.CharField(
        max_length=10,
        choices=PASS_FAIL_CHOICES,
        blank=True
    )
    
    scale = models.CharField(
        max_length=10,
        choices=PASS_FAIL_CHOICES,
        blank=True
    )
    
    spectral_reflectance = models.CharField(
        max_length=10,
        choices=PASS_FAIL_CHOICES,
        blank=True
    )
    
    comments = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['lot_evaluation', 'sample_number']
        ordering = ['sample_number']
        verbose_name = 'Lot Sample Evaluation'
        verbose_name_plural = 'Lot Sample Evaluations'
    
    def __str__(self):
        return f"{self.lot_evaluation.lot.display_name} - Sample {self.sample_number}"
    
    @property
    def all_colors_pass(self):
        """Check if all color evaluations pass for this sample"""
        color_evals = self.color_evaluations.all()
        if not color_evals.exists():
            return False
        return all(eval.is_passing for eval in color_evals)
    
    @property
    def overall_criteria_pass(self):
        """Check if Pattern, Scale, Spectral all pass"""
        if self.pattern_execution != 'pass' or self.scale != 'pass':
            return False
        if self.spectral_reflectance and self.spectral_reflectance != 'pass':
            return False
        return True
    
    @property
    def all_pass(self):
        """Check if entire sample evaluation passes"""
        return self.all_colors_pass and self.overall_criteria_pass
    
    @property
    def result(self):
        return 'pass' if self.all_pass else 'fail'


class LotSampleColorEvaluation(models.Model):
    """Individual color evaluation within a Lot sample."""
    
    sample_evaluation = models.ForeignKey(
        LotSampleEvaluation,
        on_delete=models.CASCADE,
        related_name='color_evaluations'
    )
    
    color = models.ForeignKey(
        'core.VariantColor',
        on_delete=models.PROTECT,
        related_name='lot_sample_evaluations'
    )
    
    rating = models.CharField(
        max_length=5,
        choices=SHADE_RATING_CHOICES,
        blank=True,
        help_text='Shade matching rating (>= 3 is Pass)'
    )
    
    comment = models.CharField(max_length=200, blank=True)
    
    class Meta:
        unique_together = ['sample_evaluation', 'color']
        ordering = ['color__position']
        verbose_name = 'Lot Sample Color Evaluation'
        verbose_name_plural = 'Lot Sample Color Evaluations'
    
    def __str__(self):
        return f"{self.sample_evaluation} - {self.color.color_name}: {self.rating}"
    
    @property
    def is_passing(self):
        if not self.rating:
            return False
        return is_passing_rating(self.rating)
    
    @property
    def result(self):
        return 'pass' if self.is_passing else 'fail'
