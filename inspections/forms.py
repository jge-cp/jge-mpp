from django import forms
from django.utils import timezone
from .models import (
    FirstArticleInspection, LotAcceptance, MonthlyReport,
    FAEvaluation, FAColorEvaluation,
    LotEvaluation, LotSampleEvaluation, LotSampleColorEvaluation,
    SHADE_RATING_CHOICES, PASS_FAIL_CHOICES, calculate_sample_count
)
from core.models import CamouflageType, VariantColor


# Form classes - applying form-input, form-select etc from input.css
FORM_INPUT = 'form-input'
FORM_SELECT = 'form-select'
FORM_TEXTAREA = 'form-textarea'
FORM_CHECKBOX = 'w-4 h-4 rounded'
FORM_FILE = 'form-input'


class FirstArticleInspectionForm(forms.ModelForm):
    """Form for submitting First Article Inspections"""
    
    class Meta:
        model = FirstArticleInspection
        fields = [
            'fabric_style',
            'multicam_variant',
            'shade_standard',
            'shade_standard_number',
            'spectral_reflectance_requirement',
            'fa_lot_number',
            'date_of_printing',
            'first_article_ship_date',
            'tracking_number',
            'is_bdcs',  # BDCS checkbox - if checked, skips primary review
        ]
        widgets = {
            'fabric_style': forms.TextInput(attrs={
                'class': FORM_INPUT,
                'placeholder': 'Enter fabric style'
            }),
            'multicam_variant': forms.Select(attrs={'class': FORM_SELECT}),
            'shade_standard': forms.Select(attrs={'class': FORM_SELECT}),
            'shade_standard_number': forms.TextInput(attrs={
                'class': FORM_INPUT,
                'placeholder': 'Optional'
            }),
            'spectral_reflectance_requirement': forms.Select(attrs={'class': FORM_SELECT}),
            'fa_lot_number': forms.TextInput(attrs={
                'class': FORM_INPUT,
                'placeholder': 'Enter FA lot number'
            }),
            'date_of_printing': forms.DateInput(attrs={
                'class': FORM_INPUT,
                'type': 'date'
            }),
            'first_article_ship_date': forms.DateInput(attrs={
                'class': FORM_INPUT,
                'type': 'date'
            }),
            'tracking_number': forms.TextInput(attrs={
                'class': FORM_INPUT,
                'placeholder': 'Optional tracking number'
            }),
            'is_bdcs': forms.CheckboxInput(attrs={
                'class': FORM_CHECKBOX,
            }),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Filter camouflage types to active ones
        self.fields['multicam_variant'].queryset = CamouflageType.objects.filter(status='active')


class LotAcceptanceForm(forms.ModelForm):
    """Form for submitting Lot Acceptances"""
    
    class Meta:
        model = LotAcceptance
        fields = [
            'original_fa',
            'lot_lot_number',
            'number_of_yards_printed',
            'date_of_printing',
            'date_shipped',
            'tracking_number',
        ]
        widgets = {
            'original_fa': forms.Select(attrs={
                'class': FORM_SELECT,
                'hx-get': '/portal/lot/fa-details/',
                'hx-target': '#fa-details'
            }),
            'lot_lot_number': forms.TextInput(attrs={
                'class': FORM_INPUT,
                'placeholder': 'Enter lot number'
            }),
            'number_of_yards_printed': forms.NumberInput(attrs={
                'class': FORM_INPUT,
                'min': '1',
                'placeholder': 'Enter yards printed',
                'x-model': 'yardsP printed',
                '@input': 'updateSampleCount()',
            }),
            'date_of_printing': forms.DateInput(attrs={
                'class': FORM_INPUT,
                'type': 'date'
            }),
            'date_shipped': forms.DateInput(attrs={
                'class': FORM_INPUT,
                'type': 'date'
            }),
            'tracking_number': forms.TextInput(attrs={
                'class': FORM_INPUT,
                'placeholder': 'Optional tracking number'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Only show approved FAs for this user's company (or legacy per-user)
        if user and hasattr(user, 'profile'):
            profile = user.profile
            if profile.company:
                # Company-based: show all approved FAs for the company
                approved_fas = FirstArticleInspection.objects.filter(
                    company=profile.company,
                    status='approved'
                ).order_by('-submission_date')
            else:
                # Legacy: show only this user's approved FAs
                approved_fas = FirstArticleInspection.objects.filter(
                    vendor=profile,
                    status='approved'
                ).order_by('-submission_date')
            self.fields['original_fa'].queryset = approved_fas
            if not approved_fas.exists():
                self.fields['original_fa'].help_text = (
                    'No approved First Article Inspections found. '
                    'Please submit and get approval for a First Article first.'
                )
        else:
            self.fields['original_fa'].queryset = FirstArticleInspection.objects.none()
            self.fields['original_fa'].help_text = 'Please log in to see approved First Article Inspections.'


class FAEvaluationForm(forms.ModelForm):
    """
    Form for evaluating a First Article.
    
    This form handles the overall criteria (Pattern, Scale, Spectral).
    Color evaluations are handled separately via FAColorEvaluationFormSet.
    """
    
    class Meta:
        model = FAEvaluation
        fields = [
            'pattern_execution',
            'scale',
            'spectral_reflectance',
            'comments',
        ]
        widgets = {
            'pattern_execution': forms.Select(
                choices=[('', '-- Select --')] + list(PASS_FAIL_CHOICES),
                attrs={'class': 'evaluation-select', 'data-criterion': 'pattern'}
            ),
            'scale': forms.Select(
                choices=[('', '-- Select --')] + list(PASS_FAIL_CHOICES),
                attrs={'class': 'evaluation-select', 'data-criterion': 'scale'}
            ),
            'spectral_reflectance': forms.Select(
                choices=[('', '-- Select --')] + list(PASS_FAIL_CHOICES),
                attrs={'class': 'evaluation-select', 'data-criterion': 'spectral'}
            ),
            'comments': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Overall evaluation comments'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.fa = kwargs.pop('fa', None)
        super().__init__(*args, **kwargs)
        
        # If FA has "Visible Spectrum Only", make spectral optional
        if self.fa and self.fa.spectral_reflectance_requirement == 'visible_only':
            self.fields['spectral_reflectance'].required = False
            self.fields['spectral_reflectance'].help_text = 'N/A - Visible Spectrum Only'


class FAColorEvaluationForm(forms.ModelForm):
    """Form for evaluating a single color within an FA evaluation"""
    
    class Meta:
        model = FAColorEvaluation
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(
                choices=[('', '-- Select Rating --')] + list(SHADE_RATING_CHOICES),
                attrs={'class': 'color-rating-select'}
            ),
            'comment': forms.TextInput(attrs={
                'placeholder': 'Comment (optional)',
                'class': 'color-comment-input'
            }),
        }


def create_color_evaluation_formset(fa, evaluation=None, data=None):
    """
    Create a formset for all colors in the FA's variant.
    
    Returns a list of (color, form) tuples for template rendering.
    """
    variant = fa.multicam_variant
    colors = variant.colors.all().order_by('position')
    
    forms_list = []
    
    for color in colors:
        # Get existing evaluation if any
        initial = {}
        instance = None
        
        if evaluation:
            try:
                instance = evaluation.color_evaluations.get(color=color)
            except FAColorEvaluation.DoesNotExist:
                pass
        
        prefix = f'color_{color.id}'
        
        if data:
            form = FAColorEvaluationForm(data, prefix=prefix, instance=instance)
        else:
            form = FAColorEvaluationForm(prefix=prefix, instance=instance)
        
        forms_list.append((color, form))
    
    return forms_list


# Legacy forms (kept for backwards compatibility during transition)
class FAPrimaryReviewForm(forms.ModelForm):
    """DEPRECATED: Use FAEvaluationForm instead"""
    
    class Meta:
        model = FirstArticleInspection
        fields = [
            'primary_pattern_execution',
            'primary_scale',
            'primary_spectral_reflectance',
            'primary_comments',
        ]
        widgets = {
            'primary_pattern_execution': forms.Select(attrs={}),
            'primary_scale': forms.Select(attrs={}),
            'primary_spectral_reflectance': forms.Select(attrs={}),
            'primary_comments': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Enter review comments or rejection reasons'
            }),
        }


class FAFinalReviewForm(forms.ModelForm):
    """DEPRECATED: Use FAEvaluationForm instead"""
    
    class Meta:
        model = FirstArticleInspection
        fields = [
            'final_pattern_execution',
            'final_scale',
            'final_spectral_reflectance',
            'final_comments',
        ]
        widgets = {
            'final_pattern_execution': forms.Select(attrs={}),
            'final_scale': forms.Select(attrs={}),
            'final_spectral_reflectance': forms.Select(attrs={}),
            'final_comments': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Enter review comments or rejection reasons'
            }),
        }


# Backwards compatibility alias
FAReviewForm = FAPrimaryReviewForm


class MonthlyReportForm(forms.ModelForm):
    """Form for partners to submit monthly production reports"""
    
    class Meta:
        model = MonthlyReport
        fields = [
            'period_from',
            'period_to',
            'billing_date',
            'billing_document_reference',
            'customer_name',
            'customer_po',
            'lot_number',
            'material_number',
            'fabric_type',
            'mc_variant',
            'yardage_produced',
            'cuttable_width',
            'mpg_reference',
            'non_license_fee_printing',
            'notes',
        ]
        widgets = {
            'period_from': forms.DateInput(attrs={
                'type': 'date'
            }),
            'period_to': forms.DateInput(attrs={
                'type': 'date'
            }),
            'billing_date': forms.DateInput(attrs={
                'type': 'date'
            }),
            'billing_document_reference': forms.TextInput(attrs={
                'placeholder': 'Optional billing document reference'
            }),
            'customer_name': forms.TextInput(attrs={
                'placeholder': 'Manufacturer/customer name'
            }),
            'customer_po': forms.TextInput(attrs={
                'placeholder': 'Customer PO number (optional)'
            }),
            'lot_number': forms.TextInput(attrs={
                'placeholder': 'Lot number (optional)'
            }),
            'material_number': forms.TextInput(attrs={
                'placeholder': 'Material number (optional)'
            }),
            'fabric_type': forms.TextInput(attrs={
                'placeholder': 'Fabric type/description'
            }),
            'mc_variant': forms.Select(attrs={}),
            'yardage_produced': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0',
                'placeholder': 'Total yardage produced'
            }),
            'cuttable_width': forms.NumberInput(attrs={
                'step': '0.01',
                'placeholder': 'Cuttable width (inches)'
            }),
            'mpg_reference': forms.TextInput(attrs={
                'placeholder': 'Military/Government reference (optional)'
            }),
            'non_license_fee_printing': forms.CheckboxInput(attrs={
                'class': FORM_CHECKBOX
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Additional notes (optional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Filter camouflage types to active ones
        self.fields['mc_variant'].queryset = CamouflageType.objects.filter(status='active')


class AccountingReviewForm(forms.ModelForm):
    """Form for accounting to review and add invoice reference"""
    
    class Meta:
        model = MonthlyReport
        fields = [
            'invoice_reference',
            'notes',
        ]
        widgets = {
            'invoice_reference': forms.TextInput(attrs={
                'placeholder': 'Invoice reference number'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Accounting notes'
            }),
        }


class LotReviewForm(forms.ModelForm):
    """DEPRECATED: Use LotEvaluationForm instead"""
    
    class Meta:
        model = LotAcceptance
        fields = [
            'inspector_comments',
        ]
        widgets = {
            'inspector_comments': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Enter review comments or rejection reasons'
            }),
        }


# =============================================================================
# LOT EVALUATION FORMS
# =============================================================================

class LotEvaluationForm(forms.ModelForm):
    """
    Form for overall Lot evaluation comments.
    Individual sample evaluations are handled by LotSampleEvaluationForm.
    """
    
    class Meta:
        model = LotEvaluation
        fields = ['comments']
        widgets = {
            'comments': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Overall lot evaluation comments'
            }),
        }


class LotSampleEvaluationForm(forms.ModelForm):
    """
    Form for evaluating a single sample within a Lot.
    
    Includes Pattern, Scale, Spectral (Pass/Fail).
    Color evaluations are handled separately.
    """
    
    class Meta:
        model = LotSampleEvaluation
        fields = ['pattern_execution', 'scale', 'spectral_reflectance', 'comments']
        widgets = {
            'pattern_execution': forms.Select(
                choices=[('', '-- Select --')] + list(PASS_FAIL_CHOICES),
                attrs={'class': 'evaluation-select'}
            ),
            'scale': forms.Select(
                choices=[('', '-- Select --')] + list(PASS_FAIL_CHOICES),
                attrs={'class': 'evaluation-select'}
            ),
            'spectral_reflectance': forms.Select(
                choices=[('', '-- Select --')] + list(PASS_FAIL_CHOICES),
                attrs={'class': 'evaluation-select'}
            ),
            'comments': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Sample comments (optional)'
            }),
        }


class LotSampleColorEvaluationForm(forms.ModelForm):
    """Form for evaluating a single color within a Lot sample"""
    
    class Meta:
        model = LotSampleColorEvaluation
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(
                choices=[('', '-- Select Rating --')] + list(SHADE_RATING_CHOICES),
                attrs={'class': 'color-rating-select'}
            ),
            'comment': forms.TextInput(attrs={
                'placeholder': 'Comment (optional)',
                'class': 'color-comment-input'
            }),
        }
