from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db import IntegrityError
from .models import UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create UserProfile when User is created"""
    if created:
        # Check if profile already exists (shouldn't happen, but be safe)
        if hasattr(instance, 'profile'):
            return
        
        try:
            # Use User's email if available, otherwise create placeholder
            base_email = instance.email or f"{instance.username}@example.com"
            
            # Check if this email already exists
            if UserProfile.objects.filter(technical_email=base_email).exists():
                # Generate unique variant
                counter = 1
                if '@' in base_email:
                    local, domain = base_email.rsplit('@', 1)
                    unique_email = f"{local}+{counter}@{domain}"
                else:
                    unique_email = f"{base_email}+{counter}"
                
                while UserProfile.objects.filter(technical_email=unique_email).exists():
                    counter += 1
                    if '@' in base_email:
                        local, domain = base_email.rsplit('@', 1)
                        unique_email = f"{local}+{counter}@{domain}"
                    else:
                        unique_email = f"{base_email}+{counter}"
                
                technical_email = unique_email
            else:
                technical_email = base_email
            
            # Create the profile - save() will auto-set default permissions
            UserProfile.objects.get_or_create(
                user=instance,
                defaults={
                    'company_name': instance.email.split('@')[0] if '@' in instance.email else instance.username,
                    'technical_email': technical_email,
                    'user_functionality': 'admin' if instance.is_staff else 'partner',
                }
            )
            # Note: set_default_permissions() is called automatically in UserProfile.save()
        except Exception as e:
            # Silently fail - don't break user creation or popup
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to create UserProfile for user {instance.username}: {e}")


@receiver(post_save, sender=UserProfile)
def sync_technical_email_to_user(sender, instance, created, **kwargs):
    """Sync technical_email to User.email when UserProfile is saved"""
    if instance.technical_email and instance.user.email != instance.technical_email:
        instance.user.email = instance.technical_email
        instance.user.save(update_fields=['email'])

