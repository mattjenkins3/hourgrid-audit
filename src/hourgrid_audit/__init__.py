"""Hourgrid Audit: deterministic timestamp contract checks for energy CSVs."""
from .core import AuditInputError, audit_csv

__all__ = ["AuditInputError", "audit_csv"]
__version__ = "0.1.0"
