---
title: 'amu-governance: Lineage-Gated Shared Memory for Multi-Agent Analytics'
tags:
  - python
  - artificial intelligence
  - ai agents
  - data governance
  - data lineage
  - multi-agent systems
  - privacy
authors:
  - name: Venkata Sangaraju
    orcid: 0009-0001-7716-1342
    affiliation: 1
  - name: Sudhir Vissa
    orcid: 0009-0003-7865-0863
    affiliation: 2
affiliations:
  - name: Independent Researcher
    index: 1
  - name: SAGE7 AI, Georgetown, Texas, USA
    index: 2
date: 11 July 2026
bibliography: paper.bib
---

# Summary

`amu-governance` is a small Python library that implements lineage-gated
shared memory for teams of AI agents that read from a common analytical
data store. Its central abstraction is the Analytical Memory Unit (AMU): a
cached result — a metric, a segment, an aggregate — tagged with the full
derivation path that produced it, meaning every table and column it was
computed from, plus the filter and aggregation logic applied. Retrieval
from shared memory is gated on that derivation path rather than on static
content labels: an agent may only receive a cached AMU if every column
touched in its derivation is one the agent's department or role is
permitted to see. When no eligible cached result exists, the system falls
back to a fresh, in-scope computation instead of serving a result the
requester should not see. The library also detects a second failure mode
of shared analytical memory: silent metric-definition conflicts, where two
teams compute a metric of the same name through different derivations. A
SHA-256 hash over the tables, columns, and filter logic of each AMU's
lineage flags a conflict the moment a second department writes a
differently-derived value under an existing metric name.

The package ships three interchangeable retrieval strategies —
`NoMemorySystem`, `NaiveMemorySystem`, and `LineageAwareSystem` — sharing
one `GovernancePolicy` interface, so they can be swapped and benchmarked
against identical data and permissions. Sensitivity tagging and department
permissions are supplied entirely through `GovernancePolicy`, so the same
model and system classes apply to any schema without subclassing. A
companion module, `sql_lineage`, uses `sqlglot` [@sqlglot2023] to extract
lineage automatically from executed SQL, removing any dependence on an
agent correctly self-reporting which columns it accessed.

# Statement of need

Enterprises are increasingly deploying AI agents that share a common
memory layer for analytical reuse — caching KPIs, segments, and query
results so that redundant computation across teams is avoided. Several
recent systems address memory management or access control for agent
memory in isolation: MemGPT [@packer2023memgpt] and Zep
[@rasmussen2025zep] manage memory persistence and retrieval; A-MEM
[@xu2025amem] and SSGM [@lam2026ssgm] add structured organization and
lifecycle governance; and production systems such as Oracle AI Agent
Memory [@oracle2026memory] and the Governed Memory architecture
[@taheri2026governed] gate memory access using content or access-control
tags attached to a stored item. None of these gate retrieval on *how* a
cached result was derived. A tag-based gate can be satisfied by an AMU
whose label looks permissible while its underlying derivation touched a
column the requester is not authorized to see — for example, a
"high-value customer count" that was computed by joining against a
restricted income column, cached under a generic metric name a less
privileged agent is allowed to query. Content-level governance cannot
detect this; only inspecting the derivation path can.

`amu-governance` provides a minimal, dependency-light, and independently
testable implementation of that derivation-gated mechanism, decoupled from
any specific schema or agent framework. It targets two audiences:
researchers building on or comparing against lineage-based memory
governance, for whom the three interchangeable systems and shared
`GovernancePolicy` interface offer a controlled way to benchmark
governance strategies on identical workloads; and practitioners
integrating memory sharing into a multi-agent analytics deployment, who
need a governance layer that composes with an existing schema and
department/role permission model without rewriting their data model. The
`sql_lineage` module additionally lets adopters derive lineage
automatically from real, executed SQL — including joins, subqueries, CTEs,
and aliased tables — rather than depending on agents to self-report
provenance, which prior lineage-extraction work such as LINEAGEX
[@zhang2025lineagex] and the broader provenance literature
[@moreau2011prov] has shown is unreliable when left to manual annotation.

This package is the reference implementation accompanying a research paper
that formally proves a zero-leakage guarantee for the mechanism under
complete lineage reporting, and evaluates it on a synthetic multi-department
schema and a TPC-H-derived schema [@tpch2021] against 30-seed simulation
sweeps [@sangaraju2026lineage]. That paper, and the full experiment,
benchmark, and figure-reproduction suite, live in a companion research
repository; this repository contains only the governance mechanism itself,
packaged, tested, and documented for independent reuse.

# Acknowledgements

We thank the maintainers of `sqlglot` [@sqlglot2023], whose SQL parsing
made automatic lineage extraction practical.

# References
