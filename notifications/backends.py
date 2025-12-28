"""
Custom email backend using Resend HTTP API.

This backend uses Resend's HTTP API instead of SMTP, which is more reliable
in containerized environments (Railway) where SMTP ports may be blocked.

Usage:
    Set EMAIL_BACKEND='notifications.backends.ResendEmailBackend' in settings
    Set RESEND_API_KEY to your Resend API key (can reuse EMAIL_HOST_PASSWORD)
"""

import logging
import resend
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    """
    Email backend that sends emails using Resend's HTTP API.
    
    Much more reliable than SMTP in containerized environments where
    ports 587/465 may be blocked or connections may timeout.
    """
    
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        # Use RESEND_API_KEY if set, otherwise fall back to EMAIL_HOST_PASSWORD
        resend.api_key = getattr(settings, 'RESEND_API_KEY', None) or \
                         getattr(settings, 'EMAIL_HOST_PASSWORD', '')
    
    def send_messages(self, email_messages):
        """
        Send one or more EmailMessage objects and return the number of email
        messages sent.
        """
        if not email_messages:
            return 0
        
        sent_count = 0
        for message in email_messages:
            try:
                # Build the email payload
                email_payload = {
                    "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
                    "to": list(message.to),
                    "subject": message.subject,
                }
                
                # Add text body
                if message.body:
                    email_payload["text"] = message.body
                
                # Add HTML body if present (for EmailMultiAlternatives)
                if hasattr(message, 'alternatives') and message.alternatives:
                    for content, mimetype in message.alternatives:
                        if mimetype == 'text/html':
                            email_payload["html"] = content
                            break
                
                # Add CC if present
                if message.cc:
                    email_payload["cc"] = list(message.cc)
                
                # Add BCC if present
                if message.bcc:
                    email_payload["bcc"] = list(message.bcc)
                
                # Add reply-to if present
                if message.reply_to:
                    email_payload["reply_to"] = message.reply_to[0] if message.reply_to else None
                
                # Send via Resend HTTP API
                response = resend.Emails.send(email_payload)
                
                logger.info(f"Email sent via Resend to {message.to}: {response.get('id', 'unknown')}")
                sent_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send email via Resend to {message.to}: {e}")
                if not self.fail_silently:
                    raise
        
        return sent_count

