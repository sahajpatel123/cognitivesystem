"""
Governance module for tenant capability management.
"""

from .tenant import (
    TenantConfig,
    RequestHints,
    ResolvedTenantCaps,
    resolve_tenant_caps,
)

__all__ = [
    "TenantConfig",
    "RequestHints", 
    "ResolvedTenantCaps",
    "resolve_tenant_caps",
]
