"""
Core data model: LineageStep, Lineage, and the Analytical Memory Unit (AMU).

An AMU is a cached analytical result (a metric, a segment, a computed table)
tagged with its full derivation lineage. The lineage is what makes governance
possible: instead of gating retrieval on the *content* of a cached result
(its labels, its access tags), lineage-aware governance gates on *how the
result was derived* -- which tables and columns were touched to produce it.

This module is intentionally policy-agnostic: sensitivity tagging is computed
against a GovernancePolicy supplied by the caller, not against a hardcoded
global. See policy.py.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Set, Tuple

from .policy import GovernancePolicy


@dataclass(frozen=True)
class LineageStep:
    """One (table, columns) hop in a derivation path."""

    table: str
    columns_used: Tuple[str, ...]

    def sensitive_columns(self, policy: GovernancePolicy) -> Set[str]:
        return policy.sensitivity_of(set(self.columns_used))


@dataclass(frozen=True)
class Lineage:
    """The full derivation path for a cached result: every table/column hop
    plus the filter/aggregation logic that produced the final value."""

    steps: Tuple[LineageStep, ...]
    filter_logic: str  # human-readable filter/aggregation description

    def all_columns(self) -> Set[str]:
        cols: Set[str] = set()
        for step in self.steps:
            cols.update(step.columns_used)
        return cols

    def sensitive_columns(self, policy: GovernancePolicy) -> Set[str]:
        return policy.sensitivity_of(self.all_columns())

    def definition_hash(self) -> str:
        """Hash of (tables touched, columns touched, filter logic).

        Two AMUs with the same metric_name but different definition_hash
        were derived differently -- i.e. they disagree about what the metric
        *means*, even if the metric_name string matches. This is the basis
        for metric-definition conflict detection.
        """
        tables = tuple(sorted(step.table for step in self.steps))
        cols = tuple(sorted(self.all_columns()))
        payload = f"{tables}|{cols}|{self.filter_logic}"
        return hashlib.sha256(payload.encode()).hexdigest()[:12]


@dataclass
class AMU:
    """Analytical Memory Unit: a cached result plus its full lineage.

    sensitivity_tags and definition_hash are computed lazily from the
    lineage against whatever GovernancePolicy the caller passes in --
    the same AMU class works across domains without subclassing.
    """

    metric_name: str
    value: float
    owner_department: str
    lineage: Lineage
    epoch: int

    def sensitivity_tags(self, policy: GovernancePolicy) -> Set[str]:
        return self.lineage.sensitive_columns(policy)

    @property
    def definition_hash(self) -> str:
        return self.lineage.definition_hash()
