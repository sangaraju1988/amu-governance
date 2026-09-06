# amu-governance

[![DOI](https://zenodo.org/badge/1280474791.svg)](https://doi.org/10.5281/zenodo.21302744) [![Paper](https://img.shields.io/badge/IEEE%20Access-10.1109%2FACCESS.2026.3730363-00629B)](https://doi.org/10.1109/ACCESS.2026.3730363) [![PyPI](https://img.shields.io/pypi/v/amu-governance.svg)](https://pypi.org/project/amu-governance/)

**Lineage-gated shared memory for multi-agent analytics.**

Shared memory across AI agents improves efficiency but introduces two
failure modes: an agent can retrieve an insight derived from columns it
isn't permitted to see (column-level leakage), and two teams can compute
the same KPI through divergent derivation paths with the wrong definition
propagating silently (metric-definition conflict).

`amu-governance` implements the **Analytical Memory Unit (AMU)** — a cached
result tagged with its full derivation lineage — and a **lineage-gated
retrieval** policy that blocks unsafe reuse and flags definition conflicts,
instead of gating on static content/access labels the way existing governed
shared-memory systems do.

This is the reference implementation accompanying the paper *"Lineage-Aware
Memory Governance: A Derivation-Gated Framework for Privacy-Preserving
Column-Level Access Control in Enterprise AI Agents"* (Sangaraju & Vissa),
published in [IEEE Access](https://doi.org/10.1109/ACCESS.2026.3730363)
(Early Access, open access). The paper's full experiment/benchmark suite
lives in a separate research repository:
https://github.com/sangaraju1988/Lineage-Aware-Memory. This repository
contains only the reusable software.

## Install

```bash
pip install amu-governance
```

Requires Python 3.9+ and [sqlglot](https://github.com/tobymao/sqlglot)
(installed automatically) for the optional SQL lineage extractor.

To work from a local clone instead (e.g. to run the tests or modify the
source):

```bash
pip install -e .
```

## Quick start

```python
from amu_governance import AMU, GovernancePolicy, Lineage, LineageStep, LineageAwareSystem

policy = GovernancePolicy(
    sensitive_columns={"income", "ssn"},
    department_permissions={
        "Finance":   {"customer_id", "income", "ssn", "region"},
        "Marketing": {"customer_id", "region"},   # no income, no ssn
    },
)
memory = LineageAwareSystem(policy)

lineage = Lineage(
    steps=(LineageStep("customers", ("customer_id", "income")),),
    filter_logic="income > 100000",
)
amu = AMU("high_value_segment", value=42.0, owner_department="Finance",
          lineage=lineage, epoch=0)
memory.write(amu)

result = memory.request("high_value_segment", requester_department="Marketing",
                         fresh_amu=amu)
# result.blocked  -> True   (income is not in Marketing's permitted columns)
# result.leaked   -> False  (blocked, never served)
```

See `examples/agent_demo/demo.py` for a full walkthrough against a real
SQLite database, and `examples/sql_lineage_demo.py` for automatic lineage
extraction from executed SQL (no agent self-reporting required).

## How it works

- **`GovernancePolicy`** — the only domain-specific configuration: which
  columns are sensitive, and which departments/roles may see which columns.
  The same `AMU`/`Lineage`/system classes work for any schema by swapping
  the policy — no subclassing required.
- **`Lineage` / `LineageStep`** — the derivation path of a cached result:
  every (table, columns) hop plus the filter/aggregation logic. Sensitivity
  tags and a `definition_hash` (SHA-256 over tables + columns + filter
  logic) are computed from this path.
- **`LineageAwareSystem`** — the governance mechanism (Algorithm 1 in the
  paper): on retrieval, walk cached AMUs for a metric most-recent-first and
  serve the first one whose sensitivity tags are a subset of the requester's
  permitted columns; if none qualify, fall back to fresh, in-scope compute.
  On write, flag a conflict if a different department already wrote a
  different `definition_hash` for the same metric name.
- **`sql_lineage.extract_lineage_from_sql`** — parses executed SQL with
  `sqlglot` and returns the tables/columns actually touched, so lineage
  doesn't depend on an agent accurately self-reporting what it accessed.

Two other systems are included for comparison/benchmarking:
`NoMemorySystem` (no sharing — the pre-shared-memory status quo) and
`NaiveMemorySystem` (shared memory keyed on metric name only, representative
of existing content/tag-gated governed-memory systems).

## Repository structure

```
src/amu_governance/
  model.py        AMU, Lineage, LineageStep
  policy.py        GovernancePolicy
  systems.py         NoMemorySystem, NaiveMemorySystem, LineageAwareSystem
  sql_lineage.py       Automatic SQL -> Lineage extraction (sqlglot)
tests/                  pytest unit tests for all of the above
examples/
  agent_demo/            End-to-end SQLite walkthrough
  sql_lineage_demo.py     SQL lineage extraction examples
paper/                  JOSS software paper (paper.md, paper.bib)
```

## Testing

```bash
pip install -e ".[dev]"
pytest
```

## Relationship to the research paper

The formal safety guarantee (zero column-level leakage under complete
lineage reporting), the TPC-H/synthetic-schema experiments, the fuzzy
conflict-detection study, and the statistical analysis are all in the
[research repository](https://github.com/sangaraju1988/Lineage-Aware-Memory),
which depends on this package for its core mechanism. This split exists so
the software can be installed, tested, and reused independently of the
experiment/reproduction code.

## Citation

See `CITATION.cff`, or cite the paper directly:

```bibtex
@article{sangaraju2026lineage,
  author  = {Venkata Sangaraju and Sudhir Vissa},
  title   = {Lineage-Aware Memory Governance: A Derivation-Gated Framework
             for Privacy-Preserving Column-Level Access Control in
             Enterprise AI Agents},
  journal = {IEEE Access},
  year    = {2026},
  doi     = {10.1109/ACCESS.2026.3730363}
}
```

To cite this software specifically (e.g. a particular version you built on):

```bibtex
@software{sangaraju2026amu,
  author  = {Venkata Sangaraju and Sudhir Vissa},
  title   = {amu-governance: Lineage-Gated Shared Memory for Multi-Agent Analytics},
  year    = {2026},
  url     = {https://github.com/sangaraju1988/amu-governance},
  doi     = {10.5281/zenodo.21302744}
}
```

## License

MIT — see `LICENSE`.
