"""
Three retrieval systems, evaluated on the same workload:

A) NoMemorySystem      -- every request recomputed fresh by the requester's
                           own department. The status quo before any shared
                           memory. Structurally leak-free, but zero reuse and
                           zero cross-department conflict visibility.

B) NaiveMemorySystem    -- shared AMU store, retrieval keyed on metric_name
                           only. No lineage check at retrieval time. This is
                           representative of existing governed-memory systems
                           that gate on content/access tags rather than on
                           derivation.

C) LineageAwareSystem   -- shared AMU store, retrieval gated on lineage
                           (Algorithm 1): blocks a retrieval if the stored
                           AMU's derivation touches a column the requesting
                           department isn't permitted to see, and flags
                           metric-definition conflicts by comparing
                           definition_hash across AMUs sharing a metric_name.

All three share the same GovernancePolicy so they can be benchmarked
side by side on identical data and permissions.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional

from .model import AMU
from .policy import GovernancePolicy


@dataclass
class RetrievalResult:
    served: bool            # did the requester get an answer at all
    leaked: bool             # did the answer expose unauthorized columns
    reused: bool              # was it served from memory (vs. fresh compute)
    blocked: bool              # was a memory hit blocked by governance
    conflict_flagged: bool = False
    source_department: Optional[str] = None


class NoMemorySystem:
    """Baseline: no shared memory. Every request is recomputed fresh, in
    scope, by the requesting department."""

    name = "No Memory (status quo)"

    def __init__(self, policy: GovernancePolicy):
        self.policy = policy

    def write(self, amu: AMU) -> bool:
        return False  # nothing persists

    def request(self, metric_name: str, requester_department: str, fresh_amu: AMU) -> RetrievalResult:
        return RetrievalResult(served=True, leaked=False, reused=False, blocked=False,
                                source_department=fresh_amu.owner_department)


class NaiveMemorySystem:
    """Shared memory, retrieval keyed on metric_name only. No lineage check
    at retrieval time -- content/tag-based governance, not derivation-aware
    governance."""

    name = "Naive Shared Memory (content-gated)"

    def __init__(self, policy: GovernancePolicy):
        self.policy = policy
        self.store: Dict[str, List[AMU]] = defaultdict(list)

    def write(self, amu: AMU) -> bool:
        self.store[amu.metric_name].append(amu)
        return False

    def request(self, metric_name: str, requester_department: str, fresh_amu: AMU) -> RetrievalResult:
        candidates = self.store.get(metric_name, [])
        if not candidates:
            self.write(fresh_amu)
            return RetrievalResult(served=True, leaked=False, reused=False, blocked=False,
                                    source_department=fresh_amu.owner_department)

        amu = candidates[-1]  # most recent, naive "best match"
        permitted = self.policy.permitted_columns(requester_department)
        leaked = bool(amu.sensitivity_tags(self.policy) - permitted)
        return RetrievalResult(served=True, leaked=leaked, reused=True, blocked=False,
                                source_department=amu.owner_department)


class LineageAwareSystem:
    """Shared memory, retrieval gated on lineage (Algorithm 1). Blocks --
    falling back to fresh compute -- when the stored AMU's derivation
    touches a column outside the requester's permitted set. Also flags
    metric-definition conflicts by comparing definition_hash across AMUs
    sharing the same metric_name."""

    name = "Lineage-Aware Governed Memory"

    def __init__(self, policy: GovernancePolicy):
        self.policy = policy
        self.store: Dict[str, List[AMU]] = defaultdict(list)

    def write(self, amu: AMU) -> bool:
        """Write an AMU. Returns True if this surfaces a NEW conflict with
        an existing definition of the same metric (different lineage /
        definition_hash from a different owning department)."""
        existing = self.store.get(amu.metric_name, [])
        conflict = any(
            e.owner_department != amu.owner_department and e.definition_hash != amu.definition_hash
            for e in existing
        )
        self.store[amu.metric_name].append(amu)
        return conflict

    def request(self, metric_name: str, requester_department: str, fresh_amu: AMU) -> RetrievalResult:
        candidates = self.store.get(metric_name, [])
        permitted = self.policy.permitted_columns(requester_department)

        safe_candidate: Optional[AMU] = None
        any_blocked = False
        for amu in reversed(candidates):  # most recent first
            if amu.sensitivity_tags(self.policy) - permitted:
                any_blocked = True
                continue
            safe_candidate = amu
            break

        if safe_candidate is not None:
            return RetrievalResult(served=True, leaked=False, reused=True, blocked=False,
                                    source_department=safe_candidate.owner_department)

        # No safe candidate in memory -> fall back to fresh, in-scope compute.
        return RetrievalResult(served=True, leaked=False, reused=False, blocked=any_blocked,
                                source_department=fresh_amu.owner_department)
