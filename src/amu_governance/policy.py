"""
Governance policy: the domain-specific configuration that parameterizes
the AMU model and retrieval systems.

A policy has two parts:

  sensitive_columns      -- column names that are sensitive regardless of
                             which table they appear in.
  department_permissions -- department (or role) -> set of columns that
                             department is permitted to see.

Keeping this separate from the AMU/Lineage/System classes is what lets the
same governance mechanism run against any schema (a synthetic benchmark,
TPC-H, Northwind, or a real production warehouse) without subclassing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set


@dataclass(frozen=True)
class GovernancePolicy:
    """Domain configuration for sensitivity tagging and department access."""

    sensitive_columns: Set[str] = field(default_factory=set)
    department_permissions: Dict[str, Set[str]] = field(default_factory=dict)

    def permitted_columns(self, department: str) -> Set[str]:
        """Columns a department is allowed to see. Unknown departments get
        the empty set (fail closed, not fail open)."""
        return self.department_permissions.get(department, set())

    def sensitivity_of(self, columns: Set[str]) -> Set[str]:
        """Intersect an arbitrary column set with the sensitive-column registry."""
        return columns & self.sensitive_columns
