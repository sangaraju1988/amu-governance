"""
amu-governance: lineage-gated shared memory for multi-agent analytics.

An Analytical Memory Unit (AMU) is a cached analytical result tagged with
its full derivation lineage. Retrieval is gated on *how* a result was
derived, not on static content/access labels, which closes two failure
modes of naive shared agent memory: cross-department column leakage and
silent metric-definition conflicts.

Quick start
-----------
    from amu_governance import AMU, Lineage, LineageStep, GovernancePolicy
    from amu_governance import LineageAwareSystem

    policy = GovernancePolicy(
        sensitive_columns={"income", "ssn"},
        department_permissions={
            "Finance": {"income", "ssn", "customer_id"},
            "Marketing": {"customer_id"},
        },
    )
    memory = LineageAwareSystem(policy)

See the README and examples/ for a full walkthrough, and
amu_governance.sql_lineage for automatic lineage extraction from executed
SQL (no agent self-reporting required).
"""

from .model import AMU, Lineage, LineageStep
from .policy import GovernancePolicy
from .systems import LineageAwareSystem, NaiveMemorySystem, NoMemorySystem, RetrievalResult

__version__ = "0.1.1"

__all__ = [
    "AMU",
    "Lineage",
    "LineageStep",
    "GovernancePolicy",
    "LineageAwareSystem",
    "NaiveMemorySystem",
    "NoMemorySystem",
    "RetrievalResult",
]
