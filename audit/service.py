"""
Audit logging service layer.

All sensitive actions (login, signup, logout, patient record changes,
diagnosis creation, employee account changes) must be logged through
this module. Views and business logic should call log_action() rather
than importing the AuditLog model directly.
"""

from audit.models import AuditLog


def log_action(user, action: str, target_object: str = "", metadata: dict | None = None) -> AuditLog:
    """
    Create an audit log entry for a sensitive action.

    Args:
        user: The Django user performing the action (or None for system actions).
        action: Short action identifier, e.g. "user_login", "patient_created".
        target_object: String representation of the affected object, e.g. "User:42".
        metadata: Optional dict of extra context (IP address, changed fields, etc.).

    Returns:
        The created AuditLog instance.
    """
    return AuditLog.objects.create(
        user=user,
        action=action,
        target_object=target_object,
        metadata=metadata or {},
    )
