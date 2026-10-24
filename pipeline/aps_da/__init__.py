"""Kleine client voor Autodesk Platform Services Design Automation v3 (AutoCAD).

Alleen velden en endpoints die in officiële Autodesk-bronnen staan; zie ../BRONNEN.md.
"""

from .client import (
    AUTH_URL,
    FAILED_STATUSES,
    ApsClient,
    ApsError,
    WorkItemTimeout,
    qualified_id,
    rcs_activity_spec,
)

__all__ = [
    "AUTH_URL",
    "FAILED_STATUSES",
    "ApsClient",
    "ApsError",
    "WorkItemTimeout",
    "qualified_id",
    "rcs_activity_spec",
]
