"""
Notifications / email service layer.

All email dispatch (password resets, diagnosis notifications, etc.)
must go through this module. The email provider (Resend, Brevo, etc.)
is swappable — keep the provider-specific call behind this single
service function so switching providers doesn't touch callers.

Email dispatch should be queued via the task queue (Celery / Django-RQ),
not sent inline in request handlers.
"""

from django.conf import settings


def send_email(
    to: str | list[str],
    subject: str,
    body_html: str,
    body_text: str | None = None,
    from_email: str | None = None,
) -> dict:
    """
    Send an email via the configured provider.

    Args:
        to: Recipient address or list of addresses.
        subject: Email subject line.
        body_html: HTML body content.
        body_text: Optional plain-text fallback body.
        from_email: Sender address (defaults to project-configured sender).

    Returns:
        A dict with provider-specific send metadata (e.g. message ID).

    Raises:
        NotImplementedError: Stub — not yet implemented.
    """
    raise NotImplementedError("Email sending is not yet implemented.")
