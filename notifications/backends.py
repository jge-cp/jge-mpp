"""
Custom email backends for the Multicam Partner Portal.

Available backends:
1. ResendEmailBackend - Uses Resend HTTP API (default)
2. MicrosoftGraphBackend - Uses Microsoft 365 Graph API (recommended for corporate)

Usage:
    EMAIL_BACKEND='notifications.backends.ResendEmailBackend'  # Resend
    EMAIL_BACKEND='notifications.backends.MicrosoftGraphBackend'  # MS365
"""

import logging
import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

# Try to import resend, but don't fail if not installed
try:
    import resend
except ImportError:
    resend = None

# Try to import msal for Microsoft Graph
try:
    import msal
except ImportError:
    msal = None


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


class MicrosoftGraphBackend(BaseEmailBackend):
    """
    Email backend that sends emails using Microsoft Graph API.
    
    Sends emails from your Microsoft 365 account using the Graph API.
    Requires Azure AD app registration with Mail.Send permission.
    
    Environment variables needed:
        MS_GRAPH_TENANT_ID: Your Azure AD tenant ID
        MS_GRAPH_CLIENT_ID: App registration client ID  
        MS_GRAPH_CLIENT_SECRET: App registration client secret
        MS_GRAPH_SENDER_EMAIL: Email address to send from (must be in your M365 tenant)
    """
    
    GRAPH_API_URL = "https://graph.microsoft.com/v1.0"
    
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        
        if msal is None:
            raise ImportError(
                "The 'msal' library is required for Microsoft Graph backend. "
                "Install it with: pip install msal"
            )
        
        self.tenant_id = getattr(settings, 'MS_GRAPH_TENANT_ID', '')
        self.client_id = getattr(settings, 'MS_GRAPH_CLIENT_ID', '')
        self.client_secret = getattr(settings, 'MS_GRAPH_CLIENT_SECRET', '')
        self.sender_email = getattr(settings, 'MS_GRAPH_SENDER_EMAIL', '') or \
                           getattr(settings, 'DEFAULT_FROM_EMAIL', '')
        
        self._access_token = None
    
    def _get_access_token(self):
        """Get access token using client credentials flow."""
        if not all([self.tenant_id, self.client_id, self.client_secret]):
            raise ValueError(
                "Microsoft Graph credentials not configured. "
                "Set MS_GRAPH_TENANT_ID, MS_GRAPH_CLIENT_ID, and MS_GRAPH_CLIENT_SECRET"
            )
        
        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=authority,
            client_credential=self.client_secret,
        )
        
        # Get token for Microsoft Graph
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        
        if "access_token" in result:
            return result["access_token"]
        else:
            error = result.get("error_description", result.get("error", "Unknown error"))
            raise Exception(f"Failed to acquire token: {error}")
    
    def _build_message_payload(self, message):
        """Convert Django EmailMessage to Graph API payload."""
        # Build recipient lists
        to_recipients = [{"emailAddress": {"address": email}} for email in message.to]
        cc_recipients = [{"emailAddress": {"address": email}} for email in (message.cc or [])]
        bcc_recipients = [{"emailAddress": {"address": email}} for email in (message.bcc or [])]
        
        payload = {
            "message": {
                "subject": message.subject,
                "body": {
                    "contentType": "Text",
                    "content": message.body or ""
                },
                "toRecipients": to_recipients,
            },
            "saveToSentItems": "true"
        }
        
        # Add HTML body if present
        if hasattr(message, 'alternatives') and message.alternatives:
            for content, mimetype in message.alternatives:
                if mimetype == 'text/html':
                    payload["message"]["body"] = {
                        "contentType": "HTML",
                        "content": content
                    }
                    break
        
        # Add CC recipients
        if cc_recipients:
            payload["message"]["ccRecipients"] = cc_recipients
        
        # Add BCC recipients
        if bcc_recipients:
            payload["message"]["bccRecipients"] = bcc_recipients
        
        # Add reply-to if present
        if message.reply_to:
            payload["message"]["replyTo"] = [
                {"emailAddress": {"address": message.reply_to[0]}}
            ]
        
        return payload
    
    def send_messages(self, email_messages):
        """Send one or more EmailMessage objects via Microsoft Graph."""
        if not email_messages:
            return 0
        
        try:
            access_token = self._get_access_token()
        except Exception as e:
            logger.error(f"Failed to get Microsoft Graph access token: {e}")
            if not self.fail_silently:
                raise
            return 0
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Extract sender email (remove display name if present)
        sender = self.sender_email
        if '<' in sender:
            sender = sender.split('<')[1].rstrip('>')
        
        send_url = f"{self.GRAPH_API_URL}/users/{sender}/sendMail"
        
        sent_count = 0
        for message in email_messages:
            try:
                payload = self._build_message_payload(message)
                
                response = requests.post(
                    send_url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 202:
                    logger.info(f"Email sent via Microsoft Graph to {message.to}")
                    sent_count += 1
                else:
                    error_detail = response.json() if response.text else response.status_code
                    logger.error(f"Microsoft Graph API error: {error_detail}")
                    if not self.fail_silently:
                        raise Exception(f"Graph API error: {error_detail}")
                        
            except requests.RequestException as e:
                logger.error(f"Failed to send email via Microsoft Graph to {message.to}: {e}")
                if not self.fail_silently:
                    raise
        
        return sent_count
