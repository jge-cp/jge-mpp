"""
Custom model managers for inspections app.

These managers encapsulate access control and common filtering patterns,
making querysets cleaner and more secure by default.

Usage:
    # Get all FAs visible to a user
    fas = FirstArticleInspection.objects.for_user(profile)
    
    # Get pending FAs for primary inspector queue
    pending = FirstArticleInspection.objects.pending()
    
    # Chain methods
    fas = FirstArticleInspection.objects.for_user(profile).pending()
"""
from django.db import models
from django.db.models import Q


class FAQuerySet(models.QuerySet):
    """Custom queryset for FirstArticleInspection with chainable filters."""
    
    def for_user(self, profile):
        """
        Filter FAs based on user's access level.
        
        Partners only see FAs belonging to their company.
        Inspectors and staff see all FAs.
        
        Args:
            profile: UserProfile instance
            
        Returns:
            Filtered queryset
        """
        if profile.is_partner():
            if profile.company:
                return self.filter(company=profile.company)
            else:
                # Legacy fallback for partners without company FK
                return self.filter(vendor=profile)
        # Inspectors and staff see all
        return self
    
    def pending(self):
        """FAs awaiting primary inspector review."""
        return self.filter(status='pending')
    
    def pending_final(self):
        """FAs awaiting final inspector review."""
        return self.filter(status='pending_final')
    
    def pending_any(self):
        """FAs awaiting any review (pending or pending_final)."""
        return self.filter(Q(status='pending') | Q(status='pending_final'))
    
    def approved(self):
        """Approved FAs."""
        return self.filter(status='approved')
    
    def rejected(self):
        """Rejected FAs."""
        return self.filter(status='rejected')
    
    def with_related(self):
        """Optimized queryset with common related objects."""
        return self.select_related(
            'vendor',
            'vendor__user',
            'vendor__company',
            'company',
            'multicam_variant',
        )


class FAManager(models.Manager):
    """Custom manager for FirstArticleInspection."""
    
    def get_queryset(self):
        return FAQuerySet(self.model, using=self._db)
    
    def for_user(self, profile):
        return self.get_queryset().for_user(profile)
    
    def pending(self):
        return self.get_queryset().pending()
    
    def pending_final(self):
        return self.get_queryset().pending_final()
    
    def pending_any(self):
        return self.get_queryset().pending_any()
    
    def approved(self):
        return self.get_queryset().approved()
    
    def rejected(self):
        return self.get_queryset().rejected()
    
    def with_related(self):
        return self.get_queryset().with_related()


class LotQuerySet(models.QuerySet):
    """Custom queryset for LotAcceptance with chainable filters."""
    
    def for_user(self, profile):
        """
        Filter Lots based on user's access level.
        
        Partners only see Lots belonging to their company.
        Inspectors and staff see all Lots.
        
        Args:
            profile: UserProfile instance
            
        Returns:
            Filtered queryset
        """
        if profile.is_partner():
            if profile.company:
                return self.filter(company=profile.company)
            else:
                # Legacy fallback for partners without company FK
                return self.filter(vendor=profile)
        # Inspectors and staff see all
        return self
    
    def pending(self):
        """Lots awaiting review."""
        return self.filter(status='pending')
    
    def approved(self):
        """Approved Lots."""
        return self.filter(status='approved')
    
    def rejected(self):
        """Rejected Lots."""
        return self.filter(status='rejected')
    
    def with_related(self):
        """Optimized queryset with common related objects."""
        return self.select_related(
            'vendor',
            'vendor__user',
            'vendor__company',
            'company',
            'original_fa',
            'original_fa__multicam_variant',
        )


class LotManager(models.Manager):
    """Custom manager for LotAcceptance."""
    
    def get_queryset(self):
        return LotQuerySet(self.model, using=self._db)
    
    def for_user(self, profile):
        return self.get_queryset().for_user(profile)
    
    def pending(self):
        return self.get_queryset().pending()
    
    def approved(self):
        return self.get_queryset().approved()
    
    def rejected(self):
        return self.get_queryset().rejected()
    
    def with_related(self):
        return self.get_queryset().with_related()

