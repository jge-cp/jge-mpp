from django.db import models
from django.contrib.auth.models import User


class CamouflageApproval(models.Model):
    """Links printers with approved camouflage types (DB3)"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
    ]
    
    printer = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.CASCADE,
        related_name='camouflage_approvals'
    )
    camouflage_type = models.ForeignKey(
        'core.CamouflageType',
        on_delete=models.PROTECT,
        related_name='approvals'
    )
    approval_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    supporting_documents = models.ManyToManyField(
        'core.FileUpload',
        related_name='approval_documents',
        blank=True
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='approved_camouflages'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Camouflage Approval'
        verbose_name_plural = 'Camouflage Approvals'
        unique_together = [['printer', 'camouflage_type']]
        indexes = [
            models.Index(fields=['printer', 'status']),
            models.Index(fields=['camouflage_type']),
        ]
    
    def __str__(self):
        return f"{self.printer.company_name} - {self.camouflage_type.camouflage_name}"
