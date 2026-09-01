"""Tamper-evident audit logging."""

from rci.audit.bridge import EventAuditBridge
from rci.audit.hash_chain import AuditIntegrityError, verify_chain
from rci.audit.logger import AuditLogger, AuditStorageError
from rci.audit.models import AuditEntry
from rci.audit.query import AuditQuery, query_entries

__all__ = [
    "AuditEntry",
    "AuditIntegrityError",
    "AuditLogger",
    "AuditQuery",
    "AuditStorageError",
    "EventAuditBridge",
    "query_entries",
    "verify_chain",
]
