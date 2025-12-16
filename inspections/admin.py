from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import (
    FirstArticleInspection, LotAcceptance, 
    FAEvaluation, FAColorEvaluation,
    LotEvaluation, LotSampleEvaluation, LotSampleColorEvaluation
)


class FAColorEvaluationInline(TabularInline):
    """Inline for editing color evaluations within FAEvaluation"""
    model = FAColorEvaluation
    extra = 0
    ordering = ['color__position']
    readonly_fields = ['result']
    
    def result(self, obj):
        if obj.rating:
            return '✓ Pass' if obj.is_passing else '✗ Fail'
        return '-'
    result.short_description = 'Result'


@admin.register(FAEvaluation)
class FAEvaluationAdmin(ModelAdmin):
    list_display = ['fa', 'stage', 'inspector', 'is_submitted', 'overall_result', 'evaluation_date']
    list_filter = ['stage', 'is_submitted', 'evaluation_date']
    search_fields = ['fa__fai_id', 'fa__fabric_style', 'inspector__username']
    readonly_fields = ['evaluation_date', 'submitted_at', 'all_colors_pass', 'overall_criteria_pass', 'all_pass']
    inlines = [FAColorEvaluationInline]
    
    def overall_result(self, obj):
        if not obj.is_submitted:
            return 'Not submitted'
        return '✓ Pass' if obj.all_pass else '✗ Fail'
    overall_result.short_description = 'Result'
    
    fieldsets = (
        ('FA Information', {
            'fields': ('fa', 'stage', 'inspector')
        }),
        ('Overall Criteria', {
            'fields': ('pattern_execution', 'scale', 'spectral_reflectance')
        }),
        ('Comments', {
            'fields': ('comments',)
        }),
        ('Submission Status', {
            'fields': ('is_submitted', 'submitted_at', 'evaluation_date')
        }),
        ('Results (Auto-calculated)', {
            'fields': ('all_colors_pass', 'overall_criteria_pass', 'all_pass'),
            'classes': ('collapse',)
        }),
    )


@admin.register(FAColorEvaluation)
class FAColorEvaluationAdmin(ModelAdmin):
    list_display = ['evaluation', 'color', 'rating', 'result_display', 'comment']
    list_filter = ['evaluation__stage', 'color__camouflage_type']
    search_fields = ['evaluation__fa__fai_id', 'color__color_name']
    
    def result_display(self, obj):
        if obj.rating:
            return '✓ Pass' if obj.is_passing else '✗ Fail'
        return '-'
    result_display.short_description = 'Result'


@admin.register(FirstArticleInspection)
class FirstArticleInspectionAdmin(ModelAdmin):
    list_display = ['fai_id', 'vendor', 'fabric_style', 'multicam_variant', 'status', 'is_historic', 'submission_date']
    list_filter = ['status', 'multicam_variant', 'is_historic', 'submission_date']
    search_fields = ['fai_id', 'fabric_style', 'fa_lot_number', 'vendor__company_name']
    readonly_fields = ['fai_id', 'fsid', 'submission_date', 'sheet_name_generated', 'created_at', 'updated_at']
    date_hierarchy = 'submission_date'
    
    fieldsets = (
        ('Identification', {
            'fields': ('fai_id', 'fsid', 'vendor', 'status', 'is_historic')
        }),
        ('Submission Details', {
            'fields': ('fabric_style', 'multicam_variant', 'shade_standard', 
                      'shade_standard_number', 'spectral_reflectance_requirement',
                      'fa_lot_number', 'date_of_printing')
        }),
        ('Shipping Information', {
            'fields': ('first_article_ship_date', 'tracking_number', 
                      'name_of_printer_representative'),
            'classes': ('collapse',)
        }),
        ('Submission', {
            'fields': ('submitted', 'submission_date', 'sheet_name_generated')
        }),
        ('Primary Inspector Evaluation (Stage 1)', {
            'fields': ('primary_inspector', 'primary_review_date', 'primary_pattern_execution', 
                      'primary_scale', 'primary_spectral_reflectance', 'primary_comments')
        }),
        ('Final Inspector Evaluation (Stage 2)', {
            'fields': ('final_inspector', 'final_review_date', 'final_pattern_execution', 
                      'final_scale', 'final_spectral_reflectance', 'final_comments')
        }),
        ('Documents', {
            'fields': ('submission_documents', 'inspection_documents'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LotAcceptance)
class LotAcceptanceAdmin(ModelAdmin):
    list_display = ['lot_id', 'vendor', 'fabric_style', 'original_fa', 'status', 'submission_date']
    list_filter = ['status', 'evaluation_type', 'submission_date']
    search_fields = ['lot_id', 'fabric_style', 'lot_lot_number', 'vendor__company_name']
    readonly_fields = ['lot_id', 'fsid', 'submission_date', 'sheet_name_generated', 'created_at', 'updated_at']
    date_hierarchy = 'submission_date'
    
    fieldsets = (
        ('Identification', {
            'fields': ('lot_id', 'fsid', 'vendor', 'status', 'original_fa')
        }),
        ('Lot Details', {
            'fields': ('fabric_style', 'shade_standard', 'shade_standard_number',
                      'spectral_reflectance_requirement', 'original_fa_lot_number',
                      'lot_lot_number', 'number_of_yards_printed')
        }),
        ('Samples', {
            'fields': ('number_of_samples', 'individual_sample_numbers', 'evaluation_type')
        }),
        ('Dates & Shipping', {
            'fields': ('date_of_printing', 'date_shipped', 'tracking_number', 
                      'name_of_submitter'),
            'classes': ('collapse',)
        }),
        ('Submission', {
            'fields': ('submitted', 'submission_date', 'sheet_name_generated')
        }),
        ('Evaluation', {
            'fields': ('inspector', 'review_date', 'pattern_execution', 
                      'scale', 'spectral_reflectance', 'evaluation_scores', 
                      'inspector_comments')
        }),
        ('Documents', {
            'fields': ('submission_documents', 'inspection_documents'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# =============================================================================
# LOT EVALUATION ADMIN
# =============================================================================

class LotSampleColorEvaluationInline(TabularInline):
    """Inline for editing color evaluations within LotSampleEvaluation"""
    model = LotSampleColorEvaluation
    extra = 0
    ordering = ['color__position']
    readonly_fields = ['result']
    
    def result(self, obj):
        if obj.rating:
            return '✓ Pass' if obj.is_passing else '✗ Fail'
        return '-'
    result.short_description = 'Result'


class LotSampleEvaluationInline(TabularInline):
    """Inline for editing sample evaluations within LotEvaluation"""
    model = LotSampleEvaluation
    extra = 0
    ordering = ['sample_number']
    readonly_fields = ['sample_result']
    fields = ['sample_number', 'sample_id', 'pattern_execution', 'scale', 
              'spectral_reflectance', 'sample_result']
    
    def sample_result(self, obj):
        if obj.pattern_execution and obj.scale:
            return '✓ Pass' if obj.all_pass else '✗ Fail'
        return 'Incomplete'
    sample_result.short_description = 'Result'


@admin.register(LotEvaluation)
class LotEvaluationAdmin(ModelAdmin):
    list_display = ['lot', 'inspector', 'is_submitted', 'overall_result', 'evaluation_date']
    list_filter = ['is_submitted', 'evaluation_date']
    search_fields = ['lot__lot_id', 'lot__fabric_style', 'inspector__username']
    readonly_fields = ['evaluation_date', 'submitted_at', 'all_samples_pass', 'all_pass']
    inlines = [LotSampleEvaluationInline]
    
    def overall_result(self, obj):
        if not obj.is_submitted:
            return 'Not submitted'
        return '✓ Pass' if obj.all_pass else '✗ Fail'
    overall_result.short_description = 'Result'
    
    fieldsets = (
        ('Lot Information', {
            'fields': ('lot', 'inspector')
        }),
        ('Comments', {
            'fields': ('comments',)
        }),
        ('Submission Status', {
            'fields': ('is_submitted', 'submitted_at', 'evaluation_date')
        }),
        ('Results (Auto-calculated)', {
            'fields': ('all_samples_pass', 'all_pass'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LotSampleEvaluation)
class LotSampleEvaluationAdmin(ModelAdmin):
    list_display = ['sample_id', 'lot_evaluation', 'sample_number', 'overall_result']
    list_filter = ['lot_evaluation__lot__status']
    search_fields = ['sample_id', 'lot_evaluation__lot__lot_id']
    inlines = [LotSampleColorEvaluationInline]
    
    def overall_result(self, obj):
        if obj.pattern_execution and obj.scale:
            return '✓ Pass' if obj.all_pass else '✗ Fail'
        return 'Incomplete'
    overall_result.short_description = 'Result'
    
    fieldsets = (
        ('Sample Information', {
            'fields': ('lot_evaluation', 'sample_number', 'sample_id')
        }),
        ('Overall Criteria', {
            'fields': ('pattern_execution', 'scale', 'spectral_reflectance')
        }),
        ('Comments', {
            'fields': ('comments',)
        }),
    )


@admin.register(LotSampleColorEvaluation)
class LotSampleColorEvaluationAdmin(ModelAdmin):
    list_display = ['sample_evaluation', 'color', 'rating', 'result_display', 'comment']
    list_filter = ['color__camouflage_type']
    search_fields = ['sample_evaluation__sample_id', 'color__color_name']
    
    def result_display(self, obj):
        if obj.rating:
            return '✓ Pass' if obj.is_passing else '✗ Fail'
        return '-'
    result_display.short_description = 'Result'
